import pandas as pd
import datetime
from pathlib import Path
import os
import sys

# Add parent directory to path for utils import
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir / 'scripts'))

from utils import get_todays_games, filter_data_on_change, aggregate_betting_data, get_complete_game_results, process_and_save_evaluated_bets

HEADERS = {
    'Authority': 'api.actionnetwork',
    'Accept': 'application/json',
    'Origin': 'https://www.actionnetwork.com',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36'
}


def build_soccer_prompt(model_name, hours_ahead = 2):
    """
    Build soccer betting prompt for a specific model.
    
    Args:
        model_name: Model name (chatgpt, claude, deepseek, gemini, grok)
    
    Returns:
        DataFrame with aggregated betting data
    """
    
    # Ensure directories exist (parent directory since we're in scripts/)
    Path('./data/bets').mkdir(parents=True, exist_ok=True)
    Path('./data/bets_db').mkdir(parents=True, exist_ok=True)
    Path('./data/evaluated').mkdir(parents=True, exist_ok=True)
    
    # Load existing soccer bets database
    db_path = Path('./data/bets_db/soccer_bets_db.csv')
    if db_path.exists():
        df_all = pd.read_csv(db_path)
    else:
        df_all = pd.DataFrame()
        print("Creating new soccer_bets_db.csv")

    # Sport is soccer
    sport = 'soccer'

    # Get today's date and next few days
    today = datetime.date.today()
    date_format = '%Y%m%d'
    
    # Get games for next 4 days
    date_str_list = [
        (today + datetime.timedelta(days=-1)).strftime(date_format),
        (today + datetime.timedelta(days=0)).strftime(date_format),  # Today
        (today + datetime.timedelta(days=1)).strftime(date_format),  # Tomorrow
        (today + datetime.timedelta(days=2)).strftime(date_format),  # Day after
        (today + datetime.timedelta(days=3)).strftime(date_format)   # 3 days out
    ]

    # Fetch today's games
    df = get_todays_games(sport, date_str_list, HEADERS)
    df['date_scraped'] = datetime.datetime.now()

    # Only keep scheduled games
    df = df.loc[df['status'] == 'scheduled']

    # Combine with historical data
    if not df_all.empty:
        df_all = pd.concat([df_all, df])
        df_all['date_scraped'] = pd.to_datetime(df_all['date_scraped'])

        # Filter for changes in key metrics
        dimension_cols = ['game_id', 'home_team', 'away_team']
        metric_cols = ['home_money_line', 'away_money_line', 'total_score', 'tie_money_line']
        filtered_df = filter_data_on_change(df_all, dimension_cols, metric_cols)
        
        print(f"Total records: {df_all.index.size}")
        print(f"Filtered records: {filtered_df.index.size}")
    else:
        filtered_df = df

    # Save updated database
    filtered_df.to_csv('./data/bets_db/soccer_bets_db.csv', index=False)

    # Aggregate betting data
    group_by_columns = ['game_id', 'home_team', 'away_team', 'start_time']
    metric_columns = [
        'num_bets', 'home_money_line', 'home_ml_ticket_pct', 'home_ml_money_pct',
        'away_money_line', 'away_ml_ticket_pct', 'away_ml_money_pct',
        'tie_money_line', 'tie_ml_ticket_pct', 'tie_ml_money_pct',  # Soccer-specific
        'total_score', 'over_odds', 'under_odds', 'over_ticket_pct', 'over_money_pct',
        'under_ticket_pct', 'under_money_pct', 'home_spread', 'home_spread_odds',
        'home_spread_ticket_pct', 'home_spread_money_pct', 'away_spread',
        'away_spread_odds', 'away_spread_ticket_pct', 'away_spread_money_pct'
    ]

    # Convert start_time_pt to datetime
    filtered_df['start_time_pt'] = pd.to_datetime(filtered_df['start_time_pt'])

    # Get next games list
    next_games_list = df['game_id'].unique().tolist()

    # Get top 30 upcoming games
    games_list = (filtered_df.loc[filtered_df['game_id'].isin(next_games_list)]
                  .groupby(['game_id', 'home_team', 'away_team', 'start_time_pt'])
                  .agg(rec_count=('date_scraped', 'size'))
                  .sort_values('start_time_pt', ascending=True)
                  .head(30)
                  .reset_index()['game_id'].tolist())

    # Aggregate betting data for selected games
    df_agg = aggregate_betting_data(
        filtered_df.loc[filtered_df['game_id'].isin(games_list)],
        group_by_columns,
        metric_columns
    )

    df_agg = df_agg.sort_values('start_time', ascending=True)

    # Create spread columns for display
    df_agg['home_team_spread'] = df_agg['home_team'] + " " + df_agg['home_spread_last'].apply(lambda x: f"{x:+.1f}")
    df_agg['away_team_spread'] = df_agg['away_team'] + " " + df_agg['away_spread_last'].apply(lambda x: f"{x:+.1f}")

    # Load historical results for this model
    hist_path = Path(f'./data/evaluated/soccer_bet_picks_evaluated.csv')
    if hist_path.exists():
        df_hist = pd.read_csv(hist_path)
        df_hist = df_hist.loc[df_hist['model'] == model_name]
    else:
        df_hist = pd.DataFrame()
        print(f"No historical data found for {model_name}")

    # Filter df_agg to only include games starting within the next 2 hours
    current_time = pd.Timestamp.now(tz='America/Los_Angeles')
    n_hours_from_now = current_time + pd.Timedelta(hours=hours_ahead)
    
    # Convert start_time to datetime if not already
    df_agg['start_time'] = pd.to_datetime(df_agg['start_time'])
    df_agg['start_time_pt'] = df_agg['start_time'].dt.tz_convert('America/Los_Angeles')
    
    # Filter for games starting within next n hours
    df_agg_filtered = df_agg[df_agg['start_time_pt'] <= n_hours_from_now].copy()
    
    print(f"Total games in df_agg: {len(df_agg)}")
    print(f"Games starting within next {hours_ahead} hours: {len(df_agg_filtered)}")

    # Define the prompt file path
    prompt_path = Path(f"./prompts/soccer_prompt_{model_name}.txt")
    
    # If no games in the next 2 hours, delete the prompt file if it exists and return
    if len(df_agg_filtered) == 0:
        print(f"No games starting within {hours_ahead} hours for {model_name}. Skipping prompt generation.")
        if prompt_path.exists():
            prompt_path.unlink()
            print(f"Removed existing prompt file: {prompt_path}")
        return df_agg

    # Convert DataFrames to CSV strings for prompt
    df1_string = df_agg_filtered.to_csv(index=False)
    df2_string = df_hist.to_csv(index=False) if not df_hist.empty else "No historical data yet"

    # Build the prompt (soccer-specific, following NBA/NCAAB structure)
    prompt = f"""
You are my expert Soccer betting adviser.
I will provide you with two datasets:

Dataset 1: Betting lines for upcoming games (money line, over/under, spread with first/avg/last values)
Dataset 2: Historical betting results to analyze what's working and what's not

Your goal: Maximize ROI by learning from historical patterns.

CRITICAL VALIDATION REQUIREMENTS
1. HOME vs AWAY TEAM IDENTIFICATION - READ CAREFULLY
The dataset has two columns: home_team and away_team
MATCH NAMING CONVENTION (MANDATORY):

ALWAYS use format: "home_team vs away_team"
Example: If home_team=Liverpool, away_team=Arsenal → Write "Liverpool vs Arsenal"
The home team is ALWAYS listed first, away team second
This makes it crystal clear which team is playing at home

BEFORE MAKING ANY PICK:

Identify from the dataset: Which team is in the home_team column?
Identify from the dataset: Which team is in the away_team column?
Write the match as "home_team vs away_team"
Determine which team you want to pick (or if you're picking a draw)
Set the binary indicator based on whether that team is home or away

BINARY INDICATOR RULES:

If you pick the HOME team's spread → bet_home_spread=1, bet_away_spread=0
If you pick the AWAY team's spread → bet_away_spread=1, bet_home_spread=0
If you pick the HOME team's ML → bet_home_ml=1, bet_away_ml=0
If you pick the AWAY team's ML → bet_away_ml=1, bet_home_ml=0
**SOCCER SPECIFIC**: If you pick a DRAW/TIE → This is NOT a standard bet type in our system, avoid draw picks

EXAMPLE:
Dataset shows: home_team=Liverpool, away_team=Arsenal
Match name: "Liverpool vs Arsenal"
If picking Liverpool -1.5: bet_home_spread=1 (Liverpool is home)
If picking Arsenal +1.5: bet_away_spread=1 (Arsenal is away)

---
### **2. ODDS AND LINES VALIDATION - NO EXCEPTIONS**

**Use ONLY the "_last" column values:**
- `home_money_line_last` for home team ML
- `away_money_line_last` for away team ML
- `tie_money_line_last` for draw ML (INFORMATIONAL ONLY - do not pick draws)
- `home_spread_last` and `home_spread_odds_last` for home team spread
- `away_spread_last` and `away_spread_odds_last` for away team spread
- `total_score_last`, `over_odds_last`, `under_odds_last` for totals

**NEVER:**
- Invent odds
- Approximate odds
- Use "avg" or "first" values (only use for analysis of line movement)
- Make a pick if the line is not in the dataset
- Pick draws/ties (our system doesn't support 3-way outcomes)

---

### **3. SPREAD DIRECTION RULES - READ CAREFULLY**

**Understanding Spread Signs (Asian Handicap in Soccer):**
- **NEGATIVE spread (-X.X)** = That team is FAVORED by X.X goals
- **POSITIVE spread (+X.X)** = That team is UNDERDOG getting X.X goals

**Examples:**
- `home_spread_last = -1.5` means: Home team FAVORED by 1.5 goals, Away team gets +1.5
- `home_spread_last = +0.5` means: Home team UNDERDOG getting +0.5, Away team favored by -0.5
- `away_spread_last = -1.0` means: Away team FAVORED by 1.0 goal, Home team gets +1.0
- `away_spread_last = +1.0` means: Away team UNDERDOG getting +1.0, Home team favored by -1.0

**Critical Understanding:**
- If `home_spread_last` is negative → home team is favorite
- If `home_spread_last` is positive → home team is underdog
- If `away_spread_last` is negative → away team is favorite
- If `away_spread_last` is positive → away team is underdog

---

### **4. MANDATORY DOUBLE-CHECK PROCESS**

**Before finalizing EACH pick, complete these steps:**

□ **Step 1**: Look at dataset - which team is `home_team`, which is `away_team`?
□ **Step 2**: Write match as "home_team vs away_team"
□ **Step 3**: Decide which team I want to pick
□ **Step 4**: Is that team home or away?
□ **Step 5**: Look up the EXACT line for that team in the "_last" columns
□ **Step 6**: Copy the EXACT odds from the corresponding "_odds_last" column
□ **Step 7**: Verify the sign (+ or -) matches favorite/underdog position
□ **Step 8**: Set binary indicator: bet_home_X=1 if home team, bet_away_X=1 if away team
□ **Step 9**: Cross-check one final time before writing

**If you are uncertain about ANY detail, SKIP THAT PICK rather than guess.**

---

### **5. PICK TYPES AND BINARY INDICATORS**

You can make six types of picks:

| Pick Type | Columns to Use | Binary Indicators |
|-----------|----------------|-------------------|
| Home ML | `home_money_line_last` | `bet_home_ml=1, bet_away_ml=0` |
| Away ML | `away_money_line_last` | `bet_away_ml=1, bet_home_ml=0` |
| Home Spread | `home_spread_last`, `home_spread_odds_last` | `bet_home_spread=1, bet_away_spread=0` |
| Away Spread | `away_spread_last`, `away_spread_odds_last` | `bet_away_spread=1, bet_home_spread=0` |
| Over | `total_score_last`, `over_odds_last` | `bet_over=1, bet_under=0` |
| Under | `total_score_last`, `under_odds_last` | `bet_under=1, bet_over=0` |

**All other binary indicators must be set to 0.**

**IMPORTANT**: Do NOT pick draws/ties. While `tie_money_line_last` is in the dataset, our evaluation system only supports 2-way outcomes (home/away wins).

---

### **6. CONFIDENCE & UNITS**

Please aim to evaluate each game and pick a winner and an over / under as well as a confidence level for each pick.

- Rank all picks by confidence (most confident = rank 1)
- Provide **confidence %** as integer between 0-100
- Assign units based on confidence:
- **3 units**: Highest confidence (90%+)
- **2 units**: Medium confidence (80-89%)
- **1 unit**: Lower confidence (70-79%)

---

### **7. PREDICTED SCORE FORMAT**

- Format: "HomeScore-AwayScore" (e.g., "2-1")
- Home team score ALWAYS listed first
- Away team score ALWAYS listed second
- Double-check the order matches your match naming
- **Soccer scores typically range 0-5 goals per team**

---

## **OUTPUT FORMAT**

### **Part 1: Human-Readable Table**

Create a table with these columns:
- Rank
- Match (format: "home_team vs away_team")
- Pick (e.g., "Liverpool -1.5" or "Arsenal +1.5")
- Odds
- Units
- Confidence %
- Reason
- Predicted Score (format: "HomeScore-AwayScore")

### **Part 2: CSV Block (Copy/Paste Ready)**

Exact structure with this header row:
```
rank,game_id,start_time,match,pick,odds,units,confidence_pct,reason,predicted_score,bet_home_spread,bet_home_ml,bet_away_spread,bet_away_ml,bet_over,bet_under,home_money_line,away_money_line,tie_money_line,total_score,over_odds,under_odds,home_spread,home_spread_odds,away_spread,away_spread_odds,timestamp
```
**CSV Requirements:**
- `match`: Must use "home_team vs away_team" format
- `home_team`: home team
- `away_team`: away team
- `pick`: State team name and line (e.g., "Liverpool -1.5")
- `predicted_score`: Format as "HomeScore-AwayScore"
- `bet_home_spread`, `bet_home_ml`, `bet_away_spread`, `bet_away_ml`, `bet_over`, `bet_under`: Must be 0 or 1
- `home_money_line`: Value from `home_money_line_last`
- `away_money_line`: Value from `away_money_line_last`
- `tie_money_line`: Value from `tie_money_line_last` (for reference, but don't pick draws)
- `total_score`: Value from `total_score_last`
- `over_odds`: Value from `over_odds_last`
- `under_odds`: Value from `under_odds_last`
- `home_spread`: Value from `home_spread_last`
- `home_spread_odds`: Value from `home_spread_odds_last`
- `away_spread`: Value from `away_spread_last`
- `away_spread_odds`: Value from `away_spread_odds_last`
- `timestamp`: Current analysis time in ISO 8601 format
  - **CRITICAL FORMAT REQUIREMENT**: MUST use "T" separator (NOT a space) between date and time
  - **REQUIRED FORMAT**: "YYYY-MM-DDTHH:MM:SS.000Z" (with the T and .000Z)
  - **CORRECT EXAMPLES**: "2025-12-08T18:30:00.000Z", "2025-12-08T18:30:00Z"
  - **WRONG EXAMPLES**: "2025-12-08 18:30:00+00:00" (space instead of T), "2025-12-08 18:30:00.000Z" (space instead of T)
  - Use ONLY standard ASCII characters - NO invisible Unicode characters
  - The column name must be exactly: timestamp (no extra characters)

---

## **FINAL VERIFICATION CHECKLIST**

Before submitting your picks, verify:

□ Every match uses "home_team vs away_team" format
□ Every pick references the correct team (home or away)
□ Every odds value is copied exactly from "_last" column
□ Every binary indicator correctly reflects whether the picked team is home or away
□ Every spread sign (+ or -) matches the favorite/underdog position
□ Every predicted score is in "HomeScore-AwayScore" format
□ All CSV columns match the exact structure required
□ Ensure the reason column in the csv is enclosed in double quotes
□ The timestamp column name has NO invisible Unicode characters (must be exactly "timestamp")
□ The timestamp value is in valid ISO 8601 format with only standard ASCII characters

---

## **EXAMPLE OF CORRECT PICK**

**Dataset shows:**
- game_id: 260944
- home_team: Liverpool
- away_team: Arsenal
- home_spread_last: -1.5
- home_spread_odds_last: -110

**Correct Pick:**
- Match: "Liverpool vs Arsenal"
- Pick: "Liverpool -1.5"
- Odds: -110
- Binary: bet_home_spread=1, bet_away_spread=0, all others=0
- Predicted Score: "2-1" (Liverpool score first)

**CSV Line:**
```
1,260944,2025-11-01T15:00:00.000Z,Liverpool vs Arsenal,Liverpool -1.5,-110,3,95,"Reason here",2-1,1,0,0,0,0,0,-180,145,210,2.5,-110,-110,-1.5,-110,1.5,-110,2025-11-01T12:00:00Z

Remember: Accuracy is more important than quantity. Skip any pick where you have uncertainty.


Here are the upcoming games and their odds:
{df1_string}

Here is the historical dataset of your betting advice and results:
{df2_string}
    """

    print('-------')
    print('-------')
    print('-------')
    print('-------')
    print(prompt)

    # Write prompt to file
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(prompt_path, "w") as f:
        f.write(prompt)
    
    print(f"\nPrompt file created: {prompt_path}")

    return df_agg


