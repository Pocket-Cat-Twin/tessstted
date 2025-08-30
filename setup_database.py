#!/usr/bin/env python3
"""
Database Setup and Testing Script

Initializes the game monitor database, adds test data,
and verifies performance for <1 second operations.
"""

import os
import sys
import time
import logging
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from game_monitor.database_manager import DatabaseManager, get_database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_initial_data(db: DatabaseManager):
    """Setup initial search queue and test data"""
    
    # Initial items to monitor
    initial_items = [
        "Меч огня",
        "Щит льда", 
        "Зелье лечения",
        "Кольцо силы",
        "Амулет защиты",
        "Броня света",
        "Посох магии",
        "Стрелы ветра",
        "Камень душ",
        "Эликсир мудрости"
    ]
    
    logger.info("Setting up initial search queue...")
    
    with db.get_connection() as conn:
        cursor = conn.cursor()
        
        # Clear existing queue
        cursor.execute("DELETE FROM search_queue")
        
        # Add initial items with priorities
        for i, item_name in enumerate(initial_items):
            priority = len(initial_items) - i  # Higher numbers = higher priority
            cursor.execute("""
                INSERT INTO search_queue (item_name, status, priority)
                VALUES (?, 'pending', ?)
            """, (item_name, priority))
        
        conn.commit()
    
    logger.info(f"Added {len(initial_items)} items to search queue")

def create_test_data(db: DatabaseManager):
    """Create test data for development and testing"""
    
    logger.info("Creating test inventory data...")
    
    test_inventory = [
        {
            'trader_nickname': 'TestTrader1',
            'item_name': 'Меч огня',
            'item_id': 'sword_001',
            'quantity': 5,
            'price_per_unit': 1000.0,
            'total_price': 5000.0
        },
        {
            'trader_nickname': 'TestTrader2', 
            'item_name': 'Меч огня',
            'item_id': 'sword_001',
            'quantity': 3,
            'price_per_unit': 950.0,
            'total_price': 2850.0
        },
        {
            'trader_nickname': 'TestTrader1',
            'item_name': 'Щит льда',
            'item_id': 'shield_002',
            'quantity': 2,
            'price_per_unit': 750.0,
            'total_price': 1500.0
        }
    ]
    
    # Add test inventory
    trade_ids = db.update_inventory_and_track_trades(test_inventory)
    logger.info(f"Created test inventory, generated {len(trade_ids)} initial trades")
    
    # Simulate some trades by updating quantities
    time.sleep(0.1)  # Small delay to ensure different timestamps
    
    updated_inventory = [
        {
            'trader_nickname': 'TestTrader1',
            'item_name': 'Меч огня', 
            'item_id': 'sword_001',
            'quantity': 3,  # Decreased from 5 (purchase)
            'price_per_unit': 1000.0,
            'total_price': 3000.0
        },
        {
            'trader_nickname': 'TestTrader2',
            'item_name': 'Меч огня',
            'item_id': 'sword_001', 
            'quantity': 8,  # Increased from 3 (restock)
            'price_per_unit': 950.0,
            'total_price': 7600.0
        }
    ]
    
    trade_ids = db.update_inventory_and_track_trades(updated_inventory)
    logger.info(f"Simulated trades, generated {len(trade_ids)} trade records")

