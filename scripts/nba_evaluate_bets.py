import pandas as pd
import datetime
from pathlib import Path
import os

## only  need these to reload utils
# import importlib
# import utils

# # After making changes to your_module_name.py, run this cell
# importlib.reload(utils)


from utils import get_todays_games, filter_data_on_change, aggregate_betting_data, get_complete_game_results, process_and_save_evaluated_bets

HEADERS = {
    'Authority': 'api.actionnetwork',
    'Accept': 'application/json',
    'Origin': 'https://www.actionnetwork.com',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36'
}


def build_nba_prompt(model_version):

    df_all = pd.read_csv('./data/bets_db/nba_bets_db.csv')


    # Example usage:
    HEADERS = {
        'Authority': 'api.actionnetwork',
        'Accept': 'application/json',
        'Origin': 'https://www.actionnetwork.com',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36'
    }


    # Example usage:
    sport='nba'

    # Get today's date object
    today = datetime.date.today()

    # Define the desired string format
    date_format = '%Y%m%d'

    # Create the list using strftime() to format the dates
    date_str_list = [
        (today + datetime.timedelta(days=0)).strftime(date_format), # Today
        (today + datetime.timedelta(days=1)).strftime(date_format), # Tomorrow
        (today + datetime.timedelta(days=2)).strftime(date_format), # The next day
        (today + datetime.timedelta(days=3)).strftime(date_format)  # The day after
    ]



    df = get_todays_games(sport,date_str_list,HEADERS)
    df['date_scraped'] = datetime.datetime.now()

    df = df.loc[df['status'] == 'scheduled']

    df_all = pd.concat([df_all,df])
    df_all['date_scraped'] = pd.to_datetime(df_all['date_scraped'])

    dimension_cols = ['game_id', 'home_team', 'away_team']
    metric_cols = ['home_money_line', 'away_money_line','total_score','home_money_line','away_money_line']
    filtered_df = filter_data_on_change(df_all, dimension_cols, metric_cols)
    print(df_all.index.size)
    print(filtered_df.index.size)

    filtered_df.to_csv('./data/bets_db/nba_bets_db.csv', index=False)

    today = datetime.date.today()
    today_str = today.strftime('%Y%m%d')

    group_by_columns = ['game_id', 'home_team', 'away_team','start_time']
    metric_columns = [
        'num_bets', 'home_money_line', 'home_ml_ticket_pct', 'home_ml_money_pct',
        'away_money_line', 'away_ml_ticket_pct', 'away_ml_money_pct', 'total_score',
        'over_odds', 'under_odds', 'over_ticket_pct', 'over_money_pct',
        'under_ticket_pct', 'under_money_pct', 'home_spread', 'home_spread_odds',
        'home_spread_ticket_pct', 'home_spread_money_pct', 'away_spread',
        'away_spread_odds', 'away_spread_ticket_pct', 'away_spread_money_pct'
    ]

    filtered_df['start_time_pt'] = pd.to_datetime(filtered_df['start_time_pt'])

    next_games_list = df['game_id'].unique().tolist()

    games_list = filtered_df.loc[filtered_df['game_id'].isin(next_games_list)].groupby(['game_id','home_team','away_team','start_time_pt']).agg(rec_count=('date_scraped','size')).sort_values('start_time_pt', ascending=True).head(30).reset_index()['game_id'].tolist()

    df_agg = aggregate_betting_data(filtered_df.loc[filtered_df['game_id'].isin(games_list)], group_by_columns, metric_columns)

    df_agg = df_agg.sort_values('start_time',ascending=True)
    df_agg

    # Create the home_team_spread column
    df_agg['home_team_spread'] = df_agg['home_team'] + " " + df_agg['home_spread_last'].apply(lambda x: f"{x:+.1f}")

    # Create the away_team_spread column (assuming this is the second column you wanted)
    df_agg['away_team_spread'] = df_agg['away_team'] + " " + df_agg['away_spread_last'].apply(lambda x: f"{x:+.1f}")

    # display(df_agg[['home_team','away_team','home_spread_first','home_spread_last','home_team_spread','away_team_spread']])


    df_hist = pd.read_csv('./data/evaluated/nba_bet_picks_evaluated.csv')
    df_hist = df_hist.loc[df_hist['model'] == model_version]




    # 1. Convert your DataFrames to strings
    # df1_string = df_agg.to_string(index=False)
    # df2_string = df_hist.to_string(index=False)

    df1_string = df_agg.to_csv(index=False)
    df2_string = df_hist.to_csv(index=False)

    # 2. Use an f-string (note the 'f' before the quotes) 
    #    to insert the string versions into your prompt
    prompt = f"""
You are my expert NBA betting adviser.
I will provide you with two datasets:

Dataset 1: Betting lines for upcoming games (money line, over/under, spread with first/avg/last values)
Dataset 2: Historical betting results to analyze what's working and what's not

Your goal: Maximize ROI by learning from historical patterns.

CRITICAL VALIDATION REQUIREMENTS
1. HOME vs AWAY TEAM IDENTIFICATION - READ CAREFULLY
The dataset has two columns: home_team and away_team
MATCH NAMING CONVENTION (MANDATORY):

ALWAYS use format: "home_team vs away_team"
Example: If home_team=Thunder, away_team=Wizards → Write "Thunder vs Wizards"
The home team is ALWAYS listed first, away team second
This makes it crystal clear which team is playing at home

BEFORE MAKING ANY PICK:

Identify from the dataset: Which team is in the home_team column?
Identify from the dataset: Which team is in the away_team column?
Write the match as "home_team vs away_team"
Determine which team you want to pick
Set the binary indicator based on whether that team is home or away

BINARY INDICATOR RULES:

If you pick the HOME team's spread → bet_home_spread=1, bet_away_spread=0
If you pick the AWAY team's spread → bet_away_spread=1, bet_home_spread=0
If you pick the HOME team's ML → bet_home_ml=1, bet_away_ml=0
If you pick the AWAY team's ML → bet_away_ml=1, bet_home_ml=0

EXAMPLE:
Dataset shows: home_team=Thunder, away_team=Wizards
Match name: "Thunder vs Wizards"
If picking Thunder -15.5: bet_home_spread=1 (Thunder is home)
If picking Wizards +15.5: bet_away_spread=1 (Wizards is away)

---
### **2. ODDS AND LINES VALIDATION - NO EXCEPTIONS**

**Use ONLY the "_last" column values:**
- `home_money_line_last` for home team ML
- `away_money_line_last` for away team ML
- `home_spread_last` and `home_spread_odds_last` for home team spread
- `away_spread_last` and `away_spread_odds_last` for away team spread
- `total_score_last`, `over_odds_last`, `under_odds_last` for totals

**NEVER:**
- Invent odds
- Approximate odds
- Use "avg" or "first" values (only use for analysis of line movement)
- Make a pick if the line is not in the dataset

---

### **3. SPREAD DIRECTION RULES - READ CAREFULLY**

**Understanding Spread Signs:**
- **NEGATIVE spread (-X.X)** = That team is FAVORED by X.X points
- **POSITIVE spread (+X.X)** = That team is UNDERDOG getting X.X points

**Examples:**
- `home_spread_last = -5.5` means: Home team FAVORED by 5.5, Away team gets +5.5
- `home_spread_last = +3.5` means: Home team UNDERDOG getting +3.5, Away team favored by -3.5
- `away_spread_last = -7.0` means: Away team FAVORED by 7.0, Home team gets +7.0
- `away_spread_last = +4.0` means: Away team UNDERDOG getting +4.0, Home team favored by -4.0

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

---

### **6. CONFIDENCE & UNITS**

Please aim to make around 10 picks -- you can pick more or less, but I want to have at least 10 and then we can use the confidence to determine success

- Rank all picks by confidence (most confident = rank 1)
- Provide **confidence %** as integer between 0-100
- Assign units based on confidence:
- **3 units**: Highest confidence (90%+)
- **2 units**: Medium confidence (80-89%)
- **1 unit**: Lower confidence (70-79%)

---

### **7. PREDICTED SCORE FORMAT**

- Format: "HomeScore-AwayScore" (e.g., "115-112")
- Home team score ALWAYS listed first
- Away team score ALWAYS listed second
- Double-check the order matches your match naming

---

## **OUTPUT FORMAT**

### **Part 1: Human-Readable Table**

Create a table with these columns:
- Rank
- Match (format: "home_team vs away_team")
- Pick (e.g., "Thunder -15.5" or "Wizards +15.5")
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
- `pick`: State team name and line (e.g., "Thunder -15.5")
- `predicted_score`: Format as "HomeScore-AwayScore"
- `bet_home_spread`, `bet_home_ml`, `bet_away_spread`, `bet_away_ml`, `bet_over`, `bet_under`: Must be 0 or 1
- `home_money_line`: Value from `home_money_line_last`
- `away_money_line`: Value from `away_money_line_last`
- `tie_money_line`: Always "N/A"
- `total_score`: Value from `total_score_last`
- `over_odds`: Value from `over_odds_last`
- `under_odds`: Value from `under_odds_last`
- `home_spread`: Value from `home_spread_last`
- `home_spread_odds`: Value from `home_spread_odds_last`
- `away_spread`: Value from `away_spread_last`
- `away_spread_odds`: Value from `away_spread_odds_last`
- `timestamp`: Current analysis time in ISO format

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

---

## **EXAMPLE OF CORRECT PICK**

**Dataset shows:**
- game_id: 261702
- home_team: Thunder
- away_team: Wizards
- home_spread_last: -15.5
- home_spread_odds_last: -110

**Correct Pick:**
- Match: "Thunder vs Wizards"
- Pick: "Thunder -15.5"
- Odds: -110
- Binary: bet_home_spread=1, bet_away_spread=0, all others=0
- Predicted Score: "126-108" (Thunder score first)

**CSV Line:**
```
1,261702,2025-10-31T00:00:00.000Z,Thunder vs Wizards,Thunder -15.5,-110,3,96,"Reason here",126-108,1,0,0,0,0,0,-1200,750,N/A,231.5,-110,-109,-15.5,-110,15.5,-110,2025-10-30T18:30:00Z

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

    # Now you can print the full prompt
    print(prompt)

    ## write prompt to a text file
    with open(f"./prompts/nba_prompt_{model_version}.txt", "w") as f:
        f.write(prompt) 

    return df_agg







def process_results(model_name: str, picks_dir: Path, results_csv_path: Path, sport: str):
    """
    Processes betting picks for a given model against a game results CSV.
    
    It finds missing game results, fetches them from an API, appends them
    to the main results CSV, and then evaluates all picks.
    """
    # sport = 'ncaab'
    
    # === 1. Load Picks File ===
    picks_file = picks_dir / f'{sport}_bets_{model_name}.txt'
    try:
        df_picks = pd.read_csv(picks_file)
    except FileNotFoundError:
        print(f"Error: Picks file not found at {picks_file}")
        return None # Exit function

    # === 2. Process Pick Timestamps ===
    df_picks = df_picks.rename(columns={'timestamp\u200b': 'timestamp'})
    df_picks['timestamp'] = df_picks['timestamp'].str.replace('\u200b', '')
    df_picks['timestamp'] = pd.to_datetime(df_picks['timestamp'], format='ISO8601')
    df_picks['start_time_pt'] = (
        pd.to_datetime(df_picks['start_time'], utc=True)
        .dt.tz_convert('America/Los_Angeles')
    )
    df_picks['date'] = df_picks['start_time_pt'].dt.date
    df_picks['model'] = model_name

    # === 3. Load Existing Game Results ===
    # Check if the file exists *before* trying to read it.
    # This is key for knowing whether to write the header later.
    results_file_exists = results_csv_path.is_file()
    
    try:
        df_old_results = pd.read_csv(results_csv_path)
    except FileNotFoundError:
        print(f"Results file {results_csv_path} not found. A new one will be created.")
        df_old_results = pd.DataFrame() # Start with an empty DataFrame
        df_old_results['game_id'] = []
        df_old_results['status'] = []

    # === 4. Find Missing Results ===
    # display(df_picks.sample(3))

    df_merge = pd.merge(
        df_picks[['rank', 'game_id', 'match', 'date', 'start_time', 'pick']],
        df_old_results,
        on='game_id',
        how='left',
        suffixes=('_pick', '_result')
    )
    missing_games = df_merge.loc[df_merge['status'] != 'complete']

    # === 5. Fetch and Append New Results (if any) ===
    df_new_results = pd.DataFrame() # Initialize as empty

    if not missing_games.empty:
        date_str_list = missing_games['date'].astype(str).str.replace('-', '').unique().tolist()
        
        if date_str_list:
            print(f"Found missing results for {len(date_str_list)} dates. Fetching...")
            df_new_results = get_complete_game_results(sport, date_str_list, HEADERS)
            
            if not df_new_results.empty:
                print(f"Appending {len(df_new_results)} new results to {results_csv_path}")
                # Append new data
                df_new_results.to_csv(
                    results_csv_path,
                    mode='a',
                    # Write header ONLY if the file didn't exist before
                    header=not results_file_exists, 
                    index=False
                )
            else:
                print("API call returned no new results.")
    else:
        print("No missing game results found. All picks are up-to-date.")

    # === 6. Combine All Results for Final Processing ===
    # *** THIS IS THE MAIN LOGIC FIX ***
    # Combine the old results and the brand-newly fetched results
    df_all_results = pd.concat([df_old_results, df_new_results], ignore_index=True)

    # Drop duplicates in case the API sent a game we already had
    if 'game_id' in df_all_results.columns and not df_all_results.empty:
        df_all_results = df_all_results.drop_duplicates(subset='game_id', keep='last')

    # === 7. Process and Save Evaluations ===
    # Pass the *complete* set of results (old + new)
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


model_list = ['v2', 'v2_perp','gemini','chatgpt']

for model_name in model_list:
    sport = 'nba'
    base_dir = Path('./data/bets')
    results_file = Path('./data/evaluated/nba_game_results.csv')
    df_evaluated_hist = process_results(model_name, base_dir, results_file, sport)