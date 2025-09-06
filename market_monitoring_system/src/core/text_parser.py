"""
Text parser for market monitoring system.
Extracts structured data from OCR text using regex patterns.
"""

import logging
import re
from typing import List, Dict, Optional, Tuple, Any, Pattern
from dataclasses import dataclass, field
from datetime import datetime
import json

from .database_manager import ItemData


@dataclass
class ParsingPattern:
    """Configuration for a parsing pattern."""
    name: str
    pattern: str
    description: str
    fields: List[str]  # Expected captured groups
    priority: int = 1  # Higher priority patterns are tried first
    enabled: bool = True


@dataclass
class ParsingResult:
    """Result of text parsing operation."""
    items: List[ItemData] = field(default_factory=list)
    raw_matches: List[Dict[str, Any]] = field(default_factory=list)
    parsing_stats: Dict[str, int] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    hotkey: str = ""
    screenshot_type: str = "individual_seller_items"
    processing_type: str = "full"  # NEW FIELD: 'full' or 'minimal'


class TextParsingError(Exception):
    """Exception raised for text parsing errors."""
    pass


class TextParser:
    """
    Extracts structured data from OCR text using configurable regex patterns.
    Supports different parsing strategies for different hotkey contexts.
    """
    
    def __init__(self):
        """Initialize text parser with default patterns."""
        self.logger = logging.getLogger(__name__)
        
        # Compiled regex patterns for performance
        self._compiled_patterns: Dict[str, List[Tuple[Pattern, ParsingPattern]]] = {}
        
        # Parsing statistics
        self._parsing_stats = {
            'total_texts_processed': 0,
            'successful_parses': 0,
            'failed_parses': 0,
            'total_items_extracted': 0,
            'pattern_usage': {},
            'last_parsing_time': None
        }
        
        # Initialize default patterns
        self._initialize_default_patterns()
    
    # ========== Helper Functions from Existing Scripts ==========
    
    def _clean_item_name_broker(self, item_text: str) -> str:
        """Clean item name from OCR artifacts (from extract_broker_sellers.py)"""
        # Remove colons, numbers, and special characters at the end
        cleaned = re.sub(r'[:#\d\s]+$', '', item_text)
        return cleaned.strip()
    
    def _clean_item_name_trade(self, item_text: str) -> str:
        """Remove parentheses and numbers from item name (from extract_trade_data.py)"""
        # Remove content in parentheses like (111), (10), etc.
        cleaned = re.sub(r'\s*\(\d+\)', '', item_text)
        return cleaned.strip()
    
    def _clean_price(self, price_text: str) -> str:
        """Extract and clean price from 'Unit Price : 8,888 Adena' format"""
        # Extract numbers and remove commas
        numbers = re.findall(r'[\d,]+', price_text)
        if numbers:
            return numbers[0].replace(',', '')
        return ''
    
    def _is_ocr_artifact(self, line: str) -> bool:
        """Check if line is OCR artifact to skip (from extract_broker_sellers.py)"""
        line = line.strip()
        # Skip lines like ": 13", ": 24", "#", ": 27"
        if re.match(r'^[:#\d\s&|]+$', line):
            return True
        # Skip "Currency", "Qty." headers
        if line in ['Currency', 'Qty.', 'Name']:
            return True
        return False
    
    def _extract_broker_data(self, text_content: str, hotkey: str) -> List[ItemData]:
        """
        Extract seller-item pairs from broker OCR text (minimal processing).
        Based on extract_broker_sellers.py logic.
        """
        items = []
        extraction_log = []
        
        try:
            # Split by "Item Broke" to get individual sections
            sections = text_content.split('Item Broke')
            
            for i, section in enumerate(sections):
                if not section.strip():
                    continue
                    
                try:
                    lines = [line.strip() for line in section.split('\n') if line.strip()]
                    
                    if not lines:
                        continue
                    
                    # Extract item name (first clean line)
                    item_name = ''
                    for line in lines:
                        if not self._is_ocr_artifact(line):
                            item_name = self._clean_item_name_broker(line)
                            if item_name:
                                break
                    
                    if not item_name:
                        continue
                    
                    # Find "Name" line and collect sellers after it
                    name_found = False
                    sellers = []
                    
                    for j, line in enumerate(lines):
                        if line == 'Name':
                            name_found = True
                            # Collect all sellers after "Name"
                            for seller_line in lines[j+1:]:
                                if not self._is_ocr_artifact(seller_line) and seller_line.strip():
                                    sellers.append(seller_line.strip())
                            break
                    
                    if not name_found or not sellers:
                        continue
                    
                    # Create ItemData objects for each seller-item pair
                    for seller in sellers:
                        item_data = ItemData(
                            seller_name=seller,
                            item_name=item_name,
                            price=None,  # No price in minimal processing
                            quantity=None,  # No quantity in minimal processing
                            item_id=None,
                            hotkey=hotkey,
                            processing_type="minimal"
                        )
                        items.append(item_data)
                        
                except Exception as e:
                    self.logger.warning(f"Error processing broker section {i}: {e}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"Failed to extract broker data: {e}")
        
        self.logger.info(f"Extracted {len(items)} broker seller-item pairs")
        return items
    
    def _extract_trade_data(self, text_content: str, hotkey: str) -> List[ItemData]:
        """
        Extract trade data with full details (seller, item, price, quantity).
        Based on extract_trade_data.py logic.
        """
        items = []
        
        try:
            # Split by "Trade" to get individual instances
            sections = text_content.split('Trade')
            
            for i, section in enumerate(sections):
                if not section.strip():
                    continue
                    
                try:
                    lines = [line.strip() for line in section.split('\n') if line.strip()]
                    
                    seller = ''
                    item_name = ''
                    unit_price = ''
                    quantity = ''
                    
                    # Extract seller from "Items to Sell SellerName" pattern
                    for line in lines:
                        if 'Items to Sell' in line:
                            seller_match = re.search(r'Items to Sell\\s+(.+)', line)
                            if seller_match:
                                seller = seller_match.group(1).strip()
                                break
                    
                    # Find Unit Price and preceding line for item name
                    unit_price_index = -1
                    for j, line in enumerate(lines):
                        if 'Unit Price' in line:
                            unit_price_index = j
                            # Extract price
                            unit_price = self._clean_price(line)
                            
                            # Item name should be in the line before Unit Price
                            if j > 0:
                                item_name = self._clean_item_name_trade(lines[j-1])
                            break
                    
                    # Extract quantity
                    for line in lines:
                        if line.startswith('Quantity :'):
                            quantity_match = re.search(r'Quantity\\s*:\\s*(\\d+)', line)
                            if quantity_match:
                                quantity = quantity_match.group(1)
                                break
                    
                    # Only add if we have all required fields
                    if seller and item_name and unit_price and quantity:
                        try:
                            price_float = float(unit_price) if unit_price else None
                            quantity_int = int(quantity) if quantity else None
                            
                            item_data = ItemData(
                                seller_name=seller,
                                item_name=item_name,
                                price=price_float,
                                quantity=quantity_int,
                                item_id=None,
                                hotkey=hotkey,
                                processing_type="full"
                            )
                            items.append(item_data)
                            
                        except (ValueError, TypeError) as e:
                            self.logger.warning(f"Failed to convert price/quantity for trade data: {e}")
                            continue
                            
                except Exception as e:
                    self.logger.warning(f"Error processing trade section {i}: {e}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"Failed to extract trade data: {e}")
        
        self.logger.info(f"Extracted {len(items)} trade entries")
        return items
    
    def _initialize_default_patterns(self) -> None:
        """Initialize default parsing patterns for different contexts."""
        
        # Patterns for F1 (main products page)
        f1_patterns = [
            ParsingPattern(
                name="seller_item_price_quantity",
                pattern=r'([A-Za-zА-Яа-я0-9_]+)\s+([A-Za-zА-Яа-я0-9\s\-\.]+?)\s+(\d+(?:\.\d{1,2})?)\s+(\d+)',
                description="Seller, item name, price, quantity in sequence",
                fields=['seller_name', 'item_name', 'price', 'quantity'],
                priority=3
            ),
            ParsingPattern(
                name="item_with_price",
                pattern=r'([A-Za-zА-Яа-я0-9\s\-\.]+?)\s+(?:Цена|Price|₽|руб)\s*:?\s*(\d+(?:\.\d{1,2})?)',
                description="Item name followed by price",
                fields=['item_name', 'price'],
                priority=2
            ),
            ParsingPattern(
                name="price_quantity_pair",
                pattern=r'(?:Цена|Price)\s*:?\s*(\d+(?:\.\d{1,2})?)\s+(?:Кол-во|Qty|количество)\s*:?\s*(\d+)',
                description="Price and quantity pair",
                fields=['price', 'quantity'],
                priority=2
            ),
            ParsingPattern(
                name="seller_context",
                pattern=r'(?:Продавец|Seller|Магазин)\s*:?\s*([A-Za-zА-Яа-я0-9_\-]+)',
                description="Seller name identification",
                fields=['seller_name'],
                priority=1
            )
        ]
        
        # Patterns for F2 (sellers page)
        f2_patterns = [
            ParsingPattern(
                name="seller_item_detailed",
                pattern=r'([A-Za-zА-Яа-я0-9_]+)\s*:\s*([A-Za-zА-Яа-я0-9\s\-\.]+?)\s*(?:\||\-)\s*(\d+(?:\.\d{1,2})?)\s*(?:\||\-)\s*(\d+)',
                description="Detailed seller:item format with separators",
                fields=['seller_name', 'item_name', 'price', 'quantity'],
                priority=3
            ),
            ParsingPattern(
                name="seller_inventory",
                pattern=r'([A-Za-zА-Яа-я0-9_]+)\s+(?:has|есть|продает)\s+(\d+)\s+([A-Za-zА-Яа-я0-9\s\-\.]+)',
                description="Seller has quantity item format",
                fields=['seller_name', 'quantity', 'item_name'],
                priority=2
            ),
            ParsingPattern(
                name="marketplace_listing",
                pattern=r'(\w+)\s+([A-Za-zА-Яа-я0-9\s\-\.]+?)\s+(?:за|for)\s+(\d+(?:\.\d{1,2})?)',
                description="Seller item for price format",
                fields=['seller_name', 'item_name', 'price'],
                priority=2
            )
        ]
        
        # General patterns for any hotkey
        general_patterns = [
            ParsingPattern(
                name="item_id_pattern",
                pattern=r'(?:ID|id|артикул)\s*:?\s*([A-Za-z0-9\-_]+)',
                description="Item ID extraction",
                fields=['item_id'],
                priority=1
            ),
            ParsingPattern(
                name="numeric_sequence",
                pattern=r'(\d+(?:\.\d{1,2})?)\s+(\d+)\s*(?:шт|pcs|штук)?',
                description="Price quantity numeric sequence",
                fields=['price', 'quantity'],
                priority=1
            ),
            ParsingPattern(
                name="currency_price",
                pattern=r'(\d+(?:\.\d{1,2})?)\s*(?:₽|руб|рублей|RUB)',
                description="Price with currency",
                fields=['price'],
                priority=1
            )
        ]
        
        # Store patterns by hotkey
        self._patterns = {
            'F1': f1_patterns,
            'F2': f2_patterns,
            'general': general_patterns
        }
        
        # Compile patterns for performance
        self._compile_patterns()
    
    def _compile_patterns(self) -> None:
        """Compile regex patterns for better performance."""
        self._compiled_patterns = {}
        
        for hotkey, patterns in self._patterns.items():
            compiled_list = []
            for pattern_config in patterns:
                if pattern_config.enabled:
                    try:
                        compiled_regex = re.compile(
                            pattern_config.pattern, 
                            re.IGNORECASE | re.MULTILINE
                        )
                        compiled_list.append((compiled_regex, pattern_config))
                    except re.error as e:
                        self.logger.error(f"Invalid regex pattern '{pattern_config.name}': {e}")
            
            # Sort by priority (higher priority first)
            compiled_list.sort(key=lambda x: x[1].priority, reverse=True)
            self._compiled_patterns[hotkey] = compiled_list
        
        self.logger.info(f"Compiled {sum(len(p) for p in self._compiled_patterns.values())} parsing patterns")
    
    def parse_items_data(self, text: str, hotkey: str, screenshot_type: str = "individual_seller_items", 
                        processing_type: str = "full") -> ParsingResult:
        """
        Parse OCR text to extract item data with support for different processing types.
        
        Args:
            text: OCR text to parse
            hotkey: Context hotkey (F1, F2, etc.)
            screenshot_type: Type of screenshot (individual_seller_items or item_overview)
            processing_type: 'full' for complete data extraction, 'minimal' for seller-item pairs only
            
        Returns:
            ParsingResult with extracted items and metadata
        """
        start_time = datetime.now()
        result = ParsingResult(hotkey=hotkey, screenshot_type=screenshot_type, processing_type=processing_type)
        
        try:
            if not text or not text.strip():
                result.errors.append("Empty or whitespace-only text provided")
                return result
            
            self.logger.debug(f"Parsing text for hotkey {hotkey} with {processing_type} processing: {len(text)} characters")
            
            # Choose extraction method based on processing type
            items = []
            if processing_type == "minimal":
                # Use broker data extraction (minimal processing)
                items = self._extract_broker_data(text, hotkey)
                self.logger.info(f"Using minimal processing (broker data) for {hotkey}")
            elif processing_type == "full":
                # Use trade data extraction (full processing)
                items = self._extract_trade_data(text, hotkey)
                self.logger.info(f"Using full processing (trade data) for {hotkey}")
                
                # Fallback to regex patterns if no trade data found
                if not items:
                    self.logger.info(f"No trade data found, falling back to regex patterns for {hotkey}")
                    items = self._extract_with_regex_patterns(text, hotkey)
            else:
                result.errors.append(f"Unknown processing type: {processing_type}")
                return result
            
            # Set processing_type on all items
            for item in items:
                item.processing_type = processing_type
            
            result.items = items
            
            # Update statistics
            result.parsing_stats = {
                'items_extracted': len(items),
                'processing_time_ms': int((datetime.now() - start_time).total_seconds() * 1000),
                'text_length': len(text),
                'processing_type': processing_type,
                'extraction_method': 'broker_data' if processing_type == 'minimal' else 'trade_data'
            }
            
            # Update global statistics
            self._update_parsing_stats(result)
            
            self.logger.info(
                f"Parsed {hotkey} text ({processing_type}): {len(items)} items "
                f"in {result.parsing_stats['processing_time_ms']}ms"
            )
            
            return result
            
        except Exception as e:
            result.errors.append(f"Parsing failed: {str(e)}")
            self.logger.error(f"Text parsing failed for {hotkey} ({processing_type}): {e}")
            self._parsing_stats['failed_parses'] += 1
            return result
        finally:
            self._parsing_stats['total_texts_processed'] += 1
            self._parsing_stats['last_parsing_time'] = datetime.now().isoformat()
    
    def _extract_with_regex_patterns(self, text: str, hotkey: str) -> List[ItemData]:
        """
        Fallback extraction using the original regex pattern method.
        Used when trade data extraction doesn't find any results.
        """
        try:
            # Clean and normalize text
            cleaned_text = self._clean_text(text)
            
            # Get patterns for this hotkey and general patterns
            patterns_to_use = []
            if hotkey in self._compiled_patterns:
                patterns_to_use.extend(self._compiled_patterns[hotkey])
            patterns_to_use.extend(self._compiled_patterns.get('general', []))
            
            if not patterns_to_use:
                return []
            
            # Extract raw matches using all patterns
            raw_matches = self._extract_raw_matches(cleaned_text, patterns_to_use)
            
            # Convert matches to ItemData objects
            items = self._convert_matches_to_items(raw_matches, hotkey)
            
            # Validate extracted items
            validated_items = self._validate_parsed_data(items)
            
            return validated_items
            
        except Exception as e:
            self.logger.error(f"Regex pattern extraction failed: {e}")
            return []
    
    def _clean_text(self, text: str) -> str:
        """
        Clean and normalize text for better parsing.
        
        Args:
            text: Raw text to clean
            
        Returns:
            Cleaned text
        """
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove non-printable characters except newlines
        text = re.sub(r'[^\x20-\x7E\n\u0400-\u04FF]', '', text)
        
        # Normalize currency symbols
        text = text.replace('₽', 'руб').replace('RUR', 'руб')
        
        # Normalize quantity indicators
        text = re.sub(r'шт\.?|штук|pieces|pcs', 'шт', text, flags=re.IGNORECASE)
        
        return text.strip()
    
    def _extract_raw_matches(self, text: str, 
                           patterns: List[Tuple[Pattern, ParsingPattern]]) -> List[Dict[str, Any]]:
        """
        Extract raw matches using all provided patterns.
        
        Args:
            text: Text to search
            patterns: List of compiled patterns
            
        Returns:
            List of raw match dictionaries
        """
        matches = []
        
        for compiled_pattern, pattern_config in patterns:
            try:
                for match in compiled_pattern.finditer(text):
                    match_data = {
                        'pattern_name': pattern_config.name,
                        'pattern_description': pattern_config.description,
                        'match_text': match.group(0),
                        'match_start': match.start(),
                        'match_end': match.end(),
                        'groups': list(match.groups()),
                        'fields': pattern_config.fields,
                        'priority': pattern_config.priority
                    }
                    
                    # Map groups to field names
                    for i, field_name in enumerate(pattern_config.fields):
                        if i < len(match.groups()):
                            match_data[field_name] = match.group(i + 1)
                    
                    matches.append(match_data)
                    
                    # Update pattern usage statistics
                    pattern_name = pattern_config.name
                    if pattern_name not in self._parsing_stats['pattern_usage']:
                        self._parsing_stats['pattern_usage'][pattern_name] = 0
                    self._parsing_stats['pattern_usage'][pattern_name] += 1
                    
            except Exception as e:
                self.logger.warning(f"Pattern '{pattern_config.name}' failed: {e}")
                continue
        
        # Sort by priority and position
        matches.sort(key=lambda x: (-x['priority'], x['match_start']))
        
        return matches
    
    def _convert_matches_to_items(self, raw_matches: List[Dict[str, Any]], 
                                hotkey: str) -> List[ItemData]:
        """
        Convert raw matches to ItemData objects.
        
        Args:
            raw_matches: Raw pattern matches
            hotkey: Context hotkey
            
        Returns:
            List of ItemData objects
        """
        items = []
        
        # Group matches by context (position proximity)
        match_groups = self._group_matches_by_context(raw_matches)
        
        for match_group in match_groups:
            try:
                item = self._merge_matches_to_item(match_group, hotkey)
                if item:
                    items.append(item)
            except Exception as e:
                self.logger.warning(f"Failed to convert match group to item: {e}")
                continue
        
        return items
    
    def _group_matches_by_context(self, matches: List[Dict[str, Any]], 
                                proximity_threshold: int = 50) -> List[List[Dict[str, Any]]]:
        """
        Group matches that are likely related by position proximity.
        
        Args:
            matches: List of matches to group
            proximity_threshold: Maximum character distance for grouping
            
        Returns:
            List of match groups
        """
        if not matches:
            return []
        
        groups = []
        current_group = [matches[0]]
        
        for i in range(1, len(matches)):
            current_match = matches[i]
            last_match = current_group[-1]
            
            # Check if matches are close enough to be related
            distance = current_match['match_start'] - last_match['match_end']
            
            if distance <= proximity_threshold:
                current_group.append(current_match)
            else:
                groups.append(current_group)
                current_group = [current_match]
        
        if current_group:
            groups.append(current_group)
        
        return groups
    
    def _merge_matches_to_item(self, match_group: List[Dict[str, Any]], 
                             hotkey: str) -> Optional[ItemData]:
        """
        Merge a group of matches into a single ItemData object.
        
        Args:
            match_group: Group of related matches
            hotkey: Context hotkey
            
        Returns:
            ItemData object or None if insufficient data
        """
        # Collect all field data
        field_data = {}
        
        for match in match_group:
            for field_name in ['seller_name', 'item_name', 'price', 'quantity', 'item_id']:
                if field_name in match and match[field_name]:
                    # Prefer higher priority matches
                    if (field_name not in field_data or 
                        match['priority'] > field_data.get(f'{field_name}_priority', 0)):
                        field_data[field_name] = match[field_name].strip()
                        field_data[f'{field_name}_priority'] = match['priority']
        
        # Apply smart defaults and cleaning
        seller_name = field_data.get('seller_name', 'Unknown')
        item_name = field_data.get('item_name', 'Unknown')
        
        # Parse numeric fields
        price = None
        quantity = None
        
        if 'price' in field_data:
            try:
                price = float(field_data['price'])
            except (ValueError, TypeError):
                pass
        
        if 'quantity' in field_data:
            try:
                quantity = int(field_data['quantity'])
            except (ValueError, TypeError):
                pass
        
        # Validate minimum required data
        if seller_name == 'Unknown' and item_name == 'Unknown':
            return None
        
        return ItemData(
            seller_name=seller_name,
            item_name=item_name,
            price=price,
            quantity=quantity,
            item_id=field_data.get('item_id'),
            hotkey=hotkey
        )
    
    def extract_seller_info(self, text_block: str) -> Optional[str]:
        """
        Extract seller information from text block.
        
        Args:
            text_block: Text to search for seller info
            
        Returns:
            Seller name or None if not found
        """
        seller_patterns = [
            r'(?:Продавец|Seller|Shop|Магазин)\s*:?\s*([A-Za-zА-Яа-я0-9_\-]+)',
            r'([A-Za-zА-Яа-я0-9_\-]+)\s+(?:продает|sells|offers)',
            r'(?:From|От)\s+([A-Za-zА-Яа-я0-9_\-]+)'
        ]
        
        for pattern in seller_patterns:
            match = re.search(pattern, text_block, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def extract_item_details(self, text_block: str) -> Dict[str, Any]:
        """
        Extract item details from text block.
        
        Args:
            text_block: Text to search
            
        Returns:
            Dictionary with item details
        """
        details = {}
        
        # Price extraction
        price_patterns = [
            r'(\d+(?:\.\d{1,2})?)\s*(?:₽|руб|рублей|RUB)',
            r'(?:Price|Цена)\s*:?\s*(\d+(?:\.\d{1,2})?)',
        ]
        
        for pattern in price_patterns:
            match = re.search(pattern, text_block, re.IGNORECASE)
            if match:
                try:
                    details['price'] = float(match.group(1))
                    break
                except ValueError:
                    continue
        
        # Quantity extraction
        quantity_patterns = [
            r'(\d+)\s*(?:шт|штук|pcs|pieces)',
            r'(?:Количество|Quantity|Qty)\s*:?\s*(\d+)',
            r'(?:В наличии|Available)\s*:?\s*(\d+)'
        ]
        
        for pattern in quantity_patterns:
            match = re.search(pattern, text_block, re.IGNORECASE)
            if match:
                try:
                    details['quantity'] = int(match.group(1))
                    break
                except ValueError:
                    continue
        
        return details
    
    def _validate_parsed_data(self, items: List[ItemData]) -> List[ItemData]:
        """
        Validate parsed item data and remove invalid entries.
        
        Args:
            items: List of ItemData objects to validate
            
        Returns:
            List of valid ItemData objects
        """
        valid_items = []
        
        for item in items:
            validation_errors = []
            
            # Validate seller name
            if not item.seller_name or len(item.seller_name.strip()) == 0:
                validation_errors.append("Empty seller name")
            elif len(item.seller_name) > 100:
                validation_errors.append("Seller name too long")
            
            # Validate item name
            if not item.item_name or len(item.item_name.strip()) == 0:
                validation_errors.append("Empty item name")
            elif len(item.item_name) > 200:
                validation_errors.append("Item name too long")
            
            # Validate price
            if item.price is not None:
                if item.price < 0:
                    validation_errors.append("Negative price")
                elif item.price > 1000000:  # 1M limit
                    validation_errors.append("Price too high")
            
            # Validate quantity
            if item.quantity is not None:
                if item.quantity < 0:
                    validation_errors.append("Negative quantity")
                elif item.quantity > 999999:  # 1M limit
                    validation_errors.append("Quantity too high")
            
            # Skip items with validation errors
            if validation_errors:
                self.logger.warning(
                    f"Validation failed for item {item.seller_name}/{item.item_name}: "
                    f"{', '.join(validation_errors)}"
                )
                continue
            
            valid_items.append(item)
        
        return valid_items
    
    def detect_parsing_patterns(self, text: str) -> List[str]:
        """
        Detect which patterns would match in the text.
        
        Args:
            text: Text to analyze
            
        Returns:
            List of pattern names that would match
        """
        matching_patterns = []
        
        for hotkey, patterns in self._compiled_patterns.items():
            for compiled_pattern, pattern_config in patterns:
                if compiled_pattern.search(text):
                    matching_patterns.append(f"{hotkey}:{pattern_config.name}")
        
        return matching_patterns
    
    def _update_parsing_stats(self, result: ParsingResult) -> None:
        """Update global parsing statistics."""
        if result.items:
            self._parsing_stats['successful_parses'] += 1
            self._parsing_stats['total_items_extracted'] += len(result.items)
        else:
            self._parsing_stats['failed_parses'] += 1
    
    def get_parsing_statistics(self) -> Dict[str, Any]:
        """
        Get parsing statistics.
        
        Returns:
            Dictionary with parsing statistics
        """
        stats = self._parsing_stats.copy()
        
        # Calculate success rate
        total_attempts = stats['successful_parses'] + stats['failed_parses']
        if total_attempts > 0:
            stats['success_rate'] = stats['successful_parses'] / total_attempts
        else:
            stats['success_rate'] = 0.0
        
        # Add pattern information
        stats['total_patterns'] = sum(len(p) for p in self._compiled_patterns.values())
        stats['patterns_by_hotkey'] = {
            hotkey: len(patterns) 
            for hotkey, patterns in self._compiled_patterns.items()
        }
        
        return stats
    
    def add_custom_pattern(self, hotkey: str, pattern: ParsingPattern) -> bool:
        """
        Add a custom parsing pattern.
        
        Args:
            hotkey: Hotkey context for the pattern
            pattern: Pattern configuration to add
            
        Returns:
            True if pattern was added successfully
        """
        try:
            # Validate pattern
            re.compile(pattern.pattern)
            
            # Add to patterns
            if hotkey not in self._patterns:
                self._patterns[hotkey] = []
            
            self._patterns[hotkey].append(pattern)
            
            # Recompile patterns
            self._compile_patterns()
            
            self.logger.info(f"Added custom pattern '{pattern.name}' for hotkey {hotkey}")
            return True
            
        except re.error as e:
            self.logger.error(f"Invalid custom pattern '{pattern.name}': {e}")
            return False
        except Exception as e:
            self.logger.error(f"Failed to add custom pattern: {e}")
            return False