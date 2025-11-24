# File Structure Reorganization Summary

## Date: November 24, 2024

### Overview
Reorganized the `llm_betting_model` repository to improve file organization and consistency.

---

## Changes Made

### 1. Renamed `cbb` to `ncaab`
All files and references using `cbb` (College Basketball) have been renamed to `ncaab` (NCAA Basketball) for consistency:

**Files Renamed:**
- `data/cbb_bets_claude.txt` → `data/bets/ncaab_bets_claude.txt`
- `data/cbb_bets_gemini.txt` → `data/bets/ncaab_bets_gemini.txt`
- `data/cbb_bets_perp.txt` → `data/bets/ncaab_bets_perp.txt`
- `data/ncaa_bets_db.csv` → `data/bets_db/ncaab_bets_db.csv`

---

### 2. New Directory Structure

Created three subdirectories under `data/` to organize files by purpose:

#### **`data/bets/`** - Current betting picks
Contains active bet files (*.txt) for each model:
- NBA: `nba_bets_gemini.txt`, `nba_bets_v2.txt`, `nba_bets_v2_perp.txt`
- NCAAB: `ncaab_bets_claude.txt`, `ncaab_bets_gemini.txt`, `ncaab_bets_perp.txt`
- Soccer: `soccer_bets_cliff.txt`, `soccer_bets_david.txt`, `soccer_bets_gary.txt`

#### **`data/bets_db/`** - Historical betting databases
Contains accumulated betting line data:
- `nba_bets_db.csv`
- `ncaab_bets_db.csv`
- `soccer_bets_db.csv`

#### **`data/evaluated/`** - Evaluated results and game outcomes
Contains evaluation results and game results:
- `nba_bet_picks.csv`, `nba_bet_picks_evaluated.csv`, `nba_game_results.csv`
- `ncaab_bet_picks.csv`, `ncaab_bet_picks_evaluated.csv`, `ncaab_game_results.csv`
- `soccer_bet_picks.csv`, `soccer_bet_picks_evaluated.csv`, `soccer_game_results.csv`

---

### 3. Updated Scripts

All Python scripts have been updated to reference the new directory structure:

#### **Build Prompt Scripts:**
- `scripts/nba_build_prompt.py`
- `scripts/ncaab_build_prompt.py`
- `scripts/soccer_build_prompt.py`

**Changes:**
- Database reads: `./data/bets_db/{sport}_bets_db.csv`
- Database writes: `./data/bets_db/{sport}_bets_db.csv`
- Historical data: `./data/evaluated/{sport}_bet_picks_evaluated.csv`

#### **Evaluate Bets Scripts:**
- `scripts/nba_evaluate_bets.py`
- `scripts/ncaab_evaluate_bets.py`
- `scripts/soccer_evaluate_bets.py`

**Changes:**
- Picks directory: `./data/bets/`
- Results file: `./data/evaluated/{sport}_game_results.csv`
- Historical data: `./data/evaluated/{sport}_bet_picks_evaluated.csv`

#### **Utility Functions:**
- `scripts/utils.py`

**Changes:**
- Updated `process_and_save_evaluated_bets()` to use `./data/evaluated/` for picks and evaluated files

---

## Directory Structure (After)

```
llm_betting_model/
├── data/
│   ├── bets/                    # Current betting picks (*.txt)
│   │   ├── nba_bets_*.txt
│   │   ├── ncaab_bets_*.txt
│   │   └── soccer_bets_*.txt
│   ├── bets_db/                 # Historical betting databases
│   │   ├── nba_bets_db.csv
│   │   ├── ncaab_bets_db.csv
│   │   └── soccer_bets_db.csv
│   └── evaluated/               # Evaluated results & game outcomes
│       ├── *_bet_picks.csv
│       ├── *_bet_picks_evaluated.csv
│       └── *_game_results.csv
├── prompts/
│   ├── nba_prompt_*.txt
│   ├── ncaab_prompt_*.txt
│   └── soccer_prompt_*.txt
└── scripts/
    ├── nba_build_prompt.py
    ├── nba_evaluate_bets.py
    ├── ncaab_build_prompt.py
    ├── ncaab_evaluate_bets.py
    ├── soccer_build_prompt.py
    ├── soccer_evaluate_bets.py
    └── utils.py
```

---

## Benefits

1. **Clearer Organization**: Files are now grouped by their purpose (active bets, databases, results)
2. **Consistency**: All references to NCAA Basketball now use `ncaab` instead of mixed `cbb`/`ncaa`
3. **Easier Navigation**: Developers can quickly find the type of file they need
4. **Better Separation**: Active bets are separated from historical data and evaluation results
5. **Scalability**: Adding new sports or models follows a clear pattern

---

## Migration Notes

- All file paths in scripts have been updated automatically
- Git history preserves the file rename operations
- No data was lost during the reorganization
- The Jupyter notebooks (*.ipynb) may need manual updates if used

---

## Testing Recommendations

Before deploying to production:
1. ✅ Run `nba_build_prompt.py` to verify database access
2. ✅ Run `nba_evaluate_bets.py` to verify bet evaluation
3. ✅ Run `ncaab_build_prompt.py` to verify ncaab renaming
4. ✅ Run `soccer_build_prompt.py` to verify soccer paths
5. ✅ Check GitHub Actions workflows for any hardcoded paths

---

## Commit Information

**Commit Hash**: 6a6d055
**Commit Message**: "Reorganize file structure: rename cbb to ncaab, create bets/bets_db/evaluated directories"
**Files Changed**: 29 files
**Insertions**: 44
**Deletions**: 29
