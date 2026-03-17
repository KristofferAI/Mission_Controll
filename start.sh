#!/usr/bin/env bash
# Mission Controll — Startup Script
# Usage: ./start.sh [dashboard|bot|both]

set -e

MODE="${1:-dashboard}"
PROJECT_DIR="$HOME/projects/Mission_Controll"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════╗"
echo "║      🎯 Mission Controll — Startup           ║"
echo "╚═══════════════════════════════════════════════╝"
echo -e "${NC}"

# Navigate to project
cd "$PROJECT_DIR"

# Activate venv
echo -e "${YELLOW}🔧 Aktiverer virtual environment...${NC}"
source venv/bin/activate

# Check if .env exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️  .env ikke funnet, lager fra template...${NC}"
    echo "API_FOOTBALL_KEY=din_nøkkel_her" > .env
    echo "USE_MOCK_DATA=true" >> .env
fi

# Function to start dashboard
start_dashboard() {
    echo -e "${GREEN}🚀 Starter Dashboard på http://localhost:8501${NC}"
    echo -e "${BLUE}   Trykk Ctrl+C for å stoppe${NC}"
    echo ""
    streamlit run src/dashboard/app.py \
        --server.port=8501 \
        --server.address=0.0.0.0 \
        --server.headless=true \
        --browser.gatherUsageStats=false
}

# Function to run bot once
run_bot() {
    echo -e "${GREEN}🤖 Kjører OddsBot pipeline...${NC}"
    python3 odds_bot/main.py --run
}

# Main logic
case "$MODE" in
    dashboard)
        start_dashboard
        ;;
    bot)
        run_bot
        ;;
    both)
        echo -e "${YELLOW}Starter begge...${NC}"
        # Run bot in background
        python3 odds_bot/main.py --run &
        BOT_PID=$!
        sleep 2
        # Start dashboard
        start_dashboard
        # Cleanup
        kill $BOT_PID 2>/dev/null || true
        ;;
    *)
        echo "Usage: ./start.sh [dashboard|bot|both]"
        echo "  dashboard - Start kun Streamlit dashboard (default)"
        echo "  bot       - Kjør OddsBot én gang"
        echo "  both      - Kjør bot + dashboard"
        exit 1
        ;;
esac
