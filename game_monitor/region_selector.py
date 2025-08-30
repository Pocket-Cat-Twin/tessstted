"""
Region Selection Interface for Game Monitor System

Interactive visual overlay for selecting screen regions with mouse,
manual coordinate input, and region management capabilities.
"""

import tkinter as tk
from tkinter import messagebox, simpledialog
import threading
import time
from typing import Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass
import json
from pathlib import Path

try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False


@dataclass
class RegionConfig:
    """Configuration for a screen region"""
    name: str
    x: int
    y: int
    width: int
    height: int
    hotkey: str = ""
    description: str = ""


class RegionSelector:
    """Interactive region selection overlay"""
    
    def __init__(self, parent=None):
        self.parent = parent
        self.overlay_window = None
        self.canvas = None
        self.selection_active = False
        self.start_x = 0
        self.start_y = 0
        self.end_x = 0
        self.end_y = 0
        self.selection_rect = None
        self.callback = None
        self.region_name = ""
        
        # Get screen dimensions
        if PYAUTOGUI_AVAILABLE:
            self.screen_width, self.screen_height = pyautogui.size()
        else:
            self.screen_width, self.screen_height = 1920, 1080  # Fallback
    
    def select_region(self, region_name: str, callback: Callable[[RegionConfig], None]):
        """Start interactive region selection"""
        self.region_name = region_name
        self.callback = callback
        
        # Create overlay window
        self.overlay_window = tk.Toplevel()
        self.overlay_window.title("Select Region - " + region_name)
        self.overlay_window.attributes('-fullscreen', True)
        self.overlay_window.attributes('-topmost', True)
        self.overlay_window.attributes('-alpha', 0.3)  # Semi-transparent
        self.overlay_window.configure(bg='black')
        
        # Create canvas for drawing selection
        self.canvas = tk.Canvas(
            self.overlay_window,
            width=self.screen_width,
            height=self.screen_height,
            bg='black',
            highlightthickness=0
        )
        self.canvas.pack()
        
        # Add instruction text
        instruction_text = f"Drag to select region for {region_name}\nPress ESC to cancel, ENTER to confirm"
        self.canvas.create_text(
            self.screen_width // 2, 50,
            text=instruction_text,
            fill='white',
            font=('Arial', 16, 'bold'),
            anchor='center'
        )
        
        # Bind events
        self.canvas.bind('<Button-1>', self.on_mouse_press)
        self.canvas.bind('<B1-Motion>', self.on_mouse_drag)
        self.canvas.bind('<ButtonRelease-1>', self.on_mouse_release)
        self.overlay_window.bind('<KeyPress-Escape>', self.cancel_selection)
        self.overlay_window.bind('<KeyPress-Return>', self.confirm_selection)
        
        # Focus the window to receive key events
        self.overlay_window.focus_set()
        self.canvas.focus_set()
    
    def on_mouse_press(self, event):
        """Handle mouse press - start selection"""
        self.selection_active = True
        self.start_x = event.x
        self.start_y = event.y
        
        # Clear previous selection
        if self.selection_rect:
            self.canvas.delete(self.selection_rect)
    
    def on_mouse_drag(self, event):
        """Handle mouse drag - update selection rectangle"""
        if not self.selection_active:
            return
        
        self.end_x = event.x
        self.end_y = event.y
        
        # Clear previous rectangle
        if self.selection_rect:
            self.canvas.delete(self.selection_rect)
        
        # Draw new selection rectangle
        self.selection_rect = self.canvas.create_rectangle(
            self.start_x, self.start_y, self.end_x, self.end_y,
            outline='red', width=3, fill='red', stipple='gray25'
        )
        
        # Display coordinates
        width = abs(self.end_x - self.start_x)
        height = abs(self.end_y - self.start_y)
        coord_text = f"({min(self.start_x, self.end_x)}, {min(self.start_y, self.end_y)}) - {width}x{height}"
        
        # Remove previous coordinate text
        self.canvas.delete("coord_text")
        self.canvas.create_text(
            self.screen_width // 2, self.screen_height - 50,
            text=coord_text,
            fill='white',
            font=('Arial', 14, 'bold'),
            anchor='center',
            tags="coord_text"
        )
    
    def on_mouse_release(self, event):
        """Handle mouse release - end selection"""
        self.selection_active = False
        self.end_x = event.x
        self.end_y = event.y
    
    def confirm_selection(self, event=None):
        """Confirm and return the selected region"""
        if not self.selection_rect:
            messagebox.showwarning("No Selection", "Please select a region first")
            return
        
        # Calculate region coordinates
        x = min(self.start_x, self.end_x)
        y = min(self.start_y, self.end_y)
        width = abs(self.end_x - self.start_x)
        height = abs(self.end_y - self.start_y)
        
        # Validate selection
        if width < 10 or height < 10:
            messagebox.showwarning("Invalid Selection", "Selected region is too small (minimum 10x10)")
            return
        
        # Create region config
        region = RegionConfig(
            name=self.region_name,
            x=x, y=y, width=width, height=height,
            description=f"Selected region for {self.region_name}"
        )
        
        # Close overlay
        self.close_overlay()
        
        # Call callback with result
        if self.callback:
            self.callback(region)
    
    def cancel_selection(self, event=None):
        """Cancel selection and close overlay"""
        self.close_overlay()
    
    def close_overlay(self):
        """Close the overlay window"""
        if self.overlay_window:
            self.overlay_window.destroy()
            self.overlay_window = None
        self.canvas = None
        self.selection_rect = None


