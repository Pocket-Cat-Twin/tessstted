#!/usr/bin/env python3

import threading
import time
import logging
import psutil
import gc
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Callable, Any, Union
from pathlib import Path
import sqlite3
import os
import shutil

logger = logging.getLogger(__name__)


class RecoveryActionType(Enum):
    RESTART_COMPONENT = "restart_component"
    CLEAR_CACHE = "clear_cache"
    RESET_CONNECTION = "reset_connection"
    CLEANUP_MEMORY = "cleanup_memory"
    RESTART_THREAD = "restart_thread"
    RELOAD_CONFIG = "reload_config"
    RESET_DATABASE = "reset_database"
    CLEAR_TEMP_FILES = "clear_temp_files"
    FORCE_GARBAGE_COLLECTION = "force_gc"
    RESTART_SERVICE = "restart_service"
    RESET_HOTKEYS = "reset_hotkeys"
    CLEAR_ERROR_QUEUE = "clear_error_queue"


@dataclass
class RecoveryAction:
    action_type: RecoveryActionType
    component: str
    description: str
    execution_function: Callable
    timeout: float = 30.0
    prerequisites: List[str] = None
    post_actions: List[str] = None
    success_criteria: Optional[Callable] = None
    rollback_action: Optional[Callable] = None


@dataclass
class RecoveryProcedure:
    name: str
    component: str
    error_patterns: List[str]
    actions: List[RecoveryAction]
    max_attempts: int = 3
    cooldown_period: int = 300  # 5 minutes
    enabled: bool = True
    success_rate: float = 0.0
    total_attempts: int = 0
    successful_attempts: int = 0


