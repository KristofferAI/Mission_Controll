from src.db import place_bet, settle_bet, list_bets, get_balance


class BettingService:
    """Paper betting engine — place, settle, and track bets."""

    def place(self, bot_id, match_id, home_team, away_team, stake, odds, predicted_outcome):
        place_bet(bot_id, match_id, home_team, away_team, stake, odds, predicted_outcome)

    def settle(self, bet_id: int, actual_outcome: str):
        settle_bet(bet_id, actual_outcome)

    def all_bets(self):
        return list_bets()

    def bankroll(self) -> float:
        return get_balance()
