"""
Arduino Controller for Serial Communication
Handles all communication between Python system and Arduino Micro
"""

import serial
import time
import random
import logging
import threading
from typing import Optional, Tuple
from enum import Enum


class ArduinoCommandResult(Enum):
    """Arduino command execution results"""
    SUCCESS = "OK"
    ERROR = "ERROR"
    TIMEOUT = "TIMEOUT"
    CONNECTION_FAILED = "CONNECTION_FAILED"


class ArduinoController:
    """
    Manages serial communication with Arduino Micro for automation commands.
    Thread-safe with connection management and error handling.
    """
    
    def __init__(self, port: str = 'COM3', baudrate: int = 9600, timeout: float = 5.0):
        """
        Initialize Arduino controller.
        
        Args:
            port: Serial port (Windows: COM3, COM4, etc.)
            baudrate: Communication speed (9600 default)
            timeout: Command timeout in seconds
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial_connection: Optional[serial.Serial] = None
        self.logger = logging.getLogger(__name__)
        self._lock = threading.Lock()
        self._connection_attempts = 0
        self._max_connection_attempts = 3
        
        # Connection and error statistics
        self.stats = {
            'commands_sent': 0,
            'commands_success': 0,
            'commands_error': 0,
            'connection_errors': 0,
            'timeouts': 0
        }
        
        self._connect()
    
    def _connect(self) -> bool:
        """
        Establish serial connection to Arduino.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            if self.serial_connection and self.serial_connection.is_open:
                return True
                
            self.logger.info(f"Connecting to Arduino on {self.port} at {self.baudrate} baud")
            
            self.serial_connection = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout,
                write_timeout=self.timeout
            )
            
            # Wait for Arduino to initialize
            time.sleep(2)
            
            # Clear any existing data in buffers
            self.serial_connection.flushInput()
            self.serial_connection.flushOutput()
            
            # Wait for Arduino READY signal
            if self._wait_for_ready():
                self.logger.info("Arduino connection established successfully")
                self._connection_attempts = 0
                return True
            else:
                self.logger.error("Arduino did not send READY signal")
                self._close_connection()
                return False
                
        except serial.SerialException as e:
            self.logger.error(f"Failed to connect to Arduino: {e}")
            self.stats['connection_errors'] += 1
            self._connection_attempts += 1
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error connecting to Arduino: {e}")
            self.stats['connection_errors'] += 1
            return False
    
    def _wait_for_ready(self, timeout: float = 10.0) -> bool:
        """
        Wait for Arduino READY signal.
        
        Args:
            timeout: Maximum time to wait for READY signal
            
        Returns:
            True if READY received, False if timeout
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                if self.serial_connection.in_waiting > 0:
                    response = self.serial_connection.readline().decode().strip()
                    self.logger.debug(f"Arduino response: {response}")
                    
                    if response == "READY":
                        return True
                    elif response == "HEARTBEAT":
                        continue  # Ignore heartbeat messages
                        
                time.sleep(0.1)
                
            except Exception as e:
                self.logger.error(f"Error waiting for READY: {e}")
                return False
        
        return False
    
    def _close_connection(self) -> None:
        """Close serial connection."""
        try:
            if self.serial_connection and self.serial_connection.is_open:
                self.serial_connection.close()
                self.logger.info("Arduino connection closed")
        except Exception as e:
            self.logger.error(f"Error closing Arduino connection: {e}")
        finally:
            self.serial_connection = None
    
    def _send_command(self, command: str) -> Tuple[ArduinoCommandResult, str]:
        """
        Send command to Arduino and wait for response.
        
        Args:
            command: Command string to send
            
        Returns:
            Tuple of (result, response_message)
        """
        with self._lock:
            self.stats['commands_sent'] += 1
            
            if not self.serial_connection or not self.serial_connection.is_open:
                if not self._connect():
                    return ArduinoCommandResult.CONNECTION_FAILED, "No connection to Arduino"
            
            try:
                # Send command
                command_bytes = f"{command}\n".encode()
                self.serial_connection.write(command_bytes)
                self.serial_connection.flush()
                
                self.logger.debug(f"Sent command: {command}")
                
                # Wait for response
                start_time = time.time()
                while time.time() - start_time < self.timeout:
                    if self.serial_connection.in_waiting > 0:
                        response = self.serial_connection.readline().decode().strip()
                        self.logger.debug(f"Arduino response: {response}")
                        
                        if response == "OK":
                            self.stats['commands_success'] += 1
                            return ArduinoCommandResult.SUCCESS, response
                        elif response.startswith("ERROR"):
                            self.stats['commands_error'] += 1
                            return ArduinoCommandResult.ERROR, response
                        elif response == "HEARTBEAT":
                            continue  # Ignore heartbeat, keep waiting
                    
                    time.sleep(0.01)  # Small delay to prevent CPU overload
                
                # Timeout occurred
                self.stats['timeouts'] += 1
                self.logger.warning(f"Command timeout: {command}")
                return ArduinoCommandResult.TIMEOUT, "Command timeout"
                
            except serial.SerialException as e:
                self.logger.error(f"Serial communication error: {e}")
                self._close_connection()
                self.stats['connection_errors'] += 1
                return ArduinoCommandResult.CONNECTION_FAILED, f"Serial error: {e}"
            except Exception as e:
                self.logger.error(f"Unexpected error sending command: {e}")
                self.stats['commands_error'] += 1
                return ArduinoCommandResult.ERROR, f"Unexpected error: {e}"
    
    def click_position(self, x: int, y: int) -> bool:
        """
        Click mouse at specific coordinates.
        
        Args:
            x: X coordinate
            y: Y coordinate
            
        Returns:
            True if click successful, False otherwise
        """
        command = f"CLICK:{x},{y}"
        result, message = self._send_command(command)
        
        if result == ArduinoCommandResult.SUCCESS:
            self.logger.debug(f"Mouse click successful at ({x}, {y})")
            return True
        else:
            self.logger.error(f"Mouse click failed at ({x}, {y}): {message}")
            return False
    
    def move_mouse_relative(self, delta_x: int, delta_y: int) -> bool:
        """
        Move mouse by relative offset.
        
        Args:
            delta_x: Horizontal movement in pixels (positive = right)
            delta_y: Vertical movement in pixels (positive = down)
            
        Returns:
            True if movement successful, False otherwise
        """
        command = f"MOVE:{delta_x},{delta_y}"
        result, message = self._send_command(command)
        
        if result == ArduinoCommandResult.SUCCESS:
            self.logger.debug(f"Mouse moved by ({delta_x}, {delta_y})")
            return True
        else:
            self.logger.error(f"Mouse movement failed: {message}")
            return False
    
    def type_text(self, text: str) -> bool:
        """
        Type text string.
        
        Args:
            text: Text to type
            
        Returns:
            True if typing successful, False otherwise
        """
        # Escape any problematic characters
        text = text.replace('\n', '\\n').replace('\r', '\\r')
        
        command = f"TYPE:{text}"
        result, message = self._send_command(command)
        
        if result == ArduinoCommandResult.SUCCESS:
            self.logger.debug(f"Text typing successful: {text[:50]}...")
            return True
        else:
            self.logger.error(f"Text typing failed: {message}")
            return False
    
    def press_key(self, key: str) -> bool:
        """
        Press single key.
        
        Args:
            key: Key to press (ENTER, ESC, TAB, SPACE, etc.)
            
        Returns:
            True if key press successful, False otherwise
        """
        command = f"KEY:{key}"
        result, message = self._send_command(command)
        
        if result == ArduinoCommandResult.SUCCESS:
            self.logger.debug(f"Key press successful: {key}")
            return True
        else:
            self.logger.error(f"Key press failed: {message}")
            return False
    
    def press_hotkey(self, hotkey: str) -> bool:
        """
        Press hotkey combination.
        
        Args:
            hotkey: Hotkey combination (CTRL+C, ALT+TAB, F1, etc.)
            
        Returns:
            True if hotkey successful, False otherwise
        """
        command = f"HOTKEY:{hotkey}"
        result, message = self._send_command(command)
        
        if result == ArduinoCommandResult.SUCCESS:
            self.logger.debug(f"Hotkey successful: {hotkey}")
            return True
        else:
            self.logger.error(f"Hotkey failed: {message}")
            return False
    
    def execute_delay(self, min_ms: int = 1000, max_ms: int = 2000) -> bool:
        """
        Execute randomized delay via Arduino.
        
        Args:
            min_ms: Minimum delay in milliseconds
            max_ms: Maximum delay in milliseconds
            
        Returns:
            True if delay successful, False otherwise
        """
        delay_ms = random.randint(min_ms, max_ms)
        command = f"DELAY:{delay_ms}"
        result, message = self._send_command(command)
        
        if result == ArduinoCommandResult.SUCCESS:
            self.logger.debug(f"Delay successful: {delay_ms}ms")
            return True
        else:
            self.logger.error(f"Delay failed: {message}")
            return False
    
    def ping(self) -> bool:
        """
        Test Arduino connectivity.
        
        Returns:
            True if Arduino responds to ping, False otherwise
        """
        result, message = self._send_command("PING")
        
        if result == ArduinoCommandResult.SUCCESS or message == "PONG":
            self.logger.debug("Arduino ping successful")
            return True
        else:
            self.logger.warning(f"Arduino ping failed: {message}")
            return False
    
    def get_connection_status(self) -> dict:
        """
        Get current connection status and statistics.
        
        Returns:
            Dictionary with connection info and stats
        """
        is_connected = (
            self.serial_connection is not None and 
            self.serial_connection.is_open
        )
        
        return {
            'connected': is_connected,
            'port': self.port,
            'baudrate': self.baudrate,
            'connection_attempts': self._connection_attempts,
            'stats': self.stats.copy()
        }
    
    def reset_connection(self) -> bool:
        """
        Reset Arduino connection.
        
        Returns:
            True if reset successful, False otherwise
        """
        self.logger.info("Resetting Arduino connection")
        self._close_connection()
        time.sleep(1)  # Wait before reconnecting
        return self._connect()
    
    def close(self) -> None:
        """Close Arduino controller and clean up resources."""
        self.logger.info("Closing Arduino controller")
        self._close_connection()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


class DelayManager:
    """Utility class for delay management with randomization."""
    
    @staticmethod
    def random_delay_ms(min_ms: int = 1000, max_ms: int = 2000) -> int:
        """
        Generate random delay in milliseconds.
        
        Args:
            min_ms: Minimum delay
            max_ms: Maximum delay
            
        Returns:
            Random delay value in milliseconds
        """
        return random.randint(min_ms, max_ms)
    
    @staticmethod
    def random_delay_seconds(min_seconds: float = 1.0, max_seconds: float = 2.0) -> float:
        """
        Generate random delay in seconds.
        
        Args:
            min_seconds: Minimum delay
            max_seconds: Maximum delay
            
        Returns:
            Random delay value in seconds
        """
        return random.uniform(min_seconds, max_seconds)
    
    @staticmethod
    def execute_python_delay(min_seconds: float = 1.0, max_seconds: float = 2.0) -> None:
        """
        Execute random delay in Python (not via Arduino).
        
        Args:
            min_seconds: Minimum delay
            max_seconds: Maximum delay
        """
        delay = DelayManager.random_delay_seconds(min_seconds, max_seconds)
        time.sleep(delay)