"""
Enterprise-Grade Database Manager for Game Monitor System

Advanced database management with comprehensive logging, monitoring,
backup/recovery, circuit breakers, and performance optimization.
"""

import sqlite3
import threading
import time
import json
import shutil
import hashlib
from typing import Dict, List, Optional, Tuple, Any, Callable, NamedTuple
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import queue
import tempfile
import os

from .advanced_logger import get_logger
from .error_tracker import ErrorTracker
from .performance_logger import PerformanceMonitor


class ConnectionState(NamedTuple):
    """Connection state information"""
    connection_id: str
    created_at: float
    last_used: float
    query_count: int
    error_count: int
    is_healthy: bool


@dataclass
class QueryMetrics:
    """Query execution metrics"""
    query_hash: str
    query_type: str  # SELECT, INSERT, UPDATE, DELETE
    execution_time_ms: float
    rows_affected: int
    success: bool
    error_message: Optional[str] = None


class DatabaseHealthStatus:
    """Database health monitoring"""
    
    def __init__(self):
        self.is_healthy = True
        self.last_check = datetime.now()
        self.connection_pool_status = "healthy"
        self.query_performance = "normal"
        self.disk_space_status = "sufficient"
        self.integrity_status = "verified"
        self.errors = []
        self.warnings = []


