#!/usr/bin/env python3
"""
Find Moneyline Betting Opportunities

This script analyzes upcoming bets and identifies games where betting the moneyline
instead of the spread offers better value.
"""

import pandas as pd
import glob
from pathlib import Path
import os


def find_moneyline_opportunities():
    """Find moneyline opportunities in upcoming bets."""
    
    print("="*80)
    print("MONEYLINE OPPORTUNITY FINDER")
    print("="*80)
    print()
    
    # Load all bet files
    bets_dir = Path('./data/bets')
    bet_files = list(bets_dir.glob('*_bets_*.txt'))
    
    if not bet_files:
        print(f"No bet files found in {bets_dir}")
        return
    
    print(f"Found {len(bet_files)} bet files")
    
    all_opportunities = []
    
    for filepath in bet_files:
        try:
            df = pd.read_csv(filepath)
            
            # Filter for upcoming games (no scores yet)
            upcoming = df[
                (df['home_score'].isna() | (df['home_score'] == '')) &
                (df['away_score'].isna() | (df['away_score'] == ''))
            ].copy()
            
            if len(upcoming) == 0:
                continue
            
            model = filepath.stem.replace('_bets_', '_').split('_')[1]
            
            # Analyze each upcoming bet
            for idx, row in upcoming.iterrows():
                pick = str(row.get('pick', ''))
                
                # Check if it's a spread bet with underdog
                if '+' in pick and 'Over' not in pick and 'Under' not in pick and 'ML' not in pick:
                    # Extract spread value
                    parts = pick.split()
                    if len(parts) >= 2:
                        team = ' '.join(parts[:-1])
                        line = parts[-1]
                        
                        try:
                            spread_value = float(line.replace('+', ''))
                        except:
                            continue
                        
                        # Only consider spreads of +5 or less
                        if spread_value > 5:
                            continue
                        
                        # Get ML odds
                        match_teams = str(row.get('match', '')).split(' vs ')
                        if len(match_teams) != 2:
                            continue
                        
                        home_team, away_team = match_teams
                        
                        # Determine if pick is home or away
                        if team.strip() in home_team or any(word in home_team for word in team.split()):
                            ml_odds = row.get('home_money_line', None)
                        else:
                            ml_odds = row.get('away_money_line', None)
                        
                        if ml_odds is None or pd.isna(ml_odds):
                            continue
                        
                        # Check if ML odds are positive and good value
                        if ml_odds <= 0 or ml_odds < 110:
                            continue
                        
                        # Calculate payouts
                        units = row.get('units', 3)
                        spread_odds = row.get('odds', -110)
                        
                        if spread_odds < 0:
                            spread_payout = units * (100 / abs(spread_odds))
                        else:
                            spread_payout = units * (spread_odds / 100)
                        
                        ml_payout = units * (ml_odds / 100)
                        
                        value_increase = ((ml_payout - spread_payout) / spread_payout) * 100
                        
                        # Only recommend if value increase is 30%+
                        if value_increase >= 30 and units >= 2:
                            all_opportunities.append({
                                'model': model,
                                'match': row.get('match', ''),
                                'start_time': row.get('start_time', ''),
                                'original_pick': pick,
                                'spread_odds': spread_odds,
                                'units': units,
                                'ml_odds': ml_odds,
                                'spread_payout': round(spread_payout, 2),
                                'ml_payout': round(ml_payout, 2),
                                'extra_profit': round(ml_payout - spread_payout, 2),
                                'value_increase': round(value_increase, 1)
                            })
        
        except Exception as e:
            print(f"Error processing {filepath}: {e}")
            continue
    
    if not all_opportunities:
        print("\n❌ No moneyline opportunities found")
        print("\nCriteria:")
        print("  • Underdog with +110 or better ML odds")
        print("  • Spread of +5 or less")
        print("  • Confidence of 2-3 units")
        print("  • ML payout 30%+ better than spread")
        return
    
    # Sort by value increase
    opportunities = pd.DataFrame(all_opportunities)
    opportunities = opportunities.sort_values('value_increase', ascending=False)
    
    print(f"\n🎯 FOUND {len(opportunities)} MONEYLINE OPPORTUNITIES")
    print("="*80)
    print()
    
    for idx, opp in opportunities.iterrows():
        print(f"💰 STRONG BUY - Bet Moneyline Instead!")
        print(f"   Match: {opp['match']}")
        print(f"   Time: {opp['start_time']}")
        print(f"   Model: {opp['model']}")
        print(f"   Original: {opp['original_pick']} @ {opp['spread_odds']} ({opp['units']}u)")
        print(f"   Moneyline: {opp['ml_odds']:+.0f}")
        print(f"   ")
        print(f"   💸 Value Analysis:")
        print(f"      Spread Payout: +{opp['spread_payout']} units")
        print(f"      ML Payout:     +{opp['ml_payout']} units")
        print(f"      Extra Profit:  +{opp['extra_profit']} units ({opp['value_increase']}% better!)")
        print()
    
    # Save results
    output_file = './data/moneyline_opportunities.csv'
    opportunities.to_csv(output_file, index=False)
    print(f"✅ Results saved to: {output_file}")
    print()
    
    # Summary
    print("="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Total Opportunities: {len(opportunities)}")
    print(f"Average Value Increase: {opportunities['value_increase'].mean():.1f}%")
    print(f"Max Value Increase: {opportunities['value_increase'].max():.1f}%")
    print(f"Total Extra Profit Potential: +{opportunities['extra_profit'].sum():.2f} units")
    
    return opportunities


if __name__ == '__main__':
    find_moneyline_opportunities()
