#!/bin/bash
# OddsBot Cron Setup Helper
# Prints instructions to schedule oddsbot_daily.sh at 09:50 AM daily

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DAILY_SCRIPT="$SCRIPT_DIR/oddsbot_daily.sh"
LOG_FILE="/tmp/oddsbot_cron.log"

echo "======================================================"
echo "  OddsBot Cron Setup"
echo "======================================================"
echo ""
echo "To run OddsBot every day at 09:50 AM, add this crontab entry:"
echo ""
echo "  1. Open your crontab for editing:"
echo "     crontab -e"
echo ""
echo "  2. Add this line:"
echo "     50 9 * * * $DAILY_SCRIPT >> $LOG_FILE 2>&1"
echo ""
echo "  3. Save and exit."
echo ""
echo "  To verify the cron is installed:"
echo "     crontab -l | grep oddsbot"
echo ""
echo "  To manually test:"
echo "     bash $DAILY_SCRIPT"
echo ""
echo "======================================================"

# Optionally auto-install (uncomment below to enable)
# CRON_LINE="50 9 * * * $DAILY_SCRIPT >> $LOG_FILE 2>&1"
# (crontab -l 2>/dev/null | grep -v "oddsbot_daily.sh"; echo "$CRON_LINE") | crontab -
# echo "Cron installed automatically."
