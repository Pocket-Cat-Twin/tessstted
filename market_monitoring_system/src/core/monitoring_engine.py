"""
Monitoring engine for market monitoring system.
Handles change detection, status management, and queue operations.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Set, Any
from dataclasses import dataclass
import time

from .database_manager import DatabaseManager, ItemData, ChangeLogEntry
from .text_parser import ParsingResult
from config.settings import SettingsManager, MonitoringConfig


@dataclass
class StatusTransition:
    """Represents a status transition event."""
    seller_name: str
    item_name: str
    old_status: str
    new_status: str
    timestamp: datetime
    reason: str


@dataclass
class ChangeDetection:
    """Result of change detection operation."""
    detected_changes: List[ChangeLogEntry]
    new_combinations: List[Tuple[str, str]]  # (seller, item) pairs
    removed_combinations: List[Tuple[str, str]]
    status_transitions: List[StatusTransition]


class MonitoringEngineError(Exception):
    """Exception raised for monitoring engine errors."""
    pass


class MonitoringEngine:
    """
    Core monitoring engine for managing item status lifecycle and change detection.
    Handles the NEW → CHECKED → UNCHECKED status flow and queue management.
    """
    
    # Status constants
    STATUS_NEW = 'NEW'
    STATUS_CHECKED = 'CHECKED'
    STATUS_UNCHECKED = 'UNCHECKED'
    STATUS_GONE = 'GONE'  # NEW STATUS for disappeared items with prices
    
    # Valid status transitions
    VALID_TRANSITIONS = {
        STATUS_NEW: [STATUS_CHECKED],
        STATUS_CHECKED: [STATUS_UNCHECKED, STATUS_GONE],
        STATUS_UNCHECKED: [STATUS_CHECKED, STATUS_GONE],
        STATUS_GONE: []  # Terminal status
    }
    
    def __init__(self, database_manager: DatabaseManager, settings_manager: SettingsManager):
        """
        Initialize monitoring engine.
        
        Args:
            database_manager: Database manager instance
            settings_manager: Settings manager instance
        """
        self.db = database_manager
        self.settings = settings_manager
        self.config: MonitoringConfig = settings_manager.monitoring
        self.logger = logging.getLogger(__name__)
        
        # Engine state
        self._last_status_check = None
        self._last_cleanup = None
        
        # Statistics
        self._stats = {
            'total_status_checks': 0,
            'total_transitions': 0,
            'total_changes_detected': 0,
            'total_combinations_processed': 0,
            'last_processing_time': None,
            'average_processing_time': 0.0,
            'status_distribution': {},
            'change_type_counts': {}
        }
    
    def process_parsing_results(self, parsing_results: List[ParsingResult]) -> ChangeDetection:
        """
        Process parsing results with support for different processing types.
        
        Args:
            parsing_results: List of parsing results from OCR processing
            
        Returns:
            ChangeDetection object with detected changes and transitions
        """
        start_time = time.time()
        
        try:
            # Separate items by processing type
            full_processing_items = []
            minimal_processing_items = []
            
            for result in parsing_results:
                if result.processing_type == "minimal":
                    minimal_processing_items.extend(result.items)
                else:
                    full_processing_items.extend(result.items)
            
            all_items = full_processing_items + minimal_processing_items
            
            if not all_items:
                self.logger.info("No items to process in parsing results")
                return ChangeDetection([], [], [], [])
            
            self.logger.info(
                f"Processing {len(all_items)} items: "
                f"{len(full_processing_items)} full processing, "
                f"{len(minimal_processing_items)} minimal processing"
            )
            
            # Process full processing items with existing logic
            full_changes = []
            full_new_combinations = set()
            full_removed_combinations = set()
            
            if full_processing_items:
                self.logger.info(f"Processing {len(full_processing_items)} full processing items")
                
                # Save all full processing items to history
                self.db.save_items_data(full_processing_items)
                
                # Detect changes for full processing items
                full_changes = self.db.detect_and_log_changes(full_processing_items)
                
                # Update seller current status for full processing items
                self._update_sellers_current_status(full_processing_items)
                
                # Update monitoring queue for full processing items
                self._update_monitoring_queue(full_processing_items)
                
                # Find new and removed combinations for full processing
                current_full_combinations = {(item.seller_name, item.item_name) for item in full_processing_items}
                full_new_combinations, full_removed_combinations = self._detect_combination_changes(current_full_combinations, "full")
            
            # Process minimal processing items with new logic
            minimal_changes = []
            minimal_new_combinations = set()
            minimal_removed_combinations = set()
            
            if minimal_processing_items:
                self.logger.info(f"Processing {len(minimal_processing_items)} minimal processing items")
                minimal_changes, minimal_new_combinations, minimal_removed_combinations = self._process_minimal_processing_items(minimal_processing_items)
            
            # Combine results
            all_changes = full_changes + minimal_changes
            all_new_combinations = full_new_combinations.union(minimal_new_combinations)
            all_removed_combinations = full_removed_combinations.union(minimal_removed_combinations)
            
            # Process status transitions if needed
            status_transitions = []
            if self._should_process_status_transitions():
                status_transitions = self.process_status_transitions()
            
            # Create result
            detection_result = ChangeDetection(
                detected_changes=all_changes,
                new_combinations=list(all_new_combinations),
                removed_combinations=list(all_removed_combinations),
                status_transitions=status_transitions
            )
            
            # Update statistics
            processing_time = time.time() - start_time
            self._update_processing_stats(detection_result, processing_time)
            
            self.logger.info(
                f"Processing completed: {len(all_changes)} changes, "
                f"{len(all_new_combinations)} new combinations, "
                f"{len(all_removed_combinations)} removed combinations, "
                f"{len(status_transitions)} status transitions "
                f"in {processing_time:.3f}s"
            )
            
            return detection_result
            
        except Exception as e:
            self.logger.error(f"Failed to process parsing results: {e}")
            raise MonitoringEngineError(f"Processing failed: {e}")
    
    def _update_sellers_current_status(self, items: List[ItemData]) -> None:
        """
        Update sellers_current table with latest item data.
        
        Args:
            items: List of current items
        """
        try:
            for item in items:
                success = self.db.update_sellers_status(
                    seller_name=item.seller_name,
                    item_name=item.item_name,
                    quantity=item.quantity,
                    status=self.STATUS_NEW,  # New items start as NEW
                    processing_type=item.processing_type
                )
                
                if not success:
                    self.logger.warning(
                        f"Failed to update seller status for {item.seller_name}/{item.item_name} ({item.processing_type})"
                    )
            
        except Exception as e:
            self.logger.error(f"Failed to update sellers current status: {e}")
    
    def _process_minimal_processing_items(self, items: List[ItemData]) -> Tuple[List[ChangeLogEntry], set, set]:
        """
        Process minimal processing items with seller-item combination logic.
        
        Logic:
        1. New combination appears → add with status NEW
        2. Combination disappears with price → status GONE, log sale
        3. Combination disappears without price → remove from queue
        
        Args:
            items: List of minimal processing items
            
        Returns:
            Tuple of (changes, new_combinations, removed_combinations)
        """
        changes = []
        
        try:
            # Get current combinations for minimal processing from database
            current_db_combinations = self._get_current_minimal_combinations()
            new_combinations = {(item.seller_name, item.item_name) for item in items}
            
            self.logger.info(f"Minimal processing: {len(current_db_combinations)} in DB, {len(new_combinations)} new")
            
            # Detect new combinations
            truly_new = new_combinations - current_db_combinations
            for seller, item in truly_new:
                # Add new combination with status NEW
                success = self.db.update_sellers_status(
                    seller_name=seller,
                    item_name=item,
                    quantity=None,
                    status=self.STATUS_NEW,
                    processing_type="minimal"
                )
                
                if success:
                    change = ChangeLogEntry(
                        seller_name=seller,
                        item_name=item,
                        change_type='NEW_COMBINATION',
                        old_value=None,
                        new_value='minimal_processing'
                    )
                    changes.append(change)
                    self.logger.info(f"New minimal combination: {seller}/{item}")
            
            # Detect disappeared combinations
            disappeared = current_db_combinations - new_combinations
            removed_combinations = set()
            
            for seller, item in disappeared:
                # Check if combination had price history
                had_price = self._combination_had_price(seller, item)
                
                if had_price:
                    # Combination had price → log as GONE and record sale
                    self._record_sale(seller, item)
                    success = self.db.update_sellers_status(
                        seller_name=seller,
                        item_name=item,
                        quantity=None,
                        status=self.STATUS_GONE,
                        processing_type="minimal"
                    )
                    
                    if success:
                        change = ChangeLogEntry(
                            seller_name=seller,
                            item_name=item,
                            change_type='SALE_DETECTED',
                            old_value='available',
                            new_value='sold'
                        )
                        changes.append(change)
                        self.logger.info(f"Sale detected: {seller}/{item}")
                        
                    removed_combinations.add((seller, item))
                else:
                    # Combination never had price → simply remove
                    self._remove_minimal_combination(seller, item)
                    
                    change = ChangeLogEntry(
                        seller_name=seller,
                        item_name=item,
                        change_type='COMBINATION_REMOVED',
                        old_value='tracked',
                        new_value='removed'
                    )
                    changes.append(change)
                    self.logger.info(f"Combination removed: {seller}/{item}")
                    
                    removed_combinations.add((seller, item))
            
            return changes, truly_new, removed_combinations
            
        except Exception as e:
            self.logger.error(f"Failed to process minimal processing items: {e}")
            return [], set(), set()
    
    def _get_current_minimal_combinations(self) -> set:
        """Get current minimal processing combinations from database."""
        try:
            with self.db._transaction() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT seller_name, item_name FROM sellers_current 
                    WHERE processing_type = 'minimal' AND status != 'GONE'
                ''')
                
                combinations = {(row[0], row[1]) for row in cursor.fetchall()}
                return combinations
                
        except Exception as e:
            self.logger.error(f"Failed to get current minimal combinations: {e}")
            return set()
    
    def _combination_had_price(self, seller_name: str, item_name: str) -> bool:
        """Check if combination ever had price information."""
        try:
            with self.db._transaction() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT COUNT(*) FROM items 
                    WHERE seller_name = ? AND item_name = ? AND price IS NOT NULL
                ''', (seller_name, item_name))
                
                count = cursor.fetchone()[0]
                return count > 0
                
        except Exception as e:
            self.logger.error(f"Failed to check price history for {seller_name}/{item_name}: {e}")
            return False
    
    def _record_sale(self, seller_name: str, item_name: str) -> None:
        """Record a sale in the sales_log table."""
        try:
            with self.db._transaction() as conn:
                cursor = conn.cursor()
                
                # Get last known price/quantity
                cursor.execute('''
                    SELECT price, quantity FROM items
                    WHERE seller_name = ? AND item_name = ?
                    ORDER BY created_at DESC LIMIT 1
                ''', (seller_name, item_name))
                
                last_data = cursor.fetchone()
                last_price, last_quantity = (last_data[0], last_data[1]) if last_data else (None, None)
                
                # Get previous status
                cursor.execute('''
                    SELECT status FROM sellers_current
                    WHERE seller_name = ? AND item_name = ?
                ''', (seller_name, item_name))
                
                status_data = cursor.fetchone()
                previous_status = status_data[0] if status_data else None
                
                # Insert sale record
                cursor.execute('''
                    INSERT INTO sales_log 
                    (seller_name, item_name, last_price, last_quantity, processing_type, previous_status)
                    VALUES (?, ?, ?, ?, 'minimal', ?)
                ''', (seller_name, item_name, last_price, last_quantity, previous_status))
                
                self.logger.info(f"Recorded sale: {seller_name}/{item_name} - Price: {last_price}, Qty: {last_quantity}")
                
        except Exception as e:
            self.logger.error(f"Failed to record sale for {seller_name}/{item_name}: {e}")
    
    def _remove_minimal_combination(self, seller_name: str, item_name: str) -> None:
        """Remove minimal combination from sellers_current."""
        try:
            with self.db._transaction() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM sellers_current 
                    WHERE seller_name = ? AND item_name = ? AND processing_type = 'minimal'
                ''', (seller_name, item_name))
                
                self.logger.debug(f"Removed minimal combination: {seller_name}/{item_name}")
                
        except Exception as e:
            self.logger.error(f"Failed to remove minimal combination {seller_name}/{item_name}: {e}")
    
    def _update_monitoring_queue(self, items: List[ItemData]) -> None:
        """
        Update monitoring queue with current items.
        
        Args:
            items: List of current items
        """
        try:
            self.db.manage_monitoring_queue(items)
            
        except Exception as e:
            self.logger.error(f"Failed to update monitoring queue: {e}")
    
    def _detect_combination_changes(self, current_combinations: Set[Tuple[str, str]], 
                                   processing_type: str = "full") -> Tuple[Set[Tuple[str, str]], Set[Tuple[str, str]]]:
        """
        Detect new and removed seller-item combinations for specific processing type.
        
        Args:
            current_combinations: Set of current (seller, item) combinations
            processing_type: Processing type to filter by ('full' or 'minimal')
            
        Returns:
            Tuple of (new_combinations, removed_combinations)
        """
        try:
            # Get previous combinations from monitoring queue for specific processing type
            with self.db._transaction() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT DISTINCT seller_name, item_name 
                    FROM monitoring_queue
                    WHERE processing_type = ?
                ''', (processing_type,))
                
                previous_combinations = {(row[0], row[1]) for row in cursor.fetchall()}
            
            # Calculate differences
            new_combinations = current_combinations - previous_combinations
            removed_combinations = previous_combinations - current_combinations
            
            self.logger.debug(f"Combination changes ({processing_type}): "
                            f"{len(new_combinations)} new, {len(removed_combinations)} removed")
            
            # Log new combinations as SELLER_NEW or NEW_ITEM
            for seller, item in new_combinations:
                # Check if it's a new seller or new item for existing seller
                seller_exists = any(s == seller for s, i in previous_combinations)
                
                change_type = 'SELLER_NEW' if not seller_exists else 'NEW_ITEM'
                change = ChangeLogEntry(
                    seller_name=seller,
                    item_name=item,
                    change_type=change_type,
                    old_value=None,
                    new_value=f"{seller}/{item}"
                )
                
                # Log to changes_log table
                with self.db._transaction() as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO changes_log 
                        (seller_name, item_name, change_type, old_value, new_value)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (
                        change.seller_name, change.item_name, change.change_type,
                        change.old_value, change.new_value
                    ))
            
            # Log removed combinations as ITEM_REMOVED
            for seller, item in removed_combinations:
                change = ChangeLogEntry(
                    seller_name=seller,
                    item_name=item,
                    change_type='ITEM_REMOVED',
                    old_value=f"{seller}/{item}",
                    new_value=None
                )
                
                # Log to changes_log table
                with self.db._transaction() as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO changes_log 
                        (seller_name, item_name, change_type, old_value, new_value)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (
                        change.seller_name, change.item_name, change.change_type,
                        change.old_value, change.new_value
                    ))
                    
                    # Update status to UNCHECKED for disappeared combinations
                    cursor.execute('''
                        UPDATE monitoring_queue 
                        SET status = ?, status_changed_at = CURRENT_TIMESTAMP
                        WHERE seller_name = ? AND item_name = ?
                    ''', (self.STATUS_UNCHECKED, seller, item))
                    
                    # Also update sellers_current if exists
                    cursor.execute('''
                        UPDATE sellers_current 
                        SET status = ?, status_changed_at = CURRENT_TIMESTAMP, last_updated = CURRENT_TIMESTAMP
                        WHERE seller_name = ? AND item_name = ?
                    ''', (self.STATUS_UNCHECKED, seller, item))
            
            if removed_combinations:
                self.logger.info(f"Processed {len(removed_combinations)} removed combinations")
            
            return new_combinations, removed_combinations
            
        except Exception as e:
            self.logger.error(f"Failed to detect combination changes: {e}")
            return set(), set()
    
    def process_status_transitions(self) -> List[StatusTransition]:
        """
        Process automatic status transitions according to lifecycle rules.
        
        Returns:
            List of status transitions that were performed
        """
        transitions = []
        
        try:
            with self.db._transaction() as conn:
                cursor = conn.cursor()
                
                # Find items that need status transitions
                # NEW -> CHECKED: Items that have been seen and have data in items table
                cursor.execute('''
                    SELECT mq.seller_name, mq.item_name, mq.status, mq.status_changed_at
                    FROM monitoring_queue mq
                    WHERE mq.status = ? 
                    AND EXISTS (
                        SELECT 1 FROM items i 
                        WHERE i.seller_name = mq.seller_name 
                        AND i.item_name = mq.item_name
                    )
                ''', (self.STATUS_NEW,))
                
                new_to_checked = cursor.fetchall()
                
                # CHECKED -> UNCHECKED: Items that have been CHECKED for transition delay period
                delay_cutoff = datetime.now() - timedelta(seconds=self.config.status_transition_delay)
                
                cursor.execute('''
                    SELECT seller_name, item_name, status, status_changed_at
                    FROM monitoring_queue
                    WHERE status = ? AND status_changed_at < ?
                ''', (self.STATUS_CHECKED, delay_cutoff))
                
                checked_to_unchecked = cursor.fetchall()
                
                # Process NEW -> CHECKED transitions
                for seller_name, item_name, old_status, status_changed_at in new_to_checked:
                    transition = self._execute_status_transition(
                        seller_name, item_name, old_status, self.STATUS_CHECKED,
                        "Found data in items table"
                    )
                    if transition:
                        transitions.append(transition)
                
                # Process CHECKED -> UNCHECKED transitions
                for seller_name, item_name, old_status, status_changed_at in checked_to_unchecked:
                    transition = self._execute_status_transition(
                        seller_name, item_name, old_status, self.STATUS_UNCHECKED,
                        f"Status transition delay ({self.config.status_transition_delay}s) elapsed"
                    )
                    if transition:
                        transitions.append(transition)
            
            if transitions:
                self.logger.info(f"Processed {len(transitions)} status transitions")
            
            return transitions
            
        except Exception as e:
            self.logger.error(f"Failed to process status transitions: {e}")
            return []
    
    def _execute_status_transition(self, seller_name: str, item_name: str, 
                                 old_status: str, new_status: str, reason: str) -> Optional[StatusTransition]:
        """
        Execute a single status transition.
        
        Args:
            seller_name: Seller name
            item_name: Item name
            old_status: Current status
            new_status: Target status
            reason: Reason for transition
            
        Returns:
            StatusTransition object if successful, None otherwise
        """
        try:
            # Validate transition
            if new_status not in self.VALID_TRANSITIONS.get(old_status, []):
                self.logger.warning(f"Invalid transition {old_status} -> {new_status} for {seller_name}/{item_name}")
                return None
            
            # Update monitoring queue
            with self.db._transaction() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE monitoring_queue 
                    SET status = ?, status_changed_at = CURRENT_TIMESTAMP
                    WHERE seller_name = ? AND item_name = ? AND status = ?
                ''', (new_status, seller_name, item_name, old_status))
                
                if cursor.rowcount == 0:
                    self.logger.warning(f"No rows updated for transition {seller_name}/{item_name}")
                    return None
                
                # Update sellers_current if it exists
                cursor.execute('''
                    UPDATE sellers_current 
                    SET status = ?, status_changed_at = CURRENT_TIMESTAMP
                    WHERE seller_name = ? AND item_name = ?
                ''', (new_status, seller_name, item_name))
            
            # Create transition record
            transition = StatusTransition(
                seller_name=seller_name,
                item_name=item_name,
                old_status=old_status,
                new_status=new_status,
                timestamp=datetime.now(),
                reason=reason
            )
            
            self.logger.debug(f"Status transition: {seller_name}/{item_name} {old_status} -> {new_status}")
            
            return transition
            
        except Exception as e:
            self.logger.error(f"Failed to execute status transition: {e}")
            return None
    
    def check_new_combinations(self, seller_name: str, item_name: str) -> bool:
        """
        Check if a seller-item combination is new.
        
        Args:
            seller_name: Seller name
            item_name: Item name
            
        Returns:
            True if combination is new, False otherwise
        """
        try:
            with self.db._transaction() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT COUNT(*) FROM monitoring_queue 
                    WHERE seller_name = ? AND item_name = ?
                ''', (seller_name, item_name))
                
                count = cursor.fetchone()[0]
                return count == 0
                
        except Exception as e:
            self.logger.error(f"Failed to check new combination: {e}")
            return False
    
    def update_queue_status(self, seller_name: str, item_name: str, new_status: str) -> bool:
        """
        Update status for a specific combination in the queue.
        
        Args:
            seller_name: Seller name
            item_name: Item name  
            new_status: New status to set
            
        Returns:
            True if update was successful
        """
        try:
            with self.db._transaction() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE monitoring_queue 
                    SET status = ?, status_changed_at = CURRENT_TIMESTAMP
                    WHERE seller_name = ? AND item_name = ?
                ''', (new_status, seller_name, item_name))
                
                success = cursor.rowcount > 0
                
                if success:
                    self.logger.debug(f"Updated queue status: {seller_name}/{item_name} -> {new_status}")
                
                return success
                
        except Exception as e:
            self.logger.error(f"Failed to update queue status: {e}")
            return False
    
    def detect_price_changes(self, current_items: List[ItemData]) -> List[ChangeLogEntry]:
        """
        Detect price changes for current items.
        
        Args:
            current_items: List of current items
            
        Returns:
            List of price change entries
        """
        changes = []
        
        try:
            for item in current_items:
                if item.price is None:
                    continue
                
                # Get previous price
                with self.db._transaction() as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT price FROM items 
                        WHERE seller_name = ? AND item_name = ?
                        AND price IS NOT NULL
                        ORDER BY created_at DESC LIMIT 1 OFFSET 1
                    ''', (item.seller_name, item.item_name))
                    
                    result = cursor.fetchone()
                    if result:
                        previous_price = result[0]
                        
                        if previous_price != item.price:
                            change_type = 'PRICE_INCREASE' if item.price > previous_price else 'PRICE_DECREASE'
                            
                            change = ChangeLogEntry(
                                seller_name=item.seller_name,
                                item_name=item.item_name,
                                change_type=change_type,
                                old_value=str(previous_price),
                                new_value=str(item.price)
                            )
                            changes.append(change)
            
            return changes
            
        except Exception as e:
            self.logger.error(f"Failed to detect price changes: {e}")
            return []
    
    def detect_quantity_changes(self, current_items: List[ItemData]) -> List[ChangeLogEntry]:
        """
        Detect quantity changes for current items.
        
        Args:
            current_items: List of current items
            
        Returns:
            List of quantity change entries
        """
        changes = []
        
        try:
            for item in current_items:
                if item.quantity is None:
                    continue
                
                # Get previous quantity
                with self.db._transaction() as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT quantity FROM items 
                        WHERE seller_name = ? AND item_name = ?
                        AND quantity IS NOT NULL
                        ORDER BY created_at DESC LIMIT 1 OFFSET 1
                    ''', (item.seller_name, item.item_name))
                    
                    result = cursor.fetchone()
                    if result:
                        previous_quantity = result[0]
                        
                        if previous_quantity != item.quantity:
                            change_type = 'QUANTITY_INCREASE' if item.quantity > previous_quantity else 'QUANTITY_DECREASE'
                            
                            change = ChangeLogEntry(
                                seller_name=item.seller_name,
                                item_name=item.item_name,
                                change_type=change_type,
                                old_value=str(previous_quantity),
                                new_value=str(item.quantity)
                            )
                            changes.append(change)
            
            return changes
            
        except Exception as e:
            self.logger.error(f"Failed to detect quantity changes: {e}")
            return []
    
    def remove_inactive_combinations(self, inactive_threshold_days: int = 7) -> int:
        """
        Remove combinations that have been UNCHECKED for specified days.
        
        Args:
            inactive_threshold_days: Days after which to consider UNCHECKED combinations inactive
            
        Returns:
            Number of combinations removed
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=inactive_threshold_days)
            
            with self.db._transaction() as conn:
                cursor = conn.cursor()
                
                # Find combinations that have been UNCHECKED for too long
                cursor.execute('''
                    SELECT seller_name, item_name FROM monitoring_queue
                    WHERE status = ? AND status_changed_at < ?
                ''', (self.STATUS_UNCHECKED, cutoff_date))
                
                inactive_combinations = cursor.fetchall()
                
                # Log removal for each combination (only if not already logged)
                for seller_name, item_name in inactive_combinations:
                    # Check if ITEM_REMOVED was already logged for this combination recently
                    cursor.execute('''
                        SELECT COUNT(*) FROM changes_log 
                        WHERE seller_name = ? AND item_name = ? 
                        AND change_type = 'ITEM_REMOVED' 
                        AND detected_at > ?
                    ''', (seller_name, item_name, cutoff_date))
                    
                    already_logged = cursor.fetchone()[0] > 0
                    
                    if not already_logged:
                        cursor.execute('''
                            INSERT INTO changes_log 
                            (seller_name, item_name, change_type, old_value, new_value)
                            VALUES (?, ?, ?, ?, ?)
                        ''', (
                            seller_name, item_name, 'ITEM_REMOVED',
                            f"{seller_name}/{item_name}", None
                        ))
                
                # Remove from monitoring_queue
                cursor.execute('''
                    DELETE FROM monitoring_queue
                    WHERE status = ? AND status_changed_at < ?
                ''', (self.STATUS_UNCHECKED, cutoff_date))
                
                removed_from_queue = cursor.rowcount
                
                # Also remove from sellers_current
                cursor.execute('''
                    DELETE FROM sellers_current
                    WHERE status = ? AND status_changed_at < ?
                ''', (self.STATUS_UNCHECKED, cutoff_date))
                
                removed_from_current = cursor.rowcount
                
                total_removed = removed_from_queue
            
            if total_removed > 0:
                self.logger.info(
                    f"Removed {total_removed} inactive combinations "
                    f"(queue: {removed_from_queue}, current: {removed_from_current})"
                )
            
            return total_removed
            
        except Exception as e:
            self.logger.error(f"Failed to remove inactive combinations: {e}")
            return 0
    
    def _should_process_status_transitions(self) -> bool:
        """
        Check if it's time to process status transitions.
        
        Returns:
            True if status transitions should be processed
        """
        if not self._last_status_check:
            return True
        
        time_since_last = (datetime.now() - self._last_status_check).total_seconds()
        return time_since_last >= self.config.status_check_interval
    
    def _update_processing_stats(self, detection_result: ChangeDetection, processing_time: float) -> None:
        """Update processing statistics."""
        self._stats['total_status_checks'] += 1
        self._stats['total_transitions'] += len(detection_result.status_transitions)
        self._stats['total_changes_detected'] += len(detection_result.detected_changes)
        self._stats['last_processing_time'] = datetime.now().isoformat()
        
        # Update average processing time
        current_avg = self._stats['average_processing_time']
        total_checks = self._stats['total_status_checks']
        self._stats['average_processing_time'] = (
            (current_avg * (total_checks - 1) + processing_time) / total_checks
        )
        
        # Update change type counts
        for change in detection_result.detected_changes:
            change_type = change.change_type
            if change_type not in self._stats['change_type_counts']:
                self._stats['change_type_counts'][change_type] = 0
            self._stats['change_type_counts'][change_type] += 1
        
        self._last_status_check = datetime.now()
    
    def get_monitoring_statistics(self) -> Dict[str, Any]:
        """
        Get monitoring engine statistics.
        
        Returns:
            Dictionary with monitoring statistics
        """
        stats = self._stats.copy()
        
        # Add current status distribution
        try:
            stats['status_distribution'] = self.db.get_monitoring_status_summary()
        except Exception as e:
            self.logger.error(f"Failed to get status distribution: {e}")
            stats['status_distribution'] = {}
        
        # Add timing information
        stats['last_status_check'] = self._last_status_check.isoformat() if self._last_status_check else None
        stats['next_status_check'] = (
            (self._last_status_check + timedelta(seconds=self.config.status_check_interval)).isoformat()
            if self._last_status_check else None
        )
        
        return stats
    
    def get_system_health(self) -> Dict[str, Any]:
        """
        Get system health indicators.
        
        Returns:
            Dictionary with health indicators
        """
        health = {
            'status': 'healthy',
            'issues': [],
            'last_activity': self._last_status_check.isoformat() if self._last_status_check else None
        }
        
        try:
            # Check if status transitions are running on schedule
            if self._last_status_check:
                time_since_last = (datetime.now() - self._last_status_check).total_seconds()
                if time_since_last > self.config.status_check_interval * 2:
                    health['status'] = 'warning'
                    health['issues'].append(f"Status checks delayed by {time_since_last:.1f}s")
            
            # Check status distribution for anomalies
            status_dist = self.db.get_monitoring_status_summary()
            total_items = sum(status_dist.values())
            
            if total_items == 0:
                health['status'] = 'warning'
                health['issues'].append("No items in monitoring queue")
            
            # Check for stuck items (too many in one status)
            if total_items > 0:
                for status, count in status_dist.items():
                    percentage = count / total_items
                    if status == self.STATUS_UNCHECKED and percentage > 0.8:
                        health['status'] = 'warning'
                        health['issues'].append(f"Too many items stuck in {status} status ({percentage:.1%})")
            
        except Exception as e:
            health['status'] = 'error'
            health['issues'].append(f"Health check failed: {e}")
        
        return health