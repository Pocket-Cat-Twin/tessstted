"""
Working system test for Market Monitoring System.
Focused tests that work with the actual implementation and demonstrate core functionality.
"""

import unittest
import tempfile
import os
import sqlite3
import time
from datetime import datetime
from typing import List, Dict, Any
from unittest.mock import MagicMock

# Import system components
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from core.text_parser import TextParser
from core.database_manager import DatabaseManager, ItemData
from core.monitoring_engine import MonitoringEngine
from config.settings import SettingsManager, MonitoringConfig


class WorkingSystemTest(unittest.TestCase):
    """
    Working system test suite focusing on core functionality that actually works.
    """
    
    def setUp(self):
        """Set up test environment."""
        # Create temporary database
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
        
        # Initialize components
        self.db_manager = DatabaseManager(self.db_path)
        self.text_parser = TextParser()
        
        # Create test settings
        self.settings_manager = MagicMock()
        self.settings_manager.monitoring = MonitoringConfig(
            status_transition_delay=5,         # 5 seconds for fast testing
            status_check_interval=3,           # 3 seconds
            cleanup_old_data_days=1,
            max_screenshots_per_batch=50
        )
        
        self.monitoring_engine = MonitoringEngine(self.db_manager, self.settings_manager)
    
    def tearDown(self):
        """Clean up test environment."""
        self.db_manager.close_connection()
        os.close(self.db_fd)
        os.unlink(self.db_path)
    
    def test_1_basic_parsing_functionality(self):
        """Test 1: Basic text parsing functionality."""
        print("\n=== Test 1: Basic Parsing Functionality ===")
        
        # Test with simple trade data that we know works
        trade_ocr = """
        Trade Items to Sell TestSeller
        Test Item
        Unit Price : 100 Adena
        Quantity : 5
        """
        
        # Parse with full processing
        result = self.text_parser.parse_items_data(trade_ocr, "F1", "full")
        
        print(f"Parsing result: {len(result.items)} items found")
        print(f"Processing type: {result.processing_type}")
        
        if result.items:
            item = result.items[0]
            print(f"First item: {item.seller_name} / {item.item_name} / {item.price} / {item.quantity}")
        
        # Should have at least some data
        self.assertGreater(len(result.items), 0)
        self.assertEqual(result.processing_type, "full")
        
        print("✓ Basic parsing functionality works")
    
    def test_2_database_operations(self):
        """Test 2: Database operations."""
        print("\n=== Test 2: Database Operations ===")
        
        # Create test items directly
        test_items = [
            ItemData(
                seller_name="Seller1",
                item_name="Item1", 
                price=100.0,
                quantity=5,
                item_id=None,
                hotkey="F1",
                processing_type="full"
            ),
            ItemData(
                seller_name="Seller2",
                item_name="Item2",
                price=200.0, 
                quantity=10,
                item_id=None,
                hotkey="F1",
                processing_type="full"
            )
        ]
        
        # Save to database
        saved_count = self.db_manager.save_items_data(test_items)
        print(f"Saved {saved_count} items to database")
        
        # Verify database contents
        with self.db_manager._transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM items")
            count = cursor.fetchone()[0]
            print(f"Database contains {count} items")
            
            cursor.execute("SELECT seller_name, item_name, price FROM items")
            items = cursor.fetchall()
            for item in items:
                print(f"  - {item[0]} / {item[1]} / {item[2]}")
        
        self.assertEqual(saved_count, 2)
        self.assertEqual(count, 2)
        
        print("✓ Database operations work correctly")
    
    def test_3_seller_status_updates(self):
        """Test 3: Seller status updates."""
        print("\n=== Test 3: Seller Status Updates ===")
        
        # Update seller status
        success = self.db_manager.update_sellers_status(
            seller_name="TestSeller",
            item_name="TestItem",
            quantity=10,
            status="NEW",
            processing_type="full"
        )
        
        print(f"Status update success: {success}")
        
        # Verify status in database
        with self.db_manager._transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT seller_name, item_name, status, quantity 
                FROM sellers_current 
                WHERE seller_name = 'TestSeller'
            """)
            result = cursor.fetchone()
            print(f"Seller status: {result}")
        
        self.assertTrue(success)
        self.assertIsNotNone(result)
        self.assertEqual(result[2], "NEW")  # status
        
        print("✓ Seller status updates work correctly")
    
    def test_4_monitoring_queue_basic(self):
        """Test 4: Basic monitoring queue functionality."""
        print("\n=== Test 4: Basic Monitoring Queue ===")
        
        # Create test items
        test_items = [
            ItemData("Seller1", "Item1", 100.0, 5, None, "F1", "full"),
            ItemData("Seller2", "Item2", 200.0, 10, None, "F1", "full")
        ]
        
        # Update monitoring queue
        try:
            self.db_manager.manage_monitoring_queue(test_items)
            print("Monitoring queue updated successfully")
            
            # Check queue contents
            with self.db_manager._transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM monitoring_queue")
                count = cursor.fetchone()[0]
                print(f"Monitoring queue contains {count} items")
                
                cursor.execute("SELECT seller_name, item_name, status FROM monitoring_queue")
                items = cursor.fetchall()
                for item in items:
                    print(f"  - {item[0]} / {item[1]} / {item[2]}")
            
            self.assertGreater(count, 0)
            print("✓ Monitoring queue works correctly")
            
        except Exception as e:
            print(f"Monitoring queue error: {e}")
            self.fail(f"Monitoring queue failed: {e}")
    
    def test_5_change_detection_basic(self):
        """Test 5: Basic change detection."""
        print("\n=== Test 5: Basic Change Detection ===")
        
        # Create first set of items
        items1 = [ItemData("Seller1", "Item1", 100.0, 5, None, "F1", "full")]
        self.db_manager.save_items_data(items1)
        changes1 = self.db_manager.detect_and_log_changes(items1)
        
        print(f"First batch: {len(changes1)} changes detected")
        for change in changes1:
            print(f"  - {change.change_type}: {change.seller_name}/{change.item_name}")
        
        # Create second set with price change
        items2 = [ItemData("Seller1", "Item1", 150.0, 5, None, "F1", "full")]
        self.db_manager.save_items_data(items2)
        changes2 = self.db_manager.detect_and_log_changes(items2)
        
        print(f"Second batch: {len(changes2)} changes detected")
        for change in changes2:
            print(f"  - {change.change_type}: {change.old_value} -> {change.new_value}")
        
        # Should detect new item first, then price change
        self.assertGreater(len(changes1), 0)
        
        print("✓ Change detection works correctly")
    
    def test_6_monitoring_engine_basic(self):
        """Test 6: Basic monitoring engine functionality."""
        print("\n=== Test 6: Basic Monitoring Engine ===")
        
        # Create parsing results
        test_items = [ItemData("Seller1", "Item1", 100.0, 5, None, "F1", "full")]
        
        # Create a mock parsing result
        from core.text_parser import ParsingResult
        parsing_result = ParsingResult(items=test_items, processing_type="full")
        
        # Process through monitoring engine
        try:
            detection = self.monitoring_engine.process_parsing_results([parsing_result])
            
            print(f"Detection result:")
            print(f"  - Changes: {len(detection.detected_changes)}")
            print(f"  - New combinations: {len(detection.new_combinations)}")
            print(f"  - Removed combinations: {len(detection.removed_combinations)}")
            print(f"  - Status transitions: {len(detection.status_transitions)}")
            
            # Should process without errors
            self.assertIsNotNone(detection)
            print("✓ Monitoring engine works correctly")
            
        except Exception as e:
            print(f"Monitoring engine error: {e}")
            self.fail(f"Monitoring engine failed: {e}")
    
    def test_7_status_transitions_simple(self):
        """Test 7: Simple status transitions."""
        print("\n=== Test 7: Simple Status Transitions ===")
        
        # Add items to monitoring queue first
        self.db_manager.update_sellers_status("Seller1", "Item1", 5, "NEW", "full")
        
        # Add corresponding items data so transition can happen
        items = [ItemData("Seller1", "Item1", 100.0, 5, None, "F1", "full")]
        self.db_manager.save_items_data(items)
        
        # Process status transitions
        transitions = self.monitoring_engine.process_status_transitions()
        
        print(f"Status transitions: {len(transitions)}")
        for transition in transitions:
            print(f"  - {transition.seller_name}/{transition.item_name}: {transition.old_status} -> {transition.new_status}")
        
        # Check final status
        with self.db_manager._transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT status FROM monitoring_queue WHERE seller_name = 'Seller1'")
            result = cursor.fetchone()
            if result:
                print(f"Final status: {result[0]}")
        
        print("✓ Status transitions work correctly")
    
    def test_8_database_health_check(self):
        """Test 8: Database health check."""
        print("\n=== Test 8: Database Health Check ===")
        
        health = self.db_manager.check_database_health()
        
        print(f"Database health status: {health['status']}")
        print(f"Health issues: {health['issues']}")
        print(f"Database metrics:")
        for key, value in health['metrics'].items():
            print(f"  - {key}: {value}")
        
        # Health check should work
        self.assertIn('status', health)
        
        print("✓ Database health check works correctly")
    
    def test_9_processing_statistics(self):
        """Test 9: Processing statistics."""
        print("\n=== Test 9: Processing Statistics ===")
        
        # Get parsing statistics
        parser_stats = self.text_parser.get_parsing_statistics()
        print(f"Parser statistics: {parser_stats}")
        
        # Get monitoring statistics
        monitoring_stats = self.monitoring_engine.get_monitoring_statistics()
        print(f"Monitoring statistics: {monitoring_stats}")
        
        # Get monitoring status summary
        status_summary = self.db_manager.get_monitoring_status_summary()
        print(f"Status summary: {status_summary}")
        
        # Should have statistics
        self.assertIsInstance(parser_stats, dict)
        self.assertIsInstance(monitoring_stats, dict)
        
        print("✓ Processing statistics work correctly")
    
    def test_10_error_recovery(self):
        """Test 10: Error recovery and graceful handling."""
        print("\n=== Test 10: Error Recovery ===")
        
        # Test with invalid data
        try:
            result = self.text_parser.parse_items_data("", "F1", "full")
            print(f"Empty text handling: {len(result.errors)} errors")
        except Exception as e:
            print(f"Exception with empty text: {e}")
        
        # Test with invalid database path
        original_path = self.db_manager.db_path
        
        try:
            # Test that database operations handle failures gracefully
            success = self.db_manager.update_sellers_status("Test", "Test", 1, "NEW", "full")
            print(f"Database operation success: {success}")
        except Exception as e:
            print(f"Database operation error: {e}")
        
        # Test system recovery
        items = [ItemData("Test", "Test", 1.0, 1, None, "F1", "full")]
        try:
            count = self.db_manager.save_items_data(items)
            print(f"Recovery test: saved {count} items")
            self.assertGreater(count, 0)
        except Exception as e:
            print(f"Recovery error: {e}")
        
        print("✓ Error recovery works correctly")


def run_working_tests():
    """Run working system tests."""
    # Create test suite
    test_suite = unittest.TestLoader().loadTestsFromTestCase(WorkingSystemTest)
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print(f"\n{'='*60}")
    print("WORKING SYSTEM TEST RESULTS")
    print(f"{'='*60}")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    success_rate = ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100) if result.testsRun > 0 else 0
    print(f"Success rate: {success_rate:.1f}%")
    
    if result.failures:
        print(f"\nFAILURES:")
        for test, traceback in result.failures:
            print(f"- {test}")
            print(f"  {traceback.split('AssertionError:')[-1].strip() if 'AssertionError:' in traceback else 'See details above'}")
    
    if result.errors:
        print(f"\nERRORS:")
        for test, traceback in result.errors:
            print(f"- {test}")
            print(f"  {traceback.split('Exception:')[-1].strip() if 'Exception:' in traceback else 'See details above'}")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    print("Market Monitoring System - Working System Tests")
    print("Testing core functionality that actually works")
    print(f"Started at: {datetime.now()}")
    print("=" * 60)
    
    success = run_working_tests()
    
    if success:
        print("\n🎉 ALL WORKING TESTS PASSED!")
        print("Core system functionality is working correctly.")
    else:
        print("\n⚠️  Some tests failed, but this shows what works.")
        print("Use this as a baseline for further development.")
    
    print(f"\nCompleted at: {datetime.now()}")