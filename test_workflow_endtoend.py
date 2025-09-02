#!/usr/bin/env python3
"""
End-to-End Workflow Test
Test complete trading data processing pipeline
"""

import sys
import time
import json
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from game_monitor.database_manager import get_database
from game_monitor.fast_validator import get_validator, ValidationLevel
from game_monitor.hotkey_manager import get_hotkey_manager, HotkeyType, CaptureEvent

def test_complete_workflow():
    """Test complete end-to-end workflow simulation"""
    print("="*60)
    print("END-TO-END WORKFLOW TEST")
    print("Game Monitor Trading Data Pipeline")
    print("="*60)
    
    workflow_results = {
        'total_processing_time': 0,
        'records_processed': 0,
        'records_valid': 0,
        'records_stored': 0,
        'errors': [],
        'warnings': []
    }
    
    try:
        # Initialize all components
        print("1. Initializing system components...")
        init_start = time.time()
        
        db = get_database()
        validator = get_validator()
        hotkey_manager = get_hotkey_manager()
        
        init_time = time.time() - init_start
        print(f"   ✅ All components initialized in {init_time:.3f}s")
        
        # Simulated raw OCR data (as if captured from screen)
        simulated_captures = [
            {
                'source': 'trader_list',
                'raw_ocr_data': [
                    'DragonSlayer88',
                    'MasterTrader', 
                    'ItemCollector',
                    'BulkSeller'
                ]
            },
            {
                'source': 'item_scan', 
                'raw_ocr_data': [
                    'Меч огня',
                    '15',
                    '1250.50',
                    '18757.50'
                ]
            },
            {
                'source': 'trader_inventory',
                'raw_ocr_data': [
                    'DragonSlayer88',
                    'Меч огня',
                    '15',
                    '1250.50',
                    '18757.50'
                ]
            }
        ]
        
        # Process workflow steps
        processed_trades = []
        
        print("\n2. Processing captured data...")
        
        for i, capture in enumerate(simulated_captures):
            step_start = time.time()
            
            print(f"   📸 Processing capture {i+1}: {capture['source']}")
            
            # Step A: Parse raw data into structured format
            if capture['source'] == 'trader_inventory':
                # Complete trade record
                raw_data = capture['raw_ocr_data']
                if len(raw_data) >= 5:
                    structured_data = {
                        'trader_nickname': raw_data[0],
                        'item_name': raw_data[1],
                        'quantity': raw_data[2],
                        'price_per_unit': raw_data[3],
                        'total_price': raw_data[4]
                    }
                    
                    print(f"      📋 Structured data: {structured_data}")
                    
                    # Step B: Validate the data
                    validation_start = time.time()
                    validation_result = validator.validate_trade_data(
                        structured_data, 
                        level=ValidationLevel.BALANCED
                    )
                    validation_time = time.time() - validation_start
                    
                    workflow_results['records_processed'] += 1
                    
                    if validation_result.is_valid:
                        workflow_results['records_valid'] += 1
                        print(f"      ✅ Validation passed ({validation_result.confidence:.2f}) [{validation_time:.4f}s]")
                        
                        # Step C: Store in database
                        db_start = time.time()
                        trade_data = [{
                            'trader_nickname': structured_data['trader_nickname'],
                            'item_name': structured_data['item_name'],
                            'quantity': int(float(structured_data['quantity'])),
                            'price_per_unit': float(structured_data['price_per_unit']),
                            'total_price': float(structured_data['total_price'])
                        }]
                        
                        trade_ids = db.update_inventory_and_track_trades(trade_data)
                        db_time = time.time() - db_start
                        
                        workflow_results['records_stored'] += 1
                        processed_trades.append({
                            'data': structured_data,
                            'validation_time': validation_time,
                            'db_time': db_time,
                            'confidence': validation_result.confidence
                        })
                        
                        print(f"      💾 Stored in database [{db_time:.4f}s]")
                        
                    else:
                        print(f"      ❌ Validation failed ({validation_result.confidence:.2f})")
                        if validation_result.errors:
                            for error in validation_result.errors[:2]:
                                print(f"         Error: {error}")
                        workflow_results['errors'].extend(validation_result.errors)
                        workflow_results['warnings'].extend(validation_result.warnings)
                
            else:
                print(f"      📝 Partial data: {capture['raw_ocr_data']} (waiting for complete record)")
            
            step_time = time.time() - step_start
            workflow_results['total_processing_time'] += step_time
            print(f"      ⏱️  Step completed in {step_time:.4f}s")
        
        # Step 3: Hotkey simulation (demonstrate responsiveness)
        print("\n3. Testing hotkey responsiveness during processing...")
        
        callback_results = []
        def workflow_callback(event: CaptureEvent):
            callback_results.append({
                'hotkey': event.hotkey_type.value,
                'timestamp': event.timestamp,
                'processing_time': 0.001  # Simulated
            })
        
        # Register callbacks
        for hotkey_type in [HotkeyType.TRADER_LIST, HotkeyType.ITEM_SCAN, HotkeyType.TRADER_INVENTORY]:
            hotkey_manager.register_callback(hotkey_type, workflow_callback)
        
        hotkey_manager.start()
        
        # Trigger hotkeys while "processing"
        hotkey_start = time.time()
        hotkey_manager.trigger_trader_list_capture()
        time.sleep(0.01)
        hotkey_manager.trigger_item_scan_capture() 
        time.sleep(0.01)
        hotkey_manager.trigger_trader_inventory_capture()
        
        time.sleep(0.1)  # Wait for callbacks
        hotkey_time = time.time() - hotkey_start
        
        hotkey_manager.stop()
        
        print(f"   🔥 Hotkey system responded to {len(callback_results)} triggers in {hotkey_time:.4f}s")
        
        # Step 4: Database verification 
        print("\n4. Database verification...")
        
        verification_start = time.time()
        
        # Check inventory
        inventory = db.get_current_inventory_for_item('Меч огня')
        
        # Get statistics
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM current_inventory WHERE trader_nickname = ?", ('DragonSlayer88',))
            trader_records = cursor.fetchone()[0]
        
        verification_time = time.time() - verification_start
        
        print(f"   📊 Found {len(inventory)} inventory records for 'Меч огня'")
        print(f"   📊 Trader 'DragonSlayer88' has {trader_records} inventory records")
        print(f"   ✅ Database verification completed in {verification_time:.4f}s")
        
        # Step 5: Performance analysis
        print("\n5. Performance analysis...")
        
        if processed_trades:
            avg_validation = sum(t['validation_time'] for t in processed_trades) / len(processed_trades)
            avg_db_time = sum(t['db_time'] for t in processed_trades) / len(processed_trades)
            avg_confidence = sum(t['confidence'] for t in processed_trades) / len(processed_trades)
        else:
            avg_validation = avg_db_time = avg_confidence = 0
        
        total_time = workflow_results['total_processing_time'] + init_time + hotkey_time + verification_time
        
        print(f"   📊 Component initialization: {init_time:.4f}s")
        print(f"   📊 Average validation time: {avg_validation:.4f}s") 
        print(f"   📊 Average database time: {avg_db_time:.4f}s")
        print(f"   📊 Hotkey system response: {hotkey_time:.4f}s")
        print(f"   📊 Database verification: {verification_time:.4f}s")
        print(f"   📊 Total workflow time: {total_time:.4f}s")
        print(f"   📊 Average data confidence: {avg_confidence:.2f}")
        
        # Step 6: System health check
        print("\n6. System health check...")
        
        health_issues = []
        
        # Check performance targets
        if total_time > 1.0:
            health_issues.append(f"Total processing time {total_time:.3f}s exceeds 1s target")
        
        if avg_validation > 0.01:
            health_issues.append(f"Validation time {avg_validation:.4f}s exceeds 10ms target")
        
        if avg_db_time > 0.1:
            health_issues.append(f"Database time {avg_db_time:.4f}s exceeds 100ms target")
        
        if avg_confidence < 0.8:
            health_issues.append(f"Average confidence {avg_confidence:.2f} below 80% target")
        
        # Check data processing
        success_rate = workflow_results['records_valid'] / workflow_results['records_processed'] if workflow_results['records_processed'] > 0 else 0
        storage_rate = workflow_results['records_stored'] / workflow_results['records_processed'] if workflow_results['records_processed'] > 0 else 0
        
        if success_rate < 0.8:
            health_issues.append(f"Validation success rate {success_rate:.2%} below 80% target")
        
        if storage_rate < success_rate:
            health_issues.append(f"Storage rate {storage_rate:.2%} below validation success rate")
        
        if health_issues:
            print("   ⚠️  Health issues detected:")
            for issue in health_issues:
                print(f"      - {issue}")
        else:
            print("   ✅ All health checks passed")
        
        # Step 7: Cleanup
        print("\n7. Cleaning up test data...")
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM current_inventory WHERE trader_nickname = ?", ('DragonSlayer88',))
            cursor.execute("DELETE FROM trades WHERE trader_nickname = ?", ('DragonSlayer88',))
            conn.commit()
        
        print("   ✅ Test data cleaned up")
        
        # Final evaluation
        print("\n" + "="*60)
        
        overall_success = (
            len(health_issues) == 0 and
            workflow_results['records_processed'] > 0 and
            success_rate >= 0.8 and
            total_time <= 1.0
        )
        
        if overall_success:
            print("END-TO-END WORKFLOW TEST: ✅ PASSED")
            print("="*60)
            print(f"✅ Processed {workflow_results['records_processed']} records")
            print(f"✅ Success rate: {success_rate:.1%}")
            print(f"✅ Storage rate: {storage_rate:.1%}")
            print(f"✅ Total time: {total_time:.3f}s (target: <1.0s)")
            print(f"✅ Average confidence: {avg_confidence:.2f}")
            print("🎉 Complete workflow functional and performant!")
            return True
        else:
            print("END-TO-END WORKFLOW TEST: ⚠️  ISSUES DETECTED")
            print("="*60)
            print(f"📊 Processed {workflow_results['records_processed']} records")
            print(f"📊 Success rate: {success_rate:.1%}")
            print(f"📊 Storage rate: {storage_rate:.1%}")
            print(f"📊 Total time: {total_time:.3f}s")
            print("Review health issues above for details")
            return False
        
    except Exception as e:
        print(f"\n❌ End-to-end workflow test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_complete_workflow()
    sys.exit(0 if success else 1)