def process_soccer_results(model_name: str, picks_dir: Path, results_csv_path: Path):
    """
    Process soccer betting results for a given model.
    
    Args:
        model_name: Model name (chatgpt, claude, deepseek, gemini, grok)
        picks_dir: Directory containing picks files
        results_csv_path: Path to game results CSV
    
    Returns:
        DataFrame with evaluated bets
    """
    sport = 'soccer'
    
    # Load picks file
    picks_file = picks_dir / f'soccer_bets_{model_name}.txt'
    try:
        df_picks = pd.read_csv(picks_file)
    except FileNotFoundError:
        print(f"Error: Picks file not found at {picks_file}")
        return None

    # Process timestamps
    df_picks = df_picks.rename(columns={'timestamp\u200b': 'timestamp'})
    df_picks['timestamp'] = df_picks['timestamp'].str.replace('\u200b', '')
    df_picks['timestamp'] = pd.to_datetime(df_picks['timestamp'], format='ISO8601')
    df_picks['start_time_pt'] = (
        pd.to_datetime(df_picks['start_time'], utc=True)
        .dt.tz_convert('America/Los_Angeles')
    )
    df_picks['date'] = df_picks['start_time_pt'].dt.date
    df_picks['model'] = model_name

    # Load existing game results
    results_file_exists = results_csv_path.is_file()
    
    try:
        df_old_results = pd.read_csv(results_csv_path)
    except FileNotFoundError:
        print(f"Results file {results_csv_path} not found. A new one will be created.")
        df_old_results = pd.DataFrame()
        df_old_results['game_id'] = []
        df_old_results['status'] = []

    # Find missing results
    df_merge = pd.merge(
        df_picks[['rank', 'game_id', 'match', 'date', 'start_time', 'pick']],
        df_old_results,
        on='game_id',
        how='left',
        suffixes=('_pick', '_result')
    )
    missing_games = df_merge.loc[df_merge['status'] != 'complete']

    # Fetch and append new results if needed
    df_new_results = pd.DataFrame()

    if not missing_games.empty:
        date_str_list = missing_games['date'].astype(str).str.replace('-', '').unique().tolist()
        
        if date_str_list:
            print(f"Found missing results for {len(date_str_list)} dates. Fetching...")
            df_new_results = get_complete_game_results(sport, date_str_list, HEADERS)
            
            if not df_new_results.empty:
                print(f"Appending {len(df_new_results)} new results to {results_csv_path}")
                df_new_results.to_csv(
                    results_csv_path,
                    mode='a',
                    header=not results_file_exists,
                    index=False
                )
            else:
                print("API call returned no new results.")
    else:
        print("No missing game results found. All picks are up-to-date.")

    # Combine all results
    df_all_results = pd.concat([df_old_results, df_new_results], ignore_index=True)

    # Drop duplicates
    if 'game_id' in df_all_results.columns and not df_all_results.empty:
        df_all_results = df_all_results.drop_duplicates(subset='game_id', keep='last')

    # Process and save evaluations
    df_evaluated, df_evaluated_hist = process_and_save_evaluated_bets(
        df_picks,
        df_all_results,
        sport
    )

    if 'date' in df_evaluated_hist.columns:
        df_evaluated_hist['date'] = pd.to_datetime(df_evaluated_hist['date'])
    else:
        print("Warning: 'df_evaluated_hist' has no 'date' column to convert.")

    return df_evaluated_hist


# Model list for soccer
MODEL_LIST = ['chatgpt', 'claude', 'deepseek', 'gemini', 'grok']

if __name__ == '__main__':
    # Build prompts for all models
    for model_name in MODEL_LIST:
        print(f"\n{'='*60}")
        print(f"Building prompt for model: {model_name}")
        print(f"{'='*60}")
        df = build_soccer_prompt(model_name, hours_ahead=2)
        print(f"Completed {model_name}\n")
