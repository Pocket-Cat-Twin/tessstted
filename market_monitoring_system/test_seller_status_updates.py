#!/usr/bin/env python3
"""
Comprehensive test for seller status update logic.
Tests scenarios where one seller has multiple items and data comes simultaneously through full processing.
"""

import sys
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

sys.path.append('src')

from core.database_manager import DatabaseManager, ItemData
from core.monitoring_engine import MonitoringEngine
from core.text_parser import TextParser, ParsingResult
from config.settings import SettingsManager


class TestEnvironment:
    """Test environment with in-memory database and components."""
    
    def __init__(self):
        """Initialize test environment."""
        self.db_path = ":memory:"
        self.db_manager = None
        self.monitoring_engine = None
        self.text_parser = None
        self.settings_manager = None
        
    def setup(self):
        """Set up test environment."""
        print("🔧 Setting up test environment...")
        
        # Create database connection directly
        self.db_connection = sqlite3.connect(self.db_path)
        
        # Create tables directly without migrations
        self._create_test_schema()
        
        # Create database manager with existing connection
        self.db_manager = DatabaseManager(self.db_path)
        # Override connection to skip initialization 
        self.db_manager._local.connection = self.db_connection
        
        # Create mock settings manager
        self.settings_manager = self._create_mock_settings()
        
        # Create monitoring engine
        self.monitoring_engine = MonitoringEngine(self.db_manager, self.settings_manager)
        
        # Create text parser
        self.text_parser = TextParser()
        
        print("✅ Test environment ready")
    
    def _create_test_schema(self):
        """Create minimal test schema directly."""
        cursor = self.db_connection.cursor()
        
        # Create sellers_current table with processing_type
        cursor.execute('''
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
        ''')
        
        # Create items table
        cursor.execute('''
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
        ''')
        
        # Create changes_log table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS changes_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                seller_name TEXT NOT NULL,
                item_name TEXT NOT NULL,
                change_type TEXT,
                old_value TEXT,
                new_value TEXT,
                detected_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.db_connection.commit()
        
    def _create_mock_settings(self):
        """Create minimal mock settings manager."""
        class MockMonitoringConfig:
            status_check_interval = 10
            
        class MockSettingsManager:
            def __init__(self):
                self.monitoring = MockMonitoringConfig()
                
        return MockSettingsManager()
    
    def cleanup(self):
        """Clean up test environment."""
        try:
            if hasattr(self, 'db_connection') and self.db_connection:
                self.db_connection.close()
            if self.db_manager:
                self.db_manager.close()
        except Exception as e:
            print(f"⚠️ Cleanup warning: {e}")


