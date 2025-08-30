"""
High-Performance Database Manager for Game Monitor System

Optimized for <1 second response time with connection pooling,
batch operations, and performance tuning.
"""

import sqlite3
import threading
import logging
import time
from typing import Dict, List, Optional, Tuple, Any
from contextlib import contextmanager
from pathlib import Path
import queue

logger = logging.getLogger(__name__)

class DatabaseManager:
    """High-performance database manager with connection pooling and optimizations"""
    
    def __init__(self, db_path: str = "data/game_monitor.db", pool_size: int = 5):
        self.db_path = db_path
        self.pool_size = pool_size
        self._connection_pool = queue.Queue(maxsize=pool_size)
        self._lock = threading.Lock()
        
        # Ensure database directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize connection pool
        self._init_connection_pool()
        
        # Create tables and indexes
        self.create_tables()
        
        logger.info(f"DatabaseManager initialized with pool size {pool_size}")
    
    def _init_connection_pool(self):
        """Initialize connection pool with optimized settings"""
        for _ in range(self.pool_size):
            conn = sqlite3.connect(
                self.db_path, 
                check_same_thread=False,
                timeout=5.0
            )
            
            # Performance optimizations
            conn.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging
            conn.execute("PRAGMA synchronous=NORMAL")  # Balanced performance
            conn.execute("PRAGMA cache_size=10000")  # 10MB cache
            conn.execute("PRAGMA temp_store=MEMORY")  # Use RAM for temp
            conn.execute("PRAGMA mmap_size=268435456")  # 256MB memory map
            
            # Set row factory for named access
            conn.row_factory = sqlite3.Row
            
            self._connection_pool.put(conn)
    
    @contextmanager
    def get_connection(self):
        """Get connection from pool with automatic return"""
        conn = self._connection_pool.get()
        try:
            yield conn
        finally:
            self._connection_pool.put(conn)
    
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
    
    def record_trade(self, trader_nickname: str, item_name: str, item_id: str,
                    previous_qty: int, current_qty: int, quantity_change: int,
                    price_per_unit: float, total_value: float, trade_type: str,
                    screenshot_path: str = None) -> int:
        """Record a single trade with high performance"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO trades (trader_nickname, item_name, item_id, previous_quantity,
                                  current_quantity, quantity_change, price_per_unit, 
                                  total_value, trade_type, timestamp, screenshot_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, julianday('now'), ?)
            """, (trader_nickname, item_name, item_id, previous_qty, current_qty,
                  quantity_change, price_per_unit, total_value, trade_type, screenshot_path))
            conn.commit()
            return cursor.lastrowid
    
    def batch_record_trades(self, trades_data: List[Tuple]) -> List[int]:
        """Record multiple trades in a single transaction"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany("""
                INSERT INTO trades (trader_nickname, item_name, item_id, previous_quantity,
                                  current_quantity, quantity_change, price_per_unit,
                                  total_value, trade_type, timestamp, screenshot_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, julianday('now'), ?)
            """, trades_data)
            conn.commit()
            return list(range(cursor.lastrowid - len(trades_data) + 1, cursor.lastrowid + 1))
    
    # INVENTORY OPERATIONS
    
    def update_inventory_and_track_trades(self, trader_data: List[Dict[str, Any]]) -> List[int]:
        """
        Core method: Update inventory and detect trades in one optimized operation
        Returns list of new trade IDs
        """
        trade_ids = []
        current_time = time.time()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
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
            
            conn.commit()
        
        return trade_ids
    
    def check_disappeared_traders(self, current_traders: List[str], item_name: str) -> List[int]:
        """Check for disappeared traders and record sold_out trades"""
        trade_ids = []
        current_time = time.time()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
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
            
            conn.commit()
        
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
    
    def update_item_status(self, item_name: str, status: str):
        """Update item processing status"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE search_queue 
                SET status = ?, last_processed = julianday('now')
                WHERE item_name = ?
            """, (status, item_name))
            conn.commit()
    
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
    
    def get_cached_ocr(self, image_hash: str) -> Optional[Dict]:
        """Get cached OCR result"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE ocr_cache SET hit_count = hit_count + 1
                WHERE image_hash = ?
            """, (image_hash,))
            
            cursor.execute("""
                SELECT ocr_result, confidence_score FROM ocr_cache
                WHERE image_hash = ?
            """, (image_hash,))
            
            result = cursor.fetchone()
            conn.commit()
            
            return dict(result) if result else None
    
    def cache_ocr_result(self, image_hash: str, ocr_result: str, 
                        confidence_score: float, region_type: str):
        """Cache OCR result for performance"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO ocr_cache 
                (image_hash, ocr_result, confidence_score, region_type)
                VALUES (?, ?, ?, ?)
            """, (image_hash, ocr_result, confidence_score, region_type))
            conn.commit()
    
    def cleanup_old_cache(self, days_old: int = 7):
        """Cleanup old cache entries"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM ocr_cache 
                WHERE created_at < julianday('now', '-{} days')
                AND hit_count <= 1
            """.format(days_old))
            conn.commit()
            logger.info(f"Cleaned up {cursor.rowcount} old cache entries")
    
    def close(self):
        """Close all connections in pool"""
        while not self._connection_pool.empty():
            conn = self._connection_pool.get()
            conn.close()
        logger.info("DatabaseManager connections closed")

# Singleton instance for global access
_db_instance = None
_db_lock = threading.Lock()

def get_database() -> DatabaseManager:
    """Get singleton database instance"""
    global _db_instance
    if _db_instance is None:
        with _db_lock:
            if _db_instance is None:
                _db_instance = DatabaseManager()
    return _db_instance