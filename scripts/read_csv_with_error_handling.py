import pandas as pd
import sys
from pathlib import Path

def read_csv_skip_bad_lines(file_path, bad_lines_output=None):
    """
    Read a CSV file, skip bad lines, and optionally save them to a file.
    
    Parameters:
    -----------
    file_path : str
        Path to the CSV file to read
    bad_lines_output : str, optional
        Path to save bad lines. If None, uses input filename with '_bad_lines.txt' suffix
    
    Returns:
    --------
    pd.DataFrame
        DataFrame with successfully parsed rows
    """
    file_path = Path(file_path)
    
    # Set default bad lines output path
    if bad_lines_output is None:
        bad_lines_output = file_path.parent / f"{file_path.stem}_bad_lines.txt"
    
    bad_lines = []
    
    def handle_bad_line(bad_line):
        """Callback function to handle bad lines"""
        bad_lines.append(bad_line)
        return None  # Skip the bad line
    
    # Read CSV with error handling
    print(f"Reading CSV from: {file_path}")
    df = pd.read_csv(
        file_path,
        on_bad_lines=handle_bad_line,
        engine='python'  # Python engine is more flexible with error handling
    )
    
    # Save bad lines if any were found
    if bad_lines:
        print(f"\n⚠️  Found {len(bad_lines)} bad line(s)")
        with open(bad_lines_output, 'w') as f:
            f.write("# Bad lines from CSV parsing\n")
            f.write(f"# Source file: {file_path}\n")
            f.write(f"# Total bad lines: {len(bad_lines)}\n\n")
            for i, line in enumerate(bad_lines, 1):
                f.write(f"# Bad line {i}:\n")
                f.write(str(line) + "\n\n")
        print(f"✓ Bad lines saved to: {bad_lines_output}")
    else:
        print("✓ No bad lines found")
    
    print(f"✓ Successfully loaded {len(df)} rows")
    
    return df

if __name__ == "__main__":
    # Example usage
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        bad_lines_output = sys.argv[2] if len(sys.argv) > 2 else None
        df = read_csv_skip_bad_lines(file_path, bad_lines_output)
        print(f"\nDataFrame shape: {df.shape}")
        print(f"\nColumns: {list(df.columns)}")
    else:
        print("Usage: python read_csv_with_error_handling.py <csv_file_path> [bad_lines_output_path]")
