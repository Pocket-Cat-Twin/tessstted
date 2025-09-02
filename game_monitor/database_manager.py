"""
High-Performance Database Manager for Game Monitor System

Optimized for <1 second response time with connection pooling,
batch operations, and performance tuning.
"""

import sqlite3
import threading
import logging
import time
import random
import math
import sys
from typing import Dict, List, Optional, Tuple, Any
from contextlib import contextmanager
from pathlib import Path
import queue
import weakref
import atexit
from datetime import datetime, timedelta
from dataclasses import dataclass

from .constants import Database, Performance

logger = logging.getLogger(__name__)


@dataclass
class ConnectionHealth:
    """Connection health status information"""
    is_healthy: bool
    last_validated: datetime
    validation_error: Optional[str] = None
    response_time_ms: float = 0.0
    transaction_count: int = 0
    age_seconds: float = 0.0


class ConnectionWrapper:
    """Thread-safe wrapper for database connections with health tracking"""
    
    def __init__(self, connection: sqlite3.Connection, connection_id: str):
        self.connection = connection
        self.connection_id = connection_id
        self.created_at = datetime.now()
        self.last_used = datetime.now()
        self.last_validated = datetime.now()
        self.transaction_count = 0
        self.is_healthy = True
        self.validation_error = None
        self._lock = threading.Lock()  # Per-connection lock for metadata updates
        
    def update_usage(self):
        """Update last used timestamp in thread-safe manner"""
        with self._lock:
            self.last_used = datetime.now()
            self.transaction_count += 1
    
    def get_age_seconds(self) -> float:
        """Get connection age in seconds"""
        return (datetime.now() - self.created_at).total_seconds()
    
    def is_stale(self, max_age_seconds: float = 3600) -> bool:
        """Check if connection is stale (older than max_age_seconds)"""
        return self.get_age_seconds() > max_age_seconds
    
    def is_idle(self, max_idle_seconds: float = 300) -> bool:
        """Check if connection has been idle too long"""
        with self._lock:
            idle_time = (datetime.now() - self.last_used).total_seconds()
            return idle_time > max_idle_seconds
    
    def validate_health(self) -> ConnectionHealth:
        """Perform comprehensive connection health check"""
        with self._lock:
            health_check_start = time.time()
            validation_error = None
            is_healthy = True
            
            try:
                # Test 1: Basic connectivity
                cursor = self.connection.execute("SELECT 1")
                result = cursor.fetchone()
                if not result or result[0] != 1:
                    raise sqlite3.Error("Basic connectivity test failed")
                
                # Test 2: Transaction capability
                self.connection.execute("BEGIN")
                self.connection.execute("CREATE TEMP TABLE health_check_temp (id INTEGER)")
                self.connection.execute("INSERT INTO health_check_temp (id) VALUES (1)")
                self.connection.execute("DROP TABLE health_check_temp")
                self.connection.execute("COMMIT")
                
                # Test 3: Pragma checks
                cursor = self.connection.execute("PRAGMA integrity_check(1)")
                integrity_result = cursor.fetchone()
                if not integrity_result or integrity_result[0] != 'ok':
                    raise sqlite3.Error("Database integrity check failed")
                
                self.is_healthy = True
                self.validation_error = None
                
            except Exception as e:
                is_healthy = False
                validation_error = str(e)
                self.is_healthy = False
                self.validation_error = validation_error
                
                # Try to rollback any pending transaction
                try:
                    self.connection.rollback()
                except:
                    pass
            
            response_time_ms = (time.time() - health_check_start) * 1000
            self.last_validated = datetime.now()
            
            return ConnectionHealth(
                is_healthy=is_healthy,
                last_validated=self.last_validated,
                validation_error=validation_error,
                response_time_ms=response_time_ms,
                transaction_count=self.transaction_count,
                age_seconds=self.get_age_seconds()
            )
    
    def close(self):
        """Close the underlying connection"""
        try:
            self.connection.close()
        except:
            pass