class CoordinateInputDialog:
    """Dialog for manual coordinate input"""
    
    def __init__(self, parent, region_name: str = "", initial_region: RegionConfig = None):
        self.parent = parent
        self.region_name = region_name
        self.initial_region = initial_region
        self.dialog = None
        self.result = None
        
        # Entry variables
        self.x_var = tk.IntVar()
        self.y_var = tk.IntVar()
        self.width_var = tk.IntVar()
        self.height_var = tk.IntVar()
        
        # Set initial values if provided
        if initial_region:
            self.x_var.set(initial_region.x)
            self.y_var.set(initial_region.y)
            self.width_var.set(initial_region.width)
            self.height_var.set(initial_region.height)
    
    def show(self) -> Optional[RegionConfig]:
        """Show dialog and return selected region"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title(f"Enter Coordinates - {self.region_name}")
        self.dialog.geometry("400x300")
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        self.create_interface()
        
        # Wait for dialog to complete
        self.dialog.wait_window()
        
        return self.result
    
    def create_interface(self):
        """Create coordinate input interface"""
        main_frame = tk.Frame(self.dialog, padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)
        
        # Title
        title_label = tk.Label(main_frame, text=f"Region Coordinates for {self.region_name}", 
                              font=('Arial', 12, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # Coordinate inputs
        input_frame = tk.Frame(main_frame)
        input_frame.pack(fill="x", pady=10)
        
        # X coordinate
        tk.Label(input_frame, text="X (Left):", width=12, anchor="w").grid(row=0, column=0, padx=5, pady=5)
        x_entry = tk.Entry(input_frame, textvariable=self.x_var, width=10)
        x_entry.grid(row=0, column=1, padx=5, pady=5)
        
        # Y coordinate  
        tk.Label(input_frame, text="Y (Top):", width=12, anchor="w").grid(row=1, column=0, padx=5, pady=5)
        y_entry = tk.Entry(input_frame, textvariable=self.y_var, width=10)
        y_entry.grid(row=1, column=1, padx=5, pady=5)
        
        # Width
        tk.Label(input_frame, text="Width:", width=12, anchor="w").grid(row=2, column=0, padx=5, pady=5)
        width_entry = tk.Entry(input_frame, textvariable=self.width_var, width=10)
        width_entry.grid(row=2, column=1, padx=5, pady=5)
        
        # Height
        tk.Label(input_frame, text="Height:", width=12, anchor="w").grid(row=3, column=0, padx=5, pady=5)
        height_entry = tk.Entry(input_frame, textvariable=self.height_var, width=10)
        height_entry.grid(row=3, column=1, padx=5, pady=5)
        
        # Preview button
        preview_button = tk.Button(main_frame, text="Preview Region", command=self.preview_region)
        preview_button.pack(pady=10)
        
        # Instructions
        instructions = tk.Label(main_frame, 
                               text="Enter coordinates manually or use Preview to see the selected area",
                               font=('Arial', 9), wraplength=350)
        instructions.pack(pady=10)
        
        # Buttons
        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill="x", pady=20)
        
        tk.Button(button_frame, text="OK", command=self.confirm_coordinates).pack(side="right", padx=5)
        tk.Button(button_frame, text="Cancel", command=self.cancel_dialog).pack(side="right", padx=5)
        
        # Focus first entry
        x_entry.focus_set()
    
    def preview_region(self):
        """Show preview of the selected region"""
        try:
            x = self.x_var.get()
            y = self.y_var.get() 
            width = self.width_var.get()
            height = self.height_var.get()
            
            # Validate coordinates
            if width <= 0 or height <= 0:
                messagebox.showwarning("Invalid Input", "Width and height must be positive numbers")
                return
            
            # Create preview window
            preview = tk.Toplevel(self.dialog)
            preview.title("Region Preview")
            preview.geometry(f"{width+20}x{height+40}+{x}+{y}")
            preview.configure(bg='red')
            preview.attributes('-topmost', True)
            preview.attributes('-alpha', 0.7)
            
            # Add label
            label = tk.Label(preview, text=f"Preview: {self.region_name}\n{x},{y} - {width}x{height}",
                           bg='red', fg='white', font=('Arial', 10, 'bold'))
            label.pack(expand=True)
            
            # Auto-close after 3 seconds
            preview.after(3000, preview.destroy)
            
        except tk.TclError:
            messagebox.showerror("Invalid Input", "Please enter valid numeric coordinates")
    
    def confirm_coordinates(self):
        """Confirm and return coordinates"""
        try:
            x = self.x_var.get()
            y = self.y_var.get()
            width = self.width_var.get()  
            height = self.height_var.get()
            
            # Validate
            if width <= 0 or height <= 0:
                messagebox.showwarning("Invalid Input", "Width and height must be positive")
                return
                
            if x < 0 or y < 0:
                messagebox.showwarning("Invalid Input", "X and Y coordinates must be non-negative")
                return
            
            # Create region config
            self.result = RegionConfig(
                name=self.region_name,
                x=x, y=y, width=width, height=height,
                description=f"Manual input for {self.region_name}"
            )
            
            self.dialog.destroy()
            
        except tk.TclError:
            messagebox.showerror("Invalid Input", "Please enter valid numeric values")
    
    def cancel_dialog(self):
        """Cancel dialog"""
        self.result = None
        self.dialog.destroy()


class RegionManager:
    """Manage region configurations and persistence"""
    
    def __init__(self, config_path: str = "config/regions.yaml"):
        self.config_path = Path(config_path)
        self.regions = {}
        self.load_regions()
    
    def load_regions(self):
        """Load regions from configuration file"""
        if self.config_path.exists():
            try:
                import yaml
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    if data and 'regions' in data:
                        for name, region_data in data['regions'].items():
                            self.regions[name] = RegionConfig(
                                name=name,
                                x=region_data['x'],
                                y=region_data['y'],
                                width=region_data['width'],
                                height=region_data['height'],
                                hotkey=region_data.get('hotkey', ''),
                                description=region_data.get('description', '')
                            )
            except Exception as e:
                print(f"Error loading regions: {e}")
        
        # Set default regions if none loaded
        if not self.regions:
            self.set_default_regions()
    
    def set_default_regions(self):
        """Set default region configurations"""
        defaults = {
            'trader_list': RegionConfig('trader_list', 100, 200, 600, 400, 'F1', 'Trader list region'),
            'item_scan': RegionConfig('item_scan', 200, 150, 500, 300, 'F2', 'Item scan region'),
            'trader_inventory': RegionConfig('trader_inventory', 300, 250, 700, 500, 'F3', 'Trader inventory region')
        }
        self.regions.update(defaults)
    
    def save_regions(self):
        """Save regions to configuration file"""
        try:
            # Ensure directory exists
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert to dict format
            data = {
                'regions': {
                    name: {
                        'x': region.x,
                        'y': region.y,
                        'width': region.width,
                        'height': region.height,
                        'hotkey': region.hotkey,
                        'description': region.description
                    }
                    for name, region in self.regions.items()
                }
            }
            
            import yaml
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, default_flow_style=False)
                
        except Exception as e:
            print(f"Error saving regions: {e}")
    
    def get_region(self, name: str) -> Optional[RegionConfig]:
        """Get region by name"""
        return self.regions.get(name)
    
    def set_region(self, region: RegionConfig):
        """Set/update region"""
        self.regions[region.name] = region
        self.save_regions()
    
    def delete_region(self, name: str):
        """Delete region"""
        if name in self.regions:
            del self.regions[name]
            self.save_regions()
    
    def list_regions(self) -> List[RegionConfig]:
        """Get list of all regions"""
        return list(self.regions.values())