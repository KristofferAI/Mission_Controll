"""
Result tracker: settles open parlays based on actual match results.
"""
import sys
import os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.db import (
    list_parlays, list_parlay_legs, settle_parlay,
    update_parlay_leg_result, add_learning_log,
)
from odds_bot.fetcher import get_fixture_result


def evaluate_leg(leg: dict, result: dict) -> str:
    """
    Return 'won', 'lost', or 'pending'.
    Handles bet types: over_1_5, btts, dnb, clean_sheet, match_winner.
    """
    status = result.get("status", "NS")
    if status not in ("FT", "AET", "PEN"):
        return "pending"

    home_goals = result.get("home_goals")
    away_goals = result.get("away_goals")
    if home_goals is None or away_goals is None:
        return "pending"

    total_goals = home_goals + away_goals
    bet_type = leg.get("bet_type", "")
    selection = leg.get("selection", "")
    home_team = leg.get("home_team", "")
    away_team = leg.get("away_team", "")

    if bet_type == "over_1_5":
        return "won" if total_goals > 1.5 else "lost"

    elif bet_type == "btts":
        return "won" if home_goals > 0 and away_goals > 0 else "lost"

    elif bet_type == "dnb":
        # Draw no bet: draw = refund (treat as won for paper purposes)
        if home_goals == away_goals:
            return "won"  # refund treated as won
        if home_team in selection:
            return "won" if home_goals > away_goals else "lost"
        if away_team in selection:
            return "won" if away_goals > home_goals else "lost"
        return "pending"

    elif bet_type == "clean_sheet":
        # Home team clean sheet (under 1.5 proxy)
        if home_team in selection or "Home" in selection:
            return "won" if away_goals == 0 else "lost"
        else:
            return "won" if home_goals == 0 else "lost"

    elif bet_type == "match_winner":
        if selection == home_team or selection == "Home":
            return "won" if home_goals > away_goals else "lost"
        elif selection == "Draw":
            return "won" if home_goals == away_goals else "lost"
        elif selection == away_team or selection == "Away":
            return "won" if away_goals > home_goals else "lost"
        return "pending"

    return "pending"


def check_and_settle():
    """
    For each open parlay: fetch results for all legs,
    determine win/loss per leg, settle parlay if all finished,
    and log results to learning_log.
    """
    open_parlays = [p for p in list_parlays() if p["status"] == "open"]
    if not open_parlays:
        print("[ResultTracker] No open parlays to settle.")
        return

    for parlay in open_parlays:
        parlay_id = parlay["id"]
        bot_id = parlay["bot_id"]
        legs = list_parlay_legs(parlay_id)
        leg_results = []

        for leg in legs:
            fixture_id = int(leg["match_id"]) if str(leg["match_id"]).isdigit() else 0
            result = get_fixture_result(fixture_id) if fixture_id else {
                "status": "NS", "home_goals": None, "away_goals": None,
                "home_team": leg["home_team"], "away_team": leg["away_team"],
            }
            outcome = evaluate_leg(leg, result)
            actual_result_str = (
                f"{result.get('home_goals', '?')}-{result.get('away_goals', '?')}"
                if result.get("status") in ("FT", "AET", "PEN") else ""
            )
            update_parlay_leg_result(leg["id"], outcome, actual_result_str)
            leg_results.append(outcome)

        # If any leg is still pending, skip settling
        if "pending" in leg_results:
            print(f"[ResultTracker] Parlay {parlay_id}: waiting for results on {leg_results.count('pending')} leg(s).")
            continue

        # Parlay wins only if ALL legs won
        parlay_outcome = "won" if all(r == "won" for r in leg_results) else "lost"
        settle_parlay(parlay_id, parlay_outcome)
        print(f"[ResultTracker] Parlay {parlay_id} settled: {parlay_outcome}")

        # Log to learning_log
        for leg, outcome in zip(legs, leg_results):
            add_learning_log(
                bot_id=bot_id,
                parlay_id=parlay_id,
                match_id=leg["match_id"],
                home_team=leg["home_team"],
                away_team=leg["away_team"],
                bet_type=leg["bet_type"],
                selection=leg["selection"],
                odds=leg["odds"],
                outcome=outcome,
                reasoning=parlay.get("reasoning", ""),
            )
