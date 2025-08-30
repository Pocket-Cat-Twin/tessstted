#!/usr/bin/env python3
"""
GUI Launcher for Game Monitor System
Simple launcher script to start the GUI interface
"""

import sys
import os

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    """Launch the GUI interface"""
    try:
        # Import and run GUI
        from game_monitor.gui_interface import main as gui_main
        gui_main()
    except ImportError as e:
        print(f"Error importing GUI interface: {e}")
        print("Make sure all dependencies are installed:")
        print("pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"Error starting GUI: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()