def retry_with_exponential_backoff(max_retries=3, base_delay=0.1, max_delay=5.0, exceptions=(sqlite3.DatabaseError, sqlite3.OperationalError)):
    """
    Decorator for retrying database operations with exponential backoff
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds before first retry
        max_delay: Maximum delay between retries
        exceptions: Tuple of exception types to retry on
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                    
                except exceptions as e:
                    last_exception = e
                    
                    if attempt < max_retries:
                        # Calculate exponential backoff delay with jitter
                        delay = min(base_delay * (2 ** attempt), max_delay)
                        jitter = delay * 0.1 * random.random()  # Add up to 10% jitter
                        total_delay = delay + jitter
                        
                        logger.warning(
                            f"Database operation failed (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                            f"Retrying in {total_delay:.2f}s"
                        )
                        
                        time.sleep(total_delay)
                    else:
                        logger.error(
                            f"Database operation failed after {max_retries + 1} attempts: {e}"
                        )
                        raise last_exception
                        
                except Exception as e:
                    # Don't retry on non-database exceptions
                    logger.error(f"Non-retryable error in database operation: {e}")
                    raise
            
            # Should never reach here, but just in case
            raise last_exception
            
        return wrapper
    return decorator

# Global registry for tracking database instances
_db_instances = weakref.WeakSet()

class DatabaseManager:
    """High-performance database manager with connection pooling and optimizations"""
    
    def __init__(self, db_path: str = "data/game_monitor.db", pool_size: int = 5):
        self.db_path = db_path
        self.pool_size = pool_size
        self._connection_pool = queue.Queue(maxsize=pool_size)
        self._pool_lock = threading.RLock()  # Reentrant lock for pool operations
        self._stats_lock = threading.Lock()  # Separate lock for statistics
        
        # Enhanced connection tracking
        self._active_connections = 0  # Track active connections outside pool
        self._total_connections_created = 0  # Track total connections created
        self._connection_leaks_detected = 0  # Track potential leaks
        self._connections_validated = 0  # Track validation operations
        self._connections_replaced = 0  # Track connection replacements
        self._closed = False  # Track if database manager is closed
        
        # Connection health management
        self._max_connection_age = 3600  # 1 hour max age
        self._max_idle_time = 300  # 5 minutes max idle
        self._health_check_interval = 60  # Health check every minute
        self._last_health_check = time.time()
        
        # Performance monitoring
        self._pool_wait_times = []  # Track connection wait times
        self._validation_times = []  # Track validation times
        
        # Register this instance for cleanup tracking
        _db_instances.add(self)
        
        # Ensure database directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize connection pool
        self._init_connection_pool()
        
        # Create tables and indexes
        self.create_tables()
        
        logger.info(f"DatabaseManager initialized with pool size {pool_size}, enhanced thread safety and health monitoring enabled")
    
    def _init_connection_pool(self):
        """Initialize connection pool with optimized settings and health tracking"""
        with self._pool_lock:
            for i in range(self.pool_size):
                try:
                    # Create raw connection
                    conn = sqlite3.connect(
                        self.db_path, 
                        check_same_thread=False,
                        timeout=Database.CONNECTION_TIMEOUT
                    )
                    
                    # Performance optimizations
                    conn.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging
                    conn.execute("PRAGMA synchronous=NORMAL")  # Balanced performance
                    conn.execute(f"PRAGMA cache_size={Database.CACHE_SIZE_PAGES}")  # 10MB cache
                    conn.execute("PRAGMA temp_store=MEMORY")  # Use RAM for temp
                    conn.execute("PRAGMA mmap_size=268435456")  # 256MB memory map
                    
                    # Set row factory for named access
                    conn.row_factory = sqlite3.Row
                    
                    # Wrap connection with health tracking
                    connection_id = f"conn_{self._total_connections_created}_{int(time.time())}"
                    wrapped_conn = ConnectionWrapper(conn, connection_id)
                    
                    # Add to pool
                    self._connection_pool.put(wrapped_conn)
                    
                    # Track connection creation
                    with self._stats_lock:
                        self._total_connections_created += 1
                    
                    logger.debug(f"Created connection {connection_id} for pool")
                    
                except Exception as e:
                    logger.error(f"Failed to create connection {i} during pool initialization: {e}")
                    raise RuntimeError(f"Failed to initialize connection pool: {e}")
            
            logger.info(f"Connection pool initialized with {self.pool_size} connections")
    
    @contextmanager
    def get_connection(self):
        """Get connection from pool with comprehensive health checking and thread safety"""
        if self._closed:
            raise RuntimeError("DatabaseManager has been closed")
        
        wrapped_conn = None
        connection_acquired_time = time.time()
        
        try:
            # Perform periodic health checks
            self._perform_periodic_health_checks()
            
            # Get connection from pool with timeout to detect potential deadlocks
            pool_wait_start = time.time()
            
            try:
                wrapped_conn = self._connection_pool.get(timeout=Database.CONNECTION_TIMEOUT * 2)
            except queue.Empty:
                # Connection pool exhausted - potential leak
                with self._stats_lock:
                    self._connection_leaks_detected += 1
                
                logger.error(
                    f"Connection pool exhausted! Active: {self._active_connections}, "
                    f"Pool size: {self.pool_size}, Total created: {self._total_connections_created}, "
                    f"Leaks detected: {self._connection_leaks_detected}"
                )
                raise RuntimeError("Connection pool exhausted - possible connection leak")
            
            pool_wait_time = time.time() - pool_wait_start
            
            # Track pool wait time for performance monitoring
            with self._stats_lock:
                self._pool_wait_times.append(pool_wait_time * 1000)  # Store in milliseconds
                # Keep only last 100 measurements
                if len(self._pool_wait_times) > 100:
                    self._pool_wait_times.pop(0)
            
            # Validate connection health before use
            validation_start = time.time()
            
            # Quick validation first
            try:
                wrapped_conn.connection.execute("SELECT 1").fetchone()
                wrapped_conn.update_usage()
                
                # Track active connection
                with self._stats_lock:
                    self._active_connections += 1
                
            except sqlite3.Error as validation_error:
                # Connection is broken, replace it immediately
                logger.warning(
                    f"Connection {wrapped_conn.connection_id} failed quick validation: {validation_error}"
                )
                
                # Don't increment active connections for broken connection
                new_wrapped_conn = self._replace_broken_connection_enhanced(wrapped_conn)
                wrapped_conn = new_wrapped_conn
                
                with self._stats_lock:
                    self._active_connections += 1
                    self._connections_replaced += 1
            
            validation_time = time.time() - validation_start
            
            # Track validation time for performance monitoring
            with self._stats_lock:
                self._validation_times.append(validation_time * 1000)  # Store in milliseconds
                if len(self._validation_times) > 100:
                    self._validation_times.pop(0)
                self._connections_validated += 1
            
            # Log slow connection acquisition
            total_acquisition_time = time.time() - connection_acquired_time
            if total_acquisition_time > 0.1:  # 100ms threshold
                logger.warning(
                    f"Slow connection acquisition: {total_acquisition_time*1000:.2f}ms "
                    f"(pool_wait: {pool_wait_time*1000:.2f}ms, validation: {validation_time*1000:.2f}ms)"
                )
            
            # Yield the raw connection for use
            yield wrapped_conn.connection
            
        finally:
            if wrapped_conn is not None:
                try:
                    # Perform final health check before returning to pool
                    final_health_start = time.time()
                    
                    try:
                        # Quick health check
                        wrapped_conn.connection.execute("SELECT 1").fetchone()
                        
                        # Check if connection is getting stale or has errors
                        if wrapped_conn.is_stale(self._max_connection_age):
                            logger.info(f"Connection {wrapped_conn.connection_id} is stale, replacing")
                            self._replace_broken_connection_enhanced(wrapped_conn)
                        else:
                            # Return healthy connection to pool
                            with self._pool_lock:
                                self._connection_pool.put(wrapped_conn)
                        
                    except sqlite3.Error as final_error:
                        # Connection became unhealthy during use
                        logger.warning(
                            f"Connection {wrapped_conn.connection_id} became unhealthy during use: {final_error}"
                        )
                        self._replace_broken_connection_enhanced(wrapped_conn)
                        
                        with self._stats_lock:
                            self._connections_replaced += 1
                    
                    final_health_time = time.time() - final_health_start
                    
                    # Track final health check time
                    if final_health_time > 0.05:  # 50ms threshold
                        logger.debug(f"Slow final health check: {final_health_time*1000:.2f}ms")
                    
                    # Track connection return
                    with self._stats_lock:
                        self._active_connections -= 1
                    
                except Exception as cleanup_error:
                    # Critical: cleanup failed
                    logger.error(f"Connection cleanup failed: {cleanup_error}")
                    
                    # Force decrement active connections to prevent leak tracking issues
                    with self._stats_lock:
                        self._active_connections = max(0, self._active_connections - 1)
                        self._connection_leaks_detected += 1
    
    def _replace_broken_connection(self, broken_conn):
        """Replace a broken connection with a new one (legacy method for compatibility)"""
        if isinstance(broken_conn, ConnectionWrapper):
            self._replace_broken_connection_enhanced(broken_conn)
        else:
            # Handle raw connection (legacy compatibility)
            try:
                broken_conn.close()
            except:
                pass  # Ignore errors when closing broken connection
            
            # Create new wrapped connection
            new_wrapped = self._create_new_wrapped_connection()
            
            # Return to pool
            with self._pool_lock:
                self._connection_pool.put(new_wrapped)
            
            logger.info("Replaced broken database connection (legacy mode)")
    
    def _replace_broken_connection_enhanced(self, broken_wrapped_conn: ConnectionWrapper) -> ConnectionWrapper:
        """Replace a broken wrapped connection with a new healthy one"""
        with self._pool_lock:
            try:
                # Close the broken connection
                old_id = broken_wrapped_conn.connection_id
                broken_wrapped_conn.close()
                logger.debug(f"Closed broken connection {old_id}")
            except:
                pass  # Ignore errors when closing broken connection
            
            # Create new wrapped connection
            new_wrapped_conn = self._create_new_wrapped_connection()
            
            # Return to pool immediately (will be retrieved by caller if needed)
            self._connection_pool.put(new_wrapped_conn)
            
            with self._stats_lock:
                self._connections_replaced += 1
            
            logger.info(f"Replaced broken connection {old_id} with {new_wrapped_conn.connection_id}")
            return new_wrapped_conn
    
    def _create_new_wrapped_connection(self) -> ConnectionWrapper:
        """Create a new wrapped connection with all optimizations applied"""
        try:
            # Create raw connection
            conn = sqlite3.connect(
                self.db_path, 
                check_same_thread=False,
                timeout=Database.CONNECTION_TIMEOUT
            )
            
            # Apply performance optimizations
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute(f"PRAGMA cache_size={Database.CACHE_SIZE_PAGES}")
            conn.execute("PRAGMA temp_store=MEMORY")
            conn.execute("PRAGMA mmap_size=268435456")
            conn.row_factory = sqlite3.Row
            
            # Create wrapper with unique ID
            with self._stats_lock:
                connection_id = f"conn_{self._total_connections_created}_{int(time.time())}"
                self._total_connections_created += 1
            
            wrapped_conn = ConnectionWrapper(conn, connection_id)
            
            logger.debug(f"Created new connection {connection_id}")
            return wrapped_conn
            
        except Exception as e:
            logger.error(f"Failed to create new database connection: {e}")
            raise RuntimeError(f"Could not create replacement connection: {e}")
    
    def _perform_periodic_health_checks(self):
        """Perform periodic health checks on idle connections"""
        current_time = time.time()
        
        # Only perform health checks at specified intervals
        if current_time - self._last_health_check < self._health_check_interval:
            return
        
        with self._pool_lock:
            try:
                self._last_health_check = current_time
                connections_to_check = []
                
                # Get all connections from pool for health check
                while not self._connection_pool.empty():
                    try:
                        wrapped_conn = self._connection_pool.get_nowait()
                        connections_to_check.append(wrapped_conn)
                    except queue.Empty:
                        break
                
                healthy_connections = []
                replaced_count = 0
                
                # Check each connection
                for wrapped_conn in connections_to_check:
                    try:
                        # Skip recently used connections
                        if not wrapped_conn.is_idle(self._max_idle_time):
                            healthy_connections.append(wrapped_conn)
                            continue
                        
                        # Perform health check on idle connection
                        health = wrapped_conn.validate_health()
                        
                        if health.is_healthy and not wrapped_conn.is_stale(self._max_connection_age):
                            healthy_connections.append(wrapped_conn)
                        else:
                            # Replace unhealthy or stale connection
                            reason = "stale" if wrapped_conn.is_stale(self._max_connection_age) else "unhealthy"
                            logger.info(f"Replacing {reason} connection {wrapped_conn.connection_id}")
                            
                            wrapped_conn.close()
                            new_wrapped = self._create_new_wrapped_connection()
                            healthy_connections.append(new_wrapped)
                            replaced_count += 1
                            
                    except Exception as e:
                        # Connection check failed, replace it
                        logger.warning(f"Health check failed for connection {wrapped_conn.connection_id}: {e}")
                        try:
                            wrapped_conn.close()
                        except:
                            pass
                        
                        new_wrapped = self._create_new_wrapped_connection()
                        healthy_connections.append(new_wrapped)
                        replaced_count += 1
                
                # Return all healthy connections to pool
                for healthy_conn in healthy_connections:
                    self._connection_pool.put(healthy_conn)
                
                if replaced_count > 0:
                    logger.info(f"Periodic health check replaced {replaced_count} connections")
                    with self._stats_lock:
                        self._connections_replaced += replaced_count
                
            except Exception as e:
                logger.error(f"Error during periodic health check: {e}")
                # Ensure we don't leave the pool empty
                if self._connection_pool.empty():
                    logger.warning("Connection pool became empty during health check, reinitializing")
                    self._init_connection_pool()
    
    def get_connection_pool_status(self) -> Dict[str, Any]:
        """Get comprehensive connection pool status and health information"""
        with self._stats_lock:
            pool_stats = {
                'pool_size': self.pool_size,
                'available_connections': self._connection_pool.qsize(),
                'active_connections': self._active_connections,
                'total_connections_created': self._total_connections_created,
                'connections_validated': self._connections_validated,
                'connections_replaced': self._connections_replaced,
                'connection_leaks_detected': self._connection_leaks_detected,
                'pool_utilization': (self.pool_size - self._connection_pool.qsize()) / self.pool_size,
                'is_healthy': self._connection_pool.qsize() > 0 and self._active_connections <= self.pool_size,
                'avg_pool_wait_time_ms': sum(self._pool_wait_times) / len(self._pool_wait_times) if self._pool_wait_times else 0,
                'avg_validation_time_ms': sum(self._validation_times) / len(self._validation_times) if self._validation_times else 0,
                'max_pool_wait_time_ms': max(self._pool_wait_times) if self._pool_wait_times else 0,
                'max_validation_time_ms': max(self._validation_times) if self._validation_times else 0,
                'last_health_check': self._last_health_check,
                'health_check_interval': self._health_check_interval,
                'max_connection_age': self._max_connection_age,
                'max_idle_time': self._max_idle_time
            }
        
        return pool_stats
    
    def _get_pool_statistics_unsafe(self) -> Dict[str, Any]:
        """Get pool statistics without locking (for internal use when already locked)"""
        return {
            'pool_size': self.pool_size,
            'available_connections': self._connection_pool.qsize(),
            'active_connections': self._active_connections,
            'total_connections_created': self._total_connections_created,
            'connections_replaced': self._connections_replaced,
            'connection_leaks_detected': self._connection_leaks_detected
        }
    
    def validate_all_connections(self) -> Dict[str, Any]:
        """Validate all connections in the pool and return health report"""
        validation_results = {
            'total_connections': 0,
            'healthy_connections': 0,
            'unhealthy_connections': 0,
            'replaced_connections': 0,
            'validation_errors': [],
            'avg_response_time_ms': 0,
            'max_response_time_ms': 0
        }
        
        with self._pool_lock:
            try:
                connections_to_validate = []
                response_times = []
                
                # Get all connections from pool
                while not self._connection_pool.empty():
                    try:
                        wrapped_conn = self._connection_pool.get_nowait()
                        connections_to_validate.append(wrapped_conn)
                    except queue.Empty:
                        break
                
                validation_results['total_connections'] = len(connections_to_validate)
                healthy_connections = []
                
                # Validate each connection
                for wrapped_conn in connections_to_validate:
                    try:
                        health = wrapped_conn.validate_health()
                        response_times.append(health.response_time_ms)
                        
                        if health.is_healthy:
                            validation_results['healthy_connections'] += 1
                            healthy_connections.append(wrapped_conn)
                        else:
                            validation_results['unhealthy_connections'] += 1
                            validation_results['validation_errors'].append({
                                'connection_id': wrapped_conn.connection_id,
                                'error': health.validation_error,
                                'age_seconds': health.age_seconds
                            })
                            
                            # Replace unhealthy connection
                            wrapped_conn.close()
                            new_wrapped = self._create_new_wrapped_connection()
                            healthy_connections.append(new_wrapped)
                            validation_results['replaced_connections'] += 1
                            
                    except Exception as e:
                        validation_results['unhealthy_connections'] += 1
                        validation_results['validation_errors'].append({
                            'connection_id': wrapped_conn.connection_id,
                            'error': str(e),
                            'critical': True
                        })
                        
                        # Replace broken connection
                        try:
                            wrapped_conn.close()
                        except:
                            pass
                        
                        new_wrapped = self._create_new_wrapped_connection()
                        healthy_connections.append(new_wrapped)
                        validation_results['replaced_connections'] += 1
                
                # Return all connections to pool
                for conn in healthy_connections:
                    self._connection_pool.put(conn)
                
                # Calculate response time statistics
                if response_times:
                    validation_results['avg_response_time_ms'] = sum(response_times) / len(response_times)
                    validation_results['max_response_time_ms'] = max(response_times)
                
                # Update replacement statistics
                if validation_results['replaced_connections'] > 0:
                    with self._stats_lock:
                        self._connections_replaced += validation_results['replaced_connections']
                
                logger.info(
                    f"Connection validation complete: {validation_results['healthy_connections']}/{validation_results['total_connections']} healthy, "
                    f"{validation_results['replaced_connections']} replaced"
                )
                
            except Exception as e:
                logger.error(f"Error during connection validation: {e}")
                validation_results['validation_errors'].append({
                    'critical_error': str(e)
                })
        
        return validation_results
    
    def configure_connection_health(self, max_connection_age: int = None, 
                                 max_idle_time: int = None, 
                                 health_check_interval: int = None):
        """Configure connection health management parameters"""
        config_changed = False
        
        if max_connection_age is not None:
            if max_connection_age < 60 or max_connection_age > 86400:  # 1 minute to 24 hours
                raise ValueError("max_connection_age must be between 60 and 86400 seconds")
            self._max_connection_age = max_connection_age
            config_changed = True
        
        if max_idle_time is not None:
            if max_idle_time < 30 or max_idle_time > 3600:  # 30 seconds to 1 hour
                raise ValueError("max_idle_time must be between 30 and 3600 seconds")
            self._max_idle_time = max_idle_time
            config_changed = True
        
        if health_check_interval is not None:
            if health_check_interval < 10 or health_check_interval > 600:  # 10 seconds to 10 minutes
                raise ValueError("health_check_interval must be between 10 and 600 seconds")
            self._health_check_interval = health_check_interval
            config_changed = True
        
        if config_changed:
            logger.info(
                f"Connection health configuration updated: max_age={self._max_connection_age}s, "
                f"max_idle={self._max_idle_time}s, check_interval={self._health_check_interval}s"
            )
    
    def __del__(self):
        """Ensure proper cleanup of database connections"""
        try:
            # Check if object was fully initialized before attempting cleanup
            if hasattr(self, '_closed') and not self._closed:
                if hasattr(self, 'close'):
                    self.close()
        except:
            # Don't raise exceptions in destructor - silently handle cleanup failures
            pass
    
    def get_resource_stats(self) -> Dict[str, Any]:
        """Get current resource usage statistics"""
        with self._lock:
            pool_size = self._connection_pool.qsize()
            return {
                'db_path': self.db_path,
                'pool_size_configured': self.pool_size,
                'pool_size_current': pool_size,
                'active_connections': self._active_connections,
                'total_connections_created': self._total_connections_created,
                'connection_leaks_detected': self._connection_leaks_detected,
                'pool_utilization': (self.pool_size - pool_size) / self.pool_size,
                'is_closed': self._closed
            }
    
    def check_connection_leaks(self) -> bool:
        """Check for potential connection leaks"""
        with self._lock:
            # If we have active connections for too long, it might be a leak
            if self._active_connections > 0:
                logger.warning(f"Potential connection leak detected: {self._active_connections} connections still active")
                return True
            return False
    
    def create_tables(self):
        """Create all database tables with optimized schemas"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Trades table - transaction history
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
                    screenshot_path TEXT
                )
            """)
            
            # Current inventory table - live data
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS current_inventory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trader_nickname TEXT NOT NULL,
                    item_name TEXT NOT NULL,
                    item_id TEXT,
                    quantity INTEGER NOT NULL,
                    price_per_unit REAL NOT NULL,
                    total_price REAL NOT NULL,
                    last_updated REAL NOT NULL DEFAULT (julianday('now')),
                    UNIQUE(trader_nickname, item_name, item_id) ON CONFLICT REPLACE
                )
            """)
            
            # Search queue table - items to monitor
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS search_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_name TEXT NOT NULL UNIQUE,
                    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'active', 'completed')),
                    priority INTEGER NOT NULL DEFAULT 0,
                    last_processed REAL DEFAULT NULL
                )
            """)
            
            # OCR cache table - performance optimization
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ocr_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    image_hash TEXT NOT NULL UNIQUE,
                    ocr_result TEXT NOT NULL,
                    confidence_score REAL NOT NULL,
                    region_type TEXT NOT NULL,
                    created_at REAL NOT NULL DEFAULT (julianday('now')),
                    hit_count INTEGER NOT NULL DEFAULT 1
                )
            """)
            
            # Validation log table - quality tracking
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS validation_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    operation_type TEXT NOT NULL,
                    data_before TEXT,
                    data_after TEXT,
                    validation_result TEXT NOT NULL,
                    confidence_score REAL,
                    manual_verified INTEGER DEFAULT 0,
                    timestamp REAL NOT NULL DEFAULT (julianday('now'))
                )
            """)
            
            self._create_indexes(cursor)
            conn.commit()
            logger.info("Database tables created/verified successfully")
    
    def _create_indexes(self, cursor):
        """Create performance indexes"""
        indexes = [
            # Trades table indexes
            ("idx_trades_trader", "trades", "trader_nickname"),
            ("idx_trades_item", "trades", "item_name"),
            ("idx_trades_timestamp", "trades", "timestamp"),
            ("idx_trades_type", "trades", "trade_type"),
            ("idx_trades_composite", "trades", "trader_nickname, item_name, timestamp"),
            
            # Current inventory indexes
            ("idx_inventory_trader", "current_inventory", "trader_nickname"),
            ("idx_inventory_item", "current_inventory", "item_name"),
            ("idx_inventory_updated", "current_inventory", "last_updated"),
            
            # Search queue indexes
            ("idx_queue_status", "search_queue", "status"),
            ("idx_queue_priority", "search_queue", "priority DESC"),
            
            # OCR cache indexes
            ("idx_ocr_hash", "ocr_cache", "image_hash"),
            ("idx_ocr_region", "ocr_cache", "region_type"),
            ("idx_ocr_created", "ocr_cache", "created_at"),
            
            # Validation log indexes
            ("idx_validation_type", "validation_log", "operation_type"),
            ("idx_validation_timestamp", "validation_log", "timestamp"),
        ]
        
        for idx_name, table, columns in indexes:
            cursor.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({columns})")
    
    # TRADES OPERATIONS
    
    @retry_with_exponential_backoff(max_retries=3, base_delay=0.1, max_delay=2.0)
    def record_trade(self, trader_nickname: str, item_name: str, item_id: str,
                    previous_qty: int, current_qty: int, quantity_change: int,
                    price_per_unit: float, total_value: float, trade_type: str,
                    screenshot_path: str = None) -> int:
        """Record a single trade with high performance"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                # Begin explicit transaction
                cursor.execute("BEGIN IMMEDIATE")
                
                cursor.execute("""
                    INSERT INTO trades (trader_nickname, item_name, item_id, previous_quantity,
                                      current_quantity, quantity_change, price_per_unit, 
                                      total_value, trade_type, timestamp, screenshot_path)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, julianday('now'), ?)
                """, (trader_nickname, item_name, item_id, previous_qty, current_qty,
                      quantity_change, price_per_unit, total_value, trade_type, screenshot_path))
                
                trade_id = cursor.lastrowid
                
                # Commit transaction if successful
                conn.commit()
                logger.debug(f"Successfully recorded trade {trade_id} for {trader_nickname}: {item_name}")
                return trade_id
                
            except sqlite3.IntegrityError as e:
                # Handle constraint violations
                conn.rollback()
                logger.error(f"Database integrity error in record_trade: {e}")
                raise sqlite3.DatabaseError(f"Data integrity violation: {e}")
                
            except sqlite3.OperationalError as e:
                # Handle database locked, table locked, etc.
                conn.rollback()
                logger.error(f"Database operational error in record_trade: {e}")
                raise  # Re-raise to trigger retry mechanism
                
            except Exception as e:
                # Handle any other unexpected errors
                try:
                    conn.rollback()
                except:
                    pass  # Rollback might fail if connection is broken
                
                logger.error(f"Unexpected error in record_trade: {e}")
                raise sqlite3.DatabaseError(f"Transaction failed: {e}")
    
    @retry_with_exponential_backoff(max_retries=3, base_delay=0.1, max_delay=2.0)
    def batch_record_trades(self, trades_data: List[Tuple]) -> List[int]:
        """Record multiple trades in a single transaction"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                # Begin explicit transaction
                cursor.execute("BEGIN IMMEDIATE")
                
                cursor.executemany("""
                    INSERT INTO trades (trader_nickname, item_name, item_id, previous_quantity,
                                      current_quantity, quantity_change, price_per_unit,
                                      total_value, trade_type, timestamp, screenshot_path)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, julianday('now'), ?)
                """, trades_data)
                
                trade_ids = list(range(cursor.lastrowid - len(trades_data) + 1, cursor.lastrowid + 1))
                
                # Commit transaction if successful
                conn.commit()
                logger.debug(f"Successfully batch recorded {len(trades_data)} trades")
                return trade_ids
                
            except sqlite3.IntegrityError as e:
                # Handle constraint violations
                conn.rollback()
                logger.error(f"Database integrity error in batch_record_trades: {e}")
                raise sqlite3.DatabaseError(f"Data integrity violation: {e}")
                
            except sqlite3.OperationalError as e:
                # Handle database locked, table locked, etc.
                conn.rollback()
                logger.error(f"Database operational error in batch_record_trades: {e}")
                raise  # Re-raise to trigger retry mechanism
                
            except Exception as e:
                # Handle any other unexpected errors
                try:
                    conn.rollback()
                except:
                    pass  # Rollback might fail if connection is broken
                
                logger.error(f"Unexpected error in batch_record_trades: {e}")
                raise sqlite3.DatabaseError(f"Transaction failed: {e}")
    
    # INVENTORY OPERATIONS
    
    @retry_with_exponential_backoff(max_retries=3, base_delay=0.1, max_delay=2.0)
    def update_inventory_and_track_trades(self, trader_data: List[Dict[str, Any]]) -> List[int]:
        """
        Core method: Update inventory and detect trades in one optimized operation
        Returns list of new trade IDs
        """
        trade_ids = []
        current_time = time.time()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                # Begin explicit transaction
                cursor.execute("BEGIN IMMEDIATE")
                
                for item_data in trader_data:
                    nickname = item_data['trader_nickname']
                    item_name = item_data['item_name']
                    item_id = item_data.get('item_id', '')
                    current_qty = item_data['quantity']
                    current_price = item_data['price_per_unit']
                    total_price = item_data['total_price']
                    
                    # Get previous state
                    cursor.execute("""
                        SELECT quantity, price_per_unit FROM current_inventory
                        WHERE trader_nickname=? AND item_name=? AND item_id=?
                    """, (nickname, item_name, item_id))
                    
                    previous_data = cursor.fetchone()
                    
                    if previous_data:
                        previous_qty = previous_data['quantity']
                        previous_price = previous_data['price_per_unit']
                        
                        # Detect quantity change
                        if current_qty != previous_qty:
                            quantity_change = current_qty - previous_qty
                            
                            if quantity_change > 0:
                                trade_type = 'restock'
                            else:
                                trade_type = 'purchase'
                            
                            # Use previous price for trade calculation
                            used_price = previous_price if previous_price else current_price
                            total_value = abs(quantity_change) * used_price
                            
                            # Record trade
                            cursor.execute("""
                                INSERT INTO trades (trader_nickname, item_name, item_id,
                                                  previous_quantity, current_quantity, quantity_change,
                                                  price_per_unit, total_value, trade_type, timestamp)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (nickname, item_name, item_id, previous_qty, current_qty,
                                  quantity_change, used_price, total_value, trade_type, current_time))
                            
                            trade_ids.append(cursor.lastrowid)
                    
                    # Update current inventory
                    cursor.execute("""
                        INSERT OR REPLACE INTO current_inventory 
                        (trader_nickname, item_name, item_id, quantity, price_per_unit, 
                         total_price, last_updated)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (nickname, item_name, item_id, current_qty, current_price,
                          total_price, current_time))
                
                # Commit transaction if all operations successful
                conn.commit()
                logger.debug(f"Successfully processed {len(trader_data)} trader updates, created {len(trade_ids)} trades")
                
            except sqlite3.IntegrityError as e:
                # Handle constraint violations
                conn.rollback()
                logger.error(f"Database integrity error in update_inventory_and_track_trades: {e}")
                raise sqlite3.DatabaseError(f"Data integrity violation: {e}")
                
            except sqlite3.OperationalError as e:
                # Handle database locked, table locked, etc.
                conn.rollback()
                logger.error(f"Database operational error in update_inventory_and_track_trades: {e}")
                raise  # Re-raise to trigger retry mechanism
                
            except Exception as e:
                # Handle any other unexpected errors
                try:
                    conn.rollback()
                except:
                    pass  # Rollback might fail if connection is broken
                
                logger.error(f"Unexpected error in update_inventory_and_track_trades: {e}")
                raise sqlite3.DatabaseError(f"Transaction failed: {e}")
        
        return trade_ids
    
    @retry_with_exponential_backoff(max_retries=3, base_delay=0.1, max_delay=2.0)
    def check_disappeared_traders(self, current_traders: List[str], item_name: str) -> List[int]:
        """Check for disappeared traders and record sold_out trades"""
        trade_ids = []
        current_time = time.time()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                # Begin explicit transaction
                cursor.execute("BEGIN IMMEDIATE")
                
                # Get all traders who had this item
                cursor.execute("""
                    SELECT trader_nickname, item_name, item_id, quantity, price_per_unit
                    FROM current_inventory WHERE item_name = ?
                """, (item_name,))
                
                previous_traders = cursor.fetchall()
                
                for prev_trader in previous_traders:
                    if prev_trader['trader_nickname'] not in current_traders:
                        # Trader disappeared - record sold_out
                        cursor.execute("""
                            INSERT INTO trades (trader_nickname, item_name, item_id,
                                              previous_quantity, current_quantity, quantity_change,
                                              price_per_unit, total_value, trade_type, timestamp)
                            VALUES (?, ?, ?, ?, 0, ?, ?, ?, 'sold_out', ?)
                        """, (prev_trader['trader_nickname'], prev_trader['item_name'],
                              prev_trader['item_id'], prev_trader['quantity'],
                              -prev_trader['quantity'],
                              prev_trader['price_per_unit'],
                              prev_trader['quantity'] * prev_trader['price_per_unit'],
                              current_time))
                        
                        trade_ids.append(cursor.lastrowid)
                        
                        # Remove from current inventory
                        cursor.execute("""
                            DELETE FROM current_inventory 
                            WHERE trader_nickname=? AND item_name=? AND item_id=?
                        """, (prev_trader['trader_nickname'], prev_trader['item_name'],
                              prev_trader['item_id']))
                
                # Commit transaction if all operations successful
                conn.commit()
                logger.debug(f"Successfully processed {len(previous_traders)} disappeared traders for {item_name}, created {len(trade_ids)} sold_out trades")
                
            except sqlite3.IntegrityError as e:
                # Handle constraint violations
                conn.rollback()
                logger.error(f"Database integrity error in check_disappeared_traders: {e}")
                raise sqlite3.DatabaseError(f"Data integrity violation: {e}")
                
            except sqlite3.OperationalError as e:
                # Handle database locked, table locked, etc.
                conn.rollback()
                logger.error(f"Database operational error in check_disappeared_traders: {e}")
                raise  # Re-raise to trigger retry mechanism
                
            except Exception as e:
                # Handle any other unexpected errors
                try:
                    conn.rollback()
                except:
                    pass  # Rollback might fail if connection is broken
                
                logger.error(f"Unexpected error in check_disappeared_traders: {e}")
                raise sqlite3.DatabaseError(f"Transaction failed: {e}")
        
        return trade_ids
    
    # SEARCH QUEUE OPERATIONS
    
    def get_next_item_to_process(self) -> Optional[str]:
        """Get next item from queue with highest priority"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT item_name FROM search_queue 
                WHERE status = 'pending'
                ORDER BY priority DESC, id ASC
                LIMIT 1
            """)
            result = cursor.fetchone()
            return result['item_name'] if result else None
    
    @retry_with_exponential_backoff(max_retries=3, base_delay=0.1, max_delay=2.0)
    def update_item_status(self, item_name: str, status: str):
        """Update item processing status"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                # Begin explicit transaction
                cursor.execute("BEGIN IMMEDIATE")
                
                cursor.execute("""
                    UPDATE search_queue 
                    SET status = ?, last_processed = julianday('now')
                    WHERE item_name = ?
                """, (status, item_name))
                
                # Check if the update actually affected any rows
                if cursor.rowcount == 0:
                    logger.warning(f"No rows updated for item_name: {item_name}, status: {status}")
                
                # Commit transaction if successful
                conn.commit()
                logger.debug(f"Successfully updated status for {item_name} to {status}")
                
            except sqlite3.IntegrityError as e:
                # Handle constraint violations
                conn.rollback()
                logger.error(f"Database integrity error in update_item_status: {e}")
                raise sqlite3.DatabaseError(f"Data integrity violation: {e}")
                
            except sqlite3.OperationalError as e:
                # Handle database locked, table locked, etc.
                conn.rollback()
                logger.error(f"Database operational error in update_item_status: {e}")
                raise  # Re-raise to trigger retry mechanism
                
            except Exception as e:
                # Handle any other unexpected errors
                try:
                    conn.rollback()
                except:
                    pass  # Rollback might fail if connection is broken
                
                logger.error(f"Unexpected error in update_item_status: {e}")
                raise sqlite3.DatabaseError(f"Transaction failed: {e}")
    
    # ANALYTICS & REPORTING
    
    def get_trade_statistics(self, item_name: str = None, hours: int = 24) -> List[Dict]:
        """Get trade statistics for analysis"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT trade_type, COUNT(*) as trade_count,
                       SUM(total_value) as total_value,
                       AVG(price_per_unit) as avg_price,
                       SUM(ABS(quantity_change)) as total_quantity
                FROM trades 
                WHERE timestamp >= julianday('now', '-{} hours')
            """.format(hours)
            
            params = []
            if item_name:
                query += " AND item_name = ?"
                params.append(item_name)
            
            query += " GROUP BY trade_type"
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_total_trades_count(self) -> int:
        """Get total number of trades in database"""
        query = "SELECT COUNT(*) FROM trades"
        
        with self.get_connection() as conn:
            result = conn.execute(query).fetchone()
            return result[0] if result else 0
    
    def get_unique_traders_count(self) -> int:
        """Get count of unique traders"""
        query = "SELECT COUNT(DISTINCT trader_nickname) FROM trades WHERE trader_nickname IS NOT NULL"
        
        with self.get_connection() as conn:
            result = conn.execute(query).fetchone()
            return result[0] if result else 0
    
    def get_unique_items_count(self) -> int:
        """Get count of unique items"""
        query = "SELECT COUNT(DISTINCT item_name) FROM trades WHERE item_name IS NOT NULL"
        
        with self.get_connection() as conn:
            result = conn.execute(query).fetchone()
            return result[0] if result else 0
    
    def get_recent_trades(self, limit: int = 20) -> List[Tuple]:
        """Get recent trades for display"""
        query = """
        SELECT timestamp, trader_nickname, item_name, quantity_change, price_per_unit, 0.95 as confidence
        FROM trades 
        ORDER BY timestamp DESC 
        LIMIT ?
        """
        
        with self.get_connection() as conn:
            cursor = conn.execute(query, [limit])
            return cursor.fetchall()
    
    def execute_query(self, query: str, params: List = None) -> List[Tuple]:
        """
        Execute a generic SQL query for testing and diagnostic purposes.
        
        Args:
            query: SQL query string
            params: Optional query parameters
            
        Returns:
            List of tuples containing query results
        """
        if params is None:
            params = []
            
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            return cursor.fetchall()
    
    def get_current_inventory_for_item(self, item_name: str) -> List[Dict]:
        """Get current inventory for specific item"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM current_inventory 
                WHERE item_name = ?
                ORDER BY price_per_unit ASC
            """, (item_name,))
            return [dict(row) for row in cursor.fetchall()]
    
    # OCR CACHE OPERATIONS
    
    @retry_with_exponential_backoff(max_retries=3, base_delay=0.1, max_delay=2.0)
    def get_cached_ocr(self, image_hash: str) -> Optional[Dict]:
        """Get cached OCR result"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                # Begin explicit transaction
                cursor.execute("BEGIN IMMEDIATE")
                
                cursor.execute("""
                    UPDATE ocr_cache SET hit_count = hit_count + 1
                    WHERE image_hash = ?
                """, (image_hash,))
                
                cursor.execute("""
                    SELECT ocr_result, confidence_score FROM ocr_cache
                    WHERE image_hash = ?
                """, (image_hash,))
                
                result = cursor.fetchone()
                
                # Commit transaction if successful
                conn.commit()
                
                if result:
                    logger.debug(f"OCR cache hit for image hash: {image_hash[:16]}...")
                    return dict(result)
                else:
                    logger.debug(f"OCR cache miss for image hash: {image_hash[:16]}...")
                    return None
                
            except sqlite3.IntegrityError as e:
                # Handle constraint violations
                conn.rollback()
                logger.error(f"Database integrity error in get_cached_ocr: {e}")
                raise sqlite3.DatabaseError(f"Data integrity violation: {e}")
                
            except sqlite3.OperationalError as e:
                # Handle database locked, table locked, etc.
                conn.rollback()
                logger.error(f"Database operational error in get_cached_ocr: {e}")
                raise  # Re-raise to trigger retry mechanism
                
            except Exception as e:
                # Handle any other unexpected errors
                try:
                    conn.rollback()
                except:
                    pass  # Rollback might fail if connection is broken
                
                logger.error(f"Unexpected error in get_cached_ocr: {e}")
                raise sqlite3.DatabaseError(f"Transaction failed: {e}")
    
    @retry_with_exponential_backoff(max_retries=3, base_delay=0.1, max_delay=2.0)
    def cache_ocr_result(self, image_hash: str, ocr_result: str, 
                        confidence_score: float, region_type: str):
        """Cache OCR result for performance"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                # Begin explicit transaction
                cursor.execute("BEGIN IMMEDIATE")
                
                cursor.execute("""
                    INSERT OR REPLACE INTO ocr_cache 
                    (image_hash, ocr_result, confidence_score, region_type)
                    VALUES (?, ?, ?, ?)
                """, (image_hash, ocr_result, confidence_score, region_type))
                
                # Commit transaction if successful
                conn.commit()
                logger.debug(f"Successfully cached OCR result for {region_type}")
                
            except sqlite3.IntegrityError as e:
                # Handle constraint violations
                conn.rollback()
                logger.error(f"Database integrity error in cache_ocr_result: {e}")
                raise sqlite3.DatabaseError(f"Data integrity violation: {e}")
                
            except sqlite3.OperationalError as e:
                # Handle database locked, table locked, etc.
                conn.rollback()
                logger.error(f"Database operational error in cache_ocr_result: {e}")
                raise  # Re-raise to trigger retry mechanism
                
            except Exception as e:
                # Handle any other unexpected errors
                try:
                    conn.rollback()
                except:
                    pass  # Rollback might fail if connection is broken
                
                logger.error(f"Unexpected error in cache_ocr_result: {e}")
                raise sqlite3.DatabaseError(f"Transaction failed: {e}")
    
    @retry_with_exponential_backoff(max_retries=3, base_delay=0.1, max_delay=2.0)
    def cleanup_old_cache(self, days_old: int = 7):
        """Cleanup old cache entries"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                # Begin explicit transaction
                cursor.execute("BEGIN IMMEDIATE")
                
                cursor.execute("""
                    DELETE FROM ocr_cache 
                    WHERE created_at < julianday('now', '-{} days')
                    AND hit_count <= 1
                """.format(days_old))
                
                deleted_count = cursor.rowcount
                
                # Commit transaction if successful
                conn.commit()
                logger.info(f"Successfully cleaned up {deleted_count} old cache entries")
                
            except sqlite3.IntegrityError as e:
                # Handle constraint violations
                conn.rollback()
                logger.error(f"Database integrity error in cleanup_old_cache: {e}")
                raise sqlite3.DatabaseError(f"Data integrity violation: {e}")
                
            except sqlite3.OperationalError as e:
                # Handle database locked, table locked, etc.
                conn.rollback()
                logger.error(f"Database operational error in cleanup_old_cache: {e}")
                raise  # Re-raise to trigger retry mechanism
                
            except Exception as e:
                # Handle any other unexpected errors
                try:
                    conn.rollback()
                except:
                    pass  # Rollback might fail if connection is broken
                
                logger.error(f"Unexpected error in cleanup_old_cache: {e}")
                raise sqlite3.DatabaseError(f"Transaction failed: {e}")
    
    def close(self):
        """Close all connections in pool with proper resource management"""
        if self._closed:
            logger.debug("DatabaseManager already closed")
            return
        
        with self._lock:
            self._closed = True
            
            # Get resource stats before cleanup
            stats = self.get_resource_stats()
            
            # Check for connection leaks
            if self._active_connections > 0:
                logger.warning(f"Closing DatabaseManager with {self._active_connections} active connections - potential leak")
            
            # Close all connections in pool
            connections_closed = 0
            while not self._connection_pool.empty():
                try:
                    conn = self._connection_pool.get_nowait()
                    conn.close()
                    connections_closed += 1
                except queue.Empty:
                    break
                except Exception as e:
                    logger.error(f"Error closing database connection: {e}")
                    connections_closed += 1  # Count it anyway
            
            # Remove from global instances registry
            try:
                _db_instances.discard(self)
            except:
                pass  # WeakSet operations might fail during shutdown
                
            logger.info(f"DatabaseManager closed: {connections_closed} connections closed, "
                       f"leaks detected: {stats['connection_leaks_detected']}")

# Singleton instance for global access
_db_instance = None
_db_lock = threading.Lock()

def cleanup_all_databases():
    """Cleanup all database instances - called at program exit"""
    try:
        # Create a copy of the set to avoid modification during iteration
        instances = list(_db_instances)
        if instances:
            logger.info(f"Cleaning up {len(instances)} database instances")
            for db in instances:
                try:
                    db.close()
                except:
                    pass  # Ignore cleanup errors during shutdown
    except:
        pass  # Ignore all errors during program exit

# Register cleanup function to run at program exit
atexit.register(cleanup_all_databases)

def get_database() -> DatabaseManager:
    """Get singleton database instance"""
    global _db_instance
    if _db_instance is None:
        with _db_lock:
            if _db_instance is None:
                _db_instance = DatabaseManager()
    return _db_instance

def get_all_database_stats() -> List[Dict[str, Any]]:
    """Get resource statistics for all database instances"""
    stats = []
    try:
        for db in _db_instances:
            try:
                stats.append(db.get_resource_stats())
            except:
                pass  # Skip instances that might be in invalid state
    except:
        pass  # WeakSet iteration might fail
    return stats