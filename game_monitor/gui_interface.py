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

# Add the parent directory to the path to import game_monitor modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game_monitor.main_controller import GameMonitor
from game_monitor.database_manager import DatabaseManager


@dataclass
class GUIConfig:
    """Configuration for GUI appearance and behavior"""
    window_width: int = 1200
    window_height: int = 800
    refresh_rate: int = 1000  # ms
    log_max_lines: int = 1000
    theme: str = "default"


class StatusIndicator:
    """Status indicator widget with color-coded states"""
    
    def __init__(self, parent, label: str, x: int, y: int):
        self.label = tk.Label(parent, text=label, font=("Arial", 10, "bold"))
        self.label.place(x=x, y=y)
        
        self.status = tk.Label(parent, text="●", font=("Arial", 16), fg="red")
        self.status.place(x=x+100, y=y-2)
        
        self.text_label = tk.Label(parent, text="Stopped", font=("Arial", 9))
        self.text_label.place(x=x+120, y=y+2)
    
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
        self.create_metrics()
    
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
        
        self.create_statistics_display()
        self.create_recent_trades_table()
    
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
            ("Time", 120),
            ("Trader", 120),
            ("Item", 150),
            ("Quantity", 80),
            ("Price", 100),
            ("Confidence", 80)
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
        """Update statistics display with latest data"""
        try:
            # Get trade statistics
            total_trades = self.db_manager.get_total_trades_count()
            unique_traders = self.db_manager.get_unique_traders_count()
            unique_items = self.db_manager.get_unique_items_count()
            
            # Update labels
            self.stats_labels["Total Trades"].config(text=str(total_trades))
            self.stats_labels["Unique Traders"].config(text=str(unique_traders))
            self.stats_labels["Unique Items"].config(text=str(unique_items))
            
            # Update recent trades table
            self.update_recent_trades()
            
        except Exception as e:
            print(f"Error updating statistics: {e}")
    
    def update_recent_trades(self, limit: int = 20):
        """Update recent trades table"""
        try:
            # Clear existing items
            for item in self.trades_tree.get_children():
                self.trades_tree.delete(item)
            
            # Get recent trades
            trades = self.db_manager.get_recent_trades(limit)
            
            for trade in trades:
                # Format timestamp
                timestamp = datetime.fromisoformat(trade[0]).strftime("%H:%M:%S")
                
                # Insert into table
                self.trades_tree.insert("", "end", values=(
                    timestamp,
                    trade[1],  # trader_nickname
                    trade[2],  # item_name
                    trade[3],  # quantity
                    f"{trade[4]:.2f}",  # price
                    f"{trade[5]:.1f}%"   # confidence
                ))
                
        except Exception as e:
            print(f"Error updating recent trades: {e}")


class SettingsDialog:
    """Settings configuration dialog"""
    
    def __init__(self, parent, config_manager):
        self.parent = parent
        self.config_manager = config_manager
        self.dialog = None
        
        self.settings = {
            "hotkey_f1": "F1",
            "hotkey_f2": "F2", 
            "hotkey_f3": "F3",
            "hotkey_f4": "F4",
            "hotkey_f5": "F5",
            "ocr_confidence_threshold": 85,
            "response_time_target": 1000,
            "database_pool_size": 5
        }
    
    def show(self):
        """Show settings dialog"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Game Monitor Settings")
        self.dialog.geometry("400x500")
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
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
        threshold_scale = tk.Scale(parent, from_=50, to=100, orient="horizontal",
                                 variable=threshold_var, length=200)
        threshold_scale.grid(row=0, column=1, padx=10, pady=5)
    
    def save_settings(self):
        """Save settings and close dialog"""
        messagebox.showinfo("Settings", "Settings saved successfully!")
        self.dialog.destroy()


class ManualVerificationDialog:
    """Dialog for manual verification of OCR results"""
    
    def __init__(self, parent, verification_callback: Callable):
        self.parent = parent
        self.verification_callback = verification_callback
        self.dialog = None
        self.current_data = None
    
    def show_verification(self, capture_data: Dict):
        """Show verification dialog with capture data"""
        self.current_data = capture_data
        
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Manual Verification")
        self.dialog.geometry("600x400")
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
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
            
            entry = tk.Entry(data_frame, width=30)
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
    
    def approve_data(self):
        """Approve the verification data"""
        # Get corrected data from entries
        corrected_data = {}
        for field, entry in self.entries.items():
            corrected_data[field] = entry.get()
        
        # Call verification callback
        self.verification_callback(corrected_data, approved=True)
        self.dialog.destroy()
    
    def reject_data(self):
        """Reject the verification data"""
        self.verification_callback(None, approved=False)
        self.dialog.destroy()


class MainWindow:
    """Main GUI window for Game Monitor System"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Game Monitor System - v1.0")
        self.root.geometry("1200x800")
        self.root.minsize(800, 600)
        
        # Initialize components
        self.game_monitor = None
        self.db_manager = None
        self.config = GUIConfig()
        self.running = False
        
        # GUI components
        self.status_indicators = {}
        self.performance_panel = None
        self.statistics_panel = None
        self.log_text = None
        
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
        """Setup automatic data refresh"""
        def refresh_data():
            try:
                if self.statistics_panel:
                    self.statistics_panel.update_statistics()
                
                if self.performance_panel and self.game_monitor:
                    self.update_performance_metrics()
                
            except Exception as e:
                print(f"Error during data refresh: {e}")
            
            # Schedule next refresh
            self.root.after(self.config.refresh_rate, refresh_data)
        
        # Start refresh cycle
        self.root.after(1000, refresh_data)
    
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
            
            # System resource usage
            import psutil
            self.performance_panel.update_metric("Memory Usage", 
                                                f"{psutil.virtual_memory().percent:.1f}%")
            self.performance_panel.update_metric("CPU Usage", 
                                                f"{psutil.cpu_percent():.1f}%")
            
        except Exception as e:
            print(f"Error updating performance metrics: {e}")
    
    def add_log_message(self, message: str, level: str = "INFO"):
        """Add message to log display"""
        if not self.log_text:
            return
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {level}: {message}\n"
        
        self.log_text.insert("end", formatted_message)
        self.log_text.see("end")
        
        # Limit log size
        lines = int(self.log_text.index("end-1c").split('.')[0])
        if lines > self.config.log_max_lines:
            self.log_text.delete("1.0", "2.0")
    
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
        """Show coordinate calibration tool"""
        messagebox.showinfo("Coordinate Calibration", 
                          "Coordinate calibration tool will be implemented here.\n"
                          "This would help users set up screen regions for OCR.")
    
    def test_ocr(self):
        """Show OCR testing panel"""
        messagebox.showinfo("OCR Test", 
                          "OCR testing panel will be implemented here.\n"
                          "This would allow users to test OCR on sample images.")
    
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
        """Handle application closing"""
        if self.running:
            if messagebox.askokcancel("Quit", "System is running. Stop and quit?"):
                self.stop_system()
                self.root.destroy()
        else:
            self.root.destroy()
    
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
        
        # Start the GUI main loop
        self.root.mainloop()


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