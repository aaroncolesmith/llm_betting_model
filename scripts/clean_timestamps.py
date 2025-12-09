#!/usr/bin/env python3
"""
Clean timestamp data in NBA bet picks CSV file.
Removes duplicate timestamp column with zero-width space and ensures all timestamps are in proper ISO 8601 format.
"""

import pandas as pd
import re
from pathlib import Path

def clean_timestamps(file_path):
    """
    Clean timestamp issues in the CSV file:
    1. Remove duplicate timestamp column with zero-width space
    2. Ensure all timestamps are in proper ISO 8601 format
    3. Remove any invisible Unicode characters from column names
    """
    print(f"Reading file: {file_path}")
    
    # Read the CSV
    df = pd.read_csv(file_path)
    
    print(f"Original columns: {list(df.columns)}")
    print(f"Original shape: {df.shape}")
    
    # Clean column names - remove invisible Unicode characters
    df.columns = df.columns.str.strip().str.replace('\u200b', '').str.replace('\ufeff', '')
    
    # Remove duplicate columns (keep first occurrence)
    df = df.loc[:, ~df.columns.duplicated()]
    
    print(f"Cleaned columns: {list(df.columns)}")
    print(f"New shape: {df.shape}")
    
    # Clean timestamp values if the column exists
    if 'timestamp' in df.columns:
        print("\nCleaning timestamp values...")
        
        # Remove zero-width spaces from timestamp values
        df['timestamp'] = df['timestamp'].astype(str).str.replace('\u200b', '').str.replace('\ufeff', '')
        
        # Count different timestamp formats
        print("\nTimestamp format analysis:")
        sample_timestamps = df['timestamp'].dropna().head(20)
        for idx, ts in sample_timestamps.items():
            print(f"  Row {idx}: {repr(ts)}")
        
        # Try to standardize timestamps to ISO 8601
        try:
            df['timestamp'] = pd.to_datetime(df['timestamp'], format='ISO8601', errors='coerce')
            # Convert back to string in standard format
            df['timestamp'] = df['timestamp'].dt.strftime('%Y-%m-%dT%H:%M:%S%z')
            print("\nSuccessfully standardized timestamps to ISO 8601 format")
        except Exception as e:
            print(f"\nWarning: Could not fully standardize timestamps: {e}")
            print("Timestamps will be cleaned of invisible characters only")
    
    # Backup original file
    backup_path = file_path.parent / f"{file_path.stem}_backup{file_path.suffix}"
    print(f"\nCreating backup at: {backup_path}")
    import shutil
    shutil.copy2(file_path, backup_path)
    
    # Save cleaned file
    print(f"Saving cleaned file to: {file_path}")
    df.to_csv(file_path, index=False)
    
    print("\n✓ File cleaned successfully!")
    print(f"  - Removed duplicate columns")
    print(f"  - Cleaned {len(df)} rows")
    print(f"  - Backup saved to: {backup_path}")
    
    return df

if __name__ == "__main__":
    file_path = Path("/Users/aaronsmith/Code/llm_betting_model/data/evaluated/nba_bet_picks.csv")
    
    if not file_path.exists():
        print(f"Error: File not found at {file_path}")
        exit(1)
    
    df = clean_timestamps(file_path)
    
    print("\nFirst few rows after cleaning:")
    print(df.head())
