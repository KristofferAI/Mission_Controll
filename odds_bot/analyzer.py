"""
Analyzes fixture odds to find value bets using Poisson-based probability estimation
combined with bookmaker margin removal for cross-market comparison.
"""
import math
from odds_bot.config import MIN_VALUE_THRESHOLD


# ── Poisson helpers ────────────────────────────────────────────────────────────
def _poisson_pmf(lam: float, k: int) -> float:
    """P(X=k) for Poisson(lambda)."""
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return (lam ** k) * math.exp(-lam) / math.factorial(k)


def _estimate_xg_from_market(odds_dict: dict) -> tuple:
    """
    Estimate home and away expected goals from the Goals Over/Under market.
    Uses a simple lookup from the implied O/U probability.
    Returns (home_xg, away_xg).
    """
    ou = odds_dict.get("Goals Over/Under", {})
    over15 = ou.get("Over 1.5", 0)
    if over15 <= 0:
        # Fallback: use Match Winner to rough-estimate total goals
        mw = odds_dict.get("Match Winner", {})
        home_odds = mw.get("Home", 2.0)
        away_odds = mw.get("Away", 3.5)
        # Higher home odds → expect more competitive → ~2.3 goals
        total_xg = 2.3
        home_xg = total_xg * 0.55
        away_xg = total_xg * 0.45
        return home_xg, away_xg

    # implied prob of Over 1.5 (no margin removal — use raw)
    p_over15 = 1.0 / over15
    # Calibrated lookup: P(over 1.5) → estimated total xG
    # P(total <= 1) = 1 - P(over 1.5) = sum of Poisson probs for 0,1 goals
    # Invert: using lookup table from Poisson distribution
    # Approx: total_xg = -ln(1 - p_over15) * 1.3 (empirical calibration)
    p_low = max(0.01, min(0.99, 1.0 - p_over15))
    total_xg = max(1.0, -math.log(p_low) * 1.5)

    # Split home/away assuming mild home advantage
    home_xg = total_xg * 0.55
    away_xg = total_xg * 0.45
    return home_xg, away_xg


def _model_probs(home_xg: float, away_xg: float) -> dict:
    """
    Compute match probabilities using independent Poisson model.
    Returns dict with keys: over_1_5, btts, clean_sheet_home, clean_sheet_away,
                            home_win, draw, away_win.
    """
    probs = {}

    # P(Over 1.5): P(total > 1.5) = 1 - P(0) - P(1)
    p00 = _poisson_pmf(home_xg, 0) * _poisson_pmf(away_xg, 0)
    p01 = _poisson_pmf(home_xg, 0) * _poisson_pmf(away_xg, 1)
    p10 = _poisson_pmf(home_xg, 1) * _poisson_pmf(away_xg, 0)
    probs["over_1_5"] = 1.0 - p00 - p01 - p10

    # BTTS: P(home ≥ 1) * P(away ≥ 1)
    probs["btts"] = (1.0 - _poisson_pmf(home_xg, 0)) * (1.0 - _poisson_pmf(away_xg, 0))

    # Clean sheet home (away scores 0)
    probs["clean_sheet_home"] = _poisson_pmf(away_xg, 0)

    # Clean sheet away (home scores 0)
    probs["clean_sheet_away"] = _poisson_pmf(home_xg, 0)

    # Match winner via Dixon-Coles simplified (independent Poisson)
    max_goals = 8
    home_win = 0.0
    draw = 0.0
    away_win = 0.0
    for h in range(max_goals + 1):
        for a in range(max_goals + 1):
            p = _poisson_pmf(home_xg, h) * _poisson_pmf(away_xg, a)
            if h > a:
                home_win += p
            elif h == a:
                draw += p
            else:
                away_win += p
    probs["home_win"] = home_win
    probs["draw"] = draw
    probs["away_win"] = away_win
    probs["dnb_home"] = home_win / (home_win + away_win) if (home_win + away_win) > 0 else 0.0
    probs["dnb_away"] = away_win / (home_win + away_win) if (home_win + away_win) > 0 else 0.0

    return probs


def estimate_true_prob(odds_dict: dict, bet_name: str, selection: str) -> float:
    """
    Estimate true probability via bookmaker margin removal.
    true_prob = (1/odds) / sum(1/all_odds_in_market)
    Returns 0.0 if market or selection not found.
    """
    market = odds_dict.get(bet_name, {})
    if not market or selection not in market:
        return 0.0
    total_implied = sum(1.0 / o for o in market.values() if o > 0)
    if total_implied == 0:
        return 0.0
    return (1.0 / market[selection]) / total_implied


def analyze_match(fixture: dict, odds: dict) -> list:
    """
    Returns a list of value bet opportunities for a fixture.
    Uses Poisson-based model probabilities vs bookmaker implied probs.
    Each entry: {match_id, home_team, away_team, bet_type, selection,
                 odds, true_prob, implied_prob, edge, ev}
    Only includes bets where edge > MIN_VALUE_THRESHOLD.
    """
    value_bets = []
    home = fixture.get("home_team", "Home")
    away = fixture.get("away_team", "Away")
    match_id = str(fixture.get("fixture_id", ""))

    # Estimate xG and compute model probabilities
    home_xg, away_xg = _estimate_xg_from_market(odds)
    model = _model_probs(home_xg, away_xg)

    def _check_value(bet_type: str, selection: str, model_prob: float,
                     market_name: str, market_key: str):
        market = odds.get(market_name, {})
        if market_key not in market:
            return
        bookie_odds = market[market_key]
        if bookie_odds <= 1.0:
            return
        implied_prob = 1.0 / bookie_odds
        edge = model_prob - implied_prob
        ev = edge * bookie_odds
        if edge > MIN_VALUE_THRESHOLD:
            value_bets.append({
                "match_id": match_id,
                "home_team": home,
                "away_team": away,
                "bet_type": bet_type,
                "selection": selection,
                "odds": bookie_odds,
                "true_prob": round(model_prob, 4),
                "implied_prob": round(implied_prob, 4),
                "edge": round(edge, 4),
                "ev": round(ev, 4),
            })

    # Over 1.5
    _check_value("over_1_5", "Over 1.5", model["over_1_5"],
                 "Goals Over/Under", "Over 1.5")

    # BTTS Yes
    _check_value("btts", "BTTS Yes", model["btts"],
                 "Both Teams Score", "Yes")

    # Clean sheet home (away scores 0)
    _check_value("clean_sheet", f"{home} CS", model["clean_sheet_home"],
                 "Goals Over/Under", "Under 1.5")

    # Match winner
    _check_value("match_winner", home, model["home_win"],
                 "Match Winner", "Home")
    _check_value("match_winner", "Draw", model["draw"],
                 "Match Winner", "Draw")
    _check_value("match_winner", away, model["away_win"],
                 "Match Winner", "Away")

    # Draw No Bet
    mw = odds.get("Match Winner", {})
    if "Home" in mw:
        _check_value("dnb", f"{home} DNB", model["dnb_home"],
                     "Match Winner", "Home")
    if "Away" in mw:
        _check_value("dnb", f"{away} DNB", model["dnb_away"],
                     "Match Winner", "Away")

    return value_bets
