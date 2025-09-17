"""
Array Processor Thread for Arduino Automation System
Secondary thread that processes predefined array of names with click automation
"""

import threading
import time
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from arduino_controller import ArduinoController, DelayManager
from database_integration import AutomationDatabaseManager


@dataclass
class ArrayProcessingSession:
    """Data structure for array processing session"""
    session_id: int
    started_at: float
    current_index: int = 0
    cycles_completed: int = 0
    names_processed: int = 0


class ArrayProcessorThread:
    """
    Secondary thread for array processing automation.
    
    Continuously processes predefined array of names:
    1. Click Point1
    2. Input name from array  
    3. Click Point2
    4. Press hotkey
    5. Random delay
    6. Repeat with next name in array
    """
    
    def __init__(self, arduino_controller: ArduinoController,
                 db_manager: AutomationDatabaseManager,
                 config: Dict[str, Any]):
        """
        Initialize array processor thread.
        
        Args:
            arduino_controller: Arduino communication controller
            db_manager: Database manager for logging
            config: Configuration dictionary
        """
        self.arduino = arduino_controller
        self.db_manager = db_manager
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Thread control
        self.is_running = False
        self.thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        
        # Configuration extraction
        self.automation_config = config.get('automation', {})
        self.coordinates = self.automation_config.get('coordinates', {})
        self.hotkeys = self.automation_config.get('hotkeys', {})
        self.delays = self.automation_config.get('delays', {})
        
        # Names array for processing
        self.names_array = self.automation_config.get('names_array', [])
        
        # Click coordinates
        self.point1 = self.coordinates.get('point1', {})
        self.point2 = self.coordinates.get('point2', {})
        
        # Session management
        self.session: Optional[ArrayProcessingSession] = None
        
        # Statistics
        self.stats = {
            'names_processed': 0,
            'cycles_completed': 0,
            'commands_executed': 0,
            'errors': 0,
            'session_start_time': None,
            'current_name': None,
            'current_cycle': 0
        }
        
        # Delay configuration
        self.min_delay = self.delays.get('min_milliseconds', 1000)
        self.max_delay = self.delays.get('max_milliseconds', 2000)
        self.use_arduino_delays = self.delays.get('use_arduino_delays', True)
        
        # Processing configuration
        self.cycle_delay = self.automation_config.get('threads', {}).get('thread_startup_delay', 3)
        
        # Validate configuration
        self._validate_configuration()
    
    def _validate_configuration(self) -> None:
        """Validate array processor configuration."""
        if not self.names_array:
            self.logger.warning("Names array is empty - array processor will not function")
        
        point1_x = self.point1.get('x')
        point1_y = self.point1.get('y')
        point2_x = self.point2.get('x')
        point2_y = self.point2.get('y')
        
        if (not point1_x or not point1_y or not point2_x or not point2_y or
            str(point1_x).startswith('PLACEHOLDER') or str(point1_y).startswith('PLACEHOLDER') or
            str(point2_x).startswith('PLACEHOLDER') or str(point2_y).startswith('PLACEHOLDER')):
            self.logger.warning("Click coordinates contain placeholders - array processor may not function correctly")
        
        hotkey = self.hotkeys.get('secondary_hotkey', self.hotkeys.get('main_hotkey'))
        if not hotkey or str(hotkey).startswith('PLACEHOLDER'):
            self.logger.warning("Hotkey contains placeholder - array processor may not function correctly")
    
    def start(self) -> None:
        """Start array processing thread."""
        if self.is_running:
            self.logger.warning("Array processor thread already running")
            return
        
        if not self.names_array:
            self.logger.error("Cannot start array processor: names array is empty")
            return
        
        self.is_running = True
        self._stop_event.clear()
        self._pause_event.clear()
        
        # Create database session
        session_id = self.db_manager.create_automation_session('array_processor')
        self.session = ArrayProcessingSession(
            session_id=session_id,
            started_at=time.time()
        )
        
        self.stats['session_start_time'] = time.time()
        
        # Start processing thread
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        
        self.logger.info(f"Array processor thread started with {len(self.names_array)} names")
    
    def stop(self) -> None:
        """Stop array processing thread."""
        if not self.is_running:
            return
        
        self.is_running = False
        self._stop_event.set()
        self._pause_event.set()
        
        # Wait for thread to finish
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=10.0)
        
        # End database session
        if self.session:
            self.db_manager.end_automation_session(self.session.session_id, 'stopped')
        
        self.logger.info("Array processor thread stopped")
    
    def pause(self) -> None:
        """Pause array processing."""
        if self.is_running:
            self._pause_event.set()
            self.logger.info("Array processor paused")
    
    def resume(self) -> None:
        """Resume array processing."""
        if self.is_running:
            self._pause_event.clear()
            self.logger.info("Array processor resumed")
    
    def _run_loop(self) -> None:
        """Main array processing loop."""
        self.logger.info("Array processor loop started")
        
        while self.is_running and not self._stop_event.is_set():
            try:
                # Check if paused
                if self._pause_event.is_set():
                    self._stop_event.wait(1.0)
                    continue
                
                # Process current name from array
                self._process_current_name()
                
                # Move to next name in array
                self._advance_to_next_name()
                
                # Add delay between processing cycles
                if self.cycle_delay > 0:
                    self._stop_event.wait(self.cycle_delay)
                
            except Exception as e:
                self.logger.error(f"Array processor loop error: {e}")
                self.stats['errors'] += 1
                
                if self.session:
                    self.db_manager.update_session_stats(
                        self.session.session_id, errors_count=1
                    )
                
                # Wait before retrying
                self._stop_event.wait(5.0)
        
        self.logger.info("Array processor loop ended")
    
    def _process_current_name(self) -> None:
        """Process current name in the array."""
        if not self.session:
            return
        
        current_name = self.names_array[self.session.current_index]
        self.stats['current_name'] = current_name
        
        try:
            self.logger.info(f"Processing name: {current_name} (index {self.session.current_index})")
            
            # Step 1: Click Point1
            point1_x = int(self.point1.get('x', 0))
            point1_y = int(self.point1.get('y', 0))
            
            success = self._execute_arduino_command(
                "click_point1",
                f"CLICK:{point1_x},{point1_y}",
                lambda: self.arduino.click_position(point1_x, point1_y)
            )
            if not success:
                raise Exception(f"Failed to click Point1 at ({point1_x}, {point1_y})")
            
            self._random_delay()
            
            # Step 2: Type current name
            success = self._execute_arduino_command(
                "type_name",
                f"TYPE:{current_name}",
                lambda: self.arduino.type_text(current_name)
            )
            if not success:
                raise Exception(f"Failed to type name: {current_name}")
            
            self._random_delay()
            
            # Step 3: Click Point2
            point2_x = int(self.point2.get('x', 0))
            point2_y = int(self.point2.get('y', 0))
            
            success = self._execute_arduino_command(
                "click_point2", 
                f"CLICK:{point2_x},{point2_y}",
                lambda: self.arduino.click_position(point2_x, point2_y)
            )
            if not success:
                raise Exception(f"Failed to click Point2 at ({point2_x}, {point2_y})")
            
            self._random_delay()
            
            # Step 4: Press hotkey
            hotkey = self.hotkeys.get('secondary_hotkey', self.hotkeys.get('main_hotkey', 'F1'))
            success = self._execute_arduino_command(
                "press_hotkey",
                f"HOTKEY:{hotkey}",
                lambda: self.arduino.press_hotkey(hotkey)
            )
            if not success:
                raise Exception(f"Failed to press hotkey: {hotkey}")
            
            self._random_delay()
            
            # Update statistics
            self.stats['names_processed'] += 1
            self.session.names_processed += 1
            
            # Update database session stats
            self.db_manager.update_session_stats(
                self.session.session_id, targets_processed=1
            )
            
            self.logger.debug(f"Successfully processed name: {current_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to process name '{current_name}': {e}")
            self.stats['errors'] += 1
            
            if self.session:
                self.db_manager.update_session_stats(
                    self.session.session_id, errors_count=1
                )
    
    def _advance_to_next_name(self) -> None:
        """Advance to next name in array."""
        if not self.session:
            return
        
        self.session.current_index += 1
        
        # Check if we've completed a full cycle
        if self.session.current_index >= len(self.names_array):
            self.session.current_index = 0
            self.session.cycles_completed += 1
            self.stats['cycles_completed'] = self.session.cycles_completed
            self.stats['current_cycle'] = self.session.cycles_completed
            
            self.logger.info(f"Completed cycle {self.session.cycles_completed}, starting over")
    
    def _execute_arduino_command(self, command_type: str, command_data: str, command_func) -> bool:
        """
        Execute Arduino command with logging and error handling.
        
        Args:
            command_type: Type of command for logging
            command_data: Command data for logging
            command_func: Function to execute the command
            
        Returns:
            True if command successful, False otherwise
        """
        start_time = time.time()
        
        try:
            success = command_func()
            execution_time = time.time() - start_time
            
            if success:
                self.stats['commands_executed'] += 1
                
                # Log command execution
                if self.session:
                    self.db_manager.log_command_execution(
                        self.session.session_id, command_type, command_data, 
                        execution_time, 'success'
                    )
                    self.db_manager.update_session_stats(
                        self.session.session_id, commands_executed=1
                    )
                
                return True
            else:
                # Log command failure
                if self.session:
                    self.db_manager.log_command_execution(
                        self.session.session_id, command_type, command_data,
                        execution_time, 'error', 'Command returned False'
                    )
                
                return False
                
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"Arduino command '{command_type}' failed: {e}")
            
            # Log command error
            if self.session:
                self.db_manager.log_command_execution(
                    self.session.session_id, command_type, command_data,
                    execution_time, 'error', str(e)
                )
            
            return False
    
    def _random_delay(self) -> None:
        """Execute randomized delay."""
        if self.use_arduino_delays:
            self.arduino.execute_delay(self.min_delay, self.max_delay)
        else:
            DelayManager.execute_python_delay(
                self.min_delay / 1000.0, 
                self.max_delay / 1000.0
            )
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current status of array processor thread.
        
        Returns:
            Dictionary with status information
        """
        status = {
            'running': self.is_running,
            'paused': self._pause_event.is_set() if self.is_running else False,
            'session_id': self.session.session_id if self.session else None,
            'statistics': self.stats.copy(),
            'array_info': {
                'total_names': len(self.names_array),
                'current_index': self.session.current_index if self.session else 0,
                'current_name': self.stats.get('current_name'),
                'names_preview': self.names_array[:5] if self.names_array else []
            },
            'uptime_seconds': time.time() - self.stats['session_start_time'] if self.stats['session_start_time'] else 0
        }
        
        return status
    
    def update_names_array(self, new_names: List[str]) -> None:
        """
        Update names array during runtime.
        
        Args:
            new_names: New list of names to process
        """
        old_count = len(self.names_array)
        self.names_array = new_names.copy()
        
        # Reset current index if it's out of bounds
        if self.session and self.session.current_index >= len(self.names_array):
            self.session.current_index = 0
        
        self.logger.info(f"Updated names array: {old_count} -> {len(self.names_array)} names")
    
    def get_names_array(self) -> List[str]:
        """
        Get current names array.
        
        Returns:
            Copy of current names array
        """
        return self.names_array.copy()
    
    def skip_to_name(self, name: str) -> bool:
        """
        Skip to specific name in array.
        
        Args:
            name: Name to skip to
            
        Returns:
            True if name found and skipped to, False otherwise
        """
        try:
            index = self.names_array.index(name)
            if self.session:
                self.session.current_index = index
                self.stats['current_name'] = name
                self.logger.info(f"Skipped to name: {name} (index {index})")
                return True
        except ValueError:
            self.logger.warning(f"Name '{name}' not found in array")
        
        return False
    
    def skip_to_index(self, index: int) -> bool:
        """
        Skip to specific index in array.
        
        Args:
            index: Index to skip to
            
        Returns:
            True if index valid and skipped to, False otherwise
        """
        if 0 <= index < len(self.names_array):
            if self.session:
                self.session.current_index = index
                self.stats['current_name'] = self.names_array[index]
                self.logger.info(f"Skipped to index: {index} ({self.names_array[index]})")
                return True
        else:
            self.logger.warning(f"Index {index} out of range (0-{len(self.names_array)-1})")
        
        return False