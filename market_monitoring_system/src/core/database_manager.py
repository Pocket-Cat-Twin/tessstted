"""
Database manager for market monitoring system.
Handles all database operations, schema creation, and data integrity.
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
import json
import random


@dataclass
class ItemData:
    """Data structure for item information."""
    seller_name: str
    item_name: str
    price: Optional[float]
    quantity: Optional[int]
    item_id: Optional[str]
    hotkey: str
    processing_type: str = 'full'  # NEW FIELD: 'full' or 'minimal'


@dataclass
class ChangeLogEntry:
    """Data structure for change log entries."""
    seller_name: str
    item_name: str
    change_type: str
    old_value: Optional[str]
    new_value: Optional[str]


class DatabaseManager:
    """
    Manages all database operations for the market monitoring system.
    Thread-safe with proper connection management and error handling.
    """
    
    # SQL schema definitions
    SCHEMA_SQL = {
        'items': '''
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                seller_name TEXT NOT NULL,
                item_name TEXT NOT NULL,
                price REAL,
                quantity INTEGER,
                item_id TEXT,
                hotkey TEXT NOT NULL,
                processing_type TEXT CHECK(processing_type IN ('full', 'minimal')) DEFAULT 'full',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''',
        'items_index': '''
            CREATE INDEX IF NOT EXISTS idx_seller_item_time 
            ON items(seller_name, item_name, created_at)
        ''',
        'sellers_current': '''
            CREATE TABLE IF NOT EXISTS sellers_current (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                seller_name TEXT NOT NULL,
                item_name TEXT NOT NULL,
                quantity INTEGER,
                status TEXT CHECK(status IN ('NEW', 'CHECKED', 'UNCHECKED', 'GONE')) DEFAULT 'NEW',
                processing_type TEXT CHECK(processing_type IN ('full', 'minimal')) DEFAULT 'full',
                status_changed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(seller_name, item_name)
            )
        ''',
        'monitoring_queue': '''
            CREATE TABLE IF NOT EXISTS monitoring_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                seller_name TEXT NOT NULL,
                item_name TEXT NOT NULL,
                status TEXT CHECK(status IN ('NEW', 'CHECKED', 'UNCHECKED', 'GONE')) DEFAULT 'NEW',
                processing_type TEXT CHECK(processing_type IN ('full', 'minimal')) DEFAULT 'full',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                status_changed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(seller_name, item_name)
            )
        ''',
        'changes_log': '''
            CREATE TABLE IF NOT EXISTS changes_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                seller_name TEXT NOT NULL,
                item_name TEXT NOT NULL,
                change_type TEXT CHECK(change_type IN (
                    'PRICE_INCREASE', 'PRICE_DECREASE', 
                    'QUANTITY_INCREASE', 'QUANTITY_DECREASE',
                    'NEW_ITEM', 'ITEM_REMOVED', 'SELLER_NEW', 'SELLER_REMOVED',
                    'NEW_COMBINATION', 'SALE_DETECTED', 'COMBINATION_REMOVED'
                )),
                old_value TEXT,
                new_value TEXT,
                detected_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''',
        'sales_log': '''
            CREATE TABLE IF NOT EXISTS sales_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                seller_name TEXT NOT NULL,
                item_name TEXT NOT NULL,
                last_price REAL,
                last_quantity INTEGER,
                processing_type TEXT CHECK(processing_type IN ('full', 'minimal')) DEFAULT 'minimal',
                sale_detected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                previous_status TEXT
            )
        ''',
        'ocr_sessions': '''
            CREATE TABLE IF NOT EXISTS ocr_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hotkey TEXT NOT NULL,
                processed_items INTEGER DEFAULT 0,
                processing_time REAL,
                status TEXT CHECK(status IN ('pending', 'processing', 'completed', 'failed')) DEFAULT 'pending',
                error_message TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        '''
    }
    
    

    def __init__(self, db_path: str, connection_timeout: int = 30):
        """
        Initialize database manager.
        
        Args:
            db_path: Path to SQLite database file
            connection_timeout: Connection timeout in seconds
        """
        self.db_path = Path(db_path)
        self.connection_timeout = connection_timeout
        self._local = threading.local()
        self.logger = logging.getLogger(__name__)
        
        # Ensure database directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database schema
        self._initialize_database()
        
        
    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection with optimized settings."""
        if not hasattr(self._local, 'connection'):
            self._local.connection = sqlite3.connect(
                str(self.db_path),
                timeout=self.connection_timeout,
                isolation_level=None  # Autocommit mode
            )
            
            # Optimize connection settings
            conn = self._local.connection
            
            # Enable foreign key support
            conn.execute("PRAGMA foreign_keys = ON")
            
            # Set WAL mode for better concurrency
            conn.execute("PRAGMA journal_mode = WAL")
            
            # Set synchronous mode for better performance with WAL
            conn.execute("PRAGMA synchronous = NORMAL")
            
            # Set cache size for better performance
            conn.execute("PRAGMA cache_size = -2000")  # 2MB cache
            
            # Set temp store to memory for better performance
            conn.execute("PRAGMA temp_store = MEMORY")
            
            # Set default timeout
            conn.execute("PRAGMA busy_timeout = 30000")  # 30 seconds
            
        return self._local.connection
    
    @contextmanager
    def _transaction(self, timeout_seconds: int = 30, max_retries: int = 3):
        """Context manager for database transactions with timeout and retry logic."""
        conn = self._get_connection()
        transaction_start = time.time()
        
        for attempt in range(max_retries + 1):
            try:
                # Set busy timeout to prevent immediate failures
                conn.execute(f"PRAGMA busy_timeout = {timeout_seconds * 1000}")
                
                # Use BEGIN IMMEDIATE to detect conflicts early
                conn.execute("BEGIN IMMEDIATE")
                
                # Check if transaction is taking too long
                def check_timeout():
                    if time.time() - transaction_start > timeout_seconds:
                        raise sqlite3.OperationalError("Transaction timeout exceeded")
                
                try:
                    yield conn
                    check_timeout()
                    conn.execute("COMMIT")
                    return
                except Exception as inner_e:
                    conn.execute("ROLLBACK")
                    raise inner_e
                
            except sqlite3.OperationalError as e:
                if attempt < max_retries and ("database is locked" in str(e).lower() or "busy" in str(e).lower()):
                    # Exponential backoff with jitter
                    delay = (0.1 * (2 ** attempt)) + random.uniform(0, 0.1)
                    self.logger.warning(f"Database locked (attempt {attempt + 1}/{max_retries + 1}), retrying in {delay:.3f}s")
                    time.sleep(delay)
                    continue
                else:
                    self.logger.error(f"Database transaction failed after {attempt + 1} attempts: {e}")
                    raise
            except Exception as e:
                self.logger.error(f"Database transaction failed: {e}")
                raise
    
    def _initialize_database(self) -> None:
        """Initialize database schema and indexes."""
        try:
            with self._transaction() as conn:
                # Create all tables and indexes
                for table_name, sql in self.SCHEMA_SQL.items():
                    conn.execute(sql)
                    
            self.logger.info("Database schema initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            raise
    
    def save_items_data(self, items: List[ItemData], session_id: Optional[int] = None) -> int:
        """
        Save items data to database.
        
        Args:
            items: List of ItemData objects to save
            session_id: Optional OCR session ID
            
        Returns:
            Number of items saved
        """
        if not items:
            return 0
            
        try:
            with self._transaction() as conn:
                cursor = conn.cursor()
                
                # Insert items
                for item in items:
                    cursor.execute('''
                        INSERT INTO items (seller_name, item_name, price, quantity, item_id, hotkey, processing_type)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        item.seller_name,
                        item.item_name,
                        item.price,
                        item.quantity,
                        item.item_id,
                        item.hotkey,
                        item.processing_type
                    ))
                
                saved_count = len(items)
                
                # Update OCR session if provided
                if session_id:
                    cursor.execute('''
                        UPDATE ocr_sessions 
                        SET processed_items = processed_items + ?
                        WHERE id = ?
                    ''', (saved_count, session_id))
                
                self.logger.info(f"Saved {saved_count} items to database")
                return saved_count
                
        except Exception as e:
            self.logger.error(f"Failed to save items data: {e}")
            raise
    
    def update_sellers_status(self, seller_name: str, item_name: str, 
                             quantity: Optional[int] = None, 
                             status: str = 'NEW',
                             processing_type: str = 'full') -> bool:
        """
        Update seller current status.
        
        Args:
            seller_name: Name of the seller
            item_name: Name of the item
            quantity: Current quantity (optional)
            status: Current status (NEW, CHECKED, UNCHECKED, GONE)
            processing_type: Processing type (full, minimal)
            
        Returns:
            True if update was successful
        """
        try:
            with self._transaction() as conn:
                cursor = conn.cursor()
                
                # Check if record exists
                cursor.execute('''
                    SELECT id, status FROM sellers_current 
                    WHERE seller_name = ? AND item_name = ?
                ''', (seller_name, item_name))
                
                existing = cursor.fetchone()
                
                if existing:
                    # Update existing record
                    # Always reset status_changed_at to reset the 10-minute timer when item is re-processed
                    cursor.execute('''
                        UPDATE sellers_current 
                        SET quantity = ?, status = ?, processing_type = ?,
                            status_changed_at = CURRENT_TIMESTAMP,
                            last_updated = CURRENT_TIMESTAMP
                        WHERE seller_name = ? AND item_name = ?
                    ''', (quantity, status, processing_type, seller_name, item_name))
                else:
                    # Insert new record
                    cursor.execute('''
                        INSERT INTO sellers_current 
                        (seller_name, item_name, quantity, status, processing_type, status_changed_at, last_updated)
                        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    ''', (seller_name, item_name, quantity, status, processing_type))
                
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to update seller status: {e}")
            return False
    
    def manage_monitoring_queue(self, items: List[ItemData]) -> None:
        """
        Update monitoring queue with current items.
        
        Args:
            items: Current items from OCR processing
        """
        try:
            with self._transaction() as conn:
                cursor = conn.cursor()
                
                for item in items:
                    cursor.execute('''
                        INSERT OR REPLACE INTO monitoring_queue 
                        (seller_name, item_name, status, status_changed_at)
                        VALUES (?, ?, 
                            COALESCE((SELECT status FROM monitoring_queue 
                                     WHERE seller_name = ? AND item_name = ?), 'NEW'),
                            COALESCE((SELECT status_changed_at FROM monitoring_queue 
                                     WHERE seller_name = ? AND item_name = ?), CURRENT_TIMESTAMP)
                        )
                    ''', (
                        item.seller_name, item.item_name,
                        item.seller_name, item.item_name,
                        item.seller_name, item.item_name
                    ))
                
                self.logger.info(f"Updated monitoring queue with {len(items)} items")
                
        except Exception as e:
            self.logger.error(f"Failed to manage monitoring queue: {e}")
            raise
    
    def detect_and_log_changes(self, current_items: List[ItemData]) -> List[ChangeLogEntry]:
        """
        Detect changes by comparing with previous data and log them.
        
        Args:
            current_items: Current items from OCR processing
            
        Returns:
            List of detected changes
        """
        changes = []
        
        try:
            with self._transaction() as conn:
                cursor = conn.cursor()
                
                for item in current_items:
                    # Get latest previous data for this seller-item combination
                    cursor.execute('''
                        SELECT price, quantity FROM items 
                        WHERE seller_name = ? AND item_name = ?
                        ORDER BY created_at DESC LIMIT 1 OFFSET 1
                    ''', (item.seller_name, item.item_name))
                    
                    previous = cursor.fetchone()
                    
                    if not previous:
                        # New item
                        change = ChangeLogEntry(
                            seller_name=item.seller_name,
                            item_name=item.item_name,
                            change_type='NEW_ITEM',
                            old_value=None,
                            new_value=f"Price: {item.price}, Quantity: {item.quantity}"
                        )
                        changes.append(change)
                    else:
                        prev_price, prev_quantity = previous
                        
                        # Check price changes
                        if item.price != prev_price and item.price is not None and prev_price is not None:
                            change_type = 'PRICE_INCREASE' if item.price > prev_price else 'PRICE_DECREASE'
                            change = ChangeLogEntry(
                                seller_name=item.seller_name,
                                item_name=item.item_name,
                                change_type=change_type,
                                old_value=str(prev_price),
                                new_value=str(item.price)
                            )
                            changes.append(change)
                        
                        # Check quantity changes
                        if item.quantity != prev_quantity and item.quantity is not None and prev_quantity is not None:
                            change_type = 'QUANTITY_INCREASE' if item.quantity > prev_quantity else 'QUANTITY_DECREASE'
                            change = ChangeLogEntry(
                                seller_name=item.seller_name,
                                item_name=item.item_name,
                                change_type=change_type,
                                old_value=str(prev_quantity),
                                new_value=str(item.quantity)
                            )
                            changes.append(change)
                
                # Log all detected changes
                for change in changes:
                    cursor.execute('''
                        INSERT INTO changes_log 
                        (seller_name, item_name, change_type, old_value, new_value)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (
                        change.seller_name,
                        change.item_name,
                        change.change_type,
                        change.old_value,
                        change.new_value
                    ))
                
                if changes:
                    self.logger.info(f"Detected and logged {len(changes)} changes")
                
                return changes
                
        except Exception as e:
            self.logger.error(f"Failed to detect changes: {e}")
            return []
    
    def create_ocr_session(self, hotkey: str) -> int:
        """
        Create new OCR session and return session ID.
        
        Args:
            hotkey: Hotkey that triggered the session
            
        Returns:
            Session ID
        """
        try:
            with self._transaction() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO ocr_sessions (hotkey, status)
                    VALUES (?, 'pending')
                ''', (hotkey,))
                
                session_id = cursor.lastrowid
                self.logger.info(f"Created OCR session {session_id} for hotkey {hotkey}")
                return session_id
                
        except Exception as e:
            self.logger.error(f"Failed to create OCR session: {e}")
            raise
    
    def update_ocr_session(self, session_id: int, processing_time: float, error: Optional[str] = None) -> None:
        """
        Update OCR session with processing time and optional error.
        
        Args:
            session_id: Session ID
            processing_time: Processing time in seconds
            error: Optional error message if processing failed
        """
        try:
            with self._transaction() as conn:
                cursor = conn.cursor()
                
                if error:
                    cursor.execute('''
                        UPDATE ocr_sessions 
                        SET processing_time = ?, error_message = ?, status = 'failed'
                        WHERE id = ?
                    ''', (processing_time, error, session_id))
                else:
                    cursor.execute('''
                        UPDATE ocr_sessions 
                        SET processing_time = ?, status = 'completed'
                        WHERE id = ?
                    ''', (processing_time, session_id))
                
        except Exception as e:
            self.logger.error(f"Failed to update OCR session: {e}")
    
    def cleanup_expired_records(self, days: int = 30) -> int:
        """
        Clean up records older than specified days.
        
        Args:
            days: Number of days to keep records
            
        Returns:
            Number of records deleted
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        deleted_count = 0
        
        try:
            with self._transaction() as conn:
                cursor = conn.cursor()
                
                # Clean up old items
                cursor.execute('''
                    DELETE FROM items 
                    WHERE created_at < ?
                ''', (cutoff_date,))
                deleted_count += cursor.rowcount
                
                # Clean up old changes log
                cursor.execute('''
                    DELETE FROM changes_log 
                    WHERE detected_at < ?
                ''', (cutoff_date,))
                deleted_count += cursor.rowcount
                
                # Clean up old OCR sessions
                cursor.execute('''
                    DELETE FROM ocr_sessions 
                    WHERE created_at < ?
                ''', (cutoff_date,))
                deleted_count += cursor.rowcount
                
                self.logger.info(f"Cleaned up {deleted_count} expired records")
                return deleted_count
                
        except Exception as e:
            self.logger.error(f"Failed to cleanup expired records: {e}")
            return 0
    
    def get_monitoring_status_summary(self) -> Dict[str, int]:
        """
        Get summary of monitoring queue status.
        
        Returns:
            Dictionary with status counts
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT status, COUNT(*) as count 
                FROM monitoring_queue 
                GROUP BY status
            ''')
            
            summary = {row[0]: row[1] for row in cursor.fetchall()}
            return summary
            
        except Exception as e:
            self.logger.error(f"Failed to get status summary: {e}")
            return {}
    
    def vacuum_database(self) -> None:
        """Optimize database by running VACUUM command."""
        try:
            conn = self._get_connection()
            conn.execute("VACUUM")
            self.logger.info("Database vacuum completed successfully")
            
        except Exception as e:
            self.logger.error(f"Database vacuum failed: {e}")
    
    def close_connection(self) -> None:
        """Close database connection for current thread."""
        if hasattr(self._local, 'connection'):
            self._local.connection.close()
            del self._local.connection
    
    def check_database_health(self) -> Dict[str, Any]:
        """Check database health and performance metrics."""
        health_info = {
            'status': 'healthy',
            'issues': [],
            'metrics': {}
        }
        
        try:
            with self._transaction(timeout_seconds=5) as conn:
                cursor = conn.cursor()
                
                # Check database integrity
                cursor.execute("PRAGMA integrity_check(5)")
                integrity_result = cursor.fetchall()
                if integrity_result != [('ok',)]:
                    health_info['status'] = 'warning'
                    health_info['issues'].append(f"Integrity issues: {integrity_result}")
                
                # Check WAL mode
                cursor.execute("PRAGMA journal_mode")
                journal_mode = cursor.fetchone()[0]
                health_info['metrics']['journal_mode'] = journal_mode
                
                # Check cache hit ratio
                cursor.execute("PRAGMA cache_size")
                cache_size = cursor.fetchone()[0]
                health_info['metrics']['cache_size'] = cache_size
                
                # Check database size
                cursor.execute("PRAGMA page_count")
                page_count = cursor.fetchone()[0]
                cursor.execute("PRAGMA page_size")
                page_size = cursor.fetchone()[0]
                db_size_mb = (page_count * page_size) / (1024 * 1024)
                health_info['metrics']['database_size_mb'] = round(db_size_mb, 2)
                
                # Check for large tables
                cursor.execute("""
                    SELECT name, COUNT(*) as row_count 
                    FROM sqlite_master m, pragma_table_info(m.name)
                    WHERE m.type='table'
                    GROUP BY m.name
                    HAVING row_count > 0
                """)
                table_stats = dict(cursor.fetchall())
                health_info['metrics']['table_row_counts'] = table_stats
                
        except Exception as e:
            health_info['status'] = 'error'
            health_info['issues'].append(f"Health check failed: {e}")
        
        return health_info
    
    def analyze_long_running_queries(self) -> List[Dict[str, Any]]:
        """Analyze and report long-running queries (if any)."""
        # SQLite doesn't have built-in query monitoring like PostgreSQL
        # But we can provide transaction timing information
        return [
            {
                'info': 'SQLite transaction monitoring',
                'recommendation': 'Monitor application logs for transaction timeout warnings'
            }
        ]
    
    def optimize_database(self) -> Dict[str, Any]:
        """Run database optimization operations."""
        results = {
            'operations_performed': [],
            'status': 'success'
        }
        
        try:
            with self._transaction(timeout_seconds=60) as conn:
                cursor = conn.cursor()
                
                # Analyze database for better query plans
                cursor.execute("ANALYZE")
                results['operations_performed'].append('ANALYZE')
                
                # Update table statistics
                cursor.execute("PRAGMA optimize")
                results['operations_performed'].append('PRAGMA optimize')
                
            self.logger.info(f"Database optimization completed: {results['operations_performed']}")
            
        except Exception as e:
            results['status'] = 'error'
            results['error'] = str(e)
            self.logger.error(f"Database optimization failed: {e}")
        
        return results