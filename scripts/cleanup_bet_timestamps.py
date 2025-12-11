"""
Cleanup script to standardize timestamp formats in betting data files.

This script:
1. Reads all CSV files in the data/bets directory
2. Identifies and fixes inconsistent timestamp formats
3. Converts all timestamps to ISO 8601 format: YYYY-MM-DDTHH:MM:SS.000Z
4. Saves the cleaned data back to the original files

This prevents ValueError exceptions during datetime parsing in evaluation scripts.
"""

import pandas as pd
from pathlib import Path
import re
from datetime import datetime


def clean_timestamp(timestamp_str):
    """
    Convert various timestamp formats to standardized ISO 8601 format.
    
    Handles formats like:
    - "2025-12-11 00:00:00+00:00" (space separator with timezone)
    - "2025-12-11T00:00:00.000Z" (already correct)
    - "2025-12-11T00:00:00Z" (missing milliseconds)
    - Other variations
    
    Returns: "YYYY-MM-DDTHH:MM:SS.000Z"
    """
    if pd.isna(timestamp_str) or timestamp_str == '':
        return timestamp_str
    
    try:
        # Remove any zero-width or invisible Unicode characters
        timestamp_str = str(timestamp_str).strip()
        timestamp_str = re.sub(r'[\u200b\u200c\u200d\ufeff]', '', timestamp_str)
        
        # Try to parse the timestamp with pandas (handles multiple formats)
        dt = pd.to_datetime(timestamp_str, utc=True, errors='coerce')
        
        if pd.isna(dt):
            print(f"  Warning: Could not parse timestamp: {timestamp_str}")
            return timestamp_str
        
        # Convert to standardized ISO 8601 format with milliseconds
        # Format: YYYY-MM-DDTHH:MM:SS.000Z
        standardized = dt.strftime('%Y-%m-%dT%H:%M:%S.000Z')
        
        return standardized
    
    except Exception as e:
        print(f"  Error processing timestamp '{timestamp_str}': {e}")
        return timestamp_str


def clean_start_time(start_time_str):
    """
    Convert various start_time formats to standardized ISO 8601 format.
    
    Returns: "YYYY-MM-DDTHH:MM:SS.000Z"
    """
    if pd.isna(start_time_str) or start_time_str == '':
        return start_time_str
    
    try:
        # Remove any zero-width or invisible Unicode characters
        start_time_str = str(start_time_str).strip()
        start_time_str = re.sub(r'[\u200b\u200c\u200d\ufeff]', '', start_time_str)
        
        # Try to parse the start_time with pandas
        dt = pd.to_datetime(start_time_str, utc=True, errors='coerce')
        
        if pd.isna(dt):
            print(f"  Warning: Could not parse start_time: {start_time_str}")
            return start_time_str
        
        # Convert to standardized ISO 8601 format with milliseconds
        standardized = dt.strftime('%Y-%m-%dT%H:%M:%S.000Z')
        
        return standardized
    
    except Exception as e:
        print(f"  Error processing start_time '{start_time_str}': {e}")
        return start_time_str


def clean_bet_file(file_path):
    """
    Clean a single betting data file.
    
    Args:
        file_path: Path to the CSV file to clean
    
    Returns:
        Number of timestamps cleaned
    """
    print(f"\nProcessing: {file_path.name}")
    
    try:
        # Read the CSV file
        # Use on_bad_lines='skip' to handle malformed lines gracefully
        df = pd.read_csv(file_path, on_bad_lines='skip')
        
        if df.empty:
            print(f"  File is empty, skipping.")
            return 0
        
        print(f"  Loaded {len(df)} rows")
        
        # Track changes
        changes_made = 0
        
        # Clean timestamp column if it exists
        if 'timestamp' in df.columns:
            print(f"  Cleaning 'timestamp' column...")
            original_timestamps = df['timestamp'].copy()
            df['timestamp'] = df['timestamp'].apply(clean_timestamp)
            
            # Count how many were changed
            timestamp_changes = (original_timestamps != df['timestamp']).sum()
            changes_made += timestamp_changes
            print(f"    Cleaned {timestamp_changes} timestamp values")
        
        # Also check for timestamp with zero-width character (common issue)
        timestamp_cols = [col for col in df.columns if 'timestamp' in col.lower()]
        for col in timestamp_cols:
            if col != 'timestamp':
                print(f"  Found alternate timestamp column: '{col}' - renaming to 'timestamp'")
                # Rename the column
                df = df.rename(columns={col: 'timestamp'})
                # Clean it
                df['timestamp'] = df['timestamp'].apply(clean_timestamp)
                changes_made += len(df)
        
        # Clean start_time column if it exists
        if 'start_time' in df.columns:
            print(f"  Cleaning 'start_time' column...")
            original_start_times = df['start_time'].copy()
            df['start_time'] = df['start_time'].apply(clean_start_time)
            
            # Count how many were changed
            start_time_changes = (original_start_times != df['start_time']).sum()
            changes_made += start_time_changes
            print(f"    Cleaned {start_time_changes} start_time values")
        
        # Save the cleaned data back to the file
        if changes_made > 0:
            df.to_csv(file_path, index=False)
            print(f"  ✓ Saved cleaned file with {changes_made} changes")
        else:
            print(f"  ✓ No changes needed")
        
        return changes_made
    
    except Exception as e:
        print(f"  ✗ Error processing file: {e}")
        return 0


def main():
    """
    Main function to clean all betting data files.
    """
    print("=" * 70)
    print("Betting Data Timestamp Cleanup Script")
    print("=" * 70)
    
    # Define the bets directory
    bets_dir = Path(__file__).parent.parent / 'data' / 'bets'
    
    if not bets_dir.exists():
        print(f"Error: Bets directory not found at {bets_dir}")
        return
    
    print(f"\nScanning directory: {bets_dir}")
    
    # Find all .txt files (CSV format) in the bets directory
    bet_files = list(bets_dir.glob('*.txt'))
    
    if not bet_files:
        print("No betting data files found.")
        return
    
    print(f"Found {len(bet_files)} betting data files")
    
    # Process each file
    total_changes = 0
    for file_path in sorted(bet_files):
        changes = clean_bet_file(file_path)
        total_changes += changes
    
    print("\n" + "=" * 70)
    print(f"Cleanup Complete!")
    print(f"Total changes made: {total_changes}")
    print("=" * 70)


if __name__ == "__main__":
    main()