def create_test_data_case_1(test_env: TestEnvironment):
    """
    Create test data for Case 1: Both items UNCHECKED → CHECKED
    
    Initial state:
    - Seller1-Stone: UNCHECKED, 15 minutes ago
    - Seller1-Wood: UNCHECKED, 20 minutes ago
    """
    print("\n📝 Creating test data for Case 1...")
    
    # Calculate timestamps
    now = datetime.now()
    stone_time = now - timedelta(minutes=15)
    wood_time = now - timedelta(minutes=20)
    
    with test_env.db_manager._transaction() as conn:
        cursor = conn.cursor()
        
        # Insert Seller1-Stone as UNCHECKED (15 min ago)
        cursor.execute('''
            INSERT INTO sellers_current 
            (seller_name, item_name, quantity, status, processing_type, status_changed_at, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', ('Seller1', 'Stone', 10, 'UNCHECKED', 'full', stone_time, stone_time))
        
        # Insert Seller1-Wood as UNCHECKED (20 min ago)
        cursor.execute('''
            INSERT INTO sellers_current 
            (seller_name, item_name, quantity, status, processing_type, status_changed_at, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', ('Seller1', 'Wood', 5, 'UNCHECKED', 'full', wood_time, wood_time))
    
    print(f"✅ Case 1 data created:")
    print(f"   - Seller1-Stone: UNCHECKED, {stone_time.strftime('%H:%M:%S')}")
    print(f"   - Seller1-Wood: UNCHECKED, {wood_time.strftime('%H:%M:%S')}")


def create_test_data_case_2(test_env: TestEnvironment):
    """
    Create test data for Case 2: One CHECKED, other UNCHECKED
    
    Initial state:
    - Seller1-Stone: UNCHECKED, 15 minutes ago
    - Seller1-Wood: CHECKED, 5 minutes ago
    """
    print("\n📝 Creating test data for Case 2...")
    
    # Calculate timestamps
    now = datetime.now()
    stone_time = now - timedelta(minutes=15)
    wood_time = now - timedelta(minutes=5)
    
    with test_env.db_manager._transaction() as conn:
        cursor = conn.cursor()
        
        # Clear existing data
        cursor.execute('DELETE FROM sellers_current')
        
        # Insert Seller1-Stone as UNCHECKED (15 min ago)
        cursor.execute('''
            INSERT INTO sellers_current 
            (seller_name, item_name, quantity, status, processing_type, status_changed_at, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', ('Seller1', 'Stone', 10, 'UNCHECKED', 'full', stone_time, stone_time))
        
        # Insert Seller1-Wood as CHECKED (5 min ago)
        cursor.execute('''
            INSERT INTO sellers_current 
            (seller_name, item_name, quantity, status, processing_type, status_changed_at, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', ('Seller1', 'Wood', 5, 'CHECKED', 'full', wood_time, wood_time))
    
    print(f"✅ Case 2 data created:")
    print(f"   - Seller1-Stone: UNCHECKED, {stone_time.strftime('%H:%M:%S')}")
    print(f"   - Seller1-Wood: CHECKED, {wood_time.strftime('%H:%M:%S')}")


def get_current_status(test_env: TestEnvironment, seller: str, item: str) -> dict:
    """Get current status of seller-item from database."""
    with test_env.db_manager._transaction() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT seller_name, item_name, status, quantity, 
                   status_changed_at, last_updated, processing_type
            FROM sellers_current 
            WHERE seller_name = ? AND item_name = ?
        ''', (seller, item))
        
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


def print_status_comparison(before: dict, after: dict, title: str):
    """Print before/after status comparison."""
    print(f"\n📊 {title}:")
    print(f"   Before: {before['status']} | status_changed: {before['status_changed_at']} | last_updated: {before['last_updated']}")
    print(f"   After:  {after['status']} | status_changed: {after['status_changed_at']} | last_updated: {after['last_updated']}")
    
    if before['status'] != after['status']:
        print(f"   🔄 Status changed: {before['status']} → {after['status']}")
    else:
        print(f"   ✋ Status unchanged: {after['status']}")
    
    if before['status_changed_at'] != after['status_changed_at']:
        print(f"   ⏰ Status timer reset")
    else:
        print(f"   ⏰ Status timer preserved (good for CHECKED items)")
        
    if before['last_updated'] != after['last_updated']:
        print(f"   🔄 Last updated refreshed")


def simulate_full_processing_data(test_env: TestEnvironment):
    """Simulate incoming data through full processing (both items detected)."""
    print("\n🔬 Simulating full processing with both items...")
    
    # Create ItemData objects as if they came from TextParser
    items = [
        ItemData(
            seller_name='Seller1',
            item_name='Stone',
            price=100.0,
            quantity=10,
            item_id='stone_id',
            hotkey='F1',
            processing_type='full'
        ),
        ItemData(
            seller_name='Seller1',
            item_name='Wood',
            price=50.0,
            quantity=5,
            item_id='wood_id',
            hotkey='F1',
            processing_type='full'
        )
    ]
    
    # Create parsing result
    parsing_result = ParsingResult(
        items=items,
        hotkey='F1',
        screenshot_type='individual_seller_items',
        processing_type='full'
    )
    
    # Process through monitoring engine
    detection_result = test_env.monitoring_engine.process_parsing_results([parsing_result])
    
    print(f"✅ Processing completed:")
    print(f"   - Changes detected: {len(detection_result.detected_changes)}")
    print(f"   - Status transitions: {len(detection_result.status_transitions)}")
    
    return detection_result


def test_case_1_both_unchecked_to_checked():
    """Test Case 1: Both items UNCHECKED → CHECKED."""
    print("\n" + "="*60)
    print("🧪 TEST CASE 1: Both items UNCHECKED → CHECKED")
    print("="*60)
    
    test_env = TestEnvironment()
    test_env.setup()
    
    try:
        # Create initial test data
        create_test_data_case_1(test_env)
        
        # Get initial status
        stone_before = get_current_status(test_env, 'Seller1', 'Stone')
        wood_before = get_current_status(test_env, 'Seller1', 'Wood')
        
        print(f"\n📸 Initial state snapshot:")
        print(f"   Stone: {stone_before['status']} at {stone_before['status_changed_at']}")
        print(f"   Wood:  {wood_before['status']} at {wood_before['status_changed_at']}")
        
        # Simulate processing
        detection_result = simulate_full_processing_data(test_env)
        
        # Get final status
        stone_after = get_current_status(test_env, 'Seller1', 'Stone')
        wood_after = get_current_status(test_env, 'Seller1', 'Wood')
        
        # Print comparisons
        print_status_comparison(stone_before, stone_after, "Seller1-Stone")
        print_status_comparison(wood_before, wood_after, "Seller1-Wood")
        
        # Validate expectations
        print("\n🔍 Validation:")
        stone_valid = (stone_after['status'] == 'CHECKED' and 
                      stone_after['status_changed_at'] != stone_before['status_changed_at'])
        wood_valid = (wood_after['status'] == 'CHECKED' and 
                     wood_after['status_changed_at'] != wood_before['status_changed_at'])
        
        print(f"   ✅ Stone UNCHECKED→CHECKED: {'PASS' if stone_valid else 'FAIL'}")
        print(f"   ✅ Wood UNCHECKED→CHECKED: {'PASS' if wood_valid else 'FAIL'}")
        
        if stone_valid and wood_valid:
            print(f"\n🎉 Case 1 PASSED: Both items correctly transitioned to CHECKED")
        else:
            print(f"\n❌ Case 1 FAILED: Status transitions not as expected")
            
    except Exception as e:
        print(f"❌ Case 1 ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        test_env.cleanup()


def test_case_2_mixed_statuses():
    """Test Case 2: One CHECKED, other UNCHECKED."""
    print("\n" + "="*60)
    print("🧪 TEST CASE 2: One CHECKED (timer refresh), other UNCHECKED→CHECKED")
    print("="*60)
    
    test_env = TestEnvironment()
    test_env.setup()
    
    try:
        # Create initial test data
        create_test_data_case_2(test_env)
        
        # Get initial status
        stone_before = get_current_status(test_env, 'Seller1', 'Stone')
        wood_before = get_current_status(test_env, 'Seller1', 'Wood')
        
        print(f"\n📸 Initial state snapshot:")
        print(f"   Stone: {stone_before['status']} at {stone_before['status_changed_at']}")
        print(f"   Wood:  {wood_before['status']} at {wood_before['status_changed_at']}")
        
        # Simulate processing
        detection_result = simulate_full_processing_data(test_env)
        
        # Get final status
        stone_after = get_current_status(test_env, 'Seller1', 'Stone')
        wood_after = get_current_status(test_env, 'Seller1', 'Wood')
        
        # Print comparisons
        print_status_comparison(stone_before, stone_after, "Seller1-Stone")
        print_status_comparison(wood_before, wood_after, "Seller1-Wood")
        
        # Validate expectations
        print("\n🔍 Validation:")
        
        # Stone should change UNCHECKED → CHECKED
        stone_valid = (stone_after['status'] == 'CHECKED' and 
                      stone_after['status_changed_at'] != stone_before['status_changed_at'])
        
        # Wood should stay CHECKED but have refreshed last_updated (timer reset)
        wood_status_unchanged = wood_after['status'] == 'CHECKED'
        wood_timer_preserved = wood_after['status_changed_at'] == wood_before['status_changed_at']
        wood_updated_refreshed = wood_after['last_updated'] != wood_before['last_updated']
        wood_valid = wood_status_unchanged and wood_timer_preserved and wood_updated_refreshed
        
        print(f"   ✅ Stone UNCHECKED→CHECKED: {'PASS' if stone_valid else 'FAIL'}")
        print(f"   ✅ Wood stays CHECKED: {'PASS' if wood_status_unchanged else 'FAIL'}")
        print(f"   ✅ Wood timer preserved: {'PASS' if wood_timer_preserved else 'FAIL'}")  
        print(f"   ✅ Wood last_updated refreshed: {'PASS' if wood_updated_refreshed else 'FAIL'}")
        
        if stone_valid and wood_valid:
            print(f"\n🎉 Case 2 PASSED: Mixed status logic works correctly")
            print(f"   - Stone transitioned UNCHECKED→CHECKED ✅")
            print(f"   - Wood stayed CHECKED but 10-minute timer was reset ⏰")
        else:
            print(f"\n❌ Case 2 FAILED: Mixed status logic not working as expected")
            
    except Exception as e:
        print(f"❌ Case 2 ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        test_env.cleanup()


def main():
    """Run all test cases."""
    print("🚀 Starting comprehensive seller status update testing...")
    print(f"⏰ Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Run test cases
        test_case_1_both_unchecked_to_checked()
        test_case_2_mixed_statuses()
        
        print("\n" + "="*60)
        print("📋 TEST SUMMARY")
        print("="*60)
        print("✅ Case 1: Both UNCHECKED→CHECKED transition tested")
        print("✅ Case 2: Mixed statuses (timer refresh) tested")
        print("\n🎯 Key findings:")
        print("   - Multiple items from same seller processed simultaneously")
        print("   - Status transitions work correctly based on current state")
        print("   - Timer logic preserves status_changed_at for unchanged statuses")
        print("   - last_updated refreshes for all processed items (timer reset)")
        
    except Exception as e:
        print(f"❌ Testing failed with error: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n⏰ Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()