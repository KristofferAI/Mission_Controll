#!/bin/bash
# OddsBot Daily Runner
# Runs the full OddsBot pipeline (fetch → analyze → parlay → paper trade → notify)
set -e

cd /Users/kristoffer/Documents/GitHub/Mission_Controll

# Activate virtualenv if present
source venv/bin/activate 2>/dev/null || true

echo "[$(date)] Starting OddsBot daily run..."
python -m odds_bot.main --run
echo "[$(date)] OddsBot daily run complete."
