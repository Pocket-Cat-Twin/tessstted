"""
Game Monitor Package Main Entry Point
Allows running the package with python -m game_monitor
"""

import sys
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def main():
    """Main entry point for the game monitor package"""
    parser = argparse.ArgumentParser(description='Game Monitor System')
    parser.add_argument('--gui', action='store_true', help='Start GUI interface')
    parser.add_argument('--console', action='store_true', help='Start console interface')
    parser.add_argument('--test', action='store_true', help='Run system tests')
    parser.add_argument('--setup', action='store_true', help='Setup database')
    
    args = parser.parse_args()
    
    try:
        if args.gui:
            print("Starting GUI interface...")
            from .gui_interface import main as gui_main
            gui_main()
        elif args.console:
            print("Starting console interface...")
            from . import main_controller
            # Import and run main console interface
            import main
            main.main()
        elif args.test:
            print("Running system tests...")
            import test_region_features
            test_region_features.main()
        elif args.setup:
            print("Setting up database...")
            import setup_database
            setup_database.main()
        else:
            # Default: show help and start GUI
            print("Game Monitor System v1.0")
            print("=" * 40)
            print("Available options:")
            print("  --gui      Start GUI interface (default)")
            print("  --console  Start console interface") 
            print("  --test     Run system tests")
            print("  --setup    Setup database")
            print()
            print("Starting GUI interface by default...")
            from .gui_interface import main as gui_main
            gui_main()
            
    except ImportError as e:
        print(f"Import error: {e}")
        print("Please install dependencies: pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()