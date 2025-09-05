#!/usr/bin/env python3
"""
CLI script to run the automation processor

Usage:
    python run_processor.py --data-dir data
"""

import argparse
import sys
from pathlib import Path
from automation_processor import AutomationProcessor

def main():
    parser = argparse.ArgumentParser(description='Process automation JSON files and populate Supabase database')
    parser.add_argument('--data-dir', '-d', default='data', 
                       help='Directory containing JSON files (default: data)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be processed without making changes')
    
    args = parser.parse_args()
    
    # Verify data directory exists
    data_path = Path(args.data_dir)
    if not data_path.exists():
        print(f"Error: Data directory '{args.data_dir}' not found")
        sys.exit(1)
    
    json_files = list(data_path.glob("*.json"))
    if not json_files:
        print(f"Error: No JSON files found in '{args.data_dir}'")
        sys.exit(1)
    
    print(f"Found {len(json_files)} JSON files in '{args.data_dir}'")
    
    if args.dry_run:
        print("DRY RUN MODE - No changes will be made")
        for json_file in json_files[:5]:  # Show first 5 files
            print(f"  - {json_file.name}")
        if len(json_files) > 5:
            print(f"  ... and {len(json_files) - 5} more files")
        return
    
    try:
        processor = AutomationProcessor()
        processor.process_all(args.data_dir)
        print("✅ Processing completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during processing: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()