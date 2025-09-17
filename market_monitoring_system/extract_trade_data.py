#!/usr/bin/env python3
import re
import json
import csv
import sys
from pathlib import Path

def clean_price(price_text):
    """Extract and clean price from 'Unit Price : 8,888 Adena' format"""
    # Extract numbers and remove commas
    numbers = re.findall(r'[\d,]+', price_text)
    if numbers:
        return numbers[0].replace(',', '')
    return ''

def clean_item_name(item_text):
    """Remove parentheses and numbers from item name"""
    # Remove content in parentheses like (111), (10), etc.
    cleaned = re.sub(r'\s*\(\d+\)', '', item_text)
    return cleaned.strip()

def extract_trade_data(text_content):
    """Extract trade data from OCR text using specified patterns"""
    trades = []
    extraction_log = []
    
    # Split by "Trade" to get individual instances
    sections = text_content.split('Trade')
    
    for i, section in enumerate(sections):
        if not section.strip():
            continue
            
        log_entry = f"\n--- Processing Trade Instance {i} ---\n"
        log_entry += f"Raw text:\n{section[:200]}...\n"
        
        try:
            lines = [line.strip() for line in section.split('\n') if line.strip()]
            
            seller = ''
            item_name = ''
            unit_price = ''
            quantity = ''
            
            # Extract seller from "Items to Sell SellerName" pattern
            for line in lines:
                if 'Items to Sell' in line:
                    seller_match = re.search(r'Items to Sell\s+(.+)', line)
                    if seller_match:
                        seller = seller_match.group(1).strip()
                        log_entry += f"Found seller: '{seller}'\n"
                        break
            
            # Find Unit Price and preceding line for item name
            unit_price_index = -1
            for j, line in enumerate(lines):
                if 'Unit Price' in line:
                    unit_price_index = j
                    # Extract price
                    unit_price = clean_price(line)
                    log_entry += f"Found unit price: '{unit_price}' from line: '{line}'\n"
                    
                    # Item name should be in the line before Unit Price
                    if j > 0:
                        item_name = clean_item_name(lines[j-1])
                        log_entry += f"Found item name: '{item_name}' from line: '{lines[j-1]}'\n"
                    break
            
            # Extract quantity
            for line in lines:
                if line.startswith('Quantity :'):
                    quantity_match = re.search(r'Quantity\s*:\s*(\d+)', line)
                    if quantity_match:
                        quantity = quantity_match.group(1)
                        log_entry += f"Found quantity: '{quantity}' from line: '{line}'\n"
                        break
            
            # Only add if we have all required fields
            if seller and item_name and unit_price and quantity:
                trade_data = {
                    'seller': seller,
                    'item_name': item_name,
                    'unit_price': unit_price,
                    'quantity': quantity
                }
                trades.append(trade_data)
                log_entry += f"✓ Successfully extracted: {trade_data}\n"
            else:
                log_entry += f"✗ Missing data - Seller:'{seller}', Item:'{item_name}', Price:'{unit_price}', Qty:'{quantity}'\n"
                
        except Exception as e:
            log_entry += f"✗ Error processing section: {str(e)}\n"
        
        extraction_log.append(log_entry)
    
    return trades, extraction_log

def main():
    # Input and output paths
    input_file = Path('test/merged_images_vertical_recognized.txt')
    
    if not input_file.exists():
        print(f"Error: Input file {input_file} not found")
        return
    
    # Read input file
    with open(input_file, 'r', encoding='utf-8') as f:
        text_content = f.read()
    
    print(f"Processing {input_file}...")
    
    # Extract data
    trades, extraction_log = extract_trade_data(text_content)
    
    print(f"Extracted {len(trades)} trade entries")
    
    # Save results
    # 1. JSON format
    json_file = 'extracted_data.json'
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(trades, f, ensure_ascii=False, indent=2)
    print(f"Saved JSON data to {json_file}")
    
    # 2. CSV format for database preview
    csv_file = 'extracted_data.csv'
    if trades:
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['seller', 'item_name', 'unit_price', 'quantity'])
            writer.writeheader()
            writer.writerows(trades)
        print(f"Saved CSV data to {csv_file}")
    
    # 3. Detailed extraction log
    log_file = 'extraction_log.txt'
    with open(log_file, 'w', encoding='utf-8') as f:
        f.write("TRADE DATA EXTRACTION LOG\n")
        f.write("========================\n")
        f.write(f"Total sections processed: {len(extraction_log)}\n")
        f.write(f"Successful extractions: {len(trades)}\n\n")
        for log_entry in extraction_log:
            f.write(log_entry)
    print(f"Saved extraction log to {log_file}")
    
    # Preview results
    print(f"\nPreview of extracted data:")
    print("-" * 60)
    for i, trade in enumerate(trades[:10], 1):  # Show first 10
        print(f"{i}. Seller: {trade['seller']}")
        print(f"   Item: {trade['item_name']}")
        print(f"   Price: {trade['unit_price']}")
        print(f"   Quantity: {trade['quantity']}")
        print()
    
    if len(trades) > 10:
        print(f"... and {len(trades) - 10} more entries")

if __name__ == "__main__":
    main()