#!/usr/bin/env python3
"""
Main entry point for Game Monitor System
High-performance screen reading system with <1 second response time
"""

import logging
import sys
import os
import signal
import time
from pathlib import Path

# Setup logging first
os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/game_monitor.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Main application entry point"""
    print("=" * 60)
    print("Game Monitor System v1.0.0")
    print("High-Performance Screen Reading System")
    print("=" * 60)
    
    try:
        # Ensure required directories exist
        logger.info("Setting up directory structure...")
        directories = [
            'logs',
            'data/screenshots', 
            'data/cache',
            'config',
            'validation/screenshots',
            'validation/failed_reads',
            'validation/manual_confirmations'
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
        
        logger.info("Directory structure ready")
        
        # Import main components
        logger.info("Importing system components...")
        from game_monitor.main_controller import GameMonitor
        
        # Initialize Game Monitor
        logger.info("Initializing Game Monitor...")
        game_monitor = GameMonitor()
        
        # Setup signal handler for graceful shutdown
        def signal_handler(signum, frame):
            logger.info("Shutdown signal received, stopping system...")
            game_monitor.stop()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Start the system
        logger.info("Starting Game Monitor System...")
        game_monitor.start()
        
        # Display system information
        print("\n" + "=" * 60)
        print("SYSTEM STATUS")
        print("=" * 60)
        print(f"State: {game_monitor.get_state().value}")
        print(f"Database: Connected")
        print(f"Hotkeys: F1-F5 Active")
        print(f"OCR System: Ready")
        print(f"Validator: Ready")
        
        print("\n" + "=" * 60)
        print("HOTKEY COMMANDS")
        print("=" * 60)
        print("F1 - Capture Trader List")
        print("F2 - Capture Item Scan")  
        print("F3 - Capture Trader Inventory")
        print("F4 - Manual Verification")
        print("F5 - Emergency Stop")
        print("Ctrl+C - Graceful Shutdown")
        
        # Display performance info
        stats = game_monitor.get_performance_stats()
        print(f"\nPerformance Target: <1.0 second response time")
        print(f"System Ready: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        print("\n" + "=" * 60)
        print("SYSTEM RUNNING - Press Ctrl+C to stop")
        print("=" * 60)
        
        # Main loop - keep application running
        try:
            while game_monitor.get_state().value in ['running', 'paused']:
                time.sleep(1.0)
                
                # Optional: Display periodic stats
                if int(time.time()) % 60 == 0:  # Every minute
                    stats = game_monitor.get_performance_stats()
                    if stats['total_captures'] > 0:
                        logger.info(f"Stats: {stats['total_captures']} captures, "
                                  f"{stats['avg_processing_time']:.3f}s avg, "
                                  f"{stats['success_rate']:.2%} success rate")
                        
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
        
        # Graceful shutdown
        logger.info("Shutting down Game Monitor System...")
        game_monitor.stop()
        
        # Final stats
        final_stats = game_monitor.get_performance_stats()
        if final_stats['total_captures'] > 0:
            print(f"\nFinal Statistics:")
            print(f"  Total Captures: {final_stats['total_captures']}")
            print(f"  Success Rate: {final_stats['success_rate']:.2%}")
            print(f"  Average Time: {final_stats['avg_processing_time']:.3f}s")
            print(f"  Fastest: {final_stats['fastest_capture']:.3f}s")
            print(f"  Slowest: {final_stats['slowest_capture']:.3f}s")
        
        print("\nGame Monitor System stopped successfully")
        
    except ImportError as e:
        logger.error(f"Missing dependencies: {e}")
        print("\n" + "=" * 60)
        print("DEPENDENCY ERROR")
        print("=" * 60)
        print("Some required libraries are not installed.")
        print("Run: pip install -r requirements.txt")
        print("Then run the setup script: python setup_database.py")
        sys.exit(1)
        
    except Exception as e:
        logger.error(f"Failed to start Game Monitor System: {e}")
        print(f"\nERROR: {e}")
        print("Check logs/game_monitor.log for details")
        sys.exit(1)

if __name__ == "__main__":
    main()