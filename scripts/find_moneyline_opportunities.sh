#!/bin/bash

# Moneyline Opportunity Finder
# Analyzes upcoming bets to find underdog moneyline opportunities

echo "================================================================================"
echo "MONEYLINE OPPORTUNITY FINDER"
echo "================================================================================"
echo ""
echo "Strategy: Find underdogs where ML offers 30-50% better payout than spread"
echo ""

# Count bet files
BET_COUNT=$(ls data/bets/*_bets_*.txt 2>/dev/null | wc -l)
echo "Found $BET_COUNT bet files"
echo ""

# Create output file
OUTPUT_FILE="data/moneyline_opportunities.txt"
> "$OUTPUT_FILE"

echo "Analyzing upcoming bets..."
echo ""

FOUND=0

# Process each bet file
for file in data/bets/*_bets_*.txt; do
    if [ ! -f "$file" ]; then
        continue
    fi
    
    MODEL=$(basename "$file" | sed 's/.*_bets_//' | sed 's/.txt//')
    
    # Skip header, look for upcoming games (no scores)
    # and underdog spreads (contains +)
    tail -n +2 "$file" | while IFS=',' read -r rank game_id start_time match pick odds units conf reason score rest; do
        # Skip if has scores (not upcoming)
        if echo "$score" | grep -q '[0-9]-[0-9]'; then
            continue
        fi
        
        # Check if it's an underdog spread pick (contains + but not Over/Under/ML)
        if echo "$pick" | grep -q '+' && ! echo "$pick" | grep -qE 'Over|Under|ML'; then
            # Extract spread value
            SPREAD=$(echo "$pick" | grep -oE '\+[0-9]+\.?[0-9]*' | sed 's/+//')
            
            # Only consider spreads of +5 or less
            if [ -n "$SPREAD" ] && [ "$(echo "$SPREAD <= 5" | bc -l 2>/dev/null || echo 0)" -eq 1 ]; then
                # This is a potential opportunity
                echo "🎯 Potential ML Opportunity" >> "$OUTPUT_FILE"
                echo "   Model: $MODEL" >> "$OUTPUT_FILE"
                echo "   Match: $match" >> "$OUTPUT_FILE"
                echo "   Original Pick: $pick @ $odds ($units units)" >> "$OUTPUT_FILE"
                echo "   Spread: +$SPREAD" >> "$OUTPUT_FILE"
                echo "   " >> "$OUTPUT_FILE"
                echo "   💡 Recommendation: Check moneyline odds for this underdog" >> "$OUTPUT_FILE"
                echo "   If ML odds are +110 or better, betting ML may offer 30-50% more profit!" >> "$OUTPUT_FILE"
                echo "" >> "$OUTPUT_FILE"
                
                FOUND=$((FOUND + 1))
            fi
        fi
    done
done

echo "================================================================================"
if [ $FOUND -eq 0 ]; then
    echo "❌ No moneyline opportunities found in upcoming bets"
    echo ""
    echo "Criteria:"
    echo "  • Underdog spread pick (+5 or less)"
    echo "  • No game results yet (upcoming game)"
    echo "  • Moneyline odds +110 or better (check manually)"
else
    echo "✅ Found $FOUND potential moneyline opportunities!"
    echo ""
    echo "Results saved to: $OUTPUT_FILE"
    echo ""
    cat "$OUTPUT_FILE"
fi
echo "================================================================================"
