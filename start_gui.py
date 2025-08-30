#!/usr/bin/env python3
"""
Simple GUI starter for Game Monitor System
Use this if other launch methods don't work
"""

import sys
import os
from pathlib import Path

# Ensure we're in the right directory
project_root = Path(__file__).parent
os.chdir(project_root)
sys.path.insert(0, str(project_root))

def main():
    """Start the GUI"""
    print("🚀 Starting Game Monitor GUI...")
    print(f"📁 Working directory: {os.getcwd()}")
    
    try:
        # Import and start GUI
        from game_monitor.gui_interface import MainWindow
        
        print("✅ GUI modules loaded successfully")
        
        # Create and run the application
        app = MainWindow()
        print("✅ GUI application created")
        
        print("🎯 Starting GUI main loop...")
        app.run()
        
    except ImportError as e:
        print(f"❌ Import Error: {e}")
        print("\n📋 Try installing dependencies:")
        print("   pip install tkinter")  # Usually built-in
        print("   pip install -r requirements.txt")
        
    except Exception as e:
        print(f"❌ Error starting GUI: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()