class CircuitBreakerState:
    """Circuit breaker for database operations"""
    
    def __init__(self, failure_threshold: int = 5, timeout_seconds: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open
    
    def record_success(self):
        """Record successful operation"""
        self.failure_count = 0
        self.state = "closed"
    
    def record_failure(self):
        """Record failed operation"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
    
    def can_execute(self) -> bool:
        """Check if operations can be executed"""
        if self.state == "closed":
            return True
        
        if self.state == "open":
            # Check if timeout has passed
            if (time.time() - self.last_failure_time) > self.timeout_seconds:
                self.state = "half-open"
                return True
            return False
        
        # half-open state
        return True


class EnhancedDatabaseManager:
    """Enterprise-grade database manager with comprehensive monitoring and recovery"""
    
    def __init__(self, db_path: str = "data/game_monitor.db", 
                 pool_size: int = 10,
                 enable_wal: bool = True,
                 backup_interval_hours: int = 6):
        
        # Core configuration
        self.db_path = Path(db_path)
        self.pool_size = pool_size
        self.enable_wal = enable_wal
        self.backup_interval_hours = backup_interval_hours
        
        # Logging and monitoring
        self.logger = get_logger('database_manager')
        self.error_tracker = ErrorTracker()
        self.performance_monitor = PerformanceMonitor()
        
        # Connection management
        self._connection_pool = queue.Queue(maxsize=pool_size)
        self._connection_states = {}  # connection_id -> ConnectionState
        self._pool_lock = threading.RLock()
        
        # Health monitoring
        self._health_status = DatabaseHealthStatus()
        self._health_check_interval = 300  # 5 minutes
        self._last_health_check = 0
        
        # Circuit breaker
        self._circuit_breaker = CircuitBreakerState()
        
        # Query monitoring
        self._query_metrics = deque(maxlen=10000)  # Keep last 10K queries
        self._slow_query_threshold_ms = 100.0
        self._query_cache = {}  # Simple query result cache
        self._cache_max_size = 1000
        
        # Background tasks
        self._monitoring_active = True
        self._backup_active = True
        
        # Statistics
        self._stats = {
            'total_queries': 0,
            'successful_queries': 0,
            'failed_queries': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'connections_created': 0,
            'connections_recycled': 0,
            'health_checks': 0,
            'backups_created': 0
        }
        
        # Initialize database
        self._initialize_database()
        
        # Start background monitoring
        self._start_background_tasks()
    
    def _initialize_database(self):
        """Initialize database with comprehensive setup"""
        with self.logger.operation_context('database_manager', 'initialize_database'):
            try:
                # Ensure database directory exists
                self.db_path.parent.mkdir(parents=True, exist_ok=True)
                
                self.logger.info(f"Initializing database at {self.db_path}")
                
                # Initialize connection pool
                self._init_connection_pool()
                
                # Create schema
                self._create_tables()
                
                # Initial health check
                self._perform_health_check()
                
                self.logger.info(
                    f"Database initialized successfully with {self.pool_size} connections",
                    extra_data={
                        'db_path': str(self.db_path),
                        'pool_size': self.pool_size,
                        'wal_enabled': self.enable_wal
                    }
                )
                
            except Exception as e:
                self.error_tracker.record_error(
                    'database_manager', 'initialize_database', e
                )
                raise
    
    def _init_connection_pool(self):
        """Initialize connection pool with enterprise settings"""
        for i in range(self.pool_size):
            try:
                conn_id = f"conn_{i}_{int(time.time())}"
                
                conn = sqlite3.connect(
                    str(self.db_path),
                    check_same_thread=False,
                    timeout=30.0,  # Longer timeout for enterprise use
                    isolation_level=None  # Autocommit mode
                )
                
                # Enterprise SQLite optimizations
                if self.enable_wal:
                    conn.execute("PRAGMA journal_mode=WAL")
                    conn.execute("PRAGMA wal_autocheckpoint=1000")
                
                conn.execute("PRAGMA synchronous=NORMAL")
                conn.execute("PRAGMA cache_size=20000")  # 20MB cache
                conn.execute("PRAGMA temp_store=MEMORY")
                conn.execute("PRAGMA mmap_size=536870912")  # 512MB memory map
                conn.execute("PRAGMA page_size=32768")  # 32KB pages
                conn.execute("PRAGMA optimize")
                
                # Enable foreign keys
                conn.execute("PRAGMA foreign_keys=ON")
                
                # Set row factory for named access
                conn.row_factory = sqlite3.Row
                
                # Add connection ID for tracking
                conn.connection_id = conn_id
                
                # Store connection state
                self._connection_states[conn_id] = ConnectionState(
                    connection_id=conn_id,
                    created_at=time.time(),
                    last_used=time.time(),
                    query_count=0,
                    error_count=0,
                    is_healthy=True
                )
                
                self._connection_pool.put(conn)
                self._stats['connections_created'] += 1
                
                self.logger.debug(f"Created database connection {conn_id}")
                
            except Exception as e:
                self.logger.error(f"Failed to create connection {i}: {e}")
                self.error_tracker.record_error(
                    'database_manager', 'create_connection', e
                )
                raise
    
    @contextmanager
    def get_connection(self):
        """Get connection from pool with comprehensive monitoring"""
        if not self._circuit_breaker.can_execute():
            raise RuntimeError("Database circuit breaker is OPEN - too many failures")
        
        trace_id = self.performance_monitor.start_operation(
            'database_manager', 'get_connection'
        )
        
        conn = None
        try:
            # Get connection with timeout
            try:
                conn = self._connection_pool.get(timeout=5.0)
            except queue.Empty:
                raise RuntimeError("Connection pool exhausted - no connections available")
            
            conn_id = getattr(conn, 'connection_id', 'unknown')
            
            with self._pool_lock:
                if conn_id in self._connection_states:
                    state = self._connection_states[conn_id]
                    # Update connection state
                    self._connection_states[conn_id] = ConnectionState(
                        connection_id=conn_id,
                        created_at=state.created_at,
                        last_used=time.time(),
                        query_count=state.query_count,
                        error_count=state.error_count,
                        is_healthy=state.is_healthy
                    )
            
            self.logger.trace(f"Retrieved connection {conn_id}")
            
            yield conn
            
            self.performance_monitor.finish_operation(trace_id, success=True)
            
        except Exception as e:
            self.error_tracker.record_error(
                'database_manager', 'get_connection', e, trace_id=trace_id
            )
            if trace_id:
                self.performance_monitor.finish_operation(trace_id, success=False, error_count=1)
            raise
            
        finally:
            if conn:
                self._connection_pool.put(conn)
                if hasattr(conn, 'connection_id'):
                    self.logger.trace(f"Returned connection {conn.connection_id}")
    
    def _create_tables(self):
        """Create database schema with comprehensive structure"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            self.logger.info("Creating database tables")
            
            # Trades table - enhanced with audit fields
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trader_nickname TEXT NOT NULL,
                    item_name TEXT NOT NULL,
                    item_id TEXT,
                    previous_quantity INTEGER NOT NULL DEFAULT 0,
                    current_quantity INTEGER NOT NULL,
                    quantity_change INTEGER NOT NULL,
                    price_per_unit REAL NOT NULL,
                    total_value REAL NOT NULL,
                    trade_type TEXT NOT NULL CHECK(trade_type IN ('purchase', 'restock', 'sold_out')),
                    timestamp REAL NOT NULL DEFAULT (julianday('now')),
                    screenshot_path TEXT,
                    confidence_score REAL DEFAULT 0.0,
                    processing_time_ms REAL DEFAULT 0.0,
                    created_by TEXT DEFAULT 'system',
                    created_at REAL NOT NULL DEFAULT (julianday('now')),
                    updated_at REAL NOT NULL DEFAULT (julianday('now'))
                )
            """)
            
            # Current inventory table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS current_inventory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trader_nickname TEXT NOT NULL,
                    item_name TEXT NOT NULL,
                    item_id TEXT,
                    quantity INTEGER NOT NULL,
                    price_per_unit REAL NOT NULL,
                    last_seen_timestamp REAL NOT NULL DEFAULT (julianday('now')),
                    confidence_score REAL DEFAULT 0.0,
                    status TEXT DEFAULT 'active',
                    created_at REAL NOT NULL DEFAULT (julianday('now')),
                    updated_at REAL NOT NULL DEFAULT (julianday('now')),
                    UNIQUE(trader_nickname, item_name, item_id)
                )
            """)
            
            # Search queue table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS search_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_name TEXT NOT NULL UNIQUE,
                    priority INTEGER NOT NULL DEFAULT 1,
                    status TEXT NOT NULL DEFAULT 'pending',
                    last_processed REAL,
                    retry_count INTEGER DEFAULT 0,
                    created_at REAL NOT NULL DEFAULT (julianday('now')),
                    updated_at REAL NOT NULL DEFAULT (julianday('now'))
                )
            """)
            
            # OCR cache table - enhanced
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ocr_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    image_hash TEXT NOT NULL UNIQUE,
                    ocr_result TEXT NOT NULL,
                    confidence_score REAL NOT NULL,
                    region_type TEXT NOT NULL,
                    processing_time_ms REAL DEFAULT 0.0,
                    hit_count INTEGER DEFAULT 1,
                    created_at REAL NOT NULL DEFAULT (julianday('now')),
                    last_accessed REAL NOT NULL DEFAULT (julianday('now'))
                )
            """)
            
            # Validation log table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS validation_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    operation_type TEXT NOT NULL,
                    data_hash TEXT NOT NULL,
                    validation_result TEXT NOT NULL,
                    confidence_score REAL NOT NULL,
                    validation_rules TEXT,
                    errors TEXT,
                    warnings TEXT,
                    created_at REAL NOT NULL DEFAULT (julianday('now'))
                )
            """)
            
            # Performance metrics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    operation_type TEXT NOT NULL,
                    component TEXT NOT NULL,
                    duration_ms REAL NOT NULL,
                    memory_usage_mb REAL,
                    cpu_usage_percent REAL,
                    success BOOLEAN NOT NULL,
                    error_message TEXT,
                    created_at REAL NOT NULL DEFAULT (julianday('now'))
                )
            """)
            
            # System health log
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_health_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    component TEXT NOT NULL,
                    status TEXT NOT NULL,
                    metrics TEXT,
                    issues TEXT,
                    created_at REAL NOT NULL DEFAULT (julianday('now'))
                )
            """)
            
            # Create indexes for performance
            self._create_indexes(cursor)
            
            # Create triggers for audit trails
            self._create_triggers(cursor)
            
            conn.commit()
            self.logger.info("Database tables created successfully")
    
    def _create_indexes(self, cursor):
        """Create comprehensive indexes for optimal performance"""
        indexes = [
            # Trades table indexes
            "CREATE INDEX IF NOT EXISTS idx_trades_trader ON trades(trader_nickname)",
            "CREATE INDEX IF NOT EXISTS idx_trades_item ON trades(item_name)",
            "CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_trades_type ON trades(trade_type)",
            "CREATE INDEX IF NOT EXISTS idx_trades_composite ON trades(trader_nickname, item_name, timestamp)",
            
            # Current inventory indexes
            "CREATE INDEX IF NOT EXISTS idx_inventory_trader ON current_inventory(trader_nickname)",
            "CREATE INDEX IF NOT EXISTS idx_inventory_item ON current_inventory(item_name)",
            "CREATE INDEX IF NOT EXISTS idx_inventory_updated ON current_inventory(updated_at)",
            "CREATE INDEX IF NOT EXISTS idx_inventory_status ON current_inventory(status)",
            
            # Search queue indexes
            "CREATE INDEX IF NOT EXISTS idx_search_queue_status ON search_queue(status)",
            "CREATE INDEX IF NOT EXISTS idx_search_queue_priority ON search_queue(priority)",
            
            # OCR cache indexes
            "CREATE INDEX IF NOT EXISTS idx_ocr_cache_hash ON ocr_cache(image_hash)",
            "CREATE INDEX IF NOT EXISTS idx_ocr_cache_region ON ocr_cache(region_type)",
            "CREATE INDEX IF NOT EXISTS idx_ocr_cache_accessed ON ocr_cache(last_accessed)",
            
            # Performance metrics indexes
            "CREATE INDEX IF NOT EXISTS idx_performance_component ON performance_metrics(component)",
            "CREATE INDEX IF NOT EXISTS idx_performance_operation ON performance_metrics(operation_type)",
            "CREATE INDEX IF NOT EXISTS idx_performance_created ON performance_metrics(created_at)"
        ]
        
        for index_sql in indexes:
            try:
                cursor.execute(index_sql)
                self.logger.debug(f"Created index: {index_sql}")
            except sqlite3.Error as e:
                self.logger.warning(f"Failed to create index: {e}")
    
    def _create_triggers(self, cursor):
        """Create triggers for automatic audit trail updates"""
        triggers = [
            # Update timestamp triggers
            """
            CREATE TRIGGER IF NOT EXISTS update_trades_timestamp
            AFTER UPDATE ON trades
            BEGIN
                UPDATE trades SET updated_at = julianday('now') WHERE id = NEW.id;
            END
            """,
            
            """
            CREATE TRIGGER IF NOT EXISTS update_inventory_timestamp
            AFTER UPDATE ON current_inventory
            BEGIN
                UPDATE current_inventory SET updated_at = julianday('now') WHERE id = NEW.id;
            END
            """,
            
            """
            CREATE TRIGGER IF NOT EXISTS update_search_queue_timestamp
            AFTER UPDATE ON search_queue
            BEGIN
                UPDATE search_queue SET updated_at = julianday('now') WHERE id = NEW.id;
            END
            """
        ]
        
        for trigger_sql in triggers:
            try:
                cursor.execute(trigger_sql)
                self.logger.debug("Created database trigger")
            except sqlite3.Error as e:
                self.logger.warning(f"Failed to create trigger: {e}")
    
    def execute_query(self, query: str, params: Tuple = (), 
                     fetch_all: bool = False, 
                     cache_key: Optional[str] = None) -> Any:
        """Execute query with comprehensive monitoring and caching"""
        
        # Check cache first
        if cache_key and fetch_all:
            cached_result = self._query_cache.get(cache_key)
            if cached_result:
                self._stats['cache_hits'] += 1
                self.logger.trace(f"Cache hit for query: {cache_key}")
                return cached_result
            self._stats['cache_misses'] += 1
        
        trace_id = self.performance_monitor.start_operation(
            'database_manager', 'execute_query'
        )
        
        start_time = time.time()
        query_hash = hashlib.md5(query.encode()).hexdigest()[:8]
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Log query execution
                self.logger.trace(
                    f"Executing query: {query[:100]}...",
                    extra_data={
                        'query_hash': query_hash,
                        'params': str(params)[:200] if params else None,
                        'cache_key': cache_key
                    }
                )
                
                # Execute query
                cursor.execute(query, params)
                
                # Get results
                if fetch_all:
                    result = cursor.fetchall()
                    # Convert to list of dicts for JSON serialization
                    if result:
                        result = [dict(row) for row in result]
                else:
                    result = cursor.fetchone()
                    if result:
                        result = dict(result)
                
                execution_time = (time.time() - start_time) * 1000
                
                # Update statistics
                self._stats['total_queries'] += 1
                self._stats['successful_queries'] += 1
                
                # Record query metrics
                metrics = QueryMetrics(
                    query_hash=query_hash,
                    query_type=query.strip().split()[0].upper(),
                    execution_time_ms=execution_time,
                    rows_affected=cursor.rowcount,
                    success=True
                )
                self._query_metrics.append(metrics)
                
                # Check for slow queries
                if execution_time > self._slow_query_threshold_ms:
                    self.logger.warning(
                        f"Slow query detected: {execution_time:.2f}ms",
                        extra_data={
                            'query_hash': query_hash,
                            'execution_time_ms': execution_time,
                            'query': query[:200]
                        }
                    )
                
                # Cache result if requested
                if cache_key and fetch_all and result:
                    self._cache_query_result(cache_key, result)
                
                # Record successful operation
                self._circuit_breaker.record_success()
                
                self.performance_monitor.finish_operation(
                    trace_id, 
                    success=True,
                    operation_data={
                        'query_type': metrics.query_type,
                        'rows_affected': cursor.rowcount,
                        'execution_time_ms': execution_time
                    }
                )
                
                conn.commit()
                return result
                
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            
            # Update statistics
            self._stats['failed_queries'] += 1
            
            # Record error metrics
            metrics = QueryMetrics(
                query_hash=query_hash,
                query_type=query.strip().split()[0].upper(),
                execution_time_ms=execution_time,
                rows_affected=0,
                success=False,
                error_message=str(e)
            )
            self._query_metrics.append(metrics)
            
            # Record circuit breaker failure
            self._circuit_breaker.record_failure()
            
            # Log error with full context
            self.logger.error(
                f"Query execution failed: {str(e)}",
                error=e,
                extra_data={
                    'query_hash': query_hash,
                    'query': query[:200],
                    'params': str(params)[:200] if params else None,
                    'execution_time_ms': execution_time
                }
            )
            
            # Record error
            self.error_tracker.record_error(
                'database_manager', 'execute_query', e, 
                context={
                    'query_hash': query_hash,
                    'query_type': metrics.query_type,
                    'execution_time_ms': execution_time
                },
                trace_id=trace_id
            )
            
            self.performance_monitor.finish_operation(
                trace_id, success=False, error_count=1
            )
            
            raise
    
    def _cache_query_result(self, cache_key: str, result: Any):
        """Cache query result with size management"""
        if len(self._query_cache) >= self._cache_max_size:
            # Remove oldest entries
            oldest_keys = list(self._query_cache.keys())[:100]
            for key in oldest_keys:
                del self._query_cache[key]
        
        self._query_cache[cache_key] = result
    
    # Enhanced CRUD operations with comprehensive logging
    
    def record_trade(self, trader_nickname: str, item_name: str, item_id: str,
                    previous_quantity: int, current_quantity: int,
                    price_per_unit: float, trade_type: str,
                    screenshot_path: Optional[str] = None,
                    confidence_score: float = 0.0,
                    processing_time_ms: float = 0.0) -> int:
        """Record a trade with comprehensive audit trail"""
        
        trace_id = self.performance_monitor.start_operation(
            'database_manager', 'record_trade'
        )
        
        try:
            quantity_change = current_quantity - previous_quantity
            total_value = abs(quantity_change) * price_per_unit
            
            query = """
                INSERT INTO trades 
                (trader_nickname, item_name, item_id, previous_quantity, 
                 current_quantity, quantity_change, price_per_unit, total_value, 
                 trade_type, screenshot_path, confidence_score, processing_time_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            params = (
                trader_nickname, item_name, item_id, previous_quantity,
                current_quantity, quantity_change, price_per_unit, total_value,
                trade_type, screenshot_path, confidence_score, processing_time_ms
            )
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                trade_id = cursor.lastrowid
                conn.commit()
            
            self.logger.info(
                f"Trade recorded: {trader_nickname} - {item_name} ({trade_type})",
                extra_data={
                    'trade_id': trade_id,
                    'trader_nickname': trader_nickname,
                    'item_name': item_name,
                    'quantity_change': quantity_change,
                    'price_per_unit': price_per_unit,
                    'confidence_score': confidence_score
                }
            )
            
            self.performance_monitor.finish_operation(
                trace_id, success=True,
                operation_data={'trade_id': trade_id}
            )
            
            return trade_id
            
        except Exception as e:
            self.error_tracker.record_error(
                'database_manager', 'record_trade', e,
                context={
                    'trader_nickname': trader_nickname,
                    'item_name': item_name,
                    'trade_type': trade_type
                },
                trace_id=trace_id
            )
            self.performance_monitor.finish_operation(trace_id, success=False, error_count=1)
            raise
    
    def get_database_statistics(self) -> Dict[str, Any]:
        """Get comprehensive database statistics"""
        try:
            stats = {}
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Table row counts
                tables = ['trades', 'current_inventory', 'search_queue', 'ocr_cache', 'validation_log']
                for table in tables:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    stats[f"{table}_count"] = cursor.fetchone()[0]
                
                # Database size
                cursor.execute("PRAGMA page_count")
                page_count = cursor.fetchone()[0]
                cursor.execute("PRAGMA page_size")
                page_size = cursor.fetchone()[0]
                stats['database_size_mb'] = (page_count * page_size) / (1024 * 1024)
                
                # Recent activity (last 24 hours)
                cursor.execute("""
                    SELECT COUNT(*) FROM trades 
                    WHERE timestamp > julianday('now', '-1 day')
                """)
                stats['trades_last_24h'] = cursor.fetchone()[0]
            
            # Add internal statistics
            stats.update(self._stats)
            
            # Connection pool status
            stats['connection_pool'] = {
                'size': self.pool_size,
                'available': self._connection_pool.qsize(),
                'active': self.pool_size - self._connection_pool.qsize()
            }
            
            # Circuit breaker status
            stats['circuit_breaker'] = {
                'state': self._circuit_breaker.state,
                'failure_count': self._circuit_breaker.failure_count
            }
            
            # Health status
            stats['health_status'] = asdict(self._health_status)
            
            return stats
            
        except Exception as e:
            self.error_tracker.record_error(
                'database_manager', 'get_database_statistics', e
            )
            return {'error': str(e)}
    
    def _perform_health_check(self) -> DatabaseHealthStatus:
        """Perform comprehensive database health check"""
        
        health = DatabaseHealthStatus()
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Test basic connectivity
                cursor.execute("SELECT 1")
                
                # Check database integrity
                cursor.execute("PRAGMA integrity_check(10)")
                integrity_results = cursor.fetchall()
                if any(row[0] != 'ok' for row in integrity_results):
                    health.integrity_status = "issues_found"
                    health.errors.append("Database integrity issues detected")
                
                # Check WAL mode
                cursor.execute("PRAGMA journal_mode")
                journal_mode = cursor.fetchone()[0]
                if journal_mode != 'wal' and self.enable_wal:
                    health.warnings.append(f"Journal mode is {journal_mode}, expected WAL")
                
                # Check foreign key constraints
                cursor.execute("PRAGMA foreign_key_check")
                fk_violations = cursor.fetchall()
                if fk_violations:
                    health.errors.append(f"Foreign key violations: {len(fk_violations)}")
            
            # Check connection pool health
            active_connections = self.pool_size - self._connection_pool.qsize()
            if active_connections > self.pool_size * 0.9:
                health.warnings.append("Connection pool utilization high")
            
            # Check disk space
            disk_usage = shutil.disk_usage(self.db_path.parent)
            free_space_gb = disk_usage.free / (1024**3)
            if free_space_gb < 1.0:  # Less than 1GB free
                health.disk_space_status = "low"
                health.errors.append(f"Low disk space: {free_space_gb:.2f}GB free")
            
            # Check query performance
            recent_queries = list(self._query_metrics)[-100:]  # Last 100 queries
            if recent_queries:
                avg_execution_time = sum(q.execution_time_ms for q in recent_queries) / len(recent_queries)
                if avg_execution_time > self._slow_query_threshold_ms * 2:
                    health.query_performance = "degraded"
                    health.warnings.append(f"Average query time high: {avg_execution_time:.2f}ms")
            
            health.is_healthy = len(health.errors) == 0
            health.last_check = datetime.now()
            
            self._stats['health_checks'] += 1
            
        except Exception as e:
            health.is_healthy = False
            health.errors.append(f"Health check failed: {str(e)}")
            self.error_tracker.record_error(
                'database_manager', 'health_check', e
            )
        
        self._health_status = health
        return health
    
    def create_backup(self, backup_path: Optional[str] = None) -> str:
        """Create database backup with verification"""
        
        trace_id = self.performance_monitor.start_operation(
            'database_manager', 'create_backup'
        )
        
        try:
            if not backup_path:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_path = f"{self.db_path.parent}/backup_{self.db_path.name}_{timestamp}"
            
            backup_path = Path(backup_path)
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            
            self.logger.info(f"Creating database backup to {backup_path}")
            
            # Create backup using SQLite backup API
            with self.get_connection() as source_conn:
                # Create backup connection
                backup_conn = sqlite3.connect(str(backup_path))
                
                try:
                    # Perform backup
                    source_conn.backup(backup_conn)
                    
                    # Verify backup integrity
                    backup_cursor = backup_conn.cursor()
                    backup_cursor.execute("PRAGMA integrity_check")
                    integrity_result = backup_cursor.fetchone()[0]
                    
                    if integrity_result != 'ok':
                        raise RuntimeError(f"Backup integrity check failed: {integrity_result}")
                    
                    backup_size = backup_path.stat().st_size
                    
                    self.logger.info(
                        f"Backup created successfully",
                        extra_data={
                            'backup_path': str(backup_path),
                            'backup_size_mb': backup_size / (1024*1024),
                            'backup_integrity': 'verified'
                        }
                    )
                    
                    self._stats['backups_created'] += 1
                    
                    self.performance_monitor.finish_operation(
                        trace_id, success=True,
                        operation_data={'backup_size_bytes': backup_size}
                    )
                    
                    return str(backup_path)
                    
                finally:
                    backup_conn.close()
        
        except Exception as e:
            self.error_tracker.record_error(
                'database_manager', 'create_backup', e,
                context={'backup_path': str(backup_path) if backup_path else None},
                trace_id=trace_id
            )
            self.performance_monitor.finish_operation(trace_id, success=False, error_count=1)
            raise
    
    def _start_background_tasks(self):
        """Start background monitoring and maintenance tasks"""
        
        def monitoring_loop():
            while self._monitoring_active:
                try:
                    # Perform health check
                    if time.time() - self._last_health_check > self._health_check_interval:
                        self._perform_health_check()
                        self._last_health_check = time.time()
                    
                    # Clean up old cache entries
                    self._cleanup_cache()
                    
                    # Log periodic statistics
                    stats = self.get_database_statistics()
                    self.logger.debug("Database statistics", extra_data=stats)
                    
                    time.sleep(60)  # Check every minute
                    
                except Exception as e:
                    self.logger.error(f"Error in monitoring loop: {e}")
                    time.sleep(60)
        
        def backup_loop():
            while self._backup_active:
                try:
                    time.sleep(self.backup_interval_hours * 3600)  # Convert hours to seconds
                    
                    if self._health_status.is_healthy:
                        self.create_backup()
                    else:
                        self.logger.warning("Skipping backup due to health issues")
                        
                except Exception as e:
                    self.logger.error(f"Error in backup loop: {e}")
        
        # Start monitoring thread
        self._monitoring_thread = threading.Thread(target=monitoring_loop, daemon=True)
        self._monitoring_thread.start()
        
        # Start backup thread
        self._backup_thread = threading.Thread(target=backup_loop, daemon=True)
        self._backup_thread.start()
        
        self.logger.info("Background monitoring and backup tasks started")
    
    def _cleanup_cache(self):
        """Clean up old cache entries"""
        try:
            current_time = time.time()
            cache_timeout = 3600  # 1 hour
            
            # Clean query cache
            expired_keys = [
                key for key, value in self._query_cache.items()
                if hasattr(value, 'cached_at') and 
                (current_time - value.cached_at) > cache_timeout
            ]
            
            for key in expired_keys:
                del self._query_cache[key]
            
            # Clean OCR cache in database (older than 7 days)
            query = """
                DELETE FROM ocr_cache 
                WHERE last_accessed < julianday('now', '-7 days')
            """
            self.execute_query(query)
            
        except Exception as e:
            self.logger.warning(f"Cache cleanup failed: {e}")
    
    def shutdown(self):
        """Graceful shutdown with cleanup"""
        
        self.logger.info("Shutting down database manager")
        
        # Stop background tasks
        self._monitoring_active = False
        self._backup_active = False
        
        # Wait for threads to finish
        for thread in [self._monitoring_thread, self._backup_thread]:
            if thread.is_alive():
                thread.join(timeout=10)
        
        # Close all connections
        while not self._connection_pool.empty():
            try:
                conn = self._connection_pool.get_nowait()
                conn.close()
            except queue.Empty:
                break
            except Exception as e:
                self.logger.warning(f"Error closing connection: {e}")
        
        # Final health check and backup if healthy
        if self._health_status.is_healthy:
            try:
                self.create_backup()
            except Exception as e:
                self.logger.error(f"Final backup failed: {e}")
        
        self.logger.info("Database manager shutdown complete")


# Global instance for singleton access
_enhanced_db_instance = None
_enhanced_db_lock = threading.Lock()


def get_enhanced_database() -> EnhancedDatabaseManager:
    """Get singleton enhanced database instance"""
    global _enhanced_db_instance
    if _enhanced_db_instance is None:
        with _enhanced_db_lock:
            if _enhanced_db_instance is None:
                _enhanced_db_instance = EnhancedDatabaseManager()
    return _enhanced_db_instance