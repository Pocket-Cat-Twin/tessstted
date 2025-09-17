#!/usr/bin/env python3
"""
Simple test script to verify dual processing type integration.
"""

import sys
import os
sys.path.append('src')

from core.text_parser import TextParser, ParsingResult
from core.database_manager import ItemData

def test_full_processing():
    """Test full processing with trade data extraction."""
    parser = TextParser()
    
    # Sample trade data text (based on extract_trade_data.py patterns)
    sample_text = """
Trade
Items to Sell SellerName123
Item1 (5)
Unit Price : 1,500 Adena
Quantity : 10
    """
    
    result = parser.parse_items_data(
        text=sample_text,
        hotkey="F1", 
        screenshot_type="individual_seller_items",
        processing_type="full"
    )
    
    print("=== FULL PROCESSING TEST ===")
    print(f"Processing type: {result.processing_type}")
    print(f"Items extracted: {len(result.items)}")
    for item in result.items:
        print(f"  - Seller: {item.seller_name}")
        print(f"    Item: {item.item_name}")
        print(f"    Price: {item.price}")
        print(f"    Quantity: {item.quantity}")
        print(f"    Processing type: {item.processing_type}")
    print(f"Errors: {result.errors}")
    print()
    
    return result

def test_minimal_processing():
    """Test minimal processing with broker data extraction."""
    parser = TextParser()
    
    # Sample broker data text (based on extract_broker_sellers.py patterns)
    sample_text = """
Item Broke
Sword of Power
Name
Seller1
Seller2
Seller3

Item Broke
Magic Shield
Name
VendorA
VendorB
    """
    
    result = parser.parse_items_data(
        text=sample_text,
        hotkey="F2", 
        screenshot_type="individual_seller_items",
        processing_type="minimal"
    )
    
    print("=== MINIMAL PROCESSING TEST ===")
    print(f"Processing type: {result.processing_type}")
    print(f"Items extracted: {len(result.items)}")
    for item in result.items:
        print(f"  - Seller: {item.seller_name}")
        print(f"    Item: {item.item_name}")
        print(f"    Price: {item.price}")
        print(f"    Quantity: {item.quantity}")
        print(f"    Processing type: {item.processing_type}")
    print(f"Errors: {result.errors}")
    print()
    
    return result

def test_item_data_structure():
    """Test ItemData structure with processing_type field."""
    print("=== ITEMDATA STRUCTURE TEST ===")
    
    # Test full processing ItemData
    full_item = ItemData(
        seller_name="TestSeller",
        item_name="TestItem",
        price=100.0,
        quantity=5,
        item_id="ID123",
        hotkey="F1",
        processing_type="full"
    )
    
    print(f"Full item: {full_item}")
    print(f"Processing type: {full_item.processing_type}")
    
    # Test minimal processing ItemData  
    minimal_item = ItemData(
        seller_name="TestSeller",
        item_name="TestItem",
        price=None,
        quantity=None,
        item_id=None,
        hotkey="F2",
        processing_type="minimal"
    )
    
    print(f"Minimal item: {minimal_item}")
    print(f"Processing type: {minimal_item.processing_type}")
    print()

def main():
    """Run all tests."""
    print("🚀 Starting dual processing integration test...\n")
    
    try:
        # Test data structures
        test_item_data_structure()
        
        # Test full processing
        full_result = test_full_processing()
        
        # Test minimal processing  
        minimal_result = test_minimal_processing()
        
        print("✅ All tests completed successfully!")
        print(f"   - Full processing extracted: {len(full_result.items)} items")
        print(f"   - Minimal processing extracted: {len(minimal_result.items)} items")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()