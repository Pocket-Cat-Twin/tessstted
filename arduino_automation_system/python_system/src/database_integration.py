"""
Database Integration for Arduino Automation System
Integrates with existing market monitoring system database
"""

import sqlite3
import logging
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
from pathlib import Path
import sys
import os

# Add market monitoring system to path for importing DatabaseManager
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'market_monitoring_system', 'src'))

try:
    from core.database_manager import DatabaseManager
except ImportError:
    # Fallback if import fails
    DatabaseManager = None


@dataclass
class AutomationTarget:
    """Data structure for automation targets."""
    id: Optional[int]
    target_name: str
    status: str = 'NEW'  # NEW, PROCESSING, COMPLETED
    created_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None
    processing_attempts: int = 0


@dataclass
class TraderData:
    """Data structure for trader information from sellers_current."""
    seller_name: str
    status: str
    last_updated: datetime
    priority_group: int


class AutomationDatabaseManager:
    """
    Database manager for Arduino automation system.
    Extends existing market monitoring database with automation-specific tables.
    """
    
    # SQL schema for automation tables
    AUTOMATION_SCHEMA = {
        'automation_targets': '''
            CREATE TABLE IF NOT EXISTS automation_targets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target_name TEXT NOT NULL UNIQUE,
                status TEXT CHECK(status IN ('NEW', 'PROCESSING', 'COMPLETED')) DEFAULT 'NEW',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                processed_at DATETIME,
                processing_attempts INTEGER DEFAULT 0
            )
        ''',
        'automation_targets_index': '''
            CREATE INDEX IF NOT EXISTS idx_automation_targets_status 
            ON automation_targets(status, created_at)
        ''',
        'automation_sessions': '''
            CREATE TABLE IF NOT EXISTS automation_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_type TEXT CHECK(session_type IN ('database_monitor', 'array_processor')) NOT NULL,
                started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                ended_at DATETIME,
                targets_processed INTEGER DEFAULT 0,
                commands_executed INTEGER DEFAULT 0,
                errors_count INTEGER DEFAULT 0,
                status TEXT CHECK(status IN ('running', 'completed', 'failed', 'stopped')) DEFAULT 'running'
            )
        ''',
        'automation_commands_log': '''
            CREATE TABLE IF NOT EXISTS automation_commands_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                command_type TEXT NOT NULL,
                command_data TEXT,
                execution_time REAL,
                result TEXT CHECK(result IN ('success', 'error', 'timeout')) NOT NULL,
                error_message TEXT,
                executed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES automation_sessions (id)
            )
        '''
    }
    
    def __init__(self, db_path: str, connection_timeout: int = 30):
        """
        Initialize automation database manager.
        
        Args:
            db_path: Path to SQLite database file
            connection_timeout: Connection timeout in seconds
        """
        self.db_path = Path(db_path)
        self.connection_timeout = connection_timeout
        self.logger = logging.getLogger(__name__)
        self._local = threading.local()
        
        # Try to use existing DatabaseManager if available
        self.market_db_manager = None
        if DatabaseManager:
            try:
                self.market_db_manager = DatabaseManager(str(db_path), connection_timeout)
                self.logger.info("Using existing market monitoring DatabaseManager")
            except Exception as e:
                self.logger.warning(f"Could not initialize market DatabaseManager: {e}")
        
        # Ensure database exists and has automation tables
        self._initialize_automation_tables()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        if not hasattr(self._local, 'connection'):
            self._local.connection = sqlite3.connect(
                str(self.db_path),
                timeout=self.connection_timeout,
                isolation_level=None  # Autocommit mode
            )
            
            # Enable foreign key support
            self._local.connection.execute("PRAGMA foreign_keys = ON")
            
        return self._local.connection
    
    @contextmanager
    def _transaction(self, timeout_seconds: int = 30):
        """Context manager for database transactions."""
        conn = self._get_connection()
        try:
            conn.execute("BEGIN IMMEDIATE")
            yield conn
            conn.execute("COMMIT")
        except Exception as e:
            conn.execute("ROLLBACK")
            self.logger.error(f"Database transaction failed: {e}")
            raise
    
    def _initialize_automation_tables(self) -> None:
        """Initialize automation-specific database tables."""
        try:
            with self._transaction() as conn:
                # Create automation tables
                for table_name, sql in self.AUTOMATION_SCHEMA.items():
                    conn.execute(sql)
                    
            self.logger.info("Automation database tables initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize automation tables: {e}")
            raise
    
    def add_automation_target(self, target_name: str) -> int:
        """
        Add new automation target.
        
        Args:
            target_name: Name of the target to process
            
        Returns:
            ID of created target
        """
        try:
            with self._transaction() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR IGNORE INTO automation_targets (target_name)
                    VALUES (?)
                ''', (target_name,))
                
                # Get the ID (either newly inserted or existing)
                cursor.execute('''
                    SELECT id FROM automation_targets WHERE target_name = ?
                ''', (target_name,))
                
                target_id = cursor.fetchone()[0]
                self.logger.info(f"Added automation target: {target_name} (ID: {target_id})")
                return target_id
                
        except Exception as e:
            self.logger.error(f"Failed to add automation target: {e}")
            raise
    
    def get_new_targets(self, limit: int = 10) -> List[AutomationTarget]:
        """
        Get automation targets with NEW status.
        
        Args:
            limit: Maximum number of targets to return
            
        Returns:
            List of AutomationTarget objects
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, target_name, status, created_at, processed_at, processing_attempts
                FROM automation_targets 
                WHERE status = 'NEW'
                ORDER BY created_at ASC
                LIMIT ?
            ''', (limit,))
            
            targets = []
            for row in cursor.fetchall():
                target = AutomationTarget(
                    id=row[0],
                    target_name=row[1],
                    status=row[2],
                    created_at=datetime.fromisoformat(row[3]) if row[3] else None,
                    processed_at=datetime.fromisoformat(row[4]) if row[4] else None,
                    processing_attempts=row[5]
                )
                targets.append(target)
            
            return targets
            
        except Exception as e:
            self.logger.error(f"Failed to get new targets: {e}")
            return []
    
    def update_target_status(self, target_id: int, status: str, 
                           increment_attempts: bool = False) -> bool:
        """
        Update automation target status.
        
        Args:
            target_id: Target ID
            status: New status (NEW, PROCESSING, COMPLETED)
            increment_attempts: Whether to increment processing attempts
            
        Returns:
            True if update successful
        """
        try:
            with self._transaction() as conn:
                cursor = conn.cursor()
                
                if status == 'COMPLETED':
                    # Set processed_at when completing
                    if increment_attempts:
                        cursor.execute('''
                            UPDATE automation_targets 
                            SET status = ?, processed_at = CURRENT_TIMESTAMP,
                                processing_attempts = processing_attempts + 1
                            WHERE id = ?
                        ''', (status, target_id))
                    else:
                        cursor.execute('''
                            UPDATE automation_targets 
                            SET status = ?, processed_at = CURRENT_TIMESTAMP
                            WHERE id = ?
                        ''', (status, target_id))
                else:
                    # Regular status update
                    if increment_attempts:
                        cursor.execute('''
                            UPDATE automation_targets 
                            SET status = ?, processing_attempts = processing_attempts + 1
                            WHERE id = ?
                        ''', (status, target_id))
                    else:
                        cursor.execute('''
                            UPDATE automation_targets 
                            SET status = ?
                            WHERE id = ?
                        ''', (status, target_id))
                
                updated = cursor.rowcount > 0
                if updated:
                    self.logger.debug(f"Updated target {target_id} status to {status}")
                
                return updated
                
        except Exception as e:
            self.logger.error(f"Failed to update target status: {e}")
            return False
    
    def create_automation_session(self, session_type: str) -> int:
        """
        Create new automation session.
        
        Args:
            session_type: Type of session (database_monitor, array_processor)
            
        Returns:
            Session ID
        """
        try:
            with self._transaction() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO automation_sessions (session_type)
                    VALUES (?)
                ''', (session_type,))
                
                session_id = cursor.lastrowid
                self.logger.info(f"Created automation session: {session_type} (ID: {session_id})")
                return session_id
                
        except Exception as e:
            self.logger.error(f"Failed to create automation session: {e}")
            raise
    
    def end_automation_session(self, session_id: int, status: str = 'completed') -> None:
        """
        End automation session.
        
        Args:
            session_id: Session ID
            status: Final status (completed, failed, stopped)
        """
        try:
            with self._transaction() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE automation_sessions 
                    SET ended_at = CURRENT_TIMESTAMP, status = ?
                    WHERE id = ?
                ''', (status, session_id))
                
                self.logger.info(f"Ended automation session {session_id} with status: {status}")
                
        except Exception as e:
            self.logger.error(f"Failed to end automation session: {e}")
    
    def log_command_execution(self, session_id: int, command_type: str, 
                            command_data: str, execution_time: float,
                            result: str, error_message: Optional[str] = None) -> None:
        """
        Log automation command execution.
        
        Args:
            session_id: Session ID
            command_type: Type of command (click, type, key, hotkey, delay)
            command_data: Command data/parameters
            execution_time: Execution time in seconds
            result: Execution result (success, error, timeout)
            error_message: Optional error message
        """
        try:
            with self._transaction() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO automation_commands_log 
                    (session_id, command_type, command_data, execution_time, result, error_message)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (session_id, command_type, command_data, execution_time, result, error_message))
                
        except Exception as e:
            self.logger.error(f"Failed to log command execution: {e}")
    
    def update_session_stats(self, session_id: int, targets_processed: int = 0,
                           commands_executed: int = 0, errors_count: int = 0) -> None:
        """
        Update automation session statistics.
        
        Args:
            session_id: Session ID
            targets_processed: Number of targets processed
            commands_executed: Number of commands executed
            errors_count: Number of errors encountered
        """
        try:
            with self._transaction() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE automation_sessions 
                    SET targets_processed = targets_processed + ?,
                        commands_executed = commands_executed + ?,
                        errors_count = errors_count + ?
                    WHERE id = ?
                ''', (targets_processed, commands_executed, errors_count, session_id))
                
        except Exception as e:
            self.logger.error(f"Failed to update session stats: {e}")
    
    def get_automation_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get automation statistics for the specified time period.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            Dictionary with statistics
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Calculate time threshold
            time_threshold = datetime.now() - timedelta(hours=hours)
            
            # Get target statistics
            cursor.execute('''
                SELECT status, COUNT(*) as count
                FROM automation_targets 
                WHERE created_at >= ?
                GROUP BY status
            ''', (time_threshold.isoformat(),))
            
            target_stats = {row[0]: row[1] for row in cursor.fetchall()}
            
            # Get session statistics
            cursor.execute('''
                SELECT session_type, COUNT(*) as sessions, 
                       SUM(targets_processed) as total_targets,
                       SUM(commands_executed) as total_commands,
                       SUM(errors_count) as total_errors
                FROM automation_sessions 
                WHERE started_at >= ?
                GROUP BY session_type
            ''', (time_threshold.isoformat(),))
            
            session_stats = {}
            for row in cursor.fetchall():
                session_stats[row[0]] = {
                    'sessions': row[1],
                    'targets_processed': row[2] or 0,
                    'commands_executed': row[3] or 0,
                    'errors': row[4] or 0
                }
            
            return {
                'time_period_hours': hours,
                'target_statistics': target_stats,
                'session_statistics': session_stats,
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get automation statistics: {e}")
            return {}
    
    def cleanup_old_records(self, days: int = 7) -> int:
        """
        Clean up old automation records.
        
        Args:
            days: Number of days to keep records
            
        Returns:
            Number of records deleted
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            deleted_count = 0
            
            with self._transaction() as conn:
                cursor = conn.cursor()
                
                # Clean up completed targets
                cursor.execute('''
                    DELETE FROM automation_targets 
                    WHERE status = 'COMPLETED' AND processed_at < ?
                ''', (cutoff_date.isoformat(),))
                deleted_count += cursor.rowcount
                
                # Clean up old command logs
                cursor.execute('''
                    DELETE FROM automation_commands_log 
                    WHERE executed_at < ?
                ''', (cutoff_date.isoformat(),))
                deleted_count += cursor.rowcount
                
                # Clean up old sessions
                cursor.execute('''
                    DELETE FROM automation_sessions 
                    WHERE ended_at IS NOT NULL AND ended_at < ?
                ''', (cutoff_date.isoformat(),))
                deleted_count += cursor.rowcount
                
                self.logger.info(f"Cleaned up {deleted_count} old automation records")
                return deleted_count
                
        except Exception as e:
            self.logger.error(f"Failed to cleanup old records: {e}")
            return 0
    
    def get_traders_sorted_unique(self) -> List[str]:
        """
        Get unique trader names from sellers_current with proper priority sorting.
        
        Sort Order:
        1. NEW status traders (newest first by last_updated DESC)
        2. All other status traders (newest first by last_updated DESC)
        3. Deduplication: keep only first occurrence of each seller_name
        
        Returns:
            List of unique seller names in priority order
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Enhanced query with explicit priority sorting
            cursor.execute('''
                SELECT seller_name, status, last_updated
                FROM sellers_current 
                ORDER BY 
                    -- Priority 1: NEW status first (0), all others second (1)
                    CASE 
                        WHEN status = 'NEW' THEN 0 
                        ELSE 1 
                    END ASC,
                    -- Priority 2: Within each status group, newest first
                    last_updated DESC,
                    -- Priority 3: Consistent secondary sort for deterministic results
                    seller_name ASC
            ''')
            
            # Process results maintaining priority order
            seen_traders = set()
            priority_traders = []
            
            for row in cursor.fetchall():
                seller_name = row[0]
                status = row[1]
                last_updated = row[2]
                
                # Add only first occurrence of each trader (maintains priority)
                if seller_name not in seen_traders:
                    seen_traders.add(seller_name)
                    priority_traders.append(seller_name)
                    
                    self.logger.debug(f"Added trader: {seller_name} (status: {status}, updated: {last_updated})")
            
            self.logger.info(f"Retrieved {len(priority_traders)} unique traders in priority order")
            return priority_traders
            
        except Exception as e:
            self.logger.error(f"Failed to get traders with priority sorting: {e}")
            return []
    
    def get_traders_debug_info(self) -> List[Dict[str, Any]]:
        """
        Get detailed trader information for debugging sort order.
        Returns full trader data to verify sorting logic.
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT seller_name, status, last_updated,
                       CASE WHEN status = 'NEW' THEN 0 ELSE 1 END as priority_group
                FROM sellers_current 
                ORDER BY 
                    CASE WHEN status = 'NEW' THEN 0 ELSE 1 END ASC,
                    last_updated DESC,
                    seller_name ASC
            ''')
            
            debug_traders = []
            for row in cursor.fetchall():
                debug_traders.append({
                    'seller_name': row[0],
                    'status': row[1], 
                    'last_updated': row[2],
                    'priority_group': row[3]
                })
            
            return debug_traders
            
        except Exception as e:
            self.logger.error(f"Failed to get debug trader info: {e}")
            return []
    
    def calculate_traders_hash(self, traders: List[str]) -> str:
        """Calculate hash of traders list to detect changes."""
        import hashlib
        traders_str = '|'.join(sorted(traders))
        return hashlib.md5(traders_str.encode()).hexdigest()
    
    def close_connection(self) -> None:
        """Close database connection for current thread."""
        if hasattr(self._local, 'connection'):
            self._local.connection.close()
            del self._local.connection