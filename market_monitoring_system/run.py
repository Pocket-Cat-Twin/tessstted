#!/usr/bin/env python3
"""
Launcher script for the Market Monitoring System.
Handles proper Python path setup and module execution.
"""

import sys
import os
from pathlib import Path

def setup_python_path():
    """Setup Python path for proper module imports."""
    # Get the project root directory
    project_root = Path(__file__).parent.absolute()
    
    # Add src directory to Python path
    src_path = project_root / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))
    
    # Change to project root directory
    os.chdir(project_root)

def main():
    """Main entry point."""
    setup_python_path()
    
    # Import and run the main application
    try:
        from main import main as app_main
        return app_main()
    except ImportError as e:
        print(f"Error importing main application: {e}")
        print("Make sure you're running from the project root directory.")
        return 1
    except Exception as e:
        print(f"Application error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())