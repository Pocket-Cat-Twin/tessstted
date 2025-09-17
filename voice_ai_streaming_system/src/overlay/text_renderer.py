"""Text rendering and formatting for overlay display."""

from typing import List, Dict, Any, Optional, Tuple
import re
import textwrap
from dataclasses import dataclass
from enum import Enum


class TextAlignment(Enum):
    """Text alignment options."""
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"


class TextStyle(Enum):
    """Text styling options."""
    NORMAL = "normal"
    BOLD = "bold"
    ITALIC = "italic"
    UNDERLINE = "underline"


@dataclass
class FormattingRule:
    """Text formatting rule."""
    pattern: str  # Regex pattern
    style: TextStyle
    color: Optional[str] = None


@dataclass
class RenderConfig:
    """Text rendering configuration."""
    max_width: int = 400
    max_height: int = 200
    line_spacing: float = 1.2
    word_wrap: bool = True
    alignment: TextAlignment = TextAlignment.LEFT
    max_lines: int = 10
    truncate_indicator: str = "..."
    
    # Formatting rules
    formatting_rules: List[FormattingRule] = None


class TextRenderer:
    """
    Handles text rendering and formatting for overlay display.
    
    Provides text wrapping, formatting, styling, and optimization
    for overlay window display.
    """
    
    def __init__(self, config: Optional[RenderConfig] = None):
        """
        Initialize text renderer.
        
        Args:
            config: Rendering configuration
        """
        self.config = config or RenderConfig()
        
        # Default formatting rules
        if self.config.formatting_rules is None:
            self.config.formatting_rules = self._create_default_formatting_rules()
        
        # Performance tracking
        self.stats = {
            'render_count': 0,
            'wrap_count': 0,
            'truncate_count': 0,
            'format_count': 0,
            'total_chars_processed': 0
        }
    
    def _create_default_formatting_rules(self) -> List[FormattingRule]:
        """Create default text formatting rules."""
        return [
            # Bold text: **text** or __text__
            FormattingRule(r'\*\*(.*?)\*\*', TextStyle.BOLD),
            FormattingRule(r'__(.*?)__', TextStyle.BOLD),
            
            # Italic text: *text* or _text_
            FormattingRule(r'\*(.*?)\*', TextStyle.ITALIC),
            FormattingRule(r'_(.*?)_', TextStyle.ITALIC),
            
            # Code blocks: `code`
            FormattingRule(r'`(.*?)`', TextStyle.NORMAL, '#00FF00'),
            
            # URLs
            FormattingRule(r'https?://[^\s]+', TextStyle.UNDERLINE, '#0088FF'),
            
            # Error/warning keywords
            FormattingRule(r'\b(error|fail|failed|exception)\b', TextStyle.BOLD, '#FF4444'),
            FormattingRule(r'\b(warning|warn)\b', TextStyle.BOLD, '#FFAA00'),
            FormattingRule(r'\b(success|complete|done)\b', TextStyle.BOLD, '#44FF44'),
        ]
    
    def render_text(self, text: str) -> Dict[str, Any]:
        """
        Render text with formatting and layout.
        
        Args:
            text: Input text to render
            
        Returns:
            Rendering result with formatted text and metadata
        """
        self.stats['render_count'] += 1
        self.stats['total_chars_processed'] += len(text)
        
        # Clean and prepare text
        cleaned_text = self._clean_text(text)
        
        # Apply word wrapping
        wrapped_lines = self._wrap_text(cleaned_text)
        
        # Apply line truncation if needed
        truncated_lines = self._truncate_lines(wrapped_lines)
        
        # Apply text formatting
        formatted_lines = self._apply_formatting(truncated_lines)
        
        # Calculate dimensions
        dimensions = self._calculate_dimensions(formatted_lines)
        
        return {
            'text': '\n'.join(formatted_lines),
            'lines': formatted_lines,
            'line_count': len(formatted_lines),
            'dimensions': dimensions,
            'truncated': len(wrapped_lines) > len(truncated_lines),
            'original_length': len(text),
            'processed_length': len('\n'.join(formatted_lines))
        }
    
    def render_streaming_text(self, current_text: str, new_token: str) -> Dict[str, Any]:
        """
        Render text for streaming display with incremental updates.
        
        Args:
            current_text: Previously displayed text
            new_token: New token to append
            
        Returns:
            Rendering result optimized for streaming
        """
        # Combine texts
        full_text = current_text + new_token
        
        # Render full text
        result = self.render_text(full_text)
        
        # Add streaming-specific metadata
        result.update({
            'new_token': new_token,
            'is_streaming': True,
            'needs_scroll': len(result['lines']) > self.config.max_lines
        })
        
        return result
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize input text."""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove leading/trailing whitespace
        text = text.strip()
        
        # Normalize line endings
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        return text
    
    def _wrap_text(self, text: str) -> List[str]:
        """Apply word wrapping to text."""
        if not self.config.word_wrap:
            return text.split('\n')
        
        self.stats['wrap_count'] += 1
        
        # Calculate character width (approximate)
        # This is a rough estimate - actual width depends on font
        char_width = self.config.max_width // 8  # Assume 8px per character
        
        wrapped_lines = []
        
        for line in text.split('\n'):
            if len(line) <= char_width:
                wrapped_lines.append(line)
            else:
                # Use textwrap for proper word boundary wrapping
                wrapped = textwrap.wrap(
                    line,
                    width=char_width,
                    break_long_words=True,
                    break_on_hyphens=True
                )
                wrapped_lines.extend(wrapped)
        
        return wrapped_lines
    
    def _truncate_lines(self, lines: List[str]) -> List[str]:
        """Truncate lines if exceeding maximum."""
        if len(lines) <= self.config.max_lines:
            return lines
        
        self.stats['truncate_count'] += 1
        
        # Keep first lines and add truncation indicator
        truncated = lines[:self.config.max_lines - 1]
        truncated.append(self.config.truncate_indicator)
        
        return truncated
    
    def _apply_formatting(self, lines: List[str]) -> List[str]:
        """Apply text formatting rules."""
        if not self.config.formatting_rules:
            return lines
        
        self.stats['format_count'] += 1
        
        formatted_lines = []
        
        for line in lines:
            formatted_line = line
            
            # Apply each formatting rule
            for rule in self.config.formatting_rules:
                formatted_line = self._apply_formatting_rule(formatted_line, rule)
            
            formatted_lines.append(formatted_line)
        
        return formatted_lines
    
    def _apply_formatting_rule(self, text: str, rule: FormattingRule) -> str:
        """Apply a single formatting rule to text."""
        try:
            # For now, we'll just remove markdown-style formatting
            # since tkinter Text widget has limited rich text support
            
            if rule.style == TextStyle.BOLD:
                # Remove markdown bold markers
                text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
                text = re.sub(r'__(.*?)__', r'\1', text)
            
            elif rule.style == TextStyle.ITALIC:
                # Remove markdown italic markers
                text = re.sub(r'\*(.*?)\*', r'\1', text)
                text = re.sub(r'_(.*?)_', r'\1', text)
            
            elif rule.pattern == r'`(.*?)`':
                # Remove code block markers
                text = re.sub(r'`(.*?)`', r'\1', text)
            
            return text
            
        except Exception:
            # If regex fails, return original text
            return text
    
    def _calculate_dimensions(self, lines: List[str]) -> Dict[str, int]:
        """Calculate text dimensions."""
        if not lines:
            return {'width': 0, 'height': 0}
        
        # Estimate character dimensions (rough approximation)
        char_width = 8  # Average character width in pixels
        char_height = 16  # Average character height in pixels
        
        # Calculate width (longest line)
        max_line_length = max(len(line) for line in lines)
        width = max_line_length * char_width
        
        # Calculate height
        height = len(lines) * char_height * self.config.line_spacing
        
        return {
            'width': int(width),
            'height': int(height),
            'char_width': char_width,
            'char_height': char_height,
            'line_count': len(lines),
            'max_line_length': max_line_length
        }
    
    def estimate_render_time(self, text: str) -> float:
        """Estimate rendering time for text."""
        # Simple estimation based on text length and complexity
        base_time = 0.001  # 1ms base
        char_time = len(text) * 0.00001  # 0.01ms per character
        line_time = text.count('\n') * 0.0001  # 0.1ms per line
        
        return base_time + char_time + line_time
    
    def set_config(self, config: RenderConfig) -> None:
        """Update rendering configuration."""
        self.config = config
        
        # Reset formatting rules if not provided
        if self.config.formatting_rules is None:
            self.config.formatting_rules = self._create_default_formatting_rules()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get rendering statistics."""
        stats = self.stats.copy()
        
        # Calculate derived statistics
        if stats['render_count'] > 0:
            stats['avg_chars_per_render'] = stats['total_chars_processed'] / stats['render_count']
        else:
            stats['avg_chars_per_render'] = 0
        
        stats.update({
            'config': {
                'max_width': self.config.max_width,
                'max_height': self.config.max_height,
                'max_lines': self.config.max_lines,
                'word_wrap': self.config.word_wrap,
                'alignment': self.config.alignment.value,
                'formatting_rules_count': len(self.config.formatting_rules or [])
            }
        })
        
        return stats
    
    def clear_statistics(self) -> None:
        """Clear rendering statistics."""
        self.stats = {
            'render_count': 0,
            'wrap_count': 0,
            'truncate_count': 0,
            'format_count': 0,
            'total_chars_processed': 0
        }
    
    def format_ai_response(self, response: str, source: str = "AI") -> str:
        """Format AI response with source indication."""
        # Add source prefix
        formatted = f"[{source}] {response}"
        
        # Clean up common AI response artifacts
        formatted = re.sub(r'^(AI|Assistant|Claude):\s*', '', formatted, flags=re.IGNORECASE)
        formatted = re.sub(r'\n+$', '', formatted)  # Remove trailing newlines
        
        return formatted
    
    def format_stt_result(self, text: str, confidence: float = 0.0) -> str:
        """Format STT result with confidence indication."""
        if confidence > 0:
            return f"[You] {text} ({confidence:.1%})"
        else:
            return f"[You] {text}"
    
    def format_system_message(self, message: str, level: str = "info") -> str:
        """Format system message with level indication."""
        level_indicators = {
            'info': 'ℹ',
            'warning': '⚠',
            'error': '❌',
            'success': '✅'
        }
        
        indicator = level_indicators.get(level, 'ℹ')
        return f"{indicator} {message}"
    
    def create_typing_indicator(self, dots_count: int = 3) -> str:
        """Create typing/processing indicator."""
        dots = '.' * (dots_count % 4)  # Cycle between 0-3 dots
        return f"Processing{dots}"