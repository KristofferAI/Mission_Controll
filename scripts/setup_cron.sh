#!/bin/bash
# Setup daily cron for OddsBot at 09:00
CRON_LINE="0 9 * * * cd /Users/kristoffer/projects/Mission_Controll && source venv/bin/activate && python3 odds_bot/main.py --run >> /tmp/oddsbot.log 2>&1"
echo ""
echo "Add this line to your crontab (run: crontab -e):"
echo ""
echo "$CRON_LINE"
echo ""
echo "Or run this to add automatically:"
echo "(crontab -l 2>/dev/null; echo \"$CRON_LINE\") | crontab -"