def performance_test(db: DatabaseManager):
    """Test database performance to ensure <1 second operations"""
    
    logger.info("Running performance tests...")
    
    # Test 1: Inventory update performance (critical path)
    start_time = time.time()
    
    large_inventory = []
    for i in range(100):  # 100 traders
        large_inventory.append({
            'trader_nickname': f'SpeedTrader{i}',
            'item_name': 'TestItem',
            'item_id': 'test_001',
            'quantity': i + 1,
            'price_per_unit': 100.0 + i,
            'total_price': (100.0 + i) * (i + 1)
        })
    
    trade_ids = db.update_inventory_and_track_trades(large_inventory)
    
    update_time = time.time() - start_time
    logger.info(f"Inventory update (100 traders): {update_time:.3f}s")
    
    # Test 2: Trade statistics query
    start_time = time.time()
    stats = db.get_trade_statistics()
    query_time = time.time() - start_time
    logger.info(f"Trade statistics query: {query_time:.3f}s")
    
    # Test 3: Current inventory lookup
    start_time = time.time()
    inventory = db.get_current_inventory_for_item('TestItem')
    lookup_time = time.time() - start_time
    logger.info(f"Inventory lookup: {lookup_time:.3f}s ({len(inventory)} records)")
    
    # Test 4: OCR cache operations
    start_time = time.time()
    for i in range(50):
        db.cache_ocr_result(f'hash_{i}', f'result_{i}', 0.95, 'trader_name')
        db.get_cached_ocr(f'hash_{i}')
    cache_time = time.time() - start_time
    logger.info(f"OCR cache operations (100 ops): {cache_time:.3f}s")
    
    # Performance summary
    total_time = update_time + query_time + lookup_time + cache_time
    logger.info(f"Total test time: {total_time:.3f}s")
    
    if total_time < 1.0:
        logger.info("✅ Performance test PASSED - All operations < 1 second combined")
    else:
        logger.warning("⚠️  Performance test SLOW - Consider optimization")
    
    return {
        'update_time': update_time,
        'query_time': query_time, 
        'lookup_time': lookup_time,
        'cache_time': cache_time,
        'total_time': total_time
    }

def verify_database_integrity(db: DatabaseManager):
    """Verify database structure and data integrity"""
    
    logger.info("Verifying database integrity...")
    
    with db.get_connection() as conn:
        cursor = conn.cursor()
        
        # Check tables exist
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
        """)
        tables = [row[0] for row in cursor.fetchall()]
        
        expected_tables = ['trades', 'current_inventory', 'search_queue', 'ocr_cache', 'validation_log']
        
        for table in expected_tables:
            if table in tables:
                logger.info(f"✅ Table '{table}' exists")
            else:
                logger.error(f"❌ Table '{table}' missing!")
        
        # Check indexes
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = [row[0] for row in cursor.fetchall()]
        logger.info(f"Database has {len(indexes)} indexes")
        
        # Check data counts
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            logger.info(f"Table '{table}': {count} records")

def cleanup_test_data(db: DatabaseManager):
    """Clean up test data"""
    
    logger.info("Cleaning up test data...")
    
    with db.get_connection() as conn:
        cursor = conn.cursor()
        
        # Keep search queue but clear test data
        cursor.execute("DELETE FROM trades WHERE trader_nickname LIKE 'Test%' OR trader_nickname LIKE 'Speed%'")
        cursor.execute("DELETE FROM current_inventory WHERE trader_nickname LIKE 'Test%' OR trader_nickname LIKE 'Speed%'")
        cursor.execute("DELETE FROM ocr_cache WHERE image_hash LIKE 'hash_%'")
        
        conn.commit()
    
    logger.info("Test data cleaned up")

def main():
    """Main setup function"""
    
    print("=" * 60)
    print("Game Monitor Database Setup")
    print("=" * 60)
    
    try:
        # Initialize database
        logger.info("Initializing database...")
        db = get_database()  # This will create tables automatically
        
        # Verify integrity
        verify_database_integrity(db)
        
        # Setup initial data
        setup_initial_data(db)
        
        # Create and test with sample data
        create_test_data(db)
        
        # Run performance tests
        perf_results = performance_test(db)
        
        # Cleanup test data (keep search queue)
        cleanup_test_data(db)
        
        print("\n" + "=" * 60)
        print("Database Setup Complete!")
        print("=" * 60)
        print(f"Performance Results:")
        print(f"  - Inventory Update: {perf_results['update_time']:.3f}s")
        print(f"  - Query Performance: {perf_results['query_time']:.3f}s")  
        print(f"  - Lookup Speed: {perf_results['lookup_time']:.3f}s")
        print(f"  - Cache Operations: {perf_results['cache_time']:.3f}s")
        print(f"  - Total: {perf_results['total_time']:.3f}s")
        
        if perf_results['total_time'] < 1.0:
            print("\n✅ READY FOR PRODUCTION - Performance target achieved!")
        else:
            print("\n⚠️  Performance optimization may be needed")
        
    except Exception as e:
        logger.error(f"Setup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()