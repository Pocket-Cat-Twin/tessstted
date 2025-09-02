#!/usr/bin/env python3
"""
Practical Hotkey System Test
Test hotkey manager functionality and callback system
"""

import sys
import time
import threading
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from game_monitor.hotkey_manager import HotkeyManager, HotkeyType, CaptureEvent, get_hotkey_manager

def test_hotkey_system():
    """Test practical hotkey system operations"""
    print("="*60)
    print("TESTING HOTKEY SYSTEM")
    print("="*60)
    
    try:
        # Initialize hotkey manager
        print("1. Initializing hotkey manager...")
        hotkey_manager = get_hotkey_manager()
        print("   ✅ Hotkey manager initialized successfully")
        
        # Test callback storage
        callback_results = []
        processing_times = []
        
        def test_callback(event: CaptureEvent):
            """Test callback function"""
            start_time = time.time()
            
            callback_results.append({
                'hotkey': event.hotkey_type.value,
                'timestamp': event.timestamp,
                'region': event.region
            })
            
            # Simulate some processing work
            time.sleep(0.001)  # 1ms processing time
            
            processing_time = time.time() - start_time
            processing_times.append(processing_time)
            
            print(f"      📞 Callback executed for {event.hotkey_type.value} in {processing_time:.3f}s")
        
        # Test 2: Register callbacks for all hotkeys
        print("\n2. Registering hotkey callbacks...")
        hotkey_types = [
            HotkeyType.TRADER_LIST,
            HotkeyType.ITEM_SCAN, 
            HotkeyType.TRADER_INVENTORY,
            HotkeyType.MANUAL_VERIFICATION,
            HotkeyType.EMERGENCY_STOP
        ]
        
        for hotkey_type in hotkey_types:
            hotkey_manager.register_callback(hotkey_type, test_callback)
            print(f"   ✅ Registered callback for {hotkey_type.value}")
        
        # Test 3: Start the hotkey system
        print("\n3. Starting hotkey system...")
        start_time = time.time()
        hotkey_manager.start()
        startup_time = time.time() - start_time
        print(f"   ✅ Hotkey system started in {startup_time:.3f}s")
        
        # Test 4: Trigger hotkeys programmatically (simulation mode)
        print("\n4. Testing hotkey triggers...")
        
        test_triggers = [
            ("F1", hotkey_manager.trigger_trader_list_capture),
            ("F2", hotkey_manager.trigger_item_scan_capture),
            ("F3", hotkey_manager.trigger_trader_inventory_capture),
            ("F4", hotkey_manager.trigger_manual_verification)
        ]
        
        trigger_start = time.time()
        
        for key_name, trigger_method in test_triggers:
            print(f"   🔥 Triggering {key_name}...")
            trigger_method()
            time.sleep(0.1)  # Small delay between triggers
        
        trigger_time = time.time() - trigger_start
        
        # Wait for all callbacks to complete
        print("   ⏳ Waiting for callbacks to complete...")
        time.sleep(1.0)  # Give time for all callbacks to execute
        
        # Test 5: Check results
        print("\n5. Analyzing results...")
        print(f"   📊 Total callbacks executed: {len(callback_results)}")
        print(f"   📊 Trigger sequence time: {trigger_time:.3f}s")
        
        if processing_times:
            avg_processing = sum(processing_times) / len(processing_times)
            min_processing = min(processing_times)
            max_processing = max(processing_times)
            
            print(f"   📊 Average callback time: {avg_processing:.3f}s")
            print(f"   📊 Fastest callback: {min_processing:.3f}s")
            print(f"   📊 Slowest callback: {max_processing:.3f}s")
        
        # Verify all expected callbacks were received
        expected_hotkeys = ['trader_list', 'item_scan', 'trader_inventory', 'manual_verification']
        received_hotkeys = [result['hotkey'] for result in callback_results]
        
        print("\n   📋 Callback verification:")
        for expected in expected_hotkeys:
            if expected in received_hotkeys:
                print(f"      ✅ {expected}: callback received")
            else:
                print(f"      ❌ {expected}: callback MISSING")
        
        # Test 6: Performance validation
        print("\n6. Performance validation...")
        
        total_time = startup_time + trigger_time
        if processing_times:
            avg_response = sum(processing_times) / len(processing_times)
        else:
            avg_response = 0
        
        print(f"   📊 System startup: {startup_time:.3f}s")
        print(f"   📊 Trigger processing: {trigger_time:.3f}s")
        print(f"   📊 Average response time: {avg_response:.3f}s")
        print(f"   📊 Total test time: {total_time:.3f}s")
        
        # Check performance targets
        if avg_response < 0.1:  # 100ms target
            print("   ✅ RESPONSE TIME TARGET MET (<100ms)")
        else:
            print("   ⚠️  Response time target exceeded")
        
        # Test 7: System stats
        print("\n7. Getting system statistics...")
        try:
            stats = hotkey_manager.get_statistics()
            print(f"   📊 Total captures: {stats.get('total_captures', 'N/A')}")
            print(f"   📊 Success rate: {stats.get('success_rate', 'N/A')}")
            print(f"   📊 Average processing: {stats.get('avg_processing_time', 'N/A')}")
        except Exception as e:
            print(f"   ⚠️  Statistics unavailable: {e}")
        
        # Test 8: Stop the system
        print("\n8. Stopping hotkey system...")
        stop_start = time.time()
        hotkey_manager.stop()
        stop_time = time.time() - stop_start
        print(f"   ✅ Hotkey system stopped in {stop_time:.3f}s")
        
        # Final evaluation
        print("\n" + "="*60)
        if len(callback_results) == len(expected_hotkeys) and avg_response < 0.1:
            print("HOTKEY SYSTEM TEST: ✅ PASSED")
            print("="*60)
            print("All hotkey callbacks working correctly!")
            print(f"System responsive: {avg_response:.3f}s average response time")
            return True
        else:
            print("HOTKEY SYSTEM TEST: ⚠️  PARTIAL")
            print("="*60)
            print("Some issues detected - check callback registration or timing")
            return False
        
    except Exception as e:
        print(f"\n❌ Hotkey system test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_hotkey_system()
    sys.exit(0 if success else 1)