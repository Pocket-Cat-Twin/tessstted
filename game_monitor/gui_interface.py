"""
GUI Interface for Game Monitor System

High-performance tkinter-based GUI for monitoring and controlling
the game item monitoring system with real-time data display.
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import threading
import time
from typing import Dict, List, Optional, Callable
import json
from datetime import datetime
import os
import sys
from dataclasses import dataclass
import weakref
import gc

# Add the parent directory to the path to import game_monitor modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .constants import GUI, APP_TITLE, Performance
from .error_handler import get_error_handler, ErrorContext, ErrorCategory, RecoveryStrategy
from .advanced_logger import get_logger

from game_monitor.main_controller import GameMonitor
from game_monitor.database_manager import DatabaseManager
from game_monitor.region_selector import RegionSelector, CoordinateInputDialog, RegionManager, RegionConfig
from game_monitor.vision_system import ScreenRegion, get_vision_system

logger = get_logger(__name__)  # Use centralized logger


@dataclass
class GUIConfig:
    """Configuration for GUI appearance and behavior"""
    window_width: int = GUI.DEFAULT_WIDTH
    window_height: int = GUI.DEFAULT_HEIGHT
    refresh_rate: int = int(GUI.STATISTICS_UPDATE_INTERVAL * 1000)  # ms
    log_max_lines: int = GUI.MAX_LOG_LINES
    theme: str = "default"


class StatusIndicator:
    """Status indicator widget with color-coded states"""
    
    def __init__(self, parent, label: str, x: int, y: int):
        self.label = tk.Label(parent, text=label, font=("Arial", 10, "bold"))
        self.label.place(x=x, y=y)
        
        self.status = tk.Label(parent, text="●", font=("Arial", 16), fg="red")
        self.status.place(x=x+GUI.STATUS_INDICATOR_X_OFFSET, y=y-2)
        
        self.text_label = tk.Label(parent, text="Stopped", font=("Arial", 9))
        self.text_label.place(x=x+GUI.STATUS_INDICATOR_Y_OFFSET, y=y+2)
    
    def set_status(self, active: bool, text: str = ""):
        """Update status indicator"""
        color = "green" if active else "red" 
        status_text = text or ("Running" if active else "Stopped")
        
        self.status.config(fg=color)
        self.text_label.config(text=status_text)


class PerformancePanel:
    """Panel for displaying real-time performance metrics"""
    
    def __init__(self, parent_frame):
        self.frame = ttk.LabelFrame(parent_frame, text="Performance Metrics", padding=10)
        self.frame.pack(fill="x", padx=5, pady=5)
        
        # Create metrics display
        self.metrics = {}
        self._cleanup_performed = False
        self.create_metrics()
    
    def cleanup(self):
        """Clean up panel resources"""
        if not self._cleanup_performed:
            self._cleanup_performed = True
            self.metrics.clear()
            if hasattr(self, 'frame') and self.frame:
                self.frame.destroy()
                self.frame = None
    
    def __del__(self):
        """Destructor to ensure cleanup"""
        try:
            self.cleanup()
        except Exception:
            pass
    
    def create_metrics(self):
        """Create performance metric displays"""
        metrics_config = [
            ("Response Time", "0.000s", "green"),
            ("Database Ops", "0.000s", "green"), 
            ("OCR Processing", "0.000s", "green"),
            ("Memory Usage", "0 MB", "blue"),
            ("CPU Usage", "0%", "blue"),
            ("Total Captures", "0", "purple")
        ]
        
        row = 0
        for name, default_value, color in metrics_config:
            label = tk.Label(self.frame, text=f"{name}:", font=("Arial", 9, "bold"))
            label.grid(row=row, column=0, sticky="w", padx=5, pady=2)
            
            value_label = tk.Label(self.frame, text=default_value, 
                                 font=("Arial", 9), fg=color)
            value_label.grid(row=row, column=1, sticky="w", padx=20, pady=2)
            
            self.metrics[name] = value_label
            row += 1
    
    def update_metric(self, name: str, value: str, color: str = None):
        """Update a specific metric"""
        if name in self.metrics:
            self.metrics[name].config(text=value)
            if color:
                self.metrics[name].config(fg=color)


class TradesStatisticsPanel:
    """Panel for displaying trade statistics and data"""
    
    def __init__(self, parent_frame, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.frame = ttk.LabelFrame(parent_frame, text="Trading Statistics", padding=10)
        self.frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.stats_labels = {}
        self.trades_tree = None
        self._cleanup_performed = False
        
        self.create_statistics_display()
        self.create_recent_trades_table()
    
    def cleanup(self):
        """Clean up panel resources"""
        if not self._cleanup_performed:
            self._cleanup_performed = True
            
            # Clear tree items to free memory
            if self.trades_tree:
                for item in self.trades_tree.get_children():
                    self.trades_tree.delete(item)
                    
            self.stats_labels.clear()
            self.db_manager = None
            
            if hasattr(self, 'frame') and self.frame:
                self.frame.destroy()
                self.frame = None
    
    def __del__(self):
        """Destructor to ensure cleanup"""
        try:
            self.cleanup()
        except Exception:
            pass
    
    def create_statistics_display(self):
        """Create statistics summary display"""
        stats_frame = ttk.Frame(self.frame)
        stats_frame.pack(fill="x", pady=5)
        
        # Statistics labels
        self.stats_labels = {}
        stats_config = [
            ("Total Trades", "0"),
            ("Unique Traders", "0"), 
            ("Unique Items", "0"),
            ("Avg Response Time", "0.000s")
        ]
        
        col = 0
        for name, default_value in stats_config:
            container = ttk.Frame(stats_frame)
            container.pack(side="left", padx=20)
            
            title_label = tk.Label(container, text=name, font=("Arial", 9, "bold"))
            title_label.pack()
            
            value_label = tk.Label(container, text=default_value, 
                                 font=("Arial", 12, "bold"), fg="blue")
            value_label.pack()
            
            self.stats_labels[name] = value_label
            col += 1
    
    def create_recent_trades_table(self):
        """Create table for recent trades"""
        table_frame = ttk.Frame(self.frame)
        table_frame.pack(fill="both", expand=True, pady=10)
        
        # Create treeview for trades table
        self.trades_tree = ttk.Treeview(table_frame, columns=(
            "Time", "Trader", "Item", "Quantity", "Price", "Confidence"
        ), show="headings", height=10)
        
        # Configure columns
        columns_config = [
            ("Time", GUI.TABLE_COLUMN_TIME),
            ("Trader", GUI.TABLE_COLUMN_TRADER),
            ("Item", GUI.TABLE_COLUMN_ITEM),
            ("Quantity", GUI.TABLE_COLUMN_QUANTITY),
            ("Price", GUI.TABLE_COLUMN_PRICE),
            ("Confidence", GUI.TABLE_COLUMN_CONFIDENCE)
        ]
        
        for col, width in columns_config:
            self.trades_tree.heading(col, text=col)
            self.trades_tree.column(col, width=width)
        
        # Scrollbar for table
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", 
                                command=self.trades_tree.yview)
        self.trades_tree.configure(yscrollcommand=scrollbar.set)
        
        self.trades_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def update_statistics(self):
        """Update statistics display with latest data and centralized error handling"""
        update_start = time.time()
        
        try:
            # Get trade statistics with individual error handling
            total_trades = 0
            unique_traders = 0
            unique_items = 0
            
            try:
                total_trades = self.db_manager.get_total_trades_count()
            except Exception as e:
                logger.warning(f"Failed to get total trades count: {e}")
                
            try:
                unique_traders = self.db_manager.get_unique_traders_count()
            except Exception as e:
                logger.warning(f"Failed to get unique traders count: {e}")
                
            try:
                unique_items = self.db_manager.get_unique_items_count()
            except Exception as e:
                logger.warning(f"Failed to get unique items count: {e}")
            
            # Update labels with fallback values
            self.stats_labels["Total Trades"].config(text=str(total_trades))
            self.stats_labels["Unique Traders"].config(text=str(unique_traders))
            self.stats_labels["Unique Items"].config(text=str(unique_items))
            
            # Update recent trades table
            self.update_recent_trades()
            
            update_time = time.time() - update_start
            if update_time > 0.1:  # Log if taking too long
                logger.debug(f"Statistics update took {update_time:.3f}s")
            
        except Exception as e:
            update_time = time.time() - update_start
            
            error_context = ErrorContext(
                component="gui_interface",
                operation="update_statistics",
                user_data={'update_time': update_time},
                system_state={'db_manager_available': self.db_manager is not None},
                timestamp=datetime.now()
            )
            
            error_handler = get_error_handler()
            recovery_result = error_handler.handle_error(e, error_context, RecoveryStrategy.SKIP)
            
            if not recovery_result.recovery_successful:
                logger.error(f"Critical error updating GUI statistics: {e}")
            else:
                logger.warning(f"Statistics update failed, continuing: {e}")
    
    def update_recent_trades(self, limit: int = GUI.DEFAULT_RECENT_TRADES_LIMIT):
        """Update recent trades table with memory management"""
        if self._cleanup_performed or not self.trades_tree or not self.db_manager:
            return
            
        try:
            # Clear existing items to prevent memory accumulation
            children = self.trades_tree.get_children()
            if children:
                self.trades_tree.delete(*children)  # More efficient bulk delete
            
            # Get recent trades
            trades = self.db_manager.get_recent_trades(limit)
            
            # Limit the number of items to prevent memory issues
            max_display_items = min(limit, GUI.MAX_DISPLAY_ITEMS)
            for trade in trades[:max_display_items]:
                try:
                    # Format timestamp
                    timestamp = datetime.fromisoformat(trade[0]).strftime("%H:%M:%S")
                    
                    # Insert into table
                    self.trades_tree.insert("", "end", values=(
                        timestamp,
                        str(trade[1])[:GUI.TRADER_NAME_TRUNCATE_LENGTH],  # Truncate long trader names
                        str(trade[2])[:GUI.ITEM_NAME_TRUNCATE_LENGTH],  # Truncate long item names
                        str(trade[3]),
                        f"{float(trade[4]):.2f}",
                        f"{float(trade[5]):.1f}%"
                    ))
                except (ValueError, TypeError, IndexError) as e:
                    # Skip malformed trade data with better logging
                    logger.warning(f"Skipping malformed trade data: {e}")
                    continue
                
        except Exception as e:
            if not self._cleanup_performed:
                error_context = ErrorContext(
                    component="gui_interface",
                    operation="update_recent_trades",
                    user_data={'limit': limit, 'trades_tree_exists': self.trades_tree is not None},
                    system_state={'cleanup_performed': self._cleanup_performed},
                    timestamp=datetime.now()
                )
                
                error_handler = get_error_handler()
                recovery_result = error_handler.handle_error(e, error_context, RecoveryStrategy.SKIP)
                
                if not recovery_result.recovery_successful:
                    logger.error(f"Critical error updating recent trades display: {e}")
                else:
                    logger.warning(f"Recent trades update failed, continuing: {e}")


class SettingsDialog:
    """Settings configuration dialog"""
    
    def __init__(self, parent, config_manager):
        self.parent = parent
        self.config_manager = config_manager
        self.dialog = None
        self._cleanup_performed = False
        
        self.settings = {
            "hotkey_f1": "F1",
            "hotkey_f2": "F2", 
            "hotkey_f3": "F3",
            "hotkey_f4": "F4",
            "hotkey_f5": "F5",
            "ocr_confidence_threshold": GUI.DEFAULT_CONFIDENCE_THRESHOLD,
            "response_time_target": GUI.DEFAULT_RESPONSE_TIME_TARGET,
            "database_pool_size": 5
        }
    
    def show(self):
        """Show settings dialog"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Game Monitor Settings")
        self.dialog.geometry("400x500")
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # Set up proper cleanup on dialog close
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_dialog_close)
        
        # Add to parent's active dialogs if it has dialog management
        if hasattr(self.parent, '_active_dialogs'):
            self.parent._active_dialogs.add(self.dialog)
        
        self.create_settings_interface()
    
    def create_settings_interface(self):
        """Create settings interface"""
        notebook = ttk.Notebook(self.dialog)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Hotkeys tab
        hotkeys_frame = ttk.Frame(notebook)
        notebook.add(hotkeys_frame, text="Hotkeys")
        self.create_hotkeys_tab(hotkeys_frame)
        
        # Performance tab
        performance_frame = ttk.Frame(notebook)
        notebook.add(performance_frame, text="Performance")
        self.create_performance_tab(performance_frame)
        
        # OCR tab
        ocr_frame = ttk.Frame(notebook)
        notebook.add(ocr_frame, text="OCR Settings")
        self.create_ocr_tab(ocr_frame)
        
        # Buttons
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(fill="x", padx=10, pady=10)
        
        ttk.Button(button_frame, text="Save", command=self.save_settings).pack(side="right", padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.dialog.destroy).pack(side="right")
    
    def create_hotkeys_tab(self, parent):
        """Create hotkeys configuration tab"""
        hotkeys = [
            ("Trader List Capture", "hotkey_f1"),
            ("Item Scan Capture", "hotkey_f2"),
            ("Inventory Capture", "hotkey_f3"),
            ("Manual Verification", "hotkey_f4"),
            ("Emergency Stop", "hotkey_f5")
        ]
        
        for i, (label, key) in enumerate(hotkeys):
            tk.Label(parent, text=f"{label}:", font=("Arial", 10)).grid(
                row=i, column=0, sticky="w", padx=10, pady=5
            )
            
            entry = tk.Entry(parent, width=10)
            entry.insert(0, self.settings[key])
            entry.grid(row=i, column=1, padx=10, pady=5)
    
    def create_performance_tab(self, parent):
        """Create performance settings tab"""
        settings = [
            ("Response Time Target (ms)", "response_time_target"),
            ("Database Pool Size", "database_pool_size")
        ]
        
        for i, (label, key) in enumerate(settings):
            tk.Label(parent, text=f"{label}:", font=("Arial", 10)).grid(
                row=i, column=0, sticky="w", padx=10, pady=5
            )
            
            entry = tk.Entry(parent, width=15)
            entry.insert(0, str(self.settings[key]))
            entry.grid(row=i, column=1, padx=10, pady=5)
    
    def create_ocr_tab(self, parent):
        """Create OCR settings tab"""
        tk.Label(parent, text="OCR Confidence Threshold:", font=("Arial", 10)).grid(
            row=0, column=0, sticky="w", padx=10, pady=5
        )
        
        threshold_var = tk.IntVar(value=self.settings["ocr_confidence_threshold"])
        threshold_scale = tk.Scale(parent, from_=GUI.SCALE_MIN_VALUE, to=GUI.SCALE_MAX_VALUE, orient="horizontal",
                                 variable=threshold_var, length=GUI.SCALE_LENGTH)
        threshold_scale.grid(row=0, column=1, padx=10, pady=5)
    
    def _on_dialog_close(self):
        """Handle dialog close with proper cleanup"""
        if not self._cleanup_performed:
            self._cleanup_performed = True
            
            # Remove from parent's active dialogs
            if hasattr(self.parent, '_active_dialogs') and self.dialog in self.parent._active_dialogs:
                self.parent._active_dialogs.discard(self.dialog)
            
            # Clean up references
            self.config_manager = None
            self.settings = None
        
        if self.dialog:
            self.dialog.destroy()
    
    def save_settings(self):
        """Save settings and close dialog"""
        messagebox.showinfo("Settings", "Settings saved successfully!")
        self._on_dialog_close()


