"""
Main Controller for Game Monitor System

Central orchestrator managing all subsystems with high-performance
data processing pipeline and <1 second response times.
"""

import logging
import time
import threading
import sys
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path
from datetime import datetime

from .hotkey_manager import HotkeyManager, HotkeyType, CaptureEvent, get_hotkey_manager
from .vision_system import VisionSystem, ScreenRegion, get_vision_system
from .fast_validator import FastValidator, ValidationLevel, get_validator
from .database_manager import DatabaseManager, get_database
from .advanced_logger import get_main_controller_logger
from .error_tracker import ErrorTracker
from .performance_logger import PerformanceMonitor

logger = logging.getLogger(__name__)  # Keep for compatibility

class SystemState(Enum):
    """System operational states"""
    STOPPED = "stopped"
    STARTING = "starting" 
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    ERROR = "error"

@dataclass
class ProcessingResult:
    """Result of data processing operation"""
    success: bool
    processing_time: float
    data_extracted: Dict[str, Any]
    confidence: float
    errors: List[str]
    warnings: List[str]

class GameMonitor:
    """High-performance game monitoring system controller"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        init_start = time.time()
        
        # Basic initialization
        self.config_path = config_path
        self.state = SystemState.STOPPED
        self._state_lock = threading.Lock()
        
        # Advanced logging and monitoring
        self.advanced_logger = get_main_controller_logger()
        self.error_tracker = ErrorTracker()
        self.performance_monitor = PerformanceMonitor()
        
        with self.advanced_logger.operation_context('game_monitor', 'initialization'):
            try:
                self.advanced_logger.info(
                    "Starting GameMonitor initialization",
                    extra_data={
                        'config_path': config_path,
                        'python_version': sys.version,
                        'initialization_started': datetime.now().isoformat()
                    }
                )
                
                # Stage 1: Initialize subsystems
                subsystems_start = time.time()
                self.advanced_logger.info("Initializing core subsystems")
                
                self.db = get_database()
                self.hotkey_manager = get_hotkey_manager()
                self.vision_system = get_vision_system()
                self.validator = get_validator()
                
                subsystems_time = time.time() - subsystems_start
                
                self.advanced_logger.info(
                    f"Subsystems initialized in {subsystems_time*1000:.2f}ms",
                    extra_data={
                        'subsystems_init_time_ms': subsystems_time * 1000,
                        'subsystems_count': 4,
                        'subsystems': ['database', 'hotkey_manager', 'vision_system', 'validator']
                    }
                )
                
                # Stage 2: Load configuration
                config_start = time.time()
                self.config = self._load_default_config()
                config_time = time.time() - config_start
                
                self.advanced_logger.info(
                    f"Configuration loaded in {config_time*1000:.2f}ms",
                    extra_data={
                        'config_load_time_ms': config_time * 1000,
                        'config_source': 'file' if Path(config_path).exists() else 'defaults',
                        'config_sections': list(self.config.keys()) if self.config else []
                    }
                )
                
                # Stage 3: Initialize performance tracking
                stats_start = time.time()
                self.performance_stats = {
                    'total_captures': 0,
                    'successful_captures': 0,
                    'failed_captures': 0,
                    'avg_processing_time': 0.0,
                    'total_processing_time': 0.0,
                    'fastest_capture': float('inf'),
                    'slowest_capture': 0.0,
                    'uptime_start': None
                }
                stats_time = time.time() - stats_start
                
                self.advanced_logger.debug(
                    f"Performance tracking initialized in {stats_time*1000:.2f}ms",
                    extra_data={
                        'stats_init_time_ms': stats_time * 1000,
                        'performance_fields': list(self.performance_stats.keys())
                    }
                )
                
                # Stage 4: Initialize screen regions
                regions_start = time.time()
                self.screen_regions = self._initialize_screen_regions()
                regions_time = time.time() - regions_start
                
                self.advanced_logger.info(
                    f"Screen regions initialized in {regions_time*1000:.2f}ms",
                    extra_data={
                        'regions_init_time_ms': regions_time * 1000,
                        'regions_count': len(self.screen_regions),
                        'region_names': list(self.screen_regions.keys())
                    }
                )
                
                # Stage 5: Register hotkey callbacks
                callbacks_start = time.time()
                self._register_hotkey_callbacks()
                callbacks_time = time.time() - callbacks_start
                
                self.advanced_logger.info(
                    f"Hotkey callbacks registered in {callbacks_time*1000:.2f}ms",
                    extra_data={
                        'callbacks_registration_time_ms': callbacks_time * 1000,
                        'callbacks_count': 5,
                        'hotkey_types': [hk.value for hk in HotkeyType]
                    }
                )
                
                init_time = time.time() - init_start
                
                # Final initialization log
                self.advanced_logger.info(
                    f"GameMonitor initialized successfully in {init_time*1000:.2f}ms",
                    extra_data={
                        'total_initialization_time_ms': init_time * 1000,
                        'timing_breakdown': {
                            'subsystems_ms': subsystems_time * 1000,
                            'config_ms': config_time * 1000,
                            'stats_ms': stats_time * 1000,
                            'regions_ms': regions_time * 1000,
                            'callbacks_ms': callbacks_time * 1000
                        },
                        'system_ready': True,
                        'initial_state': self.state.value,
                        'config_path': config_path
                    }
                )
                
                logger.info("GameMonitor initialized successfully")
                
            except Exception as e:
                # Log initialization failure
                init_time = time.time() - init_start
                
                self.advanced_logger.error(
                    f"GameMonitor initialization failed: {str(e)}",
                    error=e,
                    extra_data={
                        'initialization_time_ms': init_time * 1000,
                        'config_path': config_path,
                        'initialization_stage': 'unknown'
                    }
                )
                
                # Record initialization error
                self.error_tracker.record_error(
                    'game_monitor', 'initialization', e,
                    context={'config_path': config_path}
                )
                
                raise
    
    def _load_default_config(self) -> Dict[str, Any]:
        """Load default configuration"""
        default_config = {
            'screen': {
                'trader_list_region': {'x': 100, 'y': 200, 'width': 600, 'height': 400},
                'item_scan_region': {'x': 200, 'y': 150, 'width': 500, 'height': 300},
                'trader_inventory_region': {'x': 300, 'y': 250, 'width': 700, 'height': 500},
                'screenshot_save_path': 'data/screenshots'
            },
            'ocr': {
                'confidence_threshold': 0.85,
                'max_processing_time': 0.8,  # Reserve 0.2s for other operations
                'use_cache': True
            },
            'validation': {
                'default_level': 'balanced',
                'strict_mode_items': ['epic', 'legendary'],
                'auto_approve_threshold': 0.95
            },
            'performance': {
                'max_capture_time': 1.0,
                'warning_threshold': 0.8,
                'enable_performance_logging': True
            }
        }
        
        # Try to load from file if it exists
        config_path = Path(self.config_path)
        if config_path.exists():
            try:
                import yaml
                with open(config_path, 'r', encoding='utf-8') as f:
                    file_config = yaml.safe_load(f)
                    default_config.update(file_config)
                logger.info(f"Configuration loaded from {self.config_path}")
            except Exception as e:
                logger.warning(f"Failed to load config file: {e}, using defaults")
        
        return default_config
    
    def _initialize_screen_regions(self) -> Dict[str, ScreenRegion]:
        """Initialize screen regions from configuration"""
        regions = {}
        
        screen_config = self.config.get('screen', {})
        
        # Trader list region
        trader_region = screen_config.get('trader_list_region', {})
        regions['trader_list'] = ScreenRegion(
            x=trader_region.get('x', 100),
            y=trader_region.get('y', 200),
            width=trader_region.get('width', 600),
            height=trader_region.get('height', 400),
            name='trader_list'
        )
        
        # Item scan region
        item_region = screen_config.get('item_scan_region', {})
        regions['item_scan'] = ScreenRegion(
            x=item_region.get('x', 200),
            y=item_region.get('y', 150),
            width=item_region.get('width', 500),
            height=item_region.get('height', 300),
            name='item_scan'
        )
        
        # Trader inventory region
        inventory_region = screen_config.get('trader_inventory_region', {})
        regions['trader_inventory'] = ScreenRegion(
            x=inventory_region.get('x', 300),
            y=inventory_region.get('y', 250),
            width=inventory_region.get('width', 700),
            height=inventory_region.get('height', 500),
            name='trader_inventory'
        )
        
        logger.debug(f"Initialized {len(regions)} screen regions")
        return regions
    
    def _register_hotkey_callbacks(self):
        """Register callbacks for each hotkey type"""
        self.hotkey_manager.register_callback(HotkeyType.TRADER_LIST, self._handle_trader_list_capture)
        self.hotkey_manager.register_callback(HotkeyType.ITEM_SCAN, self._handle_item_scan_capture)
        self.hotkey_manager.register_callback(HotkeyType.TRADER_INVENTORY, self._handle_trader_inventory_capture)
        self.hotkey_manager.register_callback(HotkeyType.MANUAL_VERIFICATION, self._handle_manual_verification)
        self.hotkey_manager.register_callback(HotkeyType.EMERGENCY_STOP, self._handle_emergency_stop)
        
        logger.info("Hotkey callbacks registered")
    
    def start(self):
        """Start the game monitoring system with comprehensive logging"""
        # Start performance tracking for system startup
        trace_id = self.performance_monitor.start_operation(
            'game_monitor', 'system_start',
            context={'current_state': self.state.value}
        )
        
        with self.advanced_logger.operation_context('game_monitor', 'start'):
            start_time = time.time()
            
            try:
                # Check current state
                with self._state_lock:
                    if self.state == SystemState.RUNNING:
                        self.advanced_logger.warning(
                            "System start requested but already running",
                            extra_data={
                                'current_state': self.state.value,
                                'uptime': time.time() - self.performance_stats.get('uptime_start', time.time()),
                                'action_taken': 'ignored'
                            }
                        )
                        logger.warning("System already running")
                        
                        # Finish performance tracking - not an error but no action taken
                        self.performance_monitor.finish_operation(trace_id, success=True, operation_data={'already_running': True})
                        return
                    
                    # Update state to starting
                    previous_state = self.state
                    self.state = SystemState.STARTING
                
                self.advanced_logger.info(
                    "Starting Game Monitor System",
                    extra_data={
                        'previous_state': previous_state.value,
                        'new_state': self.state.value,
                        'registered_callbacks': len(getattr(self.hotkey_manager, '_callbacks', {})),
                        'screen_regions': list(self.screen_regions.keys()),
                        'config_sections': list(self.config.keys()) if self.config else []
                    }
                )
                
                logger.info("Starting Game Monitor System...")
                
                # Start hotkey manager
                hotkey_start = time.time()
                self.hotkey_manager.start()
                hotkey_time = time.time() - hotkey_start
                
                self.advanced_logger.info(
                    f"Hotkey manager started in {hotkey_time*1000:.2f}ms",
                    extra_data={
                        'hotkey_manager_start_time_ms': hotkey_time * 1000,
                        'hotkey_manager_state': 'running',
                        'registered_hotkeys': [hk.value for hk in HotkeyType]
                    }
                )
                
                # Update state and performance tracking
                state_update_start = time.time()
                with self._state_lock:
                    self.state = SystemState.RUNNING
                    self.performance_stats['uptime_start'] = time.time()
                state_update_time = time.time() - state_update_start
                
                total_time = time.time() - start_time
                
                # Log successful startup
                self.advanced_logger.info(
                    f"Game Monitor System started successfully in {total_time*1000:.2f}ms",
                    extra_data={
                        'total_startup_time_ms': total_time * 1000,
                        'timing_breakdown': {
                            'hotkey_manager_start_ms': hotkey_time * 1000,
                            'state_update_ms': state_update_time * 1000
                        },
                        'final_state': self.state.value,
                        'uptime_start': self.performance_stats['uptime_start'],
                        'system_status': 'operational',
                        'subsystems_status': {
                            'hotkey_manager': 'running',
                            'vision_system': 'ready',
                            'database': 'connected',
                            'validator': 'ready'
                        }
                    }
                )
                
                # Finish performance tracking
                self.performance_monitor.finish_operation(
                    trace_id, success=True,
                    operation_data={
                        'startup_time_ms': total_time * 1000,
                        'final_state': self.state.value,
                        'subsystems_started': ['hotkey_manager']
                    }
                )
                
                logger.info("Game Monitor System started successfully")
                
            except Exception as e:
                # Comprehensive error logging
                total_time = time.time() - start_time
                
                self.advanced_logger.error(
                    f"Failed to start Game Monitor System: {str(e)}",
                    error=e,
                    extra_data={
                        'startup_time_ms': total_time * 1000,
                        'attempted_state_change': f"{SystemState.STOPPED.value} -> {SystemState.RUNNING.value}",
                        'final_state': SystemState.ERROR.value,
                        'subsystem_states': {
                            'hotkey_manager': getattr(self.hotkey_manager, 'is_running', False),
                            'vision_system': 'unknown',
                            'database': 'unknown'
                        }
                    }
                )
                
                # Update state to error
                with self._state_lock:
                    self.state = SystemState.ERROR
                
                # Record error for tracking
                self.error_tracker.record_error(
                    'game_monitor', 'system_start', e,
                    context={
                        'startup_time_ms': total_time * 1000,
                        'config_path': self.config_path
                    },
                    trace_id=trace_id
                )
                
                # Finish performance tracking with error
                self.performance_monitor.finish_operation(trace_id, success=False, error_count=1)
                
                logger.error(f"Failed to start system: {e}")
                raise
    
    def stop(self):
        """Stop the game monitoring system"""
        with self._state_lock:
            if self.state == SystemState.STOPPED:
                return
            
            self.state = SystemState.STOPPING
        
        try:
            logger.info("Stopping Game Monitor System...")
            
            # Stop hotkey manager
            self.hotkey_manager.stop()
            
            # Update state
            with self._state_lock:
                self.state = SystemState.STOPPED
            
            logger.info("Game Monitor System stopped")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
    
    def pause(self):
        """Pause the system"""
        with self._state_lock:
            if self.state == SystemState.RUNNING:
                self.state = SystemState.PAUSED
                logger.info("System paused")
    
    def resume(self):
        """Resume the system"""
        with self._state_lock:
            if self.state == SystemState.PAUSED:
                self.state = SystemState.RUNNING
                logger.info("System resumed")
    
    def get_state(self) -> SystemState:
        """Get current system state"""
        with self._state_lock:
            return self.state
    
    # Hotkey event handlers
    
    def _handle_trader_list_capture(self, event: CaptureEvent) -> ProcessingResult:
        """Handle F1 - Trader List Capture with comprehensive logging"""
        # Start performance tracking for complete pipeline
        trace_id = self.performance_monitor.start_operation(
            'game_monitor', 'trader_list_capture',
            context={
                'hotkey': 'F1',
                'event_timestamp': event.timestamp,
                'system_state': self.state.value
            }
        )
        
        with self.advanced_logger.operation_context('game_monitor', 'trader_list_capture'):
            start_time = time.time()
            
            try:
                self.advanced_logger.info(
                    "Processing F1 - Trader List Capture",
                    extra_data={
                        'hotkey': 'F1',
                        'capture_type': 'trader_list',
                        'event_timestamp': event.timestamp,
                        'processing_delay_ms': (start_time - event.timestamp) * 1000,
                        'system_state': self.state.value
                    }
                )
                
                logger.debug("Processing trader list capture")
                
                # Stage 1: Get screen region
                region_start = time.time()
                region = self.screen_regions['trader_list']
                region_time = time.time() - region_start
                
                self.advanced_logger.debug(
                    f"Screen region retrieved in {region_time*1000:.2f}ms",
                    extra_data={
                        'region_retrieval_time_ms': region_time * 1000,
                        'region_config': {
                            'name': region.name,
                            'coordinates': f"({region.x}, {region.y})",
                            'dimensions': f"{region.width}x{region.height}",
                            'area_pixels': region.width * region.height
                        }
                    }
                )
                
                # Stage 2: Capture and process with vision system
                vision_start = time.time()
                result = self.vision_system.capture_and_process_region(
                    region, 'trader_name'
                )
                vision_time = time.time() - vision_start
                
                self.advanced_logger.info(
                    f"Vision processing completed in {vision_time*1000:.2f}ms",
                    extra_data={
                        'vision_processing_time_ms': vision_time * 1000,
                        'vision_result_available': result is not None,
                        'extracted_data_fields': list(result.keys()) if result else []
                    }
                )
                
                if result:
                    # Stage 3: Validate data
                    validation_start = time.time()
                    trader_nickname = result.get('trader_nickname', '')
                    
                    self.advanced_logger.debug(
                        f"Validating trader nickname: '{trader_nickname}'",
                        extra_data={
                            'trader_nickname': trader_nickname,
                            'nickname_length': len(trader_nickname),
                            'validation_level': 'BALANCED'
                        }
                    )
                    
                    validation_result = self.validator.validate_trader_nickname(
                        trader_nickname, ValidationLevel.BALANCED
                    )
                    validation_time = time.time() - validation_start
                    
                    self.advanced_logger.info(
                        f"Data validation completed in {validation_time*1000:.2f}ms",
                        extra_data={
                            'validation_time_ms': validation_time * 1000,
                            'validation_result': validation_result.is_valid,
                            'confidence_score': validation_result.confidence,
                            'validation_warnings': validation_result.warnings,
                            'validation_level': 'BALANCED'
                        }
                    )
                    
                    if validation_result.is_valid:
                        # Stage 4: Process and store data
                        processing_start = time.time()
                        processed_data = self._process_trader_list_data([result])
                        processing_time_stage = time.time() - processing_start
                        
                        total_processing_time = time.time() - start_time
                        self._update_performance_stats(total_processing_time, True)
                        
                        # Log successful completion
                        self.advanced_logger.info(
                            f"Trader list capture completed successfully in {total_processing_time*1000:.2f}ms",
                            extra_data={
                                'total_processing_time_ms': total_processing_time * 1000,
                                'timing_breakdown': {
                                    'region_retrieval_ms': region_time * 1000,
                                    'vision_processing_ms': vision_time * 1000,
                                    'validation_ms': validation_time * 1000,
                                    'data_processing_ms': processing_time_stage * 1000
                                },
                                'performance_status': 'EXCELLENT' if total_processing_time < 0.5 else 'GOOD' if total_processing_time < 1.0 else 'SLOW',
                                'data_extracted': {
                                    'traders_count': processed_data.get('traders_found', 0),
                                    'trade_ids_generated': len(processed_data.get('trade_ids', []))
                                },
                                'final_confidence': validation_result.confidence
                            }
                        )
                        
                        # Finish performance tracking
                        self.performance_monitor.finish_operation(
                            trace_id, success=True,
                            operation_data={
                                'total_time_ms': total_processing_time * 1000,
                                'traders_processed': processed_data.get('traders_found', 0),
                                'confidence': validation_result.confidence,
                                'pipeline_stages': 4
                            }
                        )
                        
                        return ProcessingResult(
                            success=True,
                            processing_time=total_processing_time,
                            data_extracted=processed_data,
                            confidence=validation_result.confidence,
                            errors=[],
                            warnings=validation_result.warnings
                        )
                    else:
                        # Validation failed
                        total_processing_time = time.time() - start_time
                        self._update_performance_stats(total_processing_time, False)
                        
                        self.advanced_logger.warning(
                            f"Trader list validation failed in {total_processing_time*1000:.2f}ms",
                            extra_data={
                                'total_processing_time_ms': total_processing_time * 1000,
                                'validation_confidence': validation_result.confidence,
                                'validation_warnings': validation_result.warnings,
                                'extracted_nickname': trader_nickname,
                                'failure_reason': 'validation_failed'
                            }
                        )
                        
                        # Finish performance tracking with validation failure
                        self.performance_monitor.finish_operation(
                            trace_id, success=False, error_count=1,
                            operation_data={'failure_stage': 'validation'}
                        )
                        
                        return ProcessingResult(
                            success=False,
                            processing_time=total_processing_time,
                            data_extracted={},
                            confidence=validation_result.confidence,
                            errors=["Validation failed for trader data"],
                            warnings=validation_result.warnings
                        )
                else:
                    # Vision processing failed
                    total_processing_time = time.time() - start_time
                    self._update_performance_stats(total_processing_time, False)
                    
                    self.advanced_logger.error(
                        f"Vision processing failed in {total_processing_time*1000:.2f}ms",
                        extra_data={
                            'total_processing_time_ms': total_processing_time * 1000,
                            'timing_breakdown': {
                                'region_retrieval_ms': region_time * 1000,
                                'vision_processing_ms': vision_time * 1000
                            },
                            'failure_stage': 'vision_processing',
                            'region_config': region.name
                        }
                    )
                    
                    # Record vision processing error
                    self.error_tracker.record_error(
                        'game_monitor', 'trader_list_capture_vision_failed',
                        Exception("Vision processing returned no results"),
                        context={
                            'region_name': region.name,
                            'processing_time_ms': total_processing_time * 1000
                        },
                        trace_id=trace_id
                    )
                    
                    # Finish performance tracking with vision failure
                    self.performance_monitor.finish_operation(
                        trace_id, success=False, error_count=1,
                        operation_data={'failure_stage': 'vision_processing'}
                    )
                    
                    return ProcessingResult(
                        success=False,
                        processing_time=total_processing_time,
                        data_extracted={},
                        confidence=0.0,
                        errors=["Failed to capture trader list data"],
                        warnings=[]
                    )
                
            except Exception as e:
                # Comprehensive error handling
                total_processing_time = time.time() - start_time
                self._update_performance_stats(total_processing_time, False)
                
                self.advanced_logger.error(
                    f"Trader list capture failed with exception: {str(e)}",
                    error=e,
                    extra_data={
                        'total_processing_time_ms': total_processing_time * 1000,
                        'hotkey_type': 'F1',
                        'system_state': self.state.value,
                        'event_timestamp': event.timestamp,
                        'failure_type': 'exception',
                        'region_name': self.screen_regions['trader_list'].name
                    }
                )
                
                # Record exception error
                self.error_tracker.record_error(
                    'game_monitor', 'trader_list_capture_exception', e,
                    context={
                        'hotkey_type': 'F1',
                        'processing_time_ms': total_processing_time * 1000,
                        'event_timestamp': event.timestamp
                    },
                    trace_id=trace_id
                )
                
                # Finish performance tracking with error
                self.performance_monitor.finish_operation(trace_id, success=False, error_count=1)
                
                logger.error(f"Error in trader list capture: {e}")
                
                return ProcessingResult(
                    success=False,
                    processing_time=total_processing_time,
                    data_extracted={},
                    confidence=0.0,
                    errors=[str(e)],
                    warnings=[]
                )
    
    def _handle_item_scan_capture(self, event: CaptureEvent) -> ProcessingResult:
        """Handle F2 - Item Scan Capture"""
        logger.debug("Processing item scan capture")
        
        start_time = time.time()
        
        try:
            region = self.screen_regions['item_scan']
            
            # Multiple regions for item data
            regions_to_process = [
                (region, 'item_name')
            ]
            
            # Process all regions
            results = self.vision_system.process_multiple_regions(regions_to_process)
            
            if results:
                # Validate and process results
                processed_data = self._process_item_scan_data(results)
                
                processing_time = time.time() - start_time
                self._update_performance_stats(processing_time, True)
                
                return ProcessingResult(
                    success=True,
                    processing_time=processing_time,
                    data_extracted=processed_data,
                    confidence=0.9,  # Multi-region confidence
                    errors=[],
                    warnings=[]
                )
            
            processing_time = time.time() - start_time
            self._update_performance_stats(processing_time, False)
            
            return ProcessingResult(
                success=False,
                processing_time=processing_time,
                data_extracted={},
                confidence=0.0,
                errors=["No item data found"],
                warnings=[]
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            self._update_performance_stats(processing_time, False)
            
            logger.error(f"Error in item scan capture: {e}")
            return ProcessingResult(
                success=False,
                processing_time=processing_time,
                data_extracted={},
                confidence=0.0,
                errors=[str(e)],
                warnings=[]
            )
    
    def _handle_trader_inventory_capture(self, event: CaptureEvent) -> ProcessingResult:
        """Handle F3 - Trader Inventory Capture"""
        logger.debug("Processing trader inventory capture")
        
        start_time = time.time()
        
        try:
            region = self.screen_regions['trader_inventory']
            
            # Capture full inventory screen
            screenshot = self.vision_system.take_screenshot(region)
            
            if screenshot:
                # Process inventory data (this would be more complex in real implementation)
                inventory_data = self._process_inventory_screenshot(screenshot)
                
                if inventory_data:
                    processing_time = time.time() - start_time
                    self._update_performance_stats(processing_time, True)
                    
                    return ProcessingResult(
                        success=True,
                        processing_time=processing_time,
                        data_extracted=inventory_data,
                        confidence=0.85,
                        errors=[],
                        warnings=[]
                    )
            
            processing_time = time.time() - start_time
            self._update_performance_stats(processing_time, False)
            
            return ProcessingResult(
                success=False,
                processing_time=processing_time,
                data_extracted={},
                confidence=0.0,
                errors=["Failed to capture inventory"],
                warnings=[]
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            self._update_performance_stats(processing_time, False)
            
            logger.error(f"Error in inventory capture: {e}")
            return ProcessingResult(
                success=False,
                processing_time=processing_time,
                data_extracted={},
                confidence=0.0,
                errors=[str(e)],
                warnings=[]
            )
    
    def _handle_manual_verification(self, event: CaptureEvent) -> ProcessingResult:
        """Handle F4 - Manual Verification"""
        logger.debug("Manual verification requested")
        
        # This would open a GUI dialog for manual verification
        # For now, just log the request
        
        return ProcessingResult(
            success=True,
            processing_time=0.1,
            data_extracted={'action': 'manual_verification_requested'},
            confidence=1.0,
            errors=[],
            warnings=[]
        )
    
    def _handle_emergency_stop(self, event: CaptureEvent) -> ProcessingResult:
        """Handle F5 - Emergency Stop"""
        logger.warning("Emergency stop triggered")
        
        # Stop the system immediately
        self.stop()
        
        return ProcessingResult(
            success=True,
            processing_time=0.1,
            data_extracted={'action': 'emergency_stop'},
            confidence=1.0,
            errors=[],
            warnings=[]
        )
    
    # Data processing methods
    
    def _process_trader_list_data(self, raw_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process trader list data and update database"""
        processed = {
            'traders_found': len(raw_data),
            'trade_ids': []
        }
        
        # Update database with trader data
        trade_ids = self.db.update_inventory_and_track_trades(raw_data)
        processed['trade_ids'] = trade_ids
        
        logger.info(f"Processed {len(raw_data)} traders, generated {len(trade_ids)} trades")
        
        return processed
    
    def _process_item_scan_data(self, raw_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process item scan data"""
        processed = {
            'items_found': len(raw_data),
            'items': raw_data
        }
        
        # Additional processing could be added here
        return processed
    
    def _process_inventory_screenshot(self, screenshot) -> Dict[str, Any]:
        """Process full inventory screenshot"""
        # This would be a complex method to parse multiple items from inventory
        # For now, return simulated data
        
        return {
            'inventory_type': 'trader_inventory',
            'items_count': 5,  # Simulated
            'processing_method': 'full_screenshot'
        }
    
    def _update_performance_stats(self, processing_time: float, success: bool):
        """Update performance statistics"""
        self.performance_stats['total_captures'] += 1
        self.performance_stats['total_processing_time'] += processing_time
        
        if success:
            self.performance_stats['successful_captures'] += 1
        else:
            self.performance_stats['failed_captures'] += 1
        
        # Update timing stats
        self.performance_stats['avg_processing_time'] = (
            self.performance_stats['total_processing_time'] / 
            self.performance_stats['total_captures']
        )
        
        self.performance_stats['fastest_capture'] = min(
            self.performance_stats['fastest_capture'], processing_time
        )
        self.performance_stats['slowest_capture'] = max(
            self.performance_stats['slowest_capture'], processing_time
        )
        
        # Performance warnings
        if processing_time > self.config['performance']['warning_threshold']:
            logger.warning(f"Slow capture processing: {processing_time:.3f}s")
        
        if processing_time > self.config['performance']['max_capture_time']:
            logger.error(f"Capture exceeded time limit: {processing_time:.3f}s")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics"""
        stats = self.performance_stats.copy()
        
        # Add subsystem stats
        stats['hotkey_manager'] = self.hotkey_manager.get_statistics()
        stats['vision_system'] = self.vision_system.get_statistics()
        stats['validator'] = self.validator.get_statistics()
        stats['database'] = {}  # Database stats could be added
        
        # Calculate uptime
        if stats['uptime_start']:
            stats['uptime_seconds'] = time.time() - stats['uptime_start']
        else:
            stats['uptime_seconds'] = 0.0
        
        # Calculate success rate
        if stats['total_captures'] > 0:
            stats['success_rate'] = stats['successful_captures'] / stats['total_captures']
        else:
            stats['success_rate'] = 0.0
        
        return stats
    
    def reset_performance_stats(self):
        """Reset all performance statistics"""
        self.performance_stats = {
            'total_captures': 0,
            'successful_captures': 0,
            'failed_captures': 0,
            'avg_processing_time': 0.0,
            'total_processing_time': 0.0,
            'fastest_capture': float('inf'),
            'slowest_capture': 0.0,
            'uptime_start': time.time() if self.get_state() == SystemState.RUNNING else None
        }
        
        # Reset subsystem stats
        self.hotkey_manager.reset_statistics()
        self.vision_system.reset_statistics()
        self.validator.reset_statistics()
        
        logger.info("Performance statistics reset")
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get comprehensive system information"""
        return {
            'state': self.state.value,
            'config': self.config,
            'screen_regions': {name: {
                'x': region.x, 'y': region.y,
                'width': region.width, 'height': region.height
            } for name, region in self.screen_regions.items()},
            'performance': self.get_performance_stats()
        }

# Global instance for easy access
_game_monitor_instance = None
_game_monitor_lock = threading.Lock()

def get_game_monitor() -> GameMonitor:
    """Get singleton game monitor instance"""
    global _game_monitor_instance
    if _game_monitor_instance is None:
        with _game_monitor_lock:
            if _game_monitor_instance is None:
                _game_monitor_instance = GameMonitor()
    return _game_monitor_instance