class AutomatedRecovery:
    def __init__(self):
        self.procedures: Dict[str, RecoveryProcedure] = {}
        self.component_references: Dict[str, Any] = {}
        self.recovery_history: List[Dict] = []
        self.active_procedures: Dict[str, datetime] = {}
        
        # Threading
        self._lock = threading.RLock()
        self.executor_threads: Dict[str, threading.Thread] = {}
        
        # Statistics
        self.execution_stats = {
            "total_recoveries": 0,
            "successful_recoveries": 0,
            "failed_recoveries": 0,
            "average_recovery_time": 0.0
        }
        
        self._setup_default_procedures()
    
    def _setup_default_procedures(self):
        """Setup default recovery procedures for common scenarios"""
        
        # Database connection recovery
        db_recovery = RecoveryProcedure(
            name="database_connection_recovery",
            component="database_manager",
            error_patterns=["database", "connection", "sqlite", "locked"],
            actions=[
                RecoveryAction(
                    action_type=RecoveryActionType.RESET_CONNECTION,
                    component="database_manager",
                    description="Reset database connections",
                    execution_function=self._reset_database_connections,
                    timeout=15.0
                ),
                RecoveryAction(
                    action_type=RecoveryActionType.CLEAR_CACHE,
                    component="database_manager",
                    description="Clear database cache",
                    execution_function=self._clear_database_cache,
                    timeout=10.0
                ),
                RecoveryAction(
                    action_type=RecoveryActionType.RESET_DATABASE,
                    component="database_manager",
                    description="Reset database if corrupted",
                    execution_function=self._reset_database,
                    timeout=30.0
                )
            ]
        )
        self.add_procedure(db_recovery)
        
        # Memory management recovery
        memory_recovery = RecoveryProcedure(
            name="memory_management_recovery",
            component="system",
            error_patterns=["memory", "out of memory", "allocation", "leak"],
            actions=[
                RecoveryAction(
                    action_type=RecoveryActionType.FORCE_GARBAGE_COLLECTION,
                    component="system",
                    description="Force garbage collection",
                    execution_function=self._force_garbage_collection,
                    timeout=10.0
                ),
                RecoveryAction(
                    action_type=RecoveryActionType.CLEANUP_MEMORY,
                    component="system",
                    description="Clean up memory caches",
                    execution_function=self._cleanup_memory_caches,
                    timeout=15.0
                ),
                RecoveryAction(
                    action_type=RecoveryActionType.CLEAR_TEMP_FILES,
                    component="system",
                    description="Clear temporary files",
                    execution_function=self._clear_temp_files,
                    timeout=20.0
                )
            ]
        )
        self.add_procedure(memory_recovery)
        
        # OCR system recovery
        ocr_recovery = RecoveryProcedure(
            name="ocr_system_recovery",
            component="vision_system",
            error_patterns=["tesseract", "ocr", "image", "processing"],
            actions=[
                RecoveryAction(
                    action_type=RecoveryActionType.CLEAR_CACHE,
                    component="vision_system",
                    description="Clear OCR cache",
                    execution_function=self._clear_ocr_cache,
                    timeout=5.0
                ),
                RecoveryAction(
                    action_type=RecoveryActionType.RESTART_COMPONENT,
                    component="vision_system",
                    description="Restart OCR engine",
                    execution_function=self._restart_ocr_engine,
                    timeout=20.0
                )
            ]
        )
        self.add_procedure(ocr_recovery)
        
        # Hotkey system recovery
        hotkey_recovery = RecoveryProcedure(
            name="hotkey_system_recovery",
            component="hotkey_manager",
            error_patterns=["hotkey", "keyboard", "registration", "hook"],
            actions=[
                RecoveryAction(
                    action_type=RecoveryActionType.RESET_HOTKEYS,
                    component="hotkey_manager",
                    description="Re-register hotkeys",
                    execution_function=self._reset_hotkeys,
                    timeout=10.0
                ),
                RecoveryAction(
                    action_type=RecoveryActionType.RESTART_COMPONENT,
                    component="hotkey_manager",
                    description="Restart hotkey manager",
                    execution_function=self._restart_hotkey_manager,
                    timeout=15.0
                )
            ]
        )
        self.add_procedure(hotkey_recovery)
        
        # GUI system recovery
        gui_recovery = RecoveryProcedure(
            name="gui_system_recovery",
            component="gui_interface",
            error_patterns=["gui", "tkinter", "window", "display"],
            actions=[
                RecoveryAction(
                    action_type=RecoveryActionType.RESTART_COMPONENT,
                    component="gui_interface",
                    description="Restart GUI components",
                    execution_function=self._restart_gui_components,
                    timeout=20.0
                )
            ]
        )
        self.add_procedure(gui_recovery)
        
        # Performance recovery
        performance_recovery = RecoveryProcedure(
            name="performance_recovery",
            component="performance",
            error_patterns=["timeout", "slow", "performance", "bottleneck"],
            actions=[
                RecoveryAction(
                    action_type=RecoveryActionType.CLEAR_CACHE,
                    component="system",
                    description="Clear all caches",
                    execution_function=self._clear_all_caches,
                    timeout=10.0
                ),
                RecoveryAction(
                    action_type=RecoveryActionType.FORCE_GARBAGE_COLLECTION,
                    component="system",
                    description="Force garbage collection",
                    execution_function=self._force_garbage_collection,
                    timeout=5.0
                ),
                RecoveryAction(
                    action_type=RecoveryActionType.RESTART_THREAD,
                    component="performance",
                    description="Restart worker threads",
                    execution_function=self._restart_worker_threads,
                    timeout=15.0
                )
            ]
        )
        self.add_procedure(performance_recovery)
    
    def add_procedure(self, procedure: RecoveryProcedure):
        """Add a recovery procedure"""
        with self._lock:
            self.procedures[procedure.name] = procedure
            logger.info(f"Added recovery procedure: {procedure.name}")
    
    def register_component(self, component_name: str, component_instance: Any):
        """Register a component instance for recovery operations"""
        with self._lock:
            self.component_references[component_name] = component_instance
            logger.info(f"Registered component for recovery: {component_name}")
    
    def execute_recovery(self, component: str, error_message: str) -> bool:
        """Execute recovery procedure for component error"""
        
        # Find matching procedure
        procedure = self._find_matching_procedure(component, error_message)
        if not procedure:
            logger.warning(f"No recovery procedure found for {component}: {error_message}")
            return False
        
        # Check cooldown period
        if not self._check_cooldown(procedure):
            logger.info(f"Recovery procedure {procedure.name} is in cooldown")
            return False
        
        # Execute recovery procedure
        return self._execute_procedure(procedure, error_message)
    
    def _find_matching_procedure(self, component: str, error_message: str) -> Optional[RecoveryProcedure]:
        """Find matching recovery procedure"""
        
        error_lower = error_message.lower()
        
        # First try exact component match
        for procedure in self.procedures.values():
            if not procedure.enabled:
                continue
                
            if procedure.component == component:
                for pattern in procedure.error_patterns:
                    if pattern.lower() in error_lower:
                        return procedure
        
        # Then try partial matches
        for procedure in self.procedures.values():
            if not procedure.enabled:
                continue
                
            for pattern in procedure.error_patterns:
                if pattern.lower() in error_lower:
                    return procedure
        
        return None
    
    def _check_cooldown(self, procedure: RecoveryProcedure) -> bool:
        """Check if procedure is not in cooldown period"""
        
        if procedure.name in self.active_procedures:
            last_execution = self.active_procedures[procedure.name]
            time_since_last = (datetime.now() - last_execution).total_seconds()
            
            if time_since_last < procedure.cooldown_period:
                return False
        
        return True
    
    def _execute_procedure(self, procedure: RecoveryProcedure, error_message: str) -> bool:
        """Execute a recovery procedure"""
        
        start_time = datetime.now()
        logger.info(f"Executing recovery procedure: {procedure.name}")
        
        with self._lock:
            procedure.total_attempts += 1
            self.active_procedures[procedure.name] = start_time
        
        success = False
        executed_actions = []
        
        try:
            # Execute actions in sequence
            for action in procedure.actions:
                action_success = self._execute_action(action)
                executed_actions.append((action, action_success))
                
                if not action_success:
                    logger.warning(f"Recovery action failed: {action.description}")
                    # Try rollback if available
                    if action.rollback_action:
                        try:
                            action.rollback_action()
                            logger.info(f"Rolled back action: {action.description}")
                        except Exception as e:
                            logger.error(f"Rollback failed for {action.description}: {e}")
                    break
                else:
                    logger.info(f"Recovery action succeeded: {action.description}")
            
            # Check if all actions succeeded
            success = all(action_success for _, action_success in executed_actions)
            
            # Update statistics
            with self._lock:
                if success:
                    procedure.successful_attempts += 1
                    self.execution_stats["successful_recoveries"] += 1
                else:
                    self.execution_stats["failed_recoveries"] += 1
                
                procedure.success_rate = procedure.successful_attempts / procedure.total_attempts
                self.execution_stats["total_recoveries"] += 1
                
                # Update average recovery time
                execution_time = (datetime.now() - start_time).total_seconds()
                current_avg = self.execution_stats["average_recovery_time"]
                total_recoveries = self.execution_stats["total_recoveries"]
                self.execution_stats["average_recovery_time"] = (
                    (current_avg * (total_recoveries - 1) + execution_time) / total_recoveries
                )
            
            # Record recovery attempt
            self._record_recovery_attempt(procedure, error_message, success, execution_time, executed_actions)
            
        except Exception as e:
            logger.error(f"Exception during recovery procedure {procedure.name}: {e}")
            success = False
        
        if success:
            logger.info(f"Recovery procedure {procedure.name} completed successfully")
        else:
            logger.warning(f"Recovery procedure {procedure.name} failed")
        
        return success
    
    def _execute_action(self, action: RecoveryAction) -> bool:
        """Execute a single recovery action"""
        
        logger.info(f"Executing recovery action: {action.description}")
        
        try:
            # Set up timeout
            result = None
            exception = None
            
            def action_worker():
                nonlocal result, exception
                try:
                    result = action.execution_function()
                except Exception as e:
                    exception = e
            
            thread = threading.Thread(target=action_worker, daemon=True)
            thread.start()
            thread.join(timeout=action.timeout)
            
            if thread.is_alive():
                logger.warning(f"Recovery action timed out: {action.description}")
                return False
            
            if exception:
                logger.error(f"Recovery action failed: {action.description} - {exception}")
                return False
            
            # Check success criteria if provided
            if action.success_criteria:
                return action.success_criteria()
            
            return result is not False  # Consider None as success unless explicitly False
            
        except Exception as e:
            logger.error(f"Exception executing recovery action {action.description}: {e}")
            return False
    
    def _record_recovery_attempt(self, procedure: RecoveryProcedure, error_message: str, 
                                success: bool, execution_time: float, executed_actions: List):
        """Record recovery attempt for analysis"""
        
        record = {
            "timestamp": datetime.now().isoformat(),
            "procedure_name": procedure.name,
            "component": procedure.component,
            "error_message": error_message,
            "success": success,
            "execution_time": execution_time,
            "actions_executed": len(executed_actions),
            "successful_actions": len([a for a in executed_actions if a[1]]),
            "failed_actions": len([a for a in executed_actions if not a[1]])
        }
        
        with self._lock:
            self.recovery_history.append(record)
            # Keep only last 1000 records
            if len(self.recovery_history) > 1000:
                self.recovery_history = self.recovery_history[-1000:]
    
    # Recovery action implementations
    
    def _reset_database_connections(self) -> bool:
        """Reset database connections"""
        try:
            db_manager = self.component_references.get("database_manager")
            if db_manager and hasattr(db_manager, "reset_connections"):
                db_manager.reset_connections()
                return True
            
            # Fallback: close all sqlite connections
            import sqlite3
            # Force close connections by clearing cache
            sqlite3.register_adapter(type, lambda x: None)
            return True
            
        except Exception as e:
            logger.error(f"Failed to reset database connections: {e}")
            return False
    
    def _clear_database_cache(self) -> bool:
        """Clear database cache"""
        try:
            db_manager = self.component_references.get("database_manager")
            if db_manager and hasattr(db_manager, "clear_cache"):
                db_manager.clear_cache()
                return True
            return True
        except Exception as e:
            logger.error(f"Failed to clear database cache: {e}")
            return False
    
    def _reset_database(self) -> bool:
        """Reset database if corrupted"""
        try:
            # This is a drastic measure - backup and recreate
            db_path = "data/game_monitor.db"
            if os.path.exists(db_path):
                backup_path = f"{db_path}.backup_{int(datetime.now().timestamp())}"
                shutil.copy2(db_path, backup_path)
                logger.info(f"Database backed up to: {backup_path}")
            
            db_manager = self.component_references.get("database_manager")
            if db_manager and hasattr(db_manager, "reset_database"):
                db_manager.reset_database()
                return True
            return True
        except Exception as e:
            logger.error(f"Failed to reset database: {e}")
            return False
    
    def _force_garbage_collection(self) -> bool:
        """Force garbage collection"""
        try:
            gc.collect()
            logger.info("Garbage collection completed")
            return True
        except Exception as e:
            logger.error(f"Failed to run garbage collection: {e}")
            return False
    
    def _cleanup_memory_caches(self) -> bool:
        """Clean up memory caches"""
        try:
            # Clear various caches
            components = ["vision_system", "validator", "cache_manager"]
            for comp_name in components:
                comp = self.component_references.get(comp_name)
                if comp and hasattr(comp, "clear_cache"):
                    comp.clear_cache()
            
            # Force garbage collection
            gc.collect()
            return True
        except Exception as e:
            logger.error(f"Failed to cleanup memory caches: {e}")
            return False
    
    def _clear_temp_files(self) -> bool:
        """Clear temporary files"""
        try:
            import tempfile
            temp_dir = tempfile.gettempdir()
            
            # Clear application-specific temp files
            app_temp_patterns = ["game_monitor_*", "ocr_temp_*", "*.tmp"]
            
            for pattern in app_temp_patterns:
                try:
                    import glob
                    temp_files = glob.glob(os.path.join(temp_dir, pattern))
                    for temp_file in temp_files:
                        try:
                            os.remove(temp_file)
                        except:
                            pass  # Ignore errors for individual files
                except:
                    pass
            
            return True
        except Exception as e:
            logger.error(f"Failed to clear temp files: {e}")
            return False
    
    def _clear_ocr_cache(self) -> bool:
        """Clear OCR cache"""
        try:
            vision_system = self.component_references.get("vision_system")
            if vision_system and hasattr(vision_system, "clear_ocr_cache"):
                vision_system.clear_ocr_cache()
                return True
            return True
        except Exception as e:
            logger.error(f"Failed to clear OCR cache: {e}")
            return False
    
    def _restart_ocr_engine(self) -> bool:
        """Restart OCR engine"""
        try:
            vision_system = self.component_references.get("vision_system")
            if vision_system and hasattr(vision_system, "restart_ocr"):
                vision_system.restart_ocr()
                return True
            return True
        except Exception as e:
            logger.error(f"Failed to restart OCR engine: {e}")
            return False
    
    def _reset_hotkeys(self) -> bool:
        """Reset hotkeys"""
        try:
            hotkey_manager = self.component_references.get("hotkey_manager")
            if hotkey_manager and hasattr(hotkey_manager, "reset_hotkeys"):
                hotkey_manager.reset_hotkeys()
                return True
            return True
        except Exception as e:
            logger.error(f"Failed to reset hotkeys: {e}")
            return False
    
    def _restart_hotkey_manager(self) -> bool:
        """Restart hotkey manager"""
        try:
            hotkey_manager = self.component_references.get("hotkey_manager")
            if hotkey_manager and hasattr(hotkey_manager, "restart"):
                hotkey_manager.restart()
                return True
            return True
        except Exception as e:
            logger.error(f"Failed to restart hotkey manager: {e}")
            return False
    
    def _restart_gui_components(self) -> bool:
        """Restart GUI components"""
        try:
            gui_interface = self.component_references.get("gui_interface")
            if gui_interface and hasattr(gui_interface, "restart_components"):
                gui_interface.restart_components()
                return True
            return True
        except Exception as e:
            logger.error(f"Failed to restart GUI components: {e}")
            return False
    
    def _clear_all_caches(self) -> bool:
        """Clear all system caches"""
        try:
            # Clear caches from all registered components
            cache_cleared = False
            for comp_name, comp in self.component_references.items():
                if hasattr(comp, "clear_cache"):
                    try:
                        comp.clear_cache()
                        cache_cleared = True
                    except:
                        pass
            
            return cache_cleared
        except Exception as e:
            logger.error(f"Failed to clear all caches: {e}")
            return False
    
    def _restart_worker_threads(self) -> bool:
        """Restart worker threads"""
        try:
            # This is component-specific, try to restart known components
            components = ["hotkey_manager", "vision_system", "performance_monitor"]
            restarted = False
            
            for comp_name in components:
                comp = self.component_references.get(comp_name)
                if comp and hasattr(comp, "restart_workers"):
                    try:
                        comp.restart_workers()
                        restarted = True
                    except:
                        pass
            
            return restarted
        except Exception as e:
            logger.error(f"Failed to restart worker threads: {e}")
            return False
    
    def get_recovery_statistics(self) -> Dict[str, Any]:
        """Get recovery statistics"""
        with self._lock:
            procedure_stats = {}
            for name, procedure in self.procedures.items():
                procedure_stats[name] = {
                    "total_attempts": procedure.total_attempts,
                    "successful_attempts": procedure.successful_attempts,
                    "success_rate": procedure.success_rate,
                    "enabled": procedure.enabled
                }
            
            return {
                "execution_stats": self.execution_stats.copy(),
                "procedure_stats": procedure_stats,
                "total_procedures": len(self.procedures),
                "active_procedures": len(self.active_procedures),
                "history_records": len(self.recovery_history)
            }
    
    def get_recovery_history(self, limit: int = 50) -> List[Dict]:
        """Get recovery history"""
        with self._lock:
            return self.recovery_history[-limit:]


# Singleton instance
automated_recovery = AutomatedRecovery()