class ManualVerificationDialog:
    """Dialog for manual verification of OCR results"""
    
    def __init__(self, parent, verification_callback: Callable):
        self.parent = parent
        self.verification_callback = verification_callback
        self.dialog = None
        self.current_data = None
        self._cleanup_performed = False
        self.entries = {}
    
    def show_verification(self, capture_data: Dict):
        """Show verification dialog with capture data"""
        self.current_data = capture_data
        
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Manual Verification")
        self.dialog.geometry("600x400")
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # Set up proper cleanup on dialog close
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_dialog_close)
        
        # Add to parent's active dialogs if it has dialog management
        if hasattr(self.parent, '_active_dialogs'):
            self.parent._active_dialogs.add(self.dialog)
        
        self.create_verification_interface()
    
    def create_verification_interface(self):
        """Create verification interface"""
        # Screenshot preview (placeholder)
        preview_frame = ttk.LabelFrame(self.dialog, text="Screenshot Preview", padding=10)
        preview_frame.pack(fill="x", padx=10, pady=5)
        
        preview_label = tk.Label(preview_frame, text="[Screenshot Preview Placeholder]",
                               bg="lightgray", width=60, height=8)
        preview_label.pack()
        
        # Data correction interface
        data_frame = ttk.LabelFrame(self.dialog, text="Extracted Data", padding=10)
        data_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Create entry fields for each data field
        self.entries = {}
        fields = ["trader_nickname", "item_name", "quantity", "price", "confidence"]
        
        for i, field in enumerate(fields):
            tk.Label(data_frame, text=f"{field.replace('_', ' ').title()}:", 
                    font=("Arial", 10, "bold")).grid(row=i, column=0, sticky="w", padx=10, pady=5)
            
            entry = tk.Entry(data_frame, width=GUI.ENTRY_FIELD_WIDTH)
            if self.current_data and field in self.current_data:
                entry.insert(0, str(self.current_data[field]))
            entry.grid(row=i, column=1, padx=10, pady=5)
            
            self.entries[field] = entry
        
        # Buttons
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(fill="x", padx=10, pady=10)
        
        ttk.Button(button_frame, text="Approve", 
                  command=self.approve_data).pack(side="right", padx=5)
        ttk.Button(button_frame, text="Reject", 
                  command=self.reject_data).pack(side="right", padx=5)
        ttk.Button(button_frame, text="Cancel", 
                  command=self.dialog.destroy).pack(side="right")
    
    def _on_dialog_close(self):
        """Handle dialog close with proper cleanup"""
        if not self._cleanup_performed:
            self._cleanup_performed = True
            
            # Remove from parent's active dialogs
            if hasattr(self.parent, '_active_dialogs') and self.dialog in self.parent._active_dialogs:
                self.parent._active_dialogs.discard(self.dialog)
            
            # Clean up references
            self.current_data = None
            self.entries.clear()
            self.verification_callback = None
        
        if self.dialog:
            self.dialog.destroy()
    
    def approve_data(self):
        """Approve the verification data"""
        # Get corrected data from entries
        corrected_data = {}
        for field, entry in self.entries.items():
            corrected_data[field] = entry.get()
        
        # Call verification callback
        if self.verification_callback:
            self.verification_callback(corrected_data, approved=True)
        self._on_dialog_close()
    
    def reject_data(self):
        """Reject the verification data"""
        if self.verification_callback:
            self.verification_callback(None, approved=False)
        self._on_dialog_close()


