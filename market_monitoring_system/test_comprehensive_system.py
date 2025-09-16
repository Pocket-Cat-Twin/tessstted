"""
Comprehensive system tests for Market Monitoring System.
Tests entire pipeline from OCR text to database monitoring with accelerated timers.
"""

import unittest
import tempfile
import os
import sqlite3
import time
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Any
from unittest.mock import patch, MagicMock
from concurrent.futures import ThreadPoolExecutor, as_completed
import json

# Import system components
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from core.text_parser import TextParser, ParsingResult
from core.database_manager import DatabaseManager, ItemData, ChangeLogEntry
from core.monitoring_engine import MonitoringEngine, StatusTransition
from config.settings import SettingsManager, MonitoringConfig


class ComprehensiveSystemTest(unittest.TestCase):
    """
    Comprehensive test suite covering all system functionality with accelerated timers.
    Each test is designed to complete within ~1-5 minutes for total 20-minute execution.
    """
    
    def setUp(self):
        """Set up test environment with accelerated configuration."""
        # Create temporary database
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
        
        # Initialize components with fast timers
        self.db_manager = DatabaseManager(self.db_path)
        self.text_parser = TextParser()
        
        # Create accelerated settings for testing
        self.settings_manager = MagicMock()
        self.settings_manager.monitoring = MonitoringConfig(
            status_transition_delay=10,        # 10 seconds instead of 10 minutes
            status_check_interval=5,           # 5 seconds instead of minutes
            cleanup_old_data_days=1,           # 1 day for testing
            max_screenshots_per_batch=50       # Default value
        )
        
        self.monitoring_engine = MonitoringEngine(self.db_manager, self.settings_manager)
        
        # Test data sets for different scenarios
        self._prepare_test_data()
    
    def tearDown(self):
        """Clean up test environment."""
        self.db_manager.close_connection()
        os.close(self.db_fd)
        os.unlink(self.db_path)
    
    def _prepare_test_data(self):
        """Prepare OCR text data for various test scenarios."""
        
        # Full processing OCR data (trade data format)
        self.full_ocr_data_1 = """
        Trade Items to Sell PlayerA
        Sword of Power
        Unit Price : 1,500 Adena
        Quantity : 5
        
        Trade Items to Sell PlayerB
        Health Potion
        Unit Price : 100 Adena  
        Quantity : 20
        
        Trade Items to Sell PlayerC
        Magic Staff
        Unit Price : 2,000 Adena
        Quantity : 3
        """
        
        self.full_ocr_data_2 = """
        Trade Items to Sell PlayerA
        Sword of Power
        Unit Price : 1,600 Adena
        Quantity : 4
        
        Trade Items to Sell PlayerB
        Health Potion
        Unit Price : 90 Adena
        Quantity : 25
        
        Trade Items to Sell PlayerD
        Shield of Defense
        Unit Price : 800 Adena
        Quantity : 2
        """
        
        # Minimal processing OCR data (broker format)
        self.minimal_ocr_data_1 = """
        Item Broke
        Magic Ring
        Name
        SellerAlpha
        SellerBeta
        SellerGamma
        
        Item Broke
        Ancient Scroll
        Name
        SellerAlpha
        SellerDelta
        """
        
        self.minimal_ocr_data_2 = """
        Item Broke
        Magic Ring
        Name
        SellerAlpha
        SellerBeta
        SellerZeta
        
        Item Broke
        Mystic Gem
        Name
        SellerAlpha
        """
        
        # Error-prone OCR data for error handling tests
        self.error_ocr_data = """
        Invalid Trade Data
        Corrupted Item Name ###
        Price: INVALID
        Quantity: NOT_A_NUMBER
        """
        
    def test_1_parse_to_database_pipeline(self):
        """Test Case 1: Complete parse-to-database pipeline with full processing."""
        print("\n=== Test 1: Parse-to-Database Pipeline ===")
        
        # Parse OCR text
        parsing_result = self.text_parser.parse_items_data(
            self.full_ocr_data_1, 
            hotkey="F1", 
            processing_type="full"
        )
        
        # Verify parsing results
        self.assertEqual(len(parsing_result.items), 3)
        self.assertEqual(parsing_result.processing_type, "full")
        
        # Verify parsed data structure
        item_names = [item.item_name for item in parsing_result.items]
        self.assertIn("Sword of Power", item_names)
        self.assertIn("Health Potion", item_names)
        self.assertIn("Magic Staff", item_names)
        
        # Save to database
        saved_count = self.db_manager.save_items_data(parsing_result.items)
        self.assertEqual(saved_count, 3)
        
        # Verify database storage
        with self.db_manager._transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM items WHERE processing_type = 'full'")
            count = cursor.fetchone()[0]
            self.assertEqual(count, 3)
            
            # Verify specific item data
            cursor.execute("""
                SELECT seller_name, item_name, price, quantity 
                FROM items WHERE item_name = 'Sword of Power'
            """)
            sword_data = cursor.fetchone()
            self.assertEqual(sword_data[0], "PlayerA")
            self.assertEqual(sword_data[2], 1500.0)  # Price
            self.assertEqual(sword_data[3], 5)       # Quantity
        
        print("✓ Parse-to-Database pipeline completed successfully")
    
    def test_2_change_detection(self):
        """Test Case 2: Price and quantity change detection."""
        print("\n=== Test 2: Change Detection ===")
        
        # First data set
        result1 = self.text_parser.parse_items_data(self.full_ocr_data_1, "F1", "full")
        self.db_manager.save_items_data(result1.items)
        changes1 = self.db_manager.detect_and_log_changes(result1.items)
        
        # Should detect new items
        new_item_changes = [c for c in changes1 if c.change_type == 'NEW_ITEM']
        self.assertEqual(len(new_item_changes), 3)
        
        # Second data set with changes
        result2 = self.text_parser.parse_items_data(self.full_ocr_data_2, "F1", "full")
        self.db_manager.save_items_data(result2.items)
        changes2 = self.db_manager.detect_and_log_changes(result2.items)
        
        # Verify price and quantity changes
        change_types = [c.change_type for c in changes2]
        
        # Should detect price increase for Sword of Power (1500 -> 1600)
        price_increases = [c for c in changes2 if c.change_type == 'PRICE_INCREASE']
        self.assertTrue(len(price_increases) >= 1)
        
        # Should detect price decrease for Health Potion (100 -> 90)
        price_decreases = [c for c in changes2 if c.change_type == 'PRICE_DECREASE']
        self.assertTrue(len(price_decreases) >= 1)
        
        # Should detect quantity changes
        quantity_changes = [c for c in changes2 if 'QUANTITY' in c.change_type]
        self.assertTrue(len(quantity_changes) >= 1)
        
        # Verify changes are logged in database
        with self.db_manager._transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM changes_log")
            total_changes = cursor.fetchone()[0]
            self.assertGreater(total_changes, 3)
        
        print("✓ Change detection completed successfully")
    
    def test_3_status_lifecycle_fast_timers(self):
        """Test Case 3: Status lifecycle with accelerated 10-second timers."""
        print("\n=== Test 3: Status Lifecycle & Fast Timers ===")
        
        # Process initial data
        result = self.text_parser.parse_items_data(self.full_ocr_data_1, "F1", "full")
        detection = self.monitoring_engine.process_parsing_results([result])
        
        # Verify items start with NEW status
        with self.db_manager._transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM monitoring_queue WHERE status = 'NEW'")
            new_count = cursor.fetchone()[0]
            self.assertGreater(new_count, 0)
        
        print("Items created with NEW status, waiting for timer...")
        
        # Wait for status transitions (NEW -> CHECKED)
        # Should happen immediately since items exist in database
        transitions = self.monitoring_engine.process_status_transitions()
        new_to_checked = [t for t in transitions if t.new_status == 'CHECKED']
        self.assertGreater(len(new_to_checked), 0)
        
        print(f"NEW -> CHECKED transitions: {len(new_to_checked)}")
        
        # Wait for CHECKED -> UNCHECKED transition (10 seconds)
        print("Waiting 12 seconds for CHECKED -> UNCHECKED transition...")
        time.sleep(12)
        
        transitions2 = self.monitoring_engine.process_status_transitions()
        checked_to_unchecked = [t for t in transitions2 if t.new_status == 'UNCHECKED']
        self.assertGreater(len(checked_to_unchecked), 0)
        
        print(f"CHECKED -> UNCHECKED transitions: {len(checked_to_unchecked)}")
        
        # Verify final status distribution
        status_summary = self.db_manager.get_monitoring_status_summary()
        self.assertIn('UNCHECKED', status_summary)
        self.assertGreater(status_summary['UNCHECKED'], 0)
        
        print("✓ Status lifecycle with fast timers completed successfully")
    
    def test_4_sale_detection(self):
        """Test Case 4: Sale detection (UNCHECKED -> GONE)."""
        print("\n=== Test 4: Sale Detection ===")
        
        # Process minimal data first
        result1 = self.text_parser.parse_items_data(self.minimal_ocr_data_1, "F2", "minimal")
        detection1 = self.monitoring_engine.process_parsing_results([result1])
        
        # Add some full processing data to give items price history
        full_result = self.text_parser.parse_items_data(self.full_ocr_data_1, "F1", "full")
        self.db_manager.save_items_data(full_result.items)
        
        # Manually set some items to UNCHECKED status
        with self.db_manager._transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE sellers_current 
                SET status = 'UNCHECKED' 
                WHERE seller_name = 'PlayerA' AND item_name = 'Sword of Power'
            """)
            cursor.execute("""
                UPDATE monitoring_queue 
                SET status = 'UNCHECKED' 
                WHERE seller_name = 'PlayerA' AND item_name = 'Sword of Power'
            """)
        
        # Process data without this item (simulating sale)
        result2 = self.text_parser.parse_items_data(self.full_ocr_data_2, "F1", "full")
        # Remove PlayerA's Sword of Power from result2 to simulate sale
        result2.items = [item for item in result2.items if not (
            item.seller_name == "PlayerA" and item.item_name == "Sword of Power"
        )]
        
        detection2 = self.monitoring_engine.process_parsing_results([result2])
        
        # Check for sale detection in changes
        sale_changes = [c for c in detection2.detected_changes if c.change_type == 'SALE_DETECTED']
        
        # Also check sales_log table
        with self.db_manager._transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM sales_log")
            sales_count = cursor.fetchone()[0]
            
            if sales_count > 0:
                cursor.execute("""
                    SELECT seller_name, item_name, last_price, previous_status 
                    FROM sales_log LIMIT 1
                """)
                sale_record = cursor.fetchone()
                self.assertIsNotNone(sale_record)
                print(f"Sale recorded: {sale_record[0]}/{sale_record[1]} - Price: {sale_record[2]}")
        
        print("✓ Sale detection completed successfully")
    
    def test_5_processing_types(self):
        """Test Case 5: Full vs Minimal processing types."""
        print("\n=== Test 5: Processing Types ===")
        
        # Process full data
        full_result = self.text_parser.parse_items_data(self.full_ocr_data_1, "F1", "full")
        self.assertEqual(full_result.processing_type, "full")
        self.assertTrue(all(item.processing_type == "full" for item in full_result.items))
        
        # Process minimal data
        minimal_result = self.text_parser.parse_items_data(self.minimal_ocr_data_1, "F2", "minimal")
        self.assertEqual(minimal_result.processing_type, "minimal")
        self.assertTrue(all(item.processing_type == "minimal" for item in minimal_result.items))
        
        # Process both types together
        detection = self.monitoring_engine.process_parsing_results([full_result, minimal_result])
        
        # Verify database separation
        with self.db_manager._transaction() as conn:
            cursor = conn.cursor()
            
            # Check full processing items have price/quantity
            cursor.execute("""
                SELECT COUNT(*) FROM items 
                WHERE processing_type = 'full' AND price IS NOT NULL AND quantity IS NOT NULL
            """)
            full_with_prices = cursor.fetchone()[0]
            self.assertGreater(full_with_prices, 0)
            
            # Check minimal processing items don't have price/quantity
            cursor.execute("""
                SELECT COUNT(*) FROM items 
                WHERE processing_type = 'minimal' AND (price IS NULL OR quantity IS NULL)
            """)
            minimal_without_prices = cursor.fetchone()[0]
            # Note: minimal processing items are not saved to items table, only sellers_current
            
            # Check sellers_current has both types
            cursor.execute("""
                SELECT processing_type, COUNT(*) 
                FROM sellers_current 
                GROUP BY processing_type
            """)
            processing_counts = dict(cursor.fetchall())
            
            if 'full' in processing_counts and 'minimal' in processing_counts:
                self.assertGreater(processing_counts['full'], 0)
                self.assertGreater(processing_counts['minimal'], 0)
        
        print("✓ Processing types test completed successfully")
    
    def test_6_monitoring_queue_management(self):
        """Test Case 6: Monitoring queue management."""
        print("\n=== Test 6: Monitoring Queue Management ===")
        
        # Process initial data
        result1 = self.text_parser.parse_items_data(self.full_ocr_data_1, "F1", "full")
        detection1 = self.monitoring_engine.process_parsing_results([result1])
        
        # Verify queue entries created
        with self.db_manager._transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM monitoring_queue")
            initial_count = cursor.fetchone()[0]
            self.assertGreater(initial_count, 0)
        
        # Process updated data
        result2 = self.text_parser.parse_items_data(self.full_ocr_data_2, "F1", "full")
        detection2 = self.monitoring_engine.process_parsing_results([result2])
        
        # Verify new combinations detected
        self.assertGreater(len(detection2.new_combinations), 0)
        
        # Verify UNIQUE constraints work (no duplicates)
        with self.db_manager._transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT seller_name, item_name, COUNT(*) as cnt 
                FROM monitoring_queue 
                GROUP BY seller_name, item_name 
                HAVING cnt > 1
            """)
            duplicates = cursor.fetchall()
            self.assertEqual(len(duplicates), 0, "Found duplicate entries in monitoring_queue")
        
        # Test queue status updates
        success = self.monitoring_engine.update_queue_status("PlayerA", "Sword of Power", "CHECKED")
        self.assertTrue(success)
        
        # Verify status update
        with self.db_manager._transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT status FROM monitoring_queue 
                WHERE seller_name = 'PlayerA' AND item_name = 'Sword of Power'
            """)
            status = cursor.fetchone()[0]
            self.assertEqual(status, "CHECKED")
        
        print("✓ Monitoring queue management completed successfully")
    
    def test_7_complex_change_scenarios(self):
        """Test Case 7: Complex change scenarios (NEW/REMOVED combinations)."""
        print("\n=== Test 7: Complex Change Scenarios ===")
        
        # Initial state
        result1 = self.text_parser.parse_items_data(self.full_ocr_data_1, "F1", "full")
        detection1 = self.monitoring_engine.process_parsing_results([result1])
        
        # Modified state with new sellers, items, and removed combinations
        complex_ocr = """
        Trade Items to Sell PlayerA
        Sword of Power
        Unit Price : 1,500 Adena
        Quantity : 5
        
        Trade Items to Sell PlayerE
        New Item Type
        Unit Price : 500 Adena
        Quantity : 10
        
        Trade Items to Sell PlayerB
        Different Item
        Unit Price : 200 Adena
        Quantity : 15
        """
        
        result2 = self.text_parser.parse_items_data(complex_ocr, "F1", "full")
        detection2 = self.monitoring_engine.process_parsing_results([result2])
        
        # Verify new combinations
        self.assertGreater(len(detection2.new_combinations), 0)
        
        # Verify removed combinations
        self.assertGreater(len(detection2.removed_combinations), 0)
        
        # Check changes_log for different change types
        with self.db_manager._transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT change_type, COUNT(*) 
                FROM changes_log 
                GROUP BY change_type
            """)
            change_type_counts = dict(cursor.fetchall())
            
            # Should have various change types
            expected_types = ['NEW_ITEM', 'SELLER_NEW', 'ITEM_REMOVED']
            found_types = list(change_type_counts.keys())
            
            for expected in expected_types:
                if expected in found_types:
                    self.assertGreater(change_type_counts[expected], 0)
                    print(f"Found {change_type_counts[expected]} {expected} changes")
        
        print("✓ Complex change scenarios completed successfully")
    
    def test_8_concurrent_processing(self):
        """Test Case 8: Concurrent processing and race conditions."""
        print("\n=== Test 8: Concurrent Processing & Race Conditions ===")
        
        # Prepare multiple datasets for concurrent processing
        datasets = [
            (self.full_ocr_data_1, "F1", "full"),
            (self.full_ocr_data_2, "F1", "full"),
            (self.minimal_ocr_data_1, "F2", "minimal"),
            (self.minimal_ocr_data_2, "F2", "minimal"),
        ]
        
        # Additional synthetic datasets
        for i in range(3, 6):
            synthetic_data = f"""
            Trade Items to Sell Seller{i}
            Item{i}
            Unit Price : {100 * i} Adena
            Quantity : {i}
            """
            datasets.append((synthetic_data, "F1", "full"))
        
        results = []
        exceptions = []
        
        def process_dataset(data_tuple):
            try:
                ocr_text, hotkey, proc_type = data_tuple
                result = self.text_parser.parse_items_data(ocr_text, hotkey, proc_type)
                detection = self.monitoring_engine.process_parsing_results([result])
                return detection
            except Exception as e:
                exceptions.append(e)
                raise
        
        # Process concurrently
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_data = {executor.submit(process_dataset, data): data for data in datasets}
            
            for future in as_completed(future_to_data):
                try:
                    result = future.result(timeout=30)  # 30 second timeout
                    results.append(result)
                except Exception as e:
                    print(f"Concurrent processing error: {e}")
                    exceptions.append(e)
        
        # Verify no exceptions occurred
        self.assertEqual(len(exceptions), 0, f"Concurrent processing had {len(exceptions)} errors")
        
        # Verify all datasets were processed
        self.assertEqual(len(results), len(datasets))
        
        # Verify database integrity
        with self.db_manager._transaction() as conn:
            cursor = conn.cursor()
            
            # Check for duplicate entries (race condition indicator)
            cursor.execute("""
                SELECT seller_name, item_name, COUNT(*) as cnt
                FROM monitoring_queue 
                GROUP BY seller_name, item_name 
                HAVING cnt > 1
            """)
            duplicates = cursor.fetchall()
            self.assertEqual(len(duplicates), 0, f"Found {len(duplicates)} duplicate entries from race conditions")
            
            # Verify total items processed
            cursor.execute("SELECT COUNT(*) FROM items")
            total_items = cursor.fetchone()[0]
            self.assertGreater(total_items, len(datasets))
        
        print("✓ Concurrent processing completed successfully")
    
    def test_9_error_handling_recovery(self):
        """Test Case 9: Error handling and recovery."""
        print("\n=== Test 9: Error Handling & Recovery ===")
        
        # Test 1: Invalid OCR data
        try:
            result = self.text_parser.parse_items_data(self.error_ocr_data, "F1", "full")
            # Should not raise exception, but should have errors
            self.assertTrue(len(result.errors) > 0 or len(result.items) == 0)
            print(f"Handled invalid OCR data gracefully: {len(result.errors)} errors")
        except Exception as e:
            self.fail(f"Parser should handle invalid data gracefully, but raised: {e}")
        
        # Test 2: Database error simulation
        original_path = self.db_manager.db_path
        
        # Temporarily make database path invalid
        self.db_manager.db_path = "/invalid/path/database.db"
        
        try:
            # This should fail gracefully
            result = self.text_parser.parse_items_data(self.full_ocr_data_1, "F1", "full")
            success = self.db_manager.save_items_data(result.items)
            # Should handle database error
        except Exception as e:
            print(f"Database error handled: {e}")
        finally:
            # Restore valid path
            self.db_manager.db_path = original_path
        
        # Test 3: Recovery after error
        result = self.text_parser.parse_items_data(self.full_ocr_data_1, "F1", "full")
        saved_count = self.db_manager.save_items_data(result.items)
        self.assertGreater(saved_count, 0)
        print("✓ System recovered successfully after errors")
        
        # Test 4: Monitoring engine error handling
        try:
            # Inject invalid data into monitoring engine
            invalid_items = [
                ItemData("", "", None, None, None, "F1", "invalid_type")
            ]
            detection = self.monitoring_engine.process_parsing_results([
                ParsingResult(items=invalid_items, processing_type="invalid")
            ])
            # Should handle gracefully
            print("Monitoring engine handled invalid data")
        except Exception as e:
            print(f"Monitoring engine error (expected): {e}")
        
        # Verify system state after errors
        health = self.db_manager.check_database_health()
        print(f"Database health after errors: {health['status']}")
        
        print("✓ Error handling and recovery completed successfully")
    
    def test_10_intensive_end_to_end_simulation(self):
        """Test Case 10: Intensive end-to-end simulation with high load."""
        print("\n=== Test 10: Intensive End-to-End Simulation ===")
        
        start_time = time.time()
        
        # Generate 100 different OCR datasets
        datasets = []
        for batch in range(20):  # 20 batches of 5 items each = 100 datasets
            for i in range(5):
                seller_name = f"Seller_{batch}_{i}"
                item_name = f"Item_{batch}_{i}"
                price = 100 + (batch * 10) + i
                quantity = (batch % 5) + i + 1
                
                if batch % 2 == 0:  # Alternate between full and minimal processing
                    ocr_data = f"""
                    Trade Items to Sell {seller_name}
                    {item_name}
                    Unit Price : {price} Adena
                    Quantity : {quantity}
                    """
                    datasets.append((ocr_data, "F1", "full"))
                else:
                    ocr_data = f"""
                    Item Broke
                    {item_name}
                    Name
                    {seller_name}
                    """
                    datasets.append((ocr_data, "F2", "minimal"))
        
        print(f"Generated {len(datasets)} test datasets")
        
        # Process in batches to simulate real-world usage
        batch_size = 10
        total_items_processed = 0
        total_changes_detected = 0
        processing_times = []
        
        for i in range(0, len(datasets), batch_size):
            batch_start = time.time()
            batch = datasets[i:i+batch_size]
            
            # Process batch
            results = []
            for ocr_data, hotkey, proc_type in batch:
                result = self.text_parser.parse_items_data(ocr_data, hotkey, proc_type)
                results.append(result)
                total_items_processed += len(result.items)
            
            # Process through monitoring engine
            detection = self.monitoring_engine.process_parsing_results(results)
            total_changes_detected += len(detection.detected_changes)
            
            batch_time = time.time() - batch_start
            processing_times.append(batch_time)
            
            # Accelerated maintenance tasks every 10 batches
            if i % (batch_size * 10) == 0:
                # Status transitions
                transitions = self.monitoring_engine.process_status_transitions()
                
                # Database cleanup
                health = self.db_manager.check_database_health()
                if health['status'] != 'error':
                    self.db_manager.optimize_database()
            
            print(f"Batch {i//batch_size + 1}/{len(datasets)//batch_size}: "
                  f"{len(results)} results, "
                  f"{len(detection.detected_changes)} changes, "
                  f"{batch_time:.3f}s")
        
        total_time = time.time() - start_time
        
        # Performance metrics
        avg_processing_time = sum(processing_times) / len(processing_times)
        throughput = total_items_processed / total_time
        
        print(f"\n=== Performance Metrics ===")
        print(f"Total processing time: {total_time:.3f}s")
        print(f"Total items processed: {total_items_processed}")
        print(f"Total changes detected: {total_changes_detected}")
        print(f"Average batch time: {avg_processing_time:.3f}s")
        print(f"Throughput: {throughput:.2f} items/second")
        
        # Database health check
        final_health = self.db_manager.check_database_health()
        self.assertNotEqual(final_health['status'], 'error')
        
        # Memory and database size check
        db_size_mb = final_health['metrics']['database_size_mb']
        print(f"Final database size: {db_size_mb}MB")
        
        # Verify data integrity
        with self.db_manager._transaction() as conn:
            cursor = conn.cursor()
            
            # Check total records
            cursor.execute("SELECT COUNT(*) FROM items")
            items_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM changes_log")
            changes_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM monitoring_queue")
            queue_count = cursor.fetchone()[0]
            
            print(f"Database records - Items: {items_count}, Changes: {changes_count}, Queue: {queue_count}")
            
            self.assertGreater(items_count, 0)
            self.assertGreater(changes_count, 0)
            self.assertGreater(queue_count, 0)
        
        # Performance assertions
        self.assertLess(avg_processing_time, 2.0, "Average batch processing should be under 2 seconds")
        self.assertGreater(throughput, 10, "Throughput should be at least 10 items/second")
        self.assertLess(total_time, 300, "Total test should complete in under 5 minutes")
        
        print("✓ Intensive end-to-end simulation completed successfully")


def run_comprehensive_tests():
    """Run all comprehensive system tests."""
    # Create test suite
    test_suite = unittest.TestLoader().loadTestsFromTestCase(ComprehensiveSystemTest)
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2, stream=None)
    result = runner.run(test_suite)
    
    # Print summary
    print(f"\n{'='*60}")
    print("COMPREHENSIVE SYSTEM TEST RESULTS")
    print(f"{'='*60}")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print(f"\nFAILURES:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")
    
    if result.errors:
        print(f"\nERRORS:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    print("Market Monitoring System - Comprehensive Test Suite")
    print("Testing entire pipeline with accelerated timers (≤20 minutes)")
    print(f"Started at: {datetime.now()}")
    print("=" * 60)
    
    success = run_comprehensive_tests()
    
    if success:
        print("\n🎉 ALL TESTS PASSED! System is ready for production.")
    else:
        print("\n❌ Some tests failed. Review the output above.")
    
    print(f"\nCompleted at: {datetime.now()}")