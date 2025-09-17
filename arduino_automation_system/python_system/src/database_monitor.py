"""
Database Monitor Thread for Arduino Automation System
READ-ONLY monitoring of sellers_current for unique trader names
"""

import threading
import time
import logging
import random
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from arduino_controller import ArduinoController, DelayManager
from database_integration import AutomationDatabaseManager
from tesseract_ocr import TesseractOCRManager, OCRRegion, OCRResult


@dataclass
class TraderSequence:
    """Data structure for trader automation sequence"""
    trader_name: str
    processed_at: Optional[float] = None
    ocr_change_detected: bool = False
    mouse_pattern_completed: bool = False


class DatabaseMonitorThread:
    """
    Refactored database monitor thread.
    READ-ONLY monitoring of sellers_current for unique trader names.
    
    New Logic:
    1. Monitor sellers_current table (READ-ONLY)
    2. Sort traders: NEW first (newest first), then others (newest first)
    3. Deduplicate trader names, keeping first occurrence
    4. Process each trader: /target <trader_name>
    5. Wait for OCR change (50% threshold)
    6. Execute 9-step mouse pattern: move right + hotkey each step
    """
    
    def __init__(self, arduino_controller: ArduinoController,
                 db_manager: AutomationDatabaseManager,
                 ocr_manager: TesseractOCRManager,
                 config: Dict[str, Any]):
        """
        Initialize database monitor thread.
        
        Args:
            arduino_controller: Arduino communication controller
            db_manager: Database manager (READ-ONLY access)
            ocr_manager: OCR manager for screen monitoring
            config: Configuration dictionary
        """
        self.arduino = arduino_controller
        self.db_manager = db_manager
        self.ocr_manager = ocr_manager
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Thread control
        self.is_running = False
        self.thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # NEW: Trader sequence management (READ-ONLY)
        self.trader_sequence: List[str] = []
        self.current_trader_index: int = 0
        self.last_db_hash: str = ""
        self.active_trader_session: Optional[TraderSequence] = None
        
        # Configuration
        self.polling_interval_minutes = 1  # Check database every minute
        
        # Mouse pattern configuration
        automation_config = config.get('automation', {})
        mouse_config = automation_config.get('mouse_pattern', {})
        self.mouse_movement_pixels = mouse_config.get('pixels_per_step', 50)
        self.mouse_movement_delay_ms = mouse_config.get('delay_between_steps_ms', 500)
        
        # Hotkey configuration
        hotkeys_config = automation_config.get('hotkeys', {})
        self.main_hotkey = hotkeys_config.get('main_hotkey', 'F1')
        
        # OCR setup
        self._setup_ocr_monitor()
        
        # Statistics
        self.stats = {
            'traders_processed': 0,
            'sequences_completed': 0,
            'ocr_changes_detected': 0,
            'mouse_patterns_executed': 0,
            'database_updates': 0,
            'session_start_time': None
        }
    
    def _setup_ocr_monitor(self) -> None:
        """Setup OCR monitor with 50% change threshold."""
        try:
            ocr_region_config = self.config.get('automation', {}).get('coordinates', {}).get('ocr_region', {})
            ocr_region = OCRRegion(
                x=ocr_region_config.get('x', 0),
                y=ocr_region_config.get('y', 0),
                width=ocr_region_config.get('width', 200),
                height=ocr_region_config.get('height', 100)
            )
            
            self.ocr_monitor = self.ocr_manager.create_screen_monitor(
                name="trader_monitor_ocr",
                region=ocr_region
            )
            
            # Set 50% threshold for character changes
            self.ocr_monitor.change_threshold_percent = 50
            self.ocr_monitor.add_change_callback(self._on_ocr_change_detected)
            
            self.logger.info(f"OCR monitor setup for region: {ocr_region.x},{ocr_region.y} {ocr_region.width}x{ocr_region.height} (50% threshold)")
            
        except Exception as e:
            self.logger.error(f"Failed to setup OCR monitor: {e}")
            self.ocr_monitor = None
    
    def _on_ocr_change_detected(self, new_result: OCRResult, old_result: Optional[OCRResult]) -> None:
        """
        Handle OCR change detection - trigger mouse pattern.
        
        Args:
            new_result: New OCR result
            old_result: Previous OCR result
        """
        if not self.active_trader_session:
            return
        
        trader_name = self.active_trader_session.trader_name
        self.logger.info(f"OCR change detected for trader: {trader_name}")
        self.logger.debug(f"OCR change: '{old_result.text if old_result else 'None'}' -> '{new_result.text}'")
        
        self.active_trader_session.ocr_change_detected = True
        self.stats['ocr_changes_detected'] += 1
        
        # Execute mouse pattern immediately
        self._execute_mouse_pattern()
    
    def start(self) -> None:
        """Start trader monitoring thread."""
        if self.is_running:
            self.logger.warning("Database monitor thread already running")
            return
        
        self.is_running = True
        self._stop_event.clear()
        self.stats['session_start_time'] = time.time()
        
        # Start OCR monitoring
        if self.ocr_monitor:
            self.ocr_monitor.start_monitoring(interval=0.5)  # Check OCR every 500ms
        
        # Start main thread
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        
        self.logger.info("Trader monitor thread started (READ-ONLY database access)")
    
    def stop(self) -> None:
        """Stop trader monitoring thread."""
        if not self.is_running:
            return
        
        self.is_running = False
        self._stop_event.set()
        
        # Stop OCR monitoring
        if self.ocr_monitor:
            self.ocr_monitor.stop_monitoring()
        
        # Wait for thread to finish
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=10.0)
        
        self.logger.info("Trader monitor thread stopped")
    
    def _run_loop(self) -> None:
        """Main monitoring loop - checks database every minute."""
        self.logger.info("Trader monitor loop started (1-minute polling interval)")
        
        while self.is_running and not self._stop_event.is_set():
            try:
                # Check for database changes (every minute)
                self._update_trader_sequence_if_changed()
                
                # Process next trader if no active session
                if not self.active_trader_session and self.trader_sequence:
                    self._start_next_trader_session()
                
                # Wait 1 minute before next database check
                self._stop_event.wait(60.0)  # 1 minute polling
                
            except Exception as e:
                self.logger.error(f"Trader monitor loop error: {e}")
                time.sleep(5.0)
        
        self.logger.info("Trader monitor loop ended")
    
    def _update_trader_sequence_if_changed(self) -> None:
        """Update trader sequence if database changed with detailed logging."""
        try:
            # Get current traders from database (READ-ONLY)
            current_traders = self.db_manager.get_traders_sorted_unique()
            current_hash = self.db_manager.calculate_traders_hash(current_traders)
            
            # Check if database changed
            if current_hash != self.last_db_hash:
                # Log detailed sequence for verification
                self.logger.info(f"Database changed: {len(current_traders)} unique traders found")
                
                # Get debug info to verify sorting
                if self.logger.isEnabledFor(logging.DEBUG):
                    debug_info = self.db_manager.get_traders_debug_info()
                    self.logger.debug("Trader sequence priority order:")
                    
                    new_count = 0
                    other_count = 0
                    
                    for i, trader_info in enumerate(debug_info):
                        if trader_info['priority_group'] == 0:  # NEW status
                            new_count += 1
                            group_label = "NEW"
                        else:
                            other_count += 1
                            group_label = "OTHER"
                        
                        self.logger.debug(
                            f"  {i+1:2d}. {trader_info['seller_name']} "
                            f"({group_label}, {trader_info['status']}, {trader_info['last_updated']})"
                        )
                    
                    self.logger.debug(f"Summary: {new_count} NEW traders, {other_count} other traders")
                
                # Update sequence
                self.trader_sequence = current_traders
                self.last_db_hash = current_hash
                self.current_trader_index = 0
                self.stats['database_updates'] += 1
                
                # Log final sequence order
                self.logger.info("Final trader processing sequence:")
                for i, trader in enumerate(current_traders[:10]):  # Show first 10
                    self.logger.info(f"  {i+1}. {trader}")
                if len(current_traders) > 10:
                    self.logger.info(f"  ... and {len(current_traders) - 10} more")
                
                # Cancel current session if trader no longer in list
                if (self.active_trader_session and 
                    self.active_trader_session.trader_name not in current_traders):
                    self.logger.info(f"Canceling session for removed trader: {self.active_trader_session.trader_name}")
                    self.active_trader_session = None
                
        except Exception as e:
            self.logger.error(f"Failed to update trader sequence: {e}")
    
    def _start_next_trader_session(self) -> None:
        """Start processing next trader in sequence."""
        if self.current_trader_index >= len(self.trader_sequence):
            # Restart from beginning
            self.current_trader_index = 0
            self.stats['sequences_completed'] += 1
            self.logger.info("Completed trader sequence, restarting from beginning")
        
        if self.trader_sequence:
            trader_name = self.trader_sequence[self.current_trader_index]
            self.active_trader_session = TraderSequence(trader_name=trader_name)
            
            self.logger.info(f"Starting session for trader: {trader_name} ({self.current_trader_index + 1}/{len(self.trader_sequence)})")
            
            # Execute chat automation
            self._execute_chat_automation(trader_name)
    
    def _execute_chat_automation(self, trader_name: str) -> None:
        """
        Execute chat automation for trader.
        
        Args:
            trader_name: Name of trader to process
        """
        try:
            self.logger.info(f"Starting chat automation for trader: {trader_name}")
            
            # Step 1: Press Enter
            if not self.arduino.press_key("ENTER"):
                raise Exception("Failed to press Enter")
            time.sleep(self._random_delay())
            
            # Step 2: Type "/target <trader_name>"
            command_text = f"/target {trader_name}"
            if not self.arduino.type_text(command_text):
                raise Exception(f"Failed to type command: {command_text}")
            time.sleep(self._random_delay())
            
            # Step 3: Press Enter again
            if not self.arduino.press_key("ENTER"):
                raise Exception("Failed to press Enter (confirm)")
            time.sleep(self._random_delay())
            
            # Step 4: Press hotkey
            if not self.arduino.press_hotkey(self.main_hotkey):
                raise Exception(f"Failed to press hotkey: {self.main_hotkey}")
            
            self.logger.info(f"Chat automation completed for trader: {trader_name}. Waiting for OCR change...")
            self.stats['traders_processed'] += 1
            
            # Session is now waiting for OCR change detection
            
        except Exception as e:
            self.logger.error(f"Chat automation failed for {trader_name}: {e}")
            self._complete_current_session()
    
    def _execute_mouse_pattern(self) -> None:
        """
        Execute 9-step mouse pattern: move right + hotkey each step.
        NEW LOGIC: Simple horizontal movement with hotkey presses.
        """
        if not self.active_trader_session:
            return
        
        try:
            trader_name = self.active_trader_session.trader_name
            self.logger.info(f"Executing 9-step mouse pattern for trader: {trader_name}")
            
            for step in range(1, 10):  # 9 steps
                # Move mouse right by specified pixels
                if not self.arduino.move_mouse_relative(self.mouse_movement_pixels, 0):
                    self.logger.error(f"Mouse movement failed at step {step}")
                    continue
                
                # Press hotkey after each movement
                if not self.arduino.press_hotkey(self.main_hotkey):
                    self.logger.error(f"Hotkey failed at step {step}")
                
                self.logger.debug(f"Mouse pattern step {step}/9: moved {self.mouse_movement_pixels}px right + hotkey")
                
                # 500ms delay between steps
                time.sleep(self.mouse_movement_delay_ms / 1000.0)
            
            self.active_trader_session.mouse_pattern_completed = True
            self.stats['mouse_patterns_executed'] += 1
            
            self.logger.info(f"Mouse pattern completed for trader: {trader_name}")
            
            # Complete current session and move to next trader
            self._complete_current_session()
            
        except Exception as e:
            self.logger.error(f"Mouse pattern failed: {e}")
            self._complete_current_session()
    
    def _complete_current_session(self) -> None:
        """Complete current trader session and move to next."""
        if self.active_trader_session:
            self.logger.debug(f"Completing session for trader: {self.active_trader_session.trader_name}")
        
        self.active_trader_session = None
        self.current_trader_index += 1
    
    def _random_delay(self) -> float:
        """Generate random delay between 1-2 seconds."""
        return random.uniform(1.0, 2.0)
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current status with sequence information.
        
        Returns:
            Dictionary with detailed status information
        """
        return {
            'running': self.is_running,
            'trader_sequence_length': len(self.trader_sequence),
            'current_trader_index': self.current_trader_index,
            'current_trader': self.active_trader_session.trader_name if self.active_trader_session else None,
            'waiting_for_ocr': self.active_trader_session is not None and not self.active_trader_session.ocr_change_detected,
            'next_5_traders': self.trader_sequence[self.current_trader_index:self.current_trader_index+5],
            'sequence_preview': {
                'total_traders': len(self.trader_sequence),
                'processed': self.current_trader_index,
                'remaining': len(self.trader_sequence) - self.current_trader_index,
                'progress_percent': (self.current_trader_index / len(self.trader_sequence) * 100) if self.trader_sequence else 0
            },
            'statistics': self.stats.copy(),
            'last_db_update_hash': self.last_db_hash[:8] if self.last_db_hash else None,
            'uptime_seconds': time.time() - self.stats['session_start_time'] if self.stats['session_start_time'] else 0
        }
    
    def add_trader_manually(self, trader_name: str) -> None:
        """
        Manually add trader to current sequence (for testing purposes).
        NOTE: This does not modify database (READ-ONLY access).
        
        Args:
            trader_name: Name of trader to add to sequence
        """
        if trader_name not in self.trader_sequence:
            self.trader_sequence.append(trader_name)
            self.logger.info(f"Manually added trader to sequence: {trader_name}")
        else:
            self.logger.warning(f"Trader already in sequence: {trader_name}")