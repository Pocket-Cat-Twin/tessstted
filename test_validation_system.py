#!/usr/bin/env python3
"""
Practical Validation System Test
Test validation functionality with real trader and item data
"""

import sys
import time
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from game_monitor.fast_validator import FastValidator, ValidationLevel, get_validator

def test_validation_system():
    """Test practical validation system operations"""
    print("="*60)
    print("TESTING VALIDATION SYSTEM")
    print("="*60)
    
    try:
        # Initialize validator
        print("1. Initializing validation system...")
        validator = get_validator()
        print("   ✅ Validator initialized successfully")
        
        # Test data - realistic game trading data
        test_data = [
            # Valid data
            {
                'name': 'Valid Trader Data',
                'data': {
                    'trader_nickname': 'DragonSlayer88',
                    'item_name': 'Меч огня',
                    'quantity': '15',
                    'price_per_unit': '1250.50',
                    'total_price': '18757.50'
                },
                'expected_valid': True
            },
            {
                'name': 'Valid Russian Items',
                'data': {
                    'trader_nickname': 'MasterTrader',
                    'item_name': 'Щит льда',
                    'quantity': '7',
                    'price_per_unit': '2000.00',
                    'total_price': '14000.00'
                },
                'expected_valid': True
            },
            {
                'name': 'Valid English Items',
                'data': {
                    'trader_nickname': 'ItemCollector',
                    'item_name': 'Fire Sword',
                    'quantity': '3',
                    'price_per_unit': '500.75',
                    'total_price': '1502.25'
                },
                'expected_valid': True
            },
            # Edge cases
            {
                'name': 'Large Quantity',
                'data': {
                    'trader_nickname': 'BulkSeller',
                    'item_name': 'Health Potion',
                    'quantity': '999',
                    'price_per_unit': '10.00',
                    'total_price': '9990.00'
                },
                'expected_valid': True
            },
            {
                'name': 'Small Price',
                'data': {
                    'trader_nickname': 'CheapGoods',
                    'item_name': 'Common Stone',
                    'quantity': '1',
                    'price_per_unit': '0.01',
                    'total_price': '0.01'
                },
                'expected_valid': True
            },
            # Invalid data
            {
                'name': 'Invalid Trader Name',
                'data': {
                    'trader_nickname': 'Invalid@Name!',
                    'item_name': 'Меч огня',
                    'quantity': '5',
                    'price_per_unit': '100.00',
                    'total_price': '500.00'
                },
                'expected_valid': False
            },
            {
                'name': 'Invalid Quantity',
                'data': {
                    'trader_nickname': 'ValidTrader',
                    'item_name': 'Valid Item',
                    'quantity': '-5',
                    'price_per_unit': '100.00',
                    'total_price': '500.00'
                },
                'expected_valid': False
            },
            {
                'name': 'Invalid Price Format',
                'data': {
                    'trader_nickname': 'ValidTrader',
                    'item_name': 'Valid Item',
                    'quantity': '5',
                    'price_per_unit': 'invalid_price',
                    'total_price': '500.00'
                },
                'expected_valid': False
            },
            {
                'name': 'Empty Item Name',
                'data': {
                    'trader_nickname': 'ValidTrader',
                    'item_name': '',
                    'quantity': '5',
                    'price_per_unit': '100.00',
                    'total_price': '500.00'
                },
                'expected_valid': False
            },
            {
                'name': 'Suspicious Characters',
                'data': {
                    'trader_nickname': 'ValidTrader',
                    'item_name': '!!@#$%^&*()',
                    'quantity': '5',
                    'price_per_unit': '100.00',
                    'total_price': '500.00'
                },
                'expected_valid': False
            }
        ]
        
        # Test 2: Individual field validation
        print("\n2. Testing individual field validation...")
        field_tests = [
            ('trader_nickname', 'DragonSlayer88', True, validator.validate_trader_nickname),
            ('trader_nickname', 'Invalid@Name!', False, validator.validate_trader_nickname),
            ('item_name', 'Меч огня', True, validator.validate_item_name),
            ('item_name', '!!@#$', False, validator.validate_item_name),
            ('quantity', 15, True, validator.validate_quantity),
            ('quantity', -5, False, validator.validate_quantity),
            ('quantity', 'abc', False, validator.validate_quantity),
            ('price', '1250.50', True, validator.validate_price),
            ('price', 'invalid', False, validator.validate_price),
            ('price', '-100.00', False, validator.validate_price),
        ]
        
        field_results = []
        for field_type, value, expected, validate_method in field_tests:
            start_time = time.time()
            result = validate_method(value)
            validation_time = time.time() - start_time
            
            is_valid = result.is_valid
            confidence = result.confidence
            
            field_results.append({
                'field': field_type,
                'value': value,
                'expected': expected,
                'actual': is_valid,
                'confidence': confidence,
                'time': validation_time,
                'correct': is_valid == expected
            })
            
            status = "✅" if is_valid == expected else "❌"
            print(f"   {status} {field_type}: '{value}' -> {is_valid} ({confidence:.2f}) [{validation_time:.4f}s]")
        
        # Test 3: Full record validation
        print("\n3. Testing full record validation...")
        record_results = []
        
        for test_case in test_data:
            start_time = time.time()
            
            # Test with different validation levels
            validation_result = validator.validate_trade_data(
                test_case['data'], 
                level=ValidationLevel.BALANCED
            )
            
            validation_time = time.time() - start_time
            
            is_valid = validation_result.is_valid
            confidence = validation_result.confidence
            
            record_results.append({
                'name': test_case['name'],
                'expected': test_case['expected_valid'],
                'actual': is_valid,
                'confidence': confidence,
                'time': validation_time,
                'correct': is_valid == test_case['expected_valid']
            })
            
            status = "✅" if is_valid == test_case['expected_valid'] else "❌"
            print(f"   {status} {test_case['name']}: {is_valid} ({confidence:.2f}) [{validation_time:.4f}s]")
            
            # Show error details for failed cases
            if is_valid != test_case['expected_valid'] and validation_result.errors:
                for error in validation_result.errors:
                    print(f"      - Error: {error}")
            if validation_result.warnings:
                for warning in validation_result.warnings[:2]:  # Show first 2 warnings
                    print(f"      - Warning: {warning}")
        
        # Test 4: Performance analysis
        print("\n4. Performance analysis...")
        field_times = [r['time'] for r in field_results]
        record_times = [r['time'] for r in record_results]
        
        avg_field_time = sum(field_times) / len(field_times) if field_times else 0
        avg_record_time = sum(record_times) / len(record_times) if record_times else 0
        max_record_time = max(record_times) if record_times else 0
        
        print(f"   📊 Average field validation: {avg_field_time:.4f}s")
        print(f"   📊 Average record validation: {avg_record_time:.4f}s")
        print(f"   📊 Slowest record validation: {max_record_time:.4f}s")
        
        # Performance targets
        if avg_field_time < 0.001 and avg_record_time < 0.01:
            print("   ✅ PERFORMANCE TARGET MET (<1ms field, <10ms record)")
        else:
            print("   ⚠️  Performance target exceeded")
        
        # Test 5: Accuracy analysis
        print("\n5. Accuracy analysis...")
        field_correct = sum(1 for r in field_results if r['correct'])
        record_correct = sum(1 for r in record_results if r['correct'])
        
        field_accuracy = field_correct / len(field_results) * 100 if field_results else 0
        record_accuracy = record_correct / len(record_results) * 100 if record_results else 0
        
        print(f"   📊 Field validation accuracy: {field_accuracy:.1f}% ({field_correct}/{len(field_results)})")
        print(f"   📊 Record validation accuracy: {record_accuracy:.1f}% ({record_correct}/{len(record_results)})")
        
        # Show failed cases
        failed_fields = [r for r in field_results if not r['correct']]
        failed_records = [r for r in record_results if not r['correct']]
        
        if failed_fields:
            print(f"   ⚠️  Failed field validations:")
            for fail in failed_fields:
                print(f"      - {fail['field']}: '{fail['value']}' expected {fail['expected']}, got {fail['actual']}")
        
        if failed_records:
            print(f"   ⚠️  Failed record validations:")
            for fail in failed_records:
                print(f"      - {fail['name']}: expected {fail['expected']}, got {fail['actual']}")
        
        # Test 6: Different validation levels
        print("\n6. Testing validation levels...")
        test_record = test_data[0]['data']  # Use first valid record
        
        validation_levels = [
            ValidationLevel.PERMISSIVE,
            ValidationLevel.BALANCED, 
            ValidationLevel.STRICT
        ]
        
        for level in validation_levels:
            start_time = time.time()
            result = validator.validate_trade_data(test_record, level=level)
            validation_time = time.time() - start_time
            
            print(f"   📊 {level.value}: {result.is_valid} ({result.confidence:.2f}) [{validation_time:.4f}s]")
        
        # Final evaluation
        print("\n" + "="*60)
        
        overall_accuracy = (field_correct + record_correct) / (len(field_results) + len(record_results)) * 100
        performance_ok = avg_field_time < 0.001 and avg_record_time < 0.01
        
        if overall_accuracy >= 80 and performance_ok:
            print("VALIDATION SYSTEM TEST: ✅ PASSED")
            print("="*60)
            print(f"System accuracy: {overall_accuracy:.1f}%")
            print(f"Performance: {avg_record_time:.4f}s average record validation")
            return True
        else:
            print("VALIDATION SYSTEM TEST: ⚠️  NEEDS IMPROVEMENT")
            print("="*60)
            print(f"System accuracy: {overall_accuracy:.1f}% (target: 80%+)")
            print(f"Performance: {avg_record_time:.4f}s average (target: <10ms)")
            return False
        
    except Exception as e:
        print(f"\n❌ Validation system test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_validation_system()
    sys.exit(0 if success else 1)