import os
from dotenv import load_dotenv

load_dotenv()

API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY", "")
API_FOOTBALL_HOST = "v3.football.api-sports.io"

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

LEAGUE_IDS = [103, 104]  # 103=Eliteserien, 104=1.divisjon
SEASON = 2025

STAKE_PER_PARLAY = 50.0
MIN_PARLAY_LEGS = 2
MAX_PARLAY_LEGS = 4
MIN_LEG_ODDS = 1.40
MAX_COMBINED_ODDS = 15.0
MIN_VALUE_THRESHOLD = 0.05
TOP_PARLAYS = 3
