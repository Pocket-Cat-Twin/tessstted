"""Windows invisible overlay window implementation."""

import sys
import tkinter as tk
from tkinter import font
from typing import Optional, Tuple, Dict, Any
import threading
from dataclasses import dataclass

try:
    import win32api
    import win32con
    import win32gui
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False

from ..core.event_bus import EventBus, EventType


@dataclass
class OverlayStyle:
    """Overlay appearance configuration."""
    font_family: str = "Arial"
    font_size: int = 14
    font_weight: str = "normal"
    text_color: str = "#FFFFFF"
    background_color: str = "#000000"
    background_alpha: float = 0.7
    border_width: int = 1
    border_color: str = "#333333"
    padding: int = 10
    max_width: int = 400
    max_height: int = 200


class InvisibleWindow:
    """
    Windows invisible overlay window implementation.
    
    Creates a transparent, always-on-top window for displaying AI responses.
    Uses tkinter with Windows API extensions for proper overlay behavior.
    """
    
    def __init__(self, event_bus: EventBus, style: Optional[OverlayStyle] = None):
        """
        Initialize invisible overlay window.
        
        Args:
            event_bus: Event bus for communication
            style: Overlay appearance configuration
        """
        self.event_bus = event_bus
        self.style = style or OverlayStyle()
        
        # Window state
        self.root: Optional[tk.Tk] = None
        self.text_widget: Optional[tk.Text] = None
        self.is_visible = False
        self.position = (100, 100)  # Default position
        self.hwnd: Optional[int] = None  # Windows handle
        
        # Threading
        self.ui_thread: Optional[threading.Thread] = None
        self.should_run = False
        
        # Subscribe to events
        self._subscribe_to_events()
        
        # Check Windows compatibility
        self.windows_available = WIN32_AVAILABLE and sys.platform == "win32"
        if not self.windows_available:
            self.event_bus.publish(EventType.ERROR_OCCURRED, {
                'source': 'overlay',
                'error': 'Windows overlay requires Windows platform and win32 libraries',
                'severity': 'warning'
            })
    
    def _subscribe_to_events(self) -> None:
        """Subscribe to relevant events."""
        self.event_bus.subscribe(EventType.AI_RESPONSE_RECEIVED, self._handle_ai_response)
        self.event_bus.subscribe(EventType.AI_STREAM_TOKEN, self._handle_stream_token)
        self.event_bus.subscribe(EventType.OVERLAY_SHOW, self._handle_show_overlay)
        self.event_bus.subscribe(EventType.OVERLAY_HIDE, self._handle_hide_overlay)
        self.event_bus.subscribe(EventType.OVERLAY_MOVE, self._handle_move_overlay)
        self.event_bus.subscribe(EventType.OVERLAY_UPDATE_TEXT, self._handle_update_text)
    
    def start(self) -> bool:
        """
        Start the overlay window.
        
        Returns:
            True if started successfully, False otherwise
        """
        if not self.windows_available:
            return False
        
        if self.ui_thread and self.ui_thread.is_alive():
            return True  # Already running
        
        self.should_run = True
        self.ui_thread = threading.Thread(target=self._run_ui_thread, daemon=True)
        self.ui_thread.start()
        
        # Wait for window to be created
        timeout = 5.0
        step = 0.1
        elapsed = 0.0
        while elapsed < timeout and self.root is None:
            threading.Event().wait(step)
            elapsed += step
        
        success = self.root is not None
        
        self.event_bus.publish(EventType.OVERLAY_STARTED, {
            'success': success,
            'windows_available': self.windows_available
        })
        
        return success
    
    def stop(self) -> None:
        """Stop the overlay window."""
        self.should_run = False
        
        if self.root:
            try:
                self.root.quit()
            except tk.TclError:
                pass  # Window already destroyed
        
        if self.ui_thread and self.ui_thread.is_alive():
            self.ui_thread.join(timeout=2.0)
        
        self.event_bus.publish(EventType.OVERLAY_STOPPED, {})
    
    def _run_ui_thread(self) -> None:
        """Run the UI thread with tkinter mainloop."""
        try:
            self._create_window()
            self._setup_windows_properties()
            
            # Start tkinter mainloop
            if self.root:
                self.root.mainloop()
                
        except Exception as e:
            self.event_bus.publish(EventType.ERROR_OCCURRED, {
                'source': 'overlay',
                'error': f'UI thread error: {str(e)}',
                'severity': 'error'
            })
        finally:
            self.root = None
            self.text_widget = None
            self.hwnd = None
    
    def _create_window(self) -> None:
        """Create the tkinter window with transparent properties."""
        self.root = tk.Tk()
        self.root.title("Voice AI Overlay")
        
        # Configure window properties
        self.root.overrideredirect(True)  # Remove window decorations
        self.root.attributes('-topmost', True)  # Always on top
        self.root.configure(bg=self.style.background_color)
        
        # Set transparency (if supported)
        try:
            self.root.attributes('-alpha', self.style.background_alpha)
        except tk.TclError:
            pass  # Alpha not supported on this system
        
        # Position and size
        self.root.geometry(f"{self.style.max_width}x{self.style.max_height}+{self.position[0]}+{self.position[1]}")
        
        # Create text widget
        self._create_text_widget()
        
        # Hide initially
        self.root.withdraw()
        
        # Bind events
        self.root.bind('<Button-1>', self._on_click)
        self.root.bind('<B1-Motion>', self._on_drag)
        
        # Get window handle for Windows API
        try:
            self.root.update()  # Ensure window is created
            self.hwnd = int(self.root.wm_frame(), 16) if hasattr(self.root, 'wm_frame') else None
        except:
            self.hwnd = None
    
    def _create_text_widget(self) -> None:
        """Create and configure the text display widget."""
        if not self.root:
            return
        
        # Configure font
        text_font = font.Font(
            family=self.style.font_family,
            size=self.style.font_size,
            weight=self.style.font_weight
        )
        
        # Create text widget
        self.text_widget = tk.Text(
            self.root,
            font=text_font,
            fg=self.style.text_color,
            bg=self.style.background_color,
            highlightthickness=self.style.border_width,
            highlightbackground=self.style.border_color,
            relief="solid",
            wrap=tk.WORD,
            state=tk.DISABLED,
            cursor=""
        )
        
        # Configure padding and layout
        self.text_widget.pack(
            fill=tk.BOTH,
            expand=True,
            padx=self.style.padding,
            pady=self.style.padding
        )
        
        # Remove text selection capability
        self.text_widget.bindtags((str(self.text_widget), str(self.root), "all"))
    
    def _setup_windows_properties(self) -> None:
        """Configure Windows-specific overlay properties."""
        if not self.windows_available or not self.hwnd:
            return
        
        try:
            # Get current window style
            style = win32gui.GetWindowLong(self.hwnd, win32con.GWL_EXSTYLE)
            
            # Add transparent and tool window properties
            style |= win32con.WS_EX_LAYERED
            style |= win32con.WS_EX_TRANSPARENT  # Click-through
            style |= win32con.WS_EX_TOOLWINDOW   # Don't show in taskbar
            
            # Apply new style
            win32gui.SetWindowLong(self.hwnd, win32con.GWL_EXSTYLE, style)
            
            # Set layered window attributes for transparency
            win32gui.SetLayeredWindowAttributes(
                self.hwnd,
                0,  # Transparency key (not used)
                int(255 * self.style.background_alpha),  # Alpha value
                win32con.LWA_ALPHA
            )
            
        except Exception as e:
            self.event_bus.publish(EventType.ERROR_OCCURRED, {
                'source': 'overlay',
                'error': f'Windows properties setup failed: {str(e)}',
                'severity': 'warning'
            })
    
    def _handle_ai_response(self, data: Dict[str, Any]) -> None:
        """Handle complete AI response."""
        response_text = data.get('response', '')
        if response_text:
            self._update_text_safe(response_text)
            self._show_window_safe()
    
    def _handle_stream_token(self, data: Dict[str, Any]) -> None:
        """Handle streaming AI token."""
        token = data.get('token', '')
        if token:
            self._append_text_safe(token)
            if not self.is_visible:
                self._show_window_safe()
    
    def _handle_show_overlay(self, data: Dict[str, Any]) -> None:
        """Handle show overlay event."""
        self._show_window_safe()
    
    def _handle_hide_overlay(self, data: Dict[str, Any]) -> None:
        """Handle hide overlay event."""
        self._hide_window_safe()
    
    def _handle_move_overlay(self, data: Dict[str, Any]) -> None:
        """Handle move overlay event."""
        x = data.get('x', self.position[0])
        y = data.get('y', self.position[1])
        self._move_window_safe(x, y)
    
    def _handle_update_text(self, data: Dict[str, Any]) -> None:
        """Handle text update event."""
        text = data.get('text', '')
        append = data.get('append', False)
        
        if append:
            self._append_text_safe(text)
        else:
            self._update_text_safe(text)
    
    def _update_text_safe(self, text: str) -> None:
        """Thread-safe text update."""
        if self.root:
            self.root.after(0, self._update_text, text)
    
    def _append_text_safe(self, text: str) -> None:
        """Thread-safe text append."""
        if self.root:
            self.root.after(0, self._append_text, text)
    
    def _show_window_safe(self) -> None:
        """Thread-safe window show."""
        if self.root:
            self.root.after(0, self._show_window)
    
    def _hide_window_safe(self) -> None:
        """Thread-safe window hide."""
        if self.root:
            self.root.after(0, self._hide_window)
    
    def _move_window_safe(self, x: int, y: int) -> None:
        """Thread-safe window move."""
        if self.root:
            self.root.after(0, self._move_window, x, y)
    
    def _update_text(self, text: str) -> None:
        """Update text widget content."""
        if not self.text_widget:
            return
        
        self.text_widget.config(state=tk.NORMAL)
        self.text_widget.delete(1.0, tk.END)
        self.text_widget.insert(1.0, text)
        self.text_widget.config(state=tk.DISABLED)
        
        # Auto-resize window based on content
        self._auto_resize()
    
    def _append_text(self, text: str) -> None:
        """Append text to widget content."""
        if not self.text_widget:
            return
        
        self.text_widget.config(state=tk.NORMAL)
        self.text_widget.insert(tk.END, text)
        self.text_widget.config(state=tk.DISABLED)
        
        # Scroll to bottom
        self.text_widget.see(tk.END)
        
        # Auto-resize window based on content
        self._auto_resize()
    
    def _show_window(self) -> None:
        """Show the overlay window."""
        if self.root and not self.is_visible:
            self.root.deiconify()
            self.is_visible = True
            
            self.event_bus.publish(EventType.OVERLAY_SHOWN, {})
    
    def _hide_window(self) -> None:
        """Hide the overlay window."""
        if self.root and self.is_visible:
            self.root.withdraw()
            self.is_visible = False
            
            self.event_bus.publish(EventType.OVERLAY_HIDDEN, {})
    
    def _move_window(self, x: int, y: int) -> None:
        """Move the overlay window."""
        if self.root:
            self.position = (x, y)
            self.root.geometry(f"+{x}+{y}")
            
            self.event_bus.publish(EventType.OVERLAY_MOVED, {
                'x': x, 'y': y
            })
    
    def _auto_resize(self) -> None:
        """Auto-resize window based on text content."""
        if not self.text_widget or not self.root:
            return
        
        try:
            # Update to get actual content size
            self.text_widget.update()
            
            # Get content dimensions
            content_width = self.text_widget.winfo_reqwidth()
            content_height = self.text_widget.winfo_reqheight()
            
            # Add padding
            width = min(content_width + 2 * self.style.padding, self.style.max_width)
            height = min(content_height + 2 * self.style.padding, self.style.max_height)
            
            # Minimum size
            width = max(width, 100)
            height = max(height, 50)
            
            # Update window size
            self.root.geometry(f"{width}x{height}+{self.position[0]}+{self.position[1]}")
            
        except tk.TclError:
            pass  # Widget not ready yet
    
    def _on_click(self, event) -> None:
        """Handle mouse click for dragging."""
        self._drag_start_x = event.x
        self._drag_start_y = event.y
    
    def _on_drag(self, event) -> None:
        """Handle mouse drag for window positioning."""
        if hasattr(self, '_drag_start_x') and hasattr(self, '_drag_start_y'):
            x = self.root.winfo_x() + event.x - self._drag_start_x
            y = self.root.winfo_y() + event.y - self._drag_start_y
            self._move_window(x, y)
    
    @property
    def is_running(self) -> bool:
        """Check if overlay is running."""
        return self.should_run and self.root is not None
    
    def get_position(self) -> Tuple[int, int]:
        """Get current window position."""
        return self.position
    
    def set_style(self, style: OverlayStyle) -> None:
        """Update overlay style."""
        self.style = style
        
        # Apply style changes if window exists
        if self.root:
            self.root.after(0, self._apply_style_changes)
    
    def _apply_style_changes(self) -> None:
        """Apply style changes to existing window."""
        if not self.root or not self.text_widget:
            return
        
        try:
            # Update window properties
            self.root.configure(bg=self.style.background_color)
            self.root.attributes('-alpha', self.style.background_alpha)
            
            # Update text widget
            text_font = font.Font(
                family=self.style.font_family,
                size=self.style.font_size,
                weight=self.style.font_weight
            )
            
            self.text_widget.configure(
                font=text_font,
                fg=self.style.text_color,
                bg=self.style.background_color,
                highlightbackground=self.style.border_color
            )
            
            # Update Windows properties
            self._setup_windows_properties()
            
        except Exception as e:
            self.event_bus.publish(EventType.ERROR_OCCURRED, {
                'source': 'overlay',
                'error': f'Style update failed: {str(e)}',
                'severity': 'warning'
            })