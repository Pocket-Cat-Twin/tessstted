#!/usr/bin/env python3
import re
import json
import csv
from pathlib import Path

def clean_item_name(item_text):
    """Clean item name from OCR artifacts"""
    # Remove colons, numbers, and special characters at the end
    cleaned = re.sub(r'[:#\d\s]+$', '', item_text)
    return cleaned.strip()

def is_ocr_artifact(line):
    """Check if line is OCR artifact to skip"""
    line = line.strip()
    # Skip lines like ": 13", ": 24", "#", ": 27"
    if re.match(r'^[:#\d\s&|]+$', line):
        return True
    # Skip "Currency", "Qty." headers
    if line in ['Currency', 'Qty.', 'Name']:
        return True
    return False

def extract_broker_data(text_content):
    """Extract seller-item pairs from broker OCR text"""
    pairs = []
    extraction_log = []
    
    # Split by "Item Broke" to get individual sections
    sections = text_content.split('Item Broke')
    
    for i, section in enumerate(sections):
        if not section.strip():
            continue
            
        log_entry = f"\n--- Processing Broker Section {i} ---\n"
        log_entry += f"Raw section:\n{section[:200]}...\n"
        
        try:
            lines = [line.strip() for line in section.split('\n') if line.strip()]
            
            if not lines:
                log_entry += "✗ Empty section, skipping\n"
                extraction_log.append(log_entry)
                continue
            
            # Extract item name (first clean line)
            item_name = ''
            for line in lines:
                if not is_ocr_artifact(line):
                    item_name = clean_item_name(line)
                    log_entry += f"Found item name: '{item_name}' from line: '{line}'\n"
                    break
            
            if not item_name:
                log_entry += "✗ No valid item name found\n"
                extraction_log.append(log_entry)
                continue
            
            # Find "Name" line and collect sellers after it
            name_found = False
            sellers = []
            
            for j, line in enumerate(lines):
                if line == 'Name':
                    name_found = True
                    log_entry += f"Found 'Name' header at line {j}\n"
                    # Collect all sellers after "Name"
                    for seller_line in lines[j+1:]:
                        if not is_ocr_artifact(seller_line) and seller_line.strip():
                            sellers.append(seller_line.strip())
                    break
            
            if not name_found:
                log_entry += "✗ 'Name' header not found\n"
                extraction_log.append(log_entry)
                continue
            
            log_entry += f"Found {len(sellers)} sellers: {sellers[:5]}{'...' if len(sellers) > 5 else ''}\n"
            
            # Create seller-item pairs
            section_pairs = []
            for seller in sellers:
                pair = {
                    'item_name': item_name,
                    'seller_name': seller
                }
                pairs.append(pair)
                section_pairs.append(pair)
            
            log_entry += f"✓ Created {len(section_pairs)} seller-item pairs\n"
                
        except Exception as e:
            log_entry += f"✗ Error processing section: {str(e)}\n"
        
        extraction_log.append(log_entry)
    
    return pairs, extraction_log

def main():
    # Input and output paths
    input_file = Path('test/merged_images_vertical_text.txt')
    
    if not input_file.exists():
        print(f"Error: Input file {input_file} not found")
        return
    
    # Read input file
    with open(input_file, 'r', encoding='utf-8') as f:
        text_content = f.read()
    
    print(f"Processing {input_file}...")
    
    # Extract data
    pairs, extraction_log = extract_broker_data(text_content)
    
    print(f"Extracted {len(pairs)} seller-item pairs")
    
    # Group by item for summary
    items_summary = {}
    for pair in pairs:
        item = pair['item_name']
        if item not in items_summary:
            items_summary[item] = []
        items_summary[item].append(pair['seller_name'])
    
    print("\nSummary by item:")
    for item, sellers in items_summary.items():
        print(f"- {item}: {len(sellers)} sellers")
    
    # Save results
    # 1. JSON format
    json_file = 'broker_sellers.json'
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(pairs, f, ensure_ascii=False, indent=2)
    print(f"Saved JSON data to {json_file}")
    
    # 2. CSV format for database
    csv_file = 'broker_sellers.csv'
    if pairs:
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['item_name', 'seller_name'])
            writer.writeheader()
            writer.writerows(pairs)
        print(f"Saved CSV data to {csv_file}")
    
    # 3. Detailed extraction log
    log_file = 'broker_sellers_log.txt'
    with open(log_file, 'w', encoding='utf-8') as f:
        f.write("BROKER SELLER-ITEM EXTRACTION LOG\n")
        f.write("=================================\n")
        f.write(f"Total sections processed: {len(extraction_log)}\n")
        f.write(f"Total seller-item pairs: {len(pairs)}\n\n")
        for log_entry in extraction_log:
            f.write(log_entry)
    print(f"Saved extraction log to {log_file}")
    
    # Preview results
    print(f"\nPreview of extracted pairs:")
    print("-" * 50)
    for item, sellers in items_summary.items():
        print(f"\n{item}:")
        for seller in sellers[:5]:  # Show first 5 sellers per item
            print(f"  - {seller}")
        if len(sellers) > 5:
            print(f"  ... and {len(sellers) - 5} more sellers")

if __name__ == "__main__":
    main()