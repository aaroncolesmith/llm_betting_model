# Bet Timestamp Cleanup Script

## Overview

The `cleanup_bet_timestamps.py` script standardizes all timestamp formats in betting data files to prevent `ValueError` exceptions during datetime parsing.

## Problem

The betting data files in `/data/bets/` can contain timestamps in various formats:
- `2025-12-11 00:00:00+00:00` (space separator with timezone)
- `2025-12-11T00:00:00.000Z` (ISO 8601 format)
- `2025-12-11T00:00:00Z` (ISO 8601 without milliseconds)
- Other variations with invisible Unicode characters

When the evaluation scripts try to parse these with `pd.to_datetime(..., format='ISO8601')`, inconsistent formats cause errors like:

```
ValueError: time data "2025-12-11 00:00:00+00:00" doesn't match format "%Y-%m-%dT%H:%M:%S.%f%z"
```

## Solution

This script:
1. Scans all `.txt` files in `/data/bets/`
2. Identifies timestamp columns (`timestamp`, `start_time`)
3. Converts all timestamps to standardized ISO 8601 format: `YYYY-MM-DDTHH:MM:SS.000Z`
4. Removes invisible Unicode characters (zero-width spaces, etc.)
5. Saves the cleaned data back to the original files

## Usage

### Manual Execution

Run the script manually from the project root:

```bash
python scripts/cleanup_bet_timestamps.py
```

### Automated Execution (GitHub Actions)

The script runs automatically in the GitHub Actions workflow **before** evaluating bets:

```yaml
- name: Clean up bet timestamps
  run: python scripts/cleanup_bet_timestamps.py

- name: Evaluate NBA bets
  run: python scripts/nba_evaluate_bets.py
```

This ensures all timestamps are standardized before any evaluation scripts attempt to parse them.

## Output

The script provides detailed output:

```
======================================================================
Betting Data Timestamp Cleanup Script
======================================================================

Scanning directory: /Users/aaronsmith/Code/llm_betting_model/data/bets
Found 11 betting data files

Processing: nba_bets_claude.txt
  Loaded 446 rows
  Cleaning 'timestamp' column...
    Cleaned 444 timestamp values
  Cleaning 'start_time' column...
    Cleaned 0 start_time values
  ✓ Saved cleaned file with 444 changes

...

======================================================================
Cleanup Complete!
Total changes made: 1604
======================================================================
```

## Features

- **Robust Parsing**: Uses pandas' flexible datetime parsing to handle multiple input formats
- **Unicode Cleanup**: Removes invisible zero-width characters that can cause parsing issues
- **Safe Processing**: Uses `on_bad_lines='skip'` to handle malformed CSV lines
- **Column Detection**: Automatically finds and renames timestamp columns with Unicode characters
- **Standardized Output**: All timestamps converted to `YYYY-MM-DDTHH:MM:SS.000Z` format

## Maintenance

This script should be run:
- **Automatically**: Before every bet evaluation in GitHub Actions (already configured)
- **Manually**: If you notice timestamp parsing errors in local development
- **After Updates**: When new betting data is added from external sources

## Related Files

- **Workflow**: `.github/workflows/01_evaluate_all_bets.yaml`
- **Data Directory**: `data/bets/`
- **Evaluation Scripts**: 
  - `scripts/nba_evaluate_bets.py`
  - `scripts/ncaab_evaluate_bets.py`
  - `scripts/soccer_evaluate_bets.py`
