"""
Paper trading: places and retrieves parlays from the database.
"""
import sys
import os

# Ensure project root is importable
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.db import add_parlay, add_parlay_leg, list_parlays, list_parlay_legs


class PaperTrader:
    def __init__(self, bot_id: int):
        self.bot_id = bot_id

    def place_parlay(self, parlay: dict) -> int:
        """Place a parlay into the DB. Returns parlay_id."""
        parlay_id = add_parlay(
            bot_id=self.bot_id,
            name=parlay["name"],
            combined_odds=parlay["combined_odds"],
            stake=parlay["stake"],
            reasoning=parlay.get("reasoning", ""),
        )
        for leg in parlay.get("legs", []):
            add_parlay_leg(
                parlay_id=parlay_id,
                match_id=leg["match_id"],
                home_team=leg["home_team"],
                away_team=leg["away_team"],
                bet_type=leg["bet_type"],
                selection=leg["selection"],
                odds=leg["odds"],
            )
        return parlay_id

    def get_open_parlays(self) -> list:
        """Return open parlays for this bot."""
        all_parlays = list_parlays(bot_id=self.bot_id)
        return [p for p in all_parlays if p["status"] == "open"]
