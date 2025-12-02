import pandas as pd
import datetime
from pathlib import Path
import sys

# Add parent directory to path for utils import
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir / 'scripts'))

from utils import get_complete_game_results, process_and_save_evaluated_bets

HEADERS = {
    'Authority': 'api.actionnetwork',
    'Accept': 'application/json',
    'Origin': 'https://www.actionnetwork.com',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36'
}


def evaluate_soccer_bets(model_name: str):
    """
    Evaluate soccer betting picks for a specific model.
    
    Args:
        model_name: Model name (chatgpt, claude, deepseek, gemini, grok)
    
    Returns:
        DataFrame with evaluated bets including historical data
    """
    # Ensure data directories exist (parent directory since we're in scripts/)
    Path('./data/bets').mkdir(parents=True, exist_ok=True)
    Path('./data/bets_db').mkdir(parents=True, exist_ok=True)
    Path('./data/evaluated').mkdir(parents=True, exist_ok=True)
    
    sport = 'soccer'
    picks_dir = Path('./data/bets')
    results_csv_path = Path('./data/evaluated/soccer_game_results.csv')
    
    # Load picks file
    picks_file = picks_dir / f'soccer_bets_{model_name}.txt'
    
    if not picks_file.exists():
        print(f"Error: Picks file not found at {picks_file}")
        print(f"Please ensure you have a file at: {picks_file}")
        return None
    
    try:
        df_picks = pd.read_csv(picks_file)
        print(f"Loaded {len(df_picks)} picks for {model_name}")
    except Exception as e:
        print(f"Error loading picks file: {e}")
        return None

    # Process timestamps - handle various formats
    if 'timestamp\u200b' in df_picks.columns:
        df_picks = df_picks.rename(columns={'timestamp\u200b': 'timestamp'})
    
    if 'timestamp' in df_picks.columns:
        df_picks['timestamp'] = df_picks['timestamp'].astype(str).str.replace('\u200b', '')
        try:
            df_picks['timestamp'] = pd.to_datetime(df_picks['timestamp'], format='ISO8601')
        except:
            df_picks['timestamp'] = pd.to_datetime(df_picks['timestamp'])
    
    # Process start times
    df_picks['start_time_pt'] = (
        pd.to_datetime(df_picks['start_time'], utc=True)
        .dt.tz_convert('America/Los_Angeles')
    )
    df_picks['date'] = df_picks['start_time_pt'].dt.date
    df_picks['model'] = model_name

    # Load existing game results
    results_file_exists = results_csv_path.is_file()
    
    if results_file_exists:
        try:
            df_old_results = pd.read_csv(results_csv_path)
            print(f"Loaded {len(df_old_results)} existing game results")
        except Exception as e:
            print(f"Error loading results file: {e}")
            df_old_results = pd.DataFrame()
            df_old_results['game_id'] = []
            df_old_results['status'] = []
    else:
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
    print(f"Found {len(missing_games)} games with missing results")

    # Fetch and append new results if needed
    df_new_results = pd.DataFrame()

    if not missing_games.empty:
        date_str_list = missing_games['date'].astype(str).str.replace('-', '').unique().tolist()
        
        if date_str_list:
            print(f"Fetching results for {len(date_str_list)} dates: {date_str_list}")
            try:
                df_new_results = get_complete_game_results(sport, date_str_list, HEADERS)
                
                if not df_new_results.empty:
                    print(f"Fetched {len(df_new_results)} new game results")
                    print(f"Appending to {results_csv_path}")
                    
                    # Save new results
                    df_new_results.to_csv(
                        results_csv_path,
                        mode='a',
                        header=not results_file_exists,
                        index=False
                    )
                else:
                    print("API call returned no new results.")
            except Exception as e:
                print(f"Error fetching game results: {e}")
    else:
        print("No missing game results found. All picks are up-to-date.")

    # Combine all results
    df_all_results = pd.concat([df_old_results, df_new_results], ignore_index=True)

    # Drop duplicates
    if 'game_id' in df_all_results.columns and not df_all_results.empty:
        df_all_results = df_all_results.drop_duplicates(subset='game_id', keep='last')
        print(f"Total game results after deduplication: {len(df_all_results)}")

    # Process and save evaluations
    print(f"\nEvaluating {len(df_picks)} picks against {len(df_all_results)} game results...")
    
    try:
        df_evaluated, df_evaluated_hist = process_and_save_evaluated_bets(
            df_picks,
            df_all_results,
            sport
        )
        
        print(f"Evaluation complete!")
        print(f"Evaluated picks: {len(df_evaluated)}")
        
        # Display summary statistics
        if not df_evaluated.empty and 'bet_result' in df_evaluated.columns:
            wins = (df_evaluated['bet_result'] == 'win').sum()
            losses = (df_evaluated['bet_result'] == 'loss').sum()
            total = len(df_evaluated)
            win_rate = (wins / total * 100) if total > 0 else 0
            
            print(f"\n{'='*60}")
            print(f"SUMMARY FOR {model_name.upper()}")
            print(f"{'='*60}")
            print(f"Total Evaluated: {total}")
            print(f"Wins: {wins}")
            print(f"Losses: {losses}")
            print(f"Win Rate: {win_rate:.1f}%")
            
            if 'bet_payout' in df_evaluated.columns:
                total_payout = df_evaluated['bet_payout'].sum()
                total_units = df_evaluated['units'].sum()
                roi = (total_payout / total_units * 100) if total_units > 0 else 0
                print(f"Total Payout: {total_payout:+.2f} units")
                print(f"Total Units Wagered: {total_units:.2f}")
                print(f"ROI: {roi:+.1f}%")
            print(f"{'='*60}\n")

        # Convert date column if present
        if 'date' in df_evaluated_hist.columns:
            df_evaluated_hist['date'] = pd.to_datetime(df_evaluated_hist['date'])

        return df_evaluated_hist
        
    except Exception as e:
        print(f"Error during evaluation: {e}")
        import traceback
        traceback.print_exc()
        return None


# Model list for soccer
MODEL_LIST = ['chatgpt', 'claude', 'deepseek', 'gemini', 'grok']

if __name__ == '__main__':
    print("Soccer Bet Evaluation Script")
    print("="*60)
    
    # Evaluate all models
    results = {}
    for model_name in MODEL_LIST:
        print(f"\nEvaluating model: {model_name}")
        print("-"*60)
        df_result = evaluate_soccer_bets(model_name)
        if df_result is not None:
            results[model_name] = df_result
        print()
    
    # Summary across all models
    if results:
        print("\n" + "="*60)
        print("OVERALL SUMMARY")
        print("="*60)
        for model_name, df in results.items():
            if not df.empty and 'bet_result' in df.columns:
                wins = (df['bet_result'] == 'win').sum()
                total = len(df)
                win_rate = (wins / total * 100) if total > 0 else 0
                payout = df['bet_payout'].sum() if 'bet_payout' in df.columns else 0
                print(f"{model_name:10s}: {total:3d} bets | {win_rate:5.1f}% win rate | {payout:+7.2f} units")
        print("="*60)
