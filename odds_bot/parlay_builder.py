"""
Builds top N parlays from a list of value bets.
"""
import itertools
from odds_bot.config import (
    MIN_PARLAY_LEGS, MAX_PARLAY_LEGS, MAX_COMBINED_ODDS,
    TOP_PARLAYS, STAKE_PER_PARLAY,
)


def build_parlays(value_bets: list) -> list:
    """
    Build top N parlays from value bets.
    - Combine 2-4 legs from DIFFERENT matches.
    - combined_odds = product of individual odds.
    - Filter: combined_odds <= MAX_COMBINED_ODDS.
    - Return top TOP_PARLAYS parlays sorted by combined EV descending.

    Each parlay: {name, legs, combined_odds, combined_ev, stake, reasoning}
    """
    if len(value_bets) < MIN_PARLAY_LEGS:
        return []

    parlays = []

    for n_legs in range(MIN_PARLAY_LEGS, MAX_PARLAY_LEGS + 1):
        if n_legs > len(value_bets):
            break
        for combo in itertools.combinations(value_bets, n_legs):
            # Ensure all legs are from different matches
            match_ids = [leg["match_id"] for leg in combo]
            if len(set(match_ids)) < n_legs:
                continue

            combined_odds = 1.0
            combined_ev = 0.0
            for leg in combo:
                combined_odds *= leg["odds"]
                combined_ev += leg["ev"]

            if combined_odds > MAX_COMBINED_ODDS:
                continue

            legs = list(combo)
            match_names = [f"{leg['home_team']} vs {leg['away_team']}" for leg in legs]
            selections = [f"{leg['selection']} @ {leg['odds']}" for leg in legs]
            reasoning = (
                f"Parlay of {n_legs} value bets. "
                f"Matches: {', '.join(match_names)}. "
                f"Selections: {', '.join(selections)}. "
                f"Combined EV: {combined_ev:.3f}."
            )

            parlays.append({
                "name": f"Parlay {n_legs}-leg | {' + '.join(leg['selection'] for leg in legs)}",
                "legs": legs,
                "combined_odds": round(combined_odds, 3),
                "combined_ev": round(combined_ev, 4),
                "stake": STAKE_PER_PARLAY,
                "reasoning": reasoning,
            })

    # Sort by combined EV descending, take top N
    parlays.sort(key=lambda p: p["combined_ev"], reverse=True)
    return parlays[:TOP_PARLAYS]