class MainWindow:
    """Main GUI window for Game Monitor System"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(APP_TITLE)
        self.root.geometry(f"{GUI.DEFAULT_WIDTH}x{GUI.DEFAULT_HEIGHT}")
        self.root.minsize(GUI.MIN_WINDOW_WIDTH, GUI.MIN_WINDOW_HEIGHT)
        
        # Initialize components
        self.game_monitor = None
        self.db_manager = None
        self.config = GUIConfig()
        self.running = False
        self._cleanup_performed = False
        
        # GUI components
        self.status_indicators = {}
        self.performance_panel = None
        self.statistics_panel = None
        self.log_text = None
        
        # Timer management for memory cleanup
        self._active_timers = set()
        self._refresh_timer_id = None
        self._is_shutting_down = False
        
        # Dialog management
        self._active_dialogs = set()
        
        # Initialize GUI
        self.create_interface()
        self.setup_data_refresh()
        
        # Try to initialize game monitor
        self.initialize_game_monitor()
    
    def create_interface(self):
        """Create main interface layout"""
        # Create menu
        self.create_menu()
        
        # Create main panels
        self.create_control_panel()
        self.create_status_panel() 
        self.create_main_content()
        
        # Create status bar
        self.create_status_bar()
    
    def create_menu(self):
        """Create application menu"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Export Data...", command=self.export_data)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_closing)
        
        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Settings", command=self.show_settings)
        tools_menu.add_command(label="Calibrate Coordinates", command=self.calibrate_coordinates)
        tools_menu.add_command(label="Test OCR", command=self.test_ocr)
        tools_menu.add_separator()
        tools_menu.add_command(label="Database Manager", command=self.show_database_manager)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="User Manual", command=self.show_user_manual)
        help_menu.add_command(label="About", command=self.show_about)
    
    def create_control_panel(self):
        """Create control panel with start/stop buttons"""
        control_frame = ttk.Frame(self.root)
        control_frame.pack(fill="x", padx=5, pady=5)
        
        # Main control buttons
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(side="left")
        
        self.start_button = ttk.Button(button_frame, text="Start System", 
                                     command=self.start_system, style="Accent.TButton")
        self.start_button.pack(side="left", padx=5)
        
        self.stop_button = ttk.Button(button_frame, text="Stop System", 
                                    command=self.stop_system, state="disabled")
        self.stop_button.pack(side="left", padx=5)
        
        # Emergency stop
        emergency_button = ttk.Button(button_frame, text="EMERGENCY STOP", 
                                    command=self.emergency_stop)
        emergency_button.pack(side="left", padx=20)
        emergency_button.configure(style="Emergency.TButton")
    
    def create_status_panel(self):
        """Create status indicators panel"""
        status_frame = ttk.LabelFrame(self.root, text="System Status", padding=10)
        status_frame.pack(fill="x", padx=5, pady=5)
        
        # Status indicators
        indicators = [
            ("System", 20, 20),
            ("Database", 200, 20),
            ("Hotkeys", 380, 20),
            ("Vision", 560, 20),
            ("OCR Engine", 740, 20)
        ]
        
        for name, x, y in indicators:
            self.status_indicators[name] = StatusIndicator(status_frame, name, x, y)
    
    def create_main_content(self):
        """Create main content area"""
        # Create paned window for resizable panels
        paned = ttk.PanedWindow(self.root, orient="horizontal")
        paned.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Left panel - Performance and controls
        left_panel = ttk.Frame(paned)
        paned.add(left_panel, weight=1)
        
        # Performance metrics
        self.performance_panel = PerformancePanel(left_panel)
        
        # Real-time logging panel
        self.create_logging_panel(left_panel)
        
        # Right panel - Statistics and data
        right_panel = ttk.Frame(paned)
        paned.add(right_panel, weight=2)
        
        # Initialize database manager for statistics
        try:
            self.db_manager = DatabaseManager()
            self.statistics_panel = TradesStatisticsPanel(right_panel, self.db_manager)
        except Exception as e:
            print(f"Warning: Could not initialize database manager: {e}")
    
    def create_logging_panel(self, parent):
        """Create real-time logging panel"""
        log_frame = ttk.LabelFrame(parent, text="System Log", padding=10)
        log_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Log text area with scrollbar
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, 
                                                font=("Consolas", 9))
        self.log_text.pack(fill="both", expand=True)
        
        # Add initial log message
        self.add_log_message("Game Monitor GUI initialized successfully")
    
    def create_status_bar(self):
        """Create status bar"""
        self.status_bar = tk.Label(self.root, text="Ready", bd=1, relief="sunken", anchor="w")
        self.status_bar.pack(side="bottom", fill="x")
    
    def initialize_game_monitor(self):
        """Initialize game monitor system"""
        try:
            self.game_monitor = GameMonitor()
            self.add_log_message("Game Monitor system initialized successfully")
            
            # Update status indicators
            self.status_indicators["System"].set_status(True, "Initialized")
            self.status_indicators["Database"].set_status(True, "Connected")
            
        except Exception as e:
            self.add_log_message(f"Error initializing Game Monitor: {e}")
            messagebox.showerror("Initialization Error", 
                               f"Failed to initialize Game Monitor:\n{e}")
    
    def setup_data_refresh(self):
        """Setup automatic data refresh with proper timer management"""
        def refresh_data():
            if self._is_shutting_down:
                return
                
            try:
                if self.statistics_panel and hasattr(self, 'statistics_panel'):
                    self.statistics_panel.update_statistics()
                
                if self.performance_panel and self.game_monitor and hasattr(self, 'performance_panel'):
                    self.update_performance_metrics()
                
            except Exception as e:
                if not self._is_shutting_down:
                    print(f"Error during data refresh: {e}")
            
            # Schedule next refresh only if not shutting down
            if not self._is_shutting_down and hasattr(self, 'root') and self.root.winfo_exists():
                self._refresh_timer_id = self.root.after(int(GUI.STATISTICS_UPDATE_INTERVAL * 1000), refresh_data)
                if self._refresh_timer_id:
                    self._active_timers.add(self._refresh_timer_id)
        
        # Start refresh cycle
        if not self._is_shutting_down:
            initial_timer = self.root.after(1000, refresh_data)
            if initial_timer:
                self._active_timers.add(initial_timer)
    
    def update_performance_metrics(self):
        """Update performance metrics display"""
        if not self.performance_panel or not self.game_monitor:
            return
        
        try:
            # Get performance stats from game monitor
            stats = self.game_monitor.get_performance_stats()
            
            # Update metrics
            self.performance_panel.update_metric("Response Time", 
                                                f"{stats.get('avg_response_time', 0):.3f}s")
            self.performance_panel.update_metric("Database Ops", 
                                                f"{stats.get('avg_db_time', 0):.3f}s")
            self.performance_panel.update_metric("OCR Processing", 
                                                f"{stats.get('avg_ocr_time', 0):.3f}s")
            self.performance_panel.update_metric("Total Captures", 
                                                str(stats.get('total_captures', 0)))
            
            # System resource usage (with error handling)
            try:
                import psutil
                memory_percent = psutil.virtual_memory().percent
                cpu_percent = psutil.cpu_percent()
                
                self.performance_panel.update_metric("Memory Usage", 
                                                    f"{memory_percent:.1f}%")
                self.performance_panel.update_metric("CPU Usage", 
                                                    f"{cpu_percent:.1f}%")
            except ImportError:
                # psutil not available, show placeholder
                self.performance_panel.update_metric("Memory Usage", "N/A")
                self.performance_panel.update_metric("CPU Usage", "N/A")
            except Exception as e:
                print(f"Warning: Error getting system resource usage: {e}")
            
        except Exception as e:
            print(f"Error updating performance metrics: {e}")
    
    def add_log_message(self, message: str, level: str = "INFO"):
        """Add message to log display with memory management"""
        if not self.log_text or self._is_shutting_down:
            return
        
        try:
            timestamp = datetime.now().strftime("%H:%M:%S")
            formatted_message = f"[{timestamp}] {level}: {message}\n"
            
            self.log_text.insert("end", formatted_message)
            self.log_text.see("end")
            
            # Limit log size to prevent memory growth
            lines = int(self.log_text.index("end-1c").split('.')[0])
            if lines > self.config.log_max_lines:
                # Delete multiple lines at once for better performance
                lines_to_delete = max(1, lines - self.config.log_max_lines + GUI.LOG_CLEANUP_BATCH_SIZE)  # Delete extra lines
                self.log_text.delete(GUI.TEXT_DELETE_START, f"{lines_to_delete}.0")
        except (tk.TclError, AttributeError):
            # Widget was destroyed or not available
            pass
    
    def start_system(self):
        """Start the monitoring system"""
        if not self.game_monitor:
            messagebox.showerror("Error", "Game Monitor not initialized")
            return
        
        try:
            self.game_monitor.start()
            self.running = True
            
            # Update UI
            self.start_button.config(state="disabled")
            self.stop_button.config(state="normal")
            self.status_bar.config(text="System Running")
            
            # Update status indicators
            self.status_indicators["System"].set_status(True, "Running")
            self.status_indicators["Hotkeys"].set_status(True, "Active")
            self.status_indicators["Vision"].set_status(True, "Ready")
            self.status_indicators["OCR Engine"].set_status(True, "Active")
            
            self.add_log_message("Game Monitor system started successfully")
            
        except Exception as e:
            self.add_log_message(f"Error starting system: {e}", "ERROR")
            messagebox.showerror("Start Error", f"Failed to start system:\n{e}")
    
    def stop_system(self):
        """Stop the monitoring system"""
        if not self.game_monitor:
            return
        
        try:
            self.game_monitor.stop()
            self.running = False
            
            # Update UI
            self.start_button.config(state="normal")
            self.stop_button.config(state="disabled")
            self.status_bar.config(text="System Stopped")
            
            # Update status indicators
            self.status_indicators["System"].set_status(False, "Stopped")
            self.status_indicators["Hotkeys"].set_status(False, "Inactive")
            self.status_indicators["Vision"].set_status(False, "Standby")
            self.status_indicators["OCR Engine"].set_status(False, "Inactive")
            
            self.add_log_message("Game Monitor system stopped successfully")
            
        except Exception as e:
            self.add_log_message(f"Error stopping system: {e}", "ERROR")
            messagebox.showerror("Stop Error", f"Failed to stop system:\n{e}")
    
    def emergency_stop(self):
        """Emergency stop of all operations"""
        self.add_log_message("EMERGENCY STOP ACTIVATED", "CRITICAL")
        self.stop_system()
        messagebox.showwarning("Emergency Stop", "Emergency stop activated!\nAll operations halted.")
    
    def show_settings(self):
        """Show settings dialog"""
        if self.game_monitor:
            config_manager = self.game_monitor.config
            dialog = SettingsDialog(self.root, config_manager)
            dialog.show()
        else:
            messagebox.showerror("Error", "Game Monitor not initialized")
    
    def show_manual_verification(self, capture_data: Dict):
        """Show manual verification dialog"""
        def verification_callback(data, approved):
            if approved and data:
                self.add_log_message(f"Manual verification approved: {data}")
            else:
                self.add_log_message("Manual verification rejected")
        
        dialog = ManualVerificationDialog(self.root, verification_callback)
        dialog.show_verification(capture_data)
    
    def export_data(self):
        """Export system data"""
        if not self.db_manager:
            messagebox.showerror("Error", "Database not available")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("JSON files", "*.json")],
            title="Export Data"
        )
        
        if filename:
            try:
                # Export recent trades
                trades = self.db_manager.get_recent_trades(1000)
                
                if filename.endswith('.json'):
                    # Export as JSON
                    data = []
                    for trade in trades:
                        data.append({
                            'timestamp': trade[0],
                            'trader_nickname': trade[1],
                            'item_name': trade[2],
                            'quantity': trade[3],
                            'price': trade[4],
                            'confidence': trade[5]
                        })
                    
                    with open(filename, 'w') as f:
                        json.dump(data, f, indent=2)
                else:
                    # Export as CSV
                    import csv
                    with open(filename, 'w', newline='') as f:
                        writer = csv.writer(f)
                        writer.writerow(['Timestamp', 'Trader', 'Item', 'Quantity', 'Price', 'Confidence'])
                        writer.writerows(trades)
                
                messagebox.showinfo("Export Complete", f"Data exported to {filename}")
                self.add_log_message(f"Data exported to {filename}")
                
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to export data:\n{e}")
    
    def calibrate_coordinates(self):
        """Show region selection and calibration interface"""
        self.show_region_selection_dialog()
    
    def test_ocr(self):
        """Show OCR testing interface"""
        self.show_ocr_testing_dialog()
    
    def show_database_manager(self):
        """Show database management tools"""
        messagebox.showinfo("Database Manager", 
                          "Database management tools will be implemented here.\n"
                          "This would allow users to manage the database directly.")
    
    def show_user_manual(self):
        """Show user manual"""
        messagebox.showinfo("User Manual", 
                          "User manual will be displayed here.\n"
                          "This would contain detailed usage instructions.")
    
    def show_about(self):
        """Show about dialog"""
        about_text = """Game Monitor System v1.0

High-performance game item monitoring system
with real-time OCR and database integration.

Features:
• Sub-second response time
• Advanced OCR processing  
• Real-time data capture
• Performance monitoring
• Statistical analysis

Developed with Python, tkinter, OpenCV, and Tesseract OCR."""
        
        messagebox.showinfo("About Game Monitor", about_text)
    
    def on_closing(self):
        """Handle application closing with proper cleanup"""
        if self.running:
            if messagebox.askokcancel("Quit", "System is running. Stop and quit?"):
                self.stop_system()
                self._perform_cleanup()
                self.root.destroy()
        else:
            self._perform_cleanup()
            self.root.destroy()
    
    def _perform_cleanup(self):
        """Perform comprehensive memory cleanup"""
        if self._cleanup_performed:
            return
            
        try:
            self._is_shutting_down = True
            self._cleanup_performed = True
            
            # Cancel all active timers
            if hasattr(self, 'root') and self.root.winfo_exists():
                for timer_id in self._active_timers.copy():
                    try:
                        self.root.after_cancel(timer_id)
                    except tk.TclError:
                        pass  # Timer already cancelled or completed
                self._active_timers.clear()
            
            # Close all active dialogs
            for dialog in self._active_dialogs.copy():
                try:
                    if hasattr(dialog, 'destroy'):
                        dialog.destroy()
                except tk.TclError:
                    pass  # Dialog already destroyed
            self._active_dialogs.clear()
            
            # Clean up database manager
            if hasattr(self, 'db_manager') and self.db_manager:
                try:
                    self.db_manager.close()
                    self.db_manager = None
                except Exception as e:
                    print(f"Warning: Error closing database manager: {e}")
            
            # Clean up game monitor
            if hasattr(self, 'game_monitor') and self.game_monitor:
                try:
                    if hasattr(self.game_monitor, 'stop'):
                        self.game_monitor.stop()
                    self.game_monitor = None
                except Exception as e:
                    print(f"Warning: Error stopping game monitor: {e}")
            
            # Clean up GUI component references
            if hasattr(self, 'performance_panel') and self.performance_panel:
                self.performance_panel.cleanup()
                self.performance_panel = None
            
            if hasattr(self, 'statistics_panel') and self.statistics_panel:
                self.statistics_panel.cleanup()
                self.statistics_panel = None
            
            self.status_indicators.clear()
            self.log_text = None
            
            # Force garbage collection
            gc.collect()
            
        except Exception as e:
            print(f"Warning: Error during cleanup: {e}")
    
    def __del__(self):
        """Destructor to ensure cleanup on garbage collection"""
        try:
            self._perform_cleanup()
        except Exception:
            pass  # Ignore cleanup errors during destruction
    
    def run(self):
        """Start the GUI application"""
        # Set up close handler
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Configure styles
        style = ttk.Style()
        
        # Create custom button styles
        style.configure("Accent.TButton", foreground="white", background="green")
        style.configure("Emergency.TButton", foreground="white", background="red")
        
        self.add_log_message("GUI started successfully")
        
        try:
            # Start the GUI main loop
            self.root.mainloop()
        finally:
            # Ensure cleanup happens even if mainloop exits unexpectedly
            self._perform_cleanup()
    
    def show_region_selection_dialog(self):
        """Show region selection and calibration interface"""
        if not self.game_monitor:
            messagebox.showerror("Error", "Game Monitor not initialized")
            return
        
        dialog = tk.Toplevel(self.root)
        dialog.title("Region Selection & Calibration")
        dialog.geometry("600x500")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Add to active dialogs for proper cleanup
        self._active_dialogs.add(dialog)
        
        # Set up cleanup on dialog close
        original_destroy = dialog.destroy
        def cleanup_and_destroy():
            self._active_dialogs.discard(dialog)
            original_destroy()
        dialog.destroy = cleanup_and_destroy
        
        # Initialize region manager
        region_manager = RegionManager()
        
        # Main frame
        main_frame = tk.Frame(dialog, padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)
        
        # Title
        title_label = tk.Label(main_frame, text="Screen Region Configuration", 
                              font=('Arial', 14, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # Instructions
        instructions = tk.Label(main_frame, 
                               text="Select regions for different hotkey functions. You can use visual selection or manual coordinate input.",
                               font=('Arial', 10), wraplength=550)
        instructions.pack(pady=(0, 15))
        
        # Region list frame
        regions_frame = ttk.LabelFrame(main_frame, text="Hotkey Regions", padding=15)
        regions_frame.pack(fill="both", expand=True, pady=10)
        
        # Create scrollable frame for regions
        canvas = tk.Canvas(regions_frame)
        scrollbar = ttk.Scrollbar(regions_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Add region entries
        region_configs = [
            ("trader_list", "F1 - Trader List", "Region for capturing trader list"),
            ("item_scan", "F2 - Item Scan", "Region for scanning individual items"),
            ("trader_inventory", "F3 - Trader Inventory", "Region for trader inventory view")
        ]
        
        def update_region(region_name: str, config: RegionConfig):
            """Update region configuration"""
            config.name = region_name
            region_manager.set_region(config)
            self.add_log_message(f"Updated region '{region_name}': {config.x},{config.y} {config.width}x{config.height}")
            
            # Update game monitor regions if available
            if self.game_monitor:
                screen_region = ScreenRegion(config.x, config.y, config.width, config.height, config.name)
                self.game_monitor.screen_regions[region_name] = screen_region
                self.add_log_message(f"Applied region '{region_name}' to game monitor")
        
        def select_region_visual(region_name: str):
            """Start visual region selection"""
            dialog.withdraw()  # Hide dialog during selection
            
            def on_region_selected(config: RegionConfig):
                update_region(region_name, config)
                dialog.deiconify()  # Show dialog again
                update_region_display()
            
            selector = RegionSelector(self.root)
            selector.select_region(region_name, on_region_selected)
        
        def select_region_manual(region_name: str):
            """Start manual coordinate input"""
            current_region = region_manager.get_region(region_name)
            coord_dialog = CoordinateInputDialog(dialog, region_name, current_region)
            result = coord_dialog.show()
            
            if result:
                update_region(region_name, result)
                update_region_display()
        
        def update_region_display():
            """Update the display of current regions"""
            for region_name, _, _ in region_configs:
                region = region_manager.get_region(region_name)
                if region and region_name in region_labels:
                    region_labels[region_name].config(
                        text=f"({region.x}, {region.y}) - {region.width}x{region.height}"
                    )
        
        # Store region label references for updating
        region_labels = {}
        
        for i, (region_name, display_name, description) in enumerate(region_configs):
            # Region frame
            region_frame = tk.Frame(scrollable_frame)
            region_frame.pack(fill="x", pady=5)
            
            # Region info
            info_frame = tk.Frame(region_frame)
            info_frame.pack(side="left", fill="x", expand=True)
            
            name_label = tk.Label(info_frame, text=display_name, font=('Arial', 11, 'bold'))
            name_label.pack(anchor="w")
            
            desc_label = tk.Label(info_frame, text=description, font=('Arial', 9), fg="gray")
            desc_label.pack(anchor="w")
            
            # Current coordinates
            current_region = region_manager.get_region(region_name)
            coord_text = "Not configured"
            if current_region:
                coord_text = f"({current_region.x}, {current_region.y}) - {current_region.width}x{current_region.height}"
            
            coord_label = tk.Label(info_frame, text=coord_text, font=('Arial', 10))
            coord_label.pack(anchor="w")
            region_labels[region_name] = coord_label
            
            # Buttons
            button_frame = tk.Frame(region_frame)
            button_frame.pack(side="right")
            
            tk.Button(button_frame, text="Visual Select", 
                     command=lambda rn=region_name: select_region_visual(rn)).pack(side="right", padx=2)
            tk.Button(button_frame, text="Manual Input", 
                     command=lambda rn=region_name: select_region_manual(rn)).pack(side="right", padx=2)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Control buttons
        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill="x", pady=20)
        
        tk.Button(button_frame, text="Reset to Defaults", 
                 command=lambda: self.reset_regions(region_manager, update_region_display)).pack(side="left")
        
        tk.Button(button_frame, text="Test All Regions", 
                 command=lambda: self.test_all_regions(region_manager)).pack(side="left", padx=10)
        
        tk.Button(button_frame, text="Close", command=dialog.destroy).pack(side="right")
    
    def show_ocr_testing_dialog(self):
        """Show OCR testing interface"""
        if not self.game_monitor:
            messagebox.showerror("Error", "Game Monitor not initialized")
            return
        
        dialog = tk.Toplevel(self.root)
        dialog.title("OCR Testing Interface")
        dialog.geometry("700x600")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Add to active dialogs for proper cleanup
        self._active_dialogs.add(dialog)
        
        # Set up cleanup on dialog close
        original_destroy = dialog.destroy
        def cleanup_and_destroy():
            self._active_dialogs.discard(dialog)
            original_destroy()
        dialog.destroy = cleanup_and_destroy
        
        # Get vision system
        vision_system = get_vision_system()
        
        # Main frame
        main_frame = tk.Frame(dialog, padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)
        
        # Title
        title_label = tk.Label(main_frame, text="OCR Testing & Output", 
                              font=('Arial', 14, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # Testing controls frame
        controls_frame = ttk.LabelFrame(main_frame, text="Testing Controls", padding=15)
        controls_frame.pack(fill="x", pady=10)
        
        # Testing status
        status_frame = tk.Frame(controls_frame)
        status_frame.pack(fill="x", pady=5)
        
        tk.Label(status_frame, text="Testing Output:", font=('Arial', 10, 'bold')).pack(side="left")
        
        status_label = tk.Label(status_frame, text="Disabled", fg="red")
        status_label.pack(side="left", padx=10)
        
        # Control buttons
        button_frame = tk.Frame(controls_frame)
        button_frame.pack(fill="x", pady=10)
        
        def toggle_testing():
            """Toggle testing output"""
            if vision_system.testing_enabled:
                vision_system.enable_testing_output(False)
                status_label.config(text="Disabled", fg="red")
                toggle_button.config(text="Enable Testing")
                self.add_log_message("OCR testing output disabled")
            else:
                vision_system.enable_testing_output(True)
                status_label.config(text="Enabled", fg="green")
                toggle_button.config(text="Disable Testing")
                self.add_log_message("OCR testing output enabled - Check console and files for results")
        
        toggle_button = tk.Button(button_frame, text="Enable Testing", command=toggle_testing)
        toggle_button.pack(side="left", padx=5)
        
        tk.Button(button_frame, text="Clear Output Files", 
                 command=lambda: self.clear_testing_files(vision_system)).pack(side="left", padx=5)
        
        tk.Button(button_frame, text="View Output Folder", 
                 command=self.open_testing_folder).pack(side="left", padx=5)
        
        # Testing info frame
        info_frame = ttk.LabelFrame(main_frame, text="Testing Information", padding=15)
        info_frame.pack(fill="both", expand=True, pady=10)
        
        # Instructions
        instructions = tk.Text(info_frame, height=8, wrap="word", font=('Arial', 10))
        instructions.pack(fill="x", pady=5)
        
        instructions_text = """OCR Testing Instructions:

1. Enable testing output using the button above
2. Use hotkeys (F1-F5) to capture screen regions
3. Check console output for real-time OCR results
4. Check data/testing_output.txt for simple text log
5. Check data/testing_detailed.json for detailed JSON results

Testing will show:
- Raw OCR text extracted from screenshots
- Processing time and confidence scores
- Parsed data results
- Region coordinates and settings

Use this to verify OCR accuracy and tune your regions for optimal results."""
        
        instructions.insert("1.0", instructions_text)
        instructions.config(state="disabled")
        
        # Testing summary frame
        summary_frame = ttk.LabelFrame(main_frame, text="Testing Summary", padding=10)
        summary_frame.pack(fill="x", pady=10)
        
        def update_summary():
            """Update testing summary"""
            summary = vision_system.get_testing_summary()
            summary_text.delete("1.0", tk.END)
            
            summary_info = f"""Testing Status: {'Enabled' if summary['testing_enabled'] else 'Disabled'}
Output File: {summary['output_file']}
Detailed File: {summary['detailed_file']}
Total Tests: {summary.get('total_tests', 0)}
Files Exist: Output={summary['output_file_exists']}, Detailed={summary['detailed_file_exists']}"""
            
            summary_text.insert("1.0", summary_info)
        
        summary_text = tk.Text(summary_frame, height=5, font=('Consolas', 9))
        summary_text.pack(fill="x")
        
        # Auto-update summary with proper timer management
        active_timer_ids = set()
        
        def refresh_summary():
            try:
                if dialog.winfo_exists():
                    update_summary()
                    # Schedule next refresh
                    timer_id = dialog.after(2000, refresh_summary)
                    active_timer_ids.add(timer_id)
            except tk.TclError:
                # Dialog was destroyed, stop scheduling updates
                pass
        
        # Set up cleanup when dialog closes
        def on_dialog_destroy():
            for timer_id in active_timer_ids.copy():
                try:
                    dialog.after_cancel(timer_id)
                except tk.TclError:
                    pass
            active_timer_ids.clear()
            dialog.destroy()
        
        dialog.protocol("WM_DELETE_WINDOW", on_dialog_destroy)
        refresh_summary()
        
        # Close button
        tk.Button(main_frame, text="Close", command=dialog.destroy).pack(pady=10)
        
        # Set initial testing status
        if vision_system.testing_enabled:
            status_label.config(text="Enabled", fg="green")
            toggle_button.config(text="Disable Testing")
    
    def reset_regions(self, region_manager: RegionManager, update_callback):
        """Reset regions to defaults"""
        if messagebox.askyesno("Reset Regions", "Reset all regions to default coordinates?"):
            region_manager.set_default_regions()
            update_callback()
            self.add_log_message("All regions reset to defaults")
    
    def test_all_regions(self, region_manager: RegionManager):
        """Test all configured regions"""
        regions = region_manager.list_regions()
        if not regions:
            messagebox.showwarning("No Regions", "No regions configured to test")
            return
        
        self.add_log_message("Testing all configured regions...")
        
        # Enable testing output temporarily
        vision_system = get_vision_system()
        was_enabled = vision_system.testing_enabled
        if not was_enabled:
            vision_system.enable_testing_output(True)
        
        # Test each region
        for region in regions:
            screen_region = ScreenRegion(region.x, region.y, region.width, region.height, region.name)
            self.add_log_message(f"Testing region: {region.name}")
            
            # Simulate region processing (would normally be triggered by hotkey)
            try:
                result = vision_system.capture_and_process_region(screen_region, 'general')
                if result:
                    self.add_log_message(f"✓ {region.name}: Success")
                else:
                    self.add_log_message(f"✗ {region.name}: No data extracted")
            except Exception as e:
                self.add_log_message(f"✗ {region.name}: Error - {e}")
        
        # Restore testing state
        if not was_enabled:
            vision_system.enable_testing_output(False)
        
        messagebox.showinfo("Testing Complete", "Region testing completed. Check console and log files for results.")
    
    def clear_testing_files(self, vision_system):
        """Clear testing output files"""
        if messagebox.askyesno("Clear Files", "Clear all testing output files?"):
            vision_system.clear_testing_output()
            self.add_log_message("Testing output files cleared")
    
    def open_testing_folder(self):
        """Open testing output folder"""
        import subprocess
        import platform
        
        folder_path = "data"
        
        try:
            if platform.system() == "Windows":
                subprocess.run(["explorer", folder_path])
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", folder_path])
            else:  # Linux
                subprocess.run(["xdg-open", folder_path])
        except Exception as e:
            messagebox.showerror("Error", f"Could not open folder: {e}")
            self.add_log_message(f"Failed to open testing folder: {e}")


def main():
    """Main entry point for GUI application"""
    try:
        app = MainWindow()
        app.run()
    except Exception as e:
        print(f"Failed to start GUI: {e}")
        messagebox.showerror("Startup Error", f"Failed to start application:\n{e}")


if __name__ == "__main__":
    main()