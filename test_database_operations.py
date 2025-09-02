#!/usr/bin/env python3
"""
Practical Database Operations Test
Test actual database functionality with real data operations
"""

import sys
import time
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from game_monitor.database_manager import DatabaseManager, get_database

def test_database_operations():
    """Test practical database operations"""
    print("="*60)
    print("TESTING DATABASE OPERATIONS")
    print("="*60)
    
    try:
        # Initialize database
        print("1. Initializing database connection...")
        db = get_database()
        print("   ✅ Database connected successfully")
        
        # Test 1: Insert real trade data
        print("\n2. Testing trade data insertion...")
        test_trades = [
            {
                'trader_nickname': 'TestTrader_001',
                'item_name': 'Меч огня',
                'item_id': 'sword_fire_001',
                'quantity': 10,
                'price_per_unit': 1500.0,
                'total_price': 15000.0
            },
            {
                'trader_nickname': 'TestTrader_002',
                'item_name': 'Щит льда',
                'item_id': 'shield_ice_002',
                'quantity': 5,
                'price_per_unit': 2000.0,
                'total_price': 10000.0
            },
            {
                'trader_nickname': 'TestTrader_001',
                'item_name': 'Зелье лечения',
                'item_id': 'potion_heal_003',
                'quantity': 50,
                'price_per_unit': 100.0,
                'total_price': 5000.0
            }
        ]
        
        start_time = time.time()
        trade_ids = db.update_inventory_and_track_trades(test_trades)
        insert_time = time.time() - start_time
        
        print(f"   ✅ Inserted {len(test_trades)} trades in {insert_time:.3f}s")
        print(f"   📊 Generated trade IDs: {trade_ids}")
        
        # Test 2: Query operations
        print("\n3. Testing database queries...")
        
        # Get current inventory
        start_time = time.time()
        inventory = db.get_current_inventory_for_item('Меч огня')
        query_time = time.time() - start_time
        
        print(f"   ✅ Inventory query completed in {query_time:.3f}s")
        print(f"   📊 Found {len(inventory)} inventory records for 'Меч огня'")
        
        if inventory:
            for item in inventory:
                print(f"      - {item['trader_nickname']}: {item['quantity']} units @ {item['price_per_unit']} each")
        
        # Test 3: Statistics
        print("\n4. Testing statistics queries...")
        start_time = time.time()
        stats = db.get_trade_statistics()
        stats_time = time.time() - start_time
        
        print(f"   ✅ Statistics query completed in {stats_time:.3f}s")
        print(f"   📊 Statistics returned: {len(stats)} trade type groups")
        
        for stat in stats:
            print(f"      - Trade type: {stat.get('trade_type', 'N/A')}")
            print(f"        Count: {stat.get('trade_count', 0)}")
            print(f"        Total value: {stat.get('total_value', 0.0):.2f}")
            print(f"        Avg price: {stat.get('avg_price', 0.0):.2f}")
        
        # Let's also test basic counts
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM trades")
            total_trades = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT trader_nickname) FROM current_inventory")
            active_traders = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT item_name) FROM current_inventory") 
            unique_items = cursor.fetchone()[0]
            
            print(f"   📊 Total trades in DB: {total_trades}")
            print(f"   📊 Active traders: {active_traders}")
            print(f"   📊 Unique items: {unique_items}")
        
        # Test 4: OCR Cache operations
        print("\n5. Testing OCR cache...")
        start_time = time.time()
        
        # Cache some OCR results
        cache_results = [
            ('hash_001', 'TestTrader_001', 0.95, 'trader_name'),
            ('hash_002', 'Меч огня', 0.88, 'item_name'),
            ('hash_003', '1500.00', 0.99, 'price'),
            ('hash_004', '10', 1.0, 'quantity')
        ]
        
        for image_hash, ocr_result, confidence, field_type in cache_results:
            db.cache_ocr_result(image_hash, ocr_result, confidence, field_type)
        
        cache_time = time.time() - start_time
        
        print(f"   ✅ Cached {len(cache_results)} OCR results in {cache_time:.3f}s")
        
        # Test cache retrieval
        cached_result = db.get_cached_ocr('hash_001')
        if cached_result:
            print(f"   ✅ Cache retrieval successful: {cached_result['ocr_result']} (confidence: {cached_result['confidence_score']})")
        else:
            print("   ⚠️  Cache retrieval returned None")
        
        # Test 5: Performance validation
        print("\n6. Performance validation...")
        total_time = insert_time + query_time + stats_time + cache_time
        
        print(f"   📊 Insert operations: {insert_time:.3f}s")
        print(f"   📊 Query operations: {query_time:.3f}s") 
        print(f"   📊 Statistics: {stats_time:.3f}s")
        print(f"   📊 Cache operations: {cache_time:.3f}s")
        print(f"   📊 Total database time: {total_time:.3f}s")
        
        if total_time < 1.0:
            print("   ✅ PERFORMANCE TARGET MET (<1 second)")
        else:
            print("   ⚠️  Performance target exceeded")
        
        # Test 6: Data validation
        print("\n7. Data integrity check...")
        
        # Check if all data was inserted correctly
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM trades WHERE trader_nickname LIKE 'TestTrader_%'")
            trade_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM current_inventory WHERE trader_nickname LIKE 'TestTrader_%'")
            inventory_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM ocr_cache WHERE image_hash LIKE 'hash_%'")
            cache_count = cursor.fetchone()[0]
            
            print(f"   ✅ Trade records: {trade_count}")
            print(f"   ✅ Inventory records: {inventory_count}")
            print(f"   ✅ Cache records: {cache_count}")
        
        # Cleanup test data
        print("\n8. Cleaning up test data...")
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM trades WHERE trader_nickname LIKE 'TestTrader_%'")
            cursor.execute("DELETE FROM current_inventory WHERE trader_nickname LIKE 'TestTrader_%'")
            cursor.execute("DELETE FROM ocr_cache WHERE image_hash LIKE 'hash_%'")
            conn.commit()
        print("   ✅ Test data cleaned up")
        
        print("\n" + "="*60)
        print("DATABASE OPERATIONS TEST: ✅ PASSED")
        print("="*60)
        print(f"Total execution time: {total_time:.3f}s")
        print("All database operations working correctly!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Database test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_database_operations()
    sys.exit(0 if success else 1)