#!/usr/bin/env python3
"""
Simplified test for seller status update logic.
Tests key scenarios directly with SQLite without full DatabaseManager initialization.
"""

import sqlite3
from datetime import datetime, timedelta


def create_test_database():
    """Create in-memory test database with required schema."""
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    
    # Create sellers_current table
    cursor.execute('''
        CREATE TABLE sellers_current (
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
    ''')
    
    conn.commit()
    return conn


def simulate_status_update(conn, seller_name, item_name, quantity=None, 
                          new_status='CHECKED', processing_type='full'):
    """
    Simulate the status update logic from DatabaseManager.update_sellers_status().
    This mimics the exact behavior when MonitoringEngine processes items.
    """
    cursor = conn.cursor()
    
    # Check if record exists
    cursor.execute('''
        SELECT id, status FROM sellers_current 
        WHERE seller_name = ? AND item_name = ?
    ''', (seller_name, item_name))
    
    existing = cursor.fetchone()
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    if existing:
        old_status = existing[1]
        # Update existing record - key logic here!
        cursor.execute('''
            UPDATE sellers_current 
            SET quantity = ?, status = ?, processing_type = ?,
                status_changed_at = CASE 
                    WHEN status != ? THEN ? 
                    ELSE status_changed_at 
                END,
                last_updated = ?
            WHERE seller_name = ? AND item_name = ?
        ''', (quantity, new_status, processing_type, new_status, current_time, current_time, seller_name, item_name))
        
        print(f"   📝 Updated {seller_name}-{item_name}: {old_status} → {new_status}")
    else:
        # Insert new record
        cursor.execute('''
            INSERT INTO sellers_current 
            (seller_name, item_name, quantity, status, processing_type, status_changed_at, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (seller_name, item_name, quantity, new_status, processing_type, current_time, current_time))
        
        print(f"   📝 Created {seller_name}-{item_name}: NEW → {new_status}")
    
    conn.commit()


def get_status_info(conn, seller_name, item_name):
    """Get current status information for seller-item pair."""
    cursor = conn.cursor()
    cursor.execute('''
        SELECT seller_name, item_name, status, quantity, 
               status_changed_at, last_updated, processing_type
        FROM sellers_current 
        WHERE seller_name = ? AND item_name = ?
    ''', (seller_name, item_name))
    
    result = cursor.fetchone()
    if result:
        return {
            'seller_name': result[0],
            'item_name': result[1],
            'status': result[2],
            'quantity': result[3],
            'status_changed_at': result[4],
            'last_updated': result[5],
            'processing_type': result[6]
        }
    return None


def print_status_table(conn):
    """Print current status table for debugging."""
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM sellers_current ORDER BY seller_name, item_name')
    
    print("\n📊 Current sellers_current table:")
    print("   ID | Seller  | Item  | Status    | Status Changed At    | Last Updated")
    print("   " + "-" * 75)
    
    for row in cursor.fetchall():
        print(f"   {row[0]:2} | {row[1]:7} | {row[2]:5} | {row[4]:9} | {row[6]} | {row[7]}")


def test_case_1_both_unchecked_to_checked():
    """Test Case 1: Both items UNCHECKED → CHECKED when processed simultaneously."""
    print("\n" + "="*70)
    print("🧪 TEST CASE 1: Both items UNCHECKED → CHECKED")
    print("="*70)
    
    conn = create_test_database()
    cursor = conn.cursor()
    
    # Setup: Create initial UNCHECKED status (simulate past processing)
    old_time_stone = (datetime.now() - timedelta(minutes=15)).strftime('%Y-%m-%d %H:%M:%S')
    old_time_wood = (datetime.now() - timedelta(minutes=20)).strftime('%Y-%m-%d %H:%M:%S')
    
    cursor.execute('''
        INSERT INTO sellers_current 
        (seller_name, item_name, quantity, status, processing_type, status_changed_at, last_updated)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', ('Seller1', 'Stone', 10, 'UNCHECKED', 'full', old_time_stone, old_time_stone))
    
    cursor.execute('''
        INSERT INTO sellers_current 
        (seller_name, item_name, quantity, status, processing_type, status_changed_at, last_updated)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', ('Seller1', 'Wood', 5, 'UNCHECKED', 'full', old_time_wood, old_time_wood))
    
    conn.commit()
    
    print(f"📸 Initial setup:")
    print(f"   - Seller1-Stone: UNCHECKED at {old_time_stone}")
    print(f"   - Seller1-Wood: UNCHECKED at {old_time_wood}")
    
    # Get initial status
    stone_before = get_status_info(conn, 'Seller1', 'Stone')
    wood_before = get_status_info(conn, 'Seller1', 'Wood')
    
    print_status_table(conn)
    
    # Simulate: Full processing detects both items simultaneously
    print(f"\n🔬 Simulating simultaneous full processing of both items...")
    simulate_status_update(conn, 'Seller1', 'Stone', quantity=10, new_status='CHECKED')
    simulate_status_update(conn, 'Seller1', 'Wood', quantity=5, new_status='CHECKED')
    
    # Get final status
    stone_after = get_status_info(conn, 'Seller1', 'Stone')
    wood_after = get_status_info(conn, 'Seller1', 'Wood')
    
    print_status_table(conn)
    
    # Validate results
    print(f"\n🔍 VALIDATION:")
    
    # Both should be CHECKED now
    stone_ok = stone_after['status'] == 'CHECKED'
    wood_ok = wood_after['status'] == 'CHECKED'
    
    # Status change timestamps should be updated (different from before)
    stone_timer_updated = stone_after['status_changed_at'] != stone_before['status_changed_at']
    wood_timer_updated = wood_after['status_changed_at'] != wood_before['status_changed_at']
    
    # Last updated should be refreshed
    stone_last_updated = stone_after['last_updated'] != stone_before['last_updated']
    wood_last_updated = wood_after['last_updated'] != wood_before['last_updated']
    
    print(f"   ✅ Stone UNCHECKED→CHECKED: {'PASS' if stone_ok else 'FAIL'}")
    print(f"   ✅ Wood UNCHECKED→CHECKED: {'PASS' if wood_ok else 'FAIL'}")
    print(f"   ✅ Stone status timer updated: {'PASS' if stone_timer_updated else 'FAIL'}")
    print(f"   ✅ Wood status timer updated: {'PASS' if wood_timer_updated else 'FAIL'}")
    print(f"   ✅ Stone last_updated refreshed: {'PASS' if stone_last_updated else 'FAIL'}")
    print(f"   ✅ Wood last_updated refreshed: {'PASS' if wood_last_updated else 'FAIL'}")
    
    all_pass = all([stone_ok, wood_ok, stone_timer_updated, wood_timer_updated, 
                   stone_last_updated, wood_last_updated])
    
    print(f"\n🎯 Case 1 Result: {'✅ PASS' if all_pass else '❌ FAIL'}")
    
    conn.close()
    return all_pass


def test_case_2_mixed_statuses():
    """Test Case 2: One CHECKED (timer refresh), other UNCHECKED → CHECKED."""
    print("\n" + "="*70)
    print("🧪 TEST CASE 2: One CHECKED (timer refresh), other UNCHECKED → CHECKED")
    print("="*70)
    
    conn = create_test_database()
    cursor = conn.cursor()
    
    # Setup: Stone=UNCHECKED (15 min ago), Wood=CHECKED (5 min ago) 
    old_time_stone = (datetime.now() - timedelta(minutes=15)).strftime('%Y-%m-%d %H:%M:%S')
    old_time_wood = (datetime.now() - timedelta(minutes=5)).strftime('%Y-%m-%d %H:%M:%S')
    
    cursor.execute('''
        INSERT INTO sellers_current 
        (seller_name, item_name, quantity, status, processing_type, status_changed_at, last_updated)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', ('Seller1', 'Stone', 10, 'UNCHECKED', 'full', old_time_stone, old_time_stone))
    
    cursor.execute('''
        INSERT INTO sellers_current 
        (seller_name, item_name, quantity, status, processing_type, status_changed_at, last_updated)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', ('Seller1', 'Wood', 5, 'CHECKED', 'full', old_time_wood, old_time_wood))
    
    conn.commit()
    
    print(f"📸 Initial setup:")
    print(f"   - Seller1-Stone: UNCHECKED at {old_time_stone}")
    print(f"   - Seller1-Wood: CHECKED at {old_time_wood}")
    
    # Get initial status
    stone_before = get_status_info(conn, 'Seller1', 'Stone')
    wood_before = get_status_info(conn, 'Seller1', 'Wood')
    
    print_status_table(conn)
    
    # Simulate: Full processing detects both items simultaneously  
    print(f"\n🔬 Simulating simultaneous full processing of both items...")
    simulate_status_update(conn, 'Seller1', 'Stone', quantity=10, new_status='CHECKED')
    simulate_status_update(conn, 'Seller1', 'Wood', quantity=5, new_status='CHECKED')
    
    # Get final status
    stone_after = get_status_info(conn, 'Seller1', 'Stone')
    wood_after = get_status_info(conn, 'Seller1', 'Wood')
    
    print_status_table(conn)
    
    # Validate results
    print(f"\n🔍 VALIDATION:")
    
    # Stone: Should change UNCHECKED → CHECKED
    stone_status_changed = stone_after['status'] == 'CHECKED' and stone_before['status'] == 'UNCHECKED'
    stone_timer_updated = stone_after['status_changed_at'] != stone_before['status_changed_at']
    stone_last_updated = stone_after['last_updated'] != stone_before['last_updated']
    
    # Wood: Should STAY CHECKED but refresh timers
    wood_status_unchanged = wood_after['status'] == 'CHECKED' and wood_before['status'] == 'CHECKED'
    wood_timer_preserved = wood_after['status_changed_at'] == wood_before['status_changed_at']  # Key point!
    wood_last_updated = wood_after['last_updated'] != wood_before['last_updated']
    
    print(f"   ✅ Stone UNCHECKED→CHECKED: {'PASS' if stone_status_changed else 'FAIL'}")
    print(f"   ✅ Stone status timer updated: {'PASS' if stone_timer_updated else 'FAIL'}")  
    print(f"   ✅ Stone last_updated refreshed: {'PASS' if stone_last_updated else 'FAIL'}")
    print(f"   ✅ Wood stays CHECKED: {'PASS' if wood_status_unchanged else 'FAIL'}")
    print(f"   ✅ Wood status timer PRESERVED: {'PASS' if wood_timer_preserved else 'FAIL'}")  # Important!
    print(f"   ✅ Wood last_updated refreshed: {'PASS' if wood_last_updated else 'FAIL'}")
    
    all_pass = all([stone_status_changed, stone_timer_updated, stone_last_updated,
                   wood_status_unchanged, wood_timer_preserved, wood_last_updated])
    
    print(f"\n🎯 Case 2 Result: {'✅ PASS' if all_pass else '❌ FAIL'}")
    
    if all_pass:
        print(f"   🎉 Perfect! Wood's 10-minute timer was NOT reset (status_changed_at preserved)")
        print(f"   🎉 But Wood's last_updated WAS refreshed (indicates recent processing)")
    
    conn.close()
    return all_pass


def main():
    """Run all test cases."""
    print("🚀 Starting SIMPLIFIED seller status update testing...")
    print(f"⏰ Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Run test cases
        case1_result = test_case_1_both_unchecked_to_checked()
        case2_result = test_case_2_mixed_statuses()
        
        print("\n" + "="*70)
        print("📋 FINAL TEST SUMMARY")
        print("="*70)
        
        print(f"✅ Case 1 (Both UNCHECKED→CHECKED): {'PASS' if case1_result else 'FAIL'}")
        print(f"✅ Case 2 (Mixed: timer logic): {'PASS' if case2_result else 'FAIL'}")
        
        if case1_result and case2_result:
            print(f"\n🎉 ALL TESTS PASSED!")
            print(f"🎯 Key findings confirmed:")
            print(f"   - Multiple items from same seller are processed correctly")
            print(f"   - UNCHECKED items transition to CHECKED when detected")
            print(f"   - CHECKED items preserve their status_changed_at timer")
            print(f"   - last_updated refreshes for all processed items (10-min counter reset)")
        else:
            print(f"\n❌ Some tests failed - review the logic!")
            
    except Exception as e:
        print(f"❌ Testing failed with error: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n⏰ Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()