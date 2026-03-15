#!/usr/bin/env python3
"""
OddsBot — Daily betting recommendation engine.
Uses The Odds API to find value bets via margin removal.

Usage:
  python3 odds_bot/main.py --run      # Fetch + analyze + save recommendations
  python3 odds_bot/main.py --settle   # Settle completed bets via scores API
"""

import os
import sys
import json
import argparse
import math
import itertools
import logging
import random
from datetime import datetime, timezone
from typing import Optional

import requests
from dotenv import load_dotenv

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

load_dotenv(os.path.join(_ROOT, '.env'))

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

ODDS_API_KEY = os.getenv('ODDS_API_KEY', '')
BASE_URL = 'https://api.the-odds-api.com/v4'

SPORTS = [
    'soccer_epl',
    'soccer_uefa_champs_league',
    'soccer_uefa_europa_league',
    'soccer_spain_la_liga',
    'soccer_germany_bundesliga',
    'soccer_italy_serie_a',
]

SPORT_LABELS = {
    'soccer_epl': 'Premier League',
    'soccer_uefa_champs_league': 'Champions League',
    'soccer_uefa_europa_league': 'Europa League',
    'soccer_spain_la_liga': 'La Liga',
    'soccer_germany_bundesliga': 'Bundesliga',
    'soccer_italy_serie_a': 'Serie A',
}

MIN_EDGE_PCT = 2.0
MIN_STAKE = 50.0
MAX_STAKE = 200.0
BANKROLL = 10000.0
MAX_PARLAY_LEGS = 4
MIN_PARLAY_LEGS = 2
MAX_COMBINED_ODDS = 15.0


# ── API helpers ───────────────────────────────────────────────────────────────

def fetch_odds(sport: str) -> list:
    """Fetch odds from The Odds API for a given sport.
    Tries full market list first, falls back to h2h+totals, then h2h only.
    """
    market_tries = [
        'h2h,totals,btts',
        'h2h,totals',
        'h2h',
    ]
    for markets in market_tries:
        url = (
            f"{BASE_URL}/sports/{sport}/odds/"
            f"?apiKey={ODDS_API_KEY}"
            f"&regions=eu"
            f"&markets={markets}"
            f"&oddsFormat=decimal"
        )
        try:
            resp = requests.get(url, timeout=15)
            if resp.status_code == 422:
                logger.debug(f"422 for {sport} markets={markets}, trying fewer markets")
                continue
            resp.raise_for_status()
            data = resp.json()
            logger.info(f"Fetched {len(data)} events for {sport} (markets={markets})")
            return data
        except requests.exceptions.HTTPError:
            continue
        except Exception as e:
            logger.warning(f"Failed to fetch odds for {sport}: {e}")
            return []
    logger.warning(f"Could not fetch any odds for {sport}")
    return []


def parse_bookmaker_odds(event: dict) -> dict:
    """
    Parse bookmaker data from an event into a clean structure with
    per-outcome lists of all bookmaker odds.
    """
    markets: dict = {}

    for bookmaker in event.get('bookmakers', []):
        for market in bookmaker.get('markets', []):
            key = market['key']  # h2h, totals, btts
            if key not in markets:
                markets[key] = {}
            for outcome in market.get('outcomes', []):
                name = outcome['name']
                price = float(outcome['price'])
                markets[key].setdefault(name, []).append(price)

    return {
        'fixture_id': event['id'],
        'home_team': event['home_team'],
        'away_team': event['away_team'],
        'commence_time': event['commence_time'],
        'markets': markets,
    }


def remove_margin(outcome_odds: dict) -> dict:
    """
    Given outcome → list[odds], return outcome → true_probability
    using average margin removal across bookmakers.
    """
    outcomes = list(outcome_odds.keys())
    n_bookmakers = max(len(v) for v in outcome_odds.values()) if outcome_odds else 0
    if n_bookmakers == 0:
        return {}

    # We'll accumulate true_probs per outcome across bookmakers
    true_prob_sums = {o: 0.0 for o in outcomes}
    valid_counts = {o: 0 for o in outcomes}

    # For each "bookmaker index", compute overround and distribute
    for i in range(n_bookmakers):
        bk_odds = {}
        for outcome in outcomes:
            odds_list = outcome_odds[outcome]
            if i < len(odds_list):
                bk_odds[outcome] = odds_list[i]

        if len(bk_odds) < len(outcomes):
            continue  # skip incomplete bookmakers

        overround = sum(1.0 / o for o in bk_odds.values())
        if overround <= 0:
            continue

        for outcome, odd in bk_odds.items():
            raw_prob = (1.0 / odd) / overround
            true_prob_sums[outcome] += raw_prob
            valid_counts[outcome] += 1

    result = {}
    for outcome in outcomes:
        if valid_counts[outcome] > 0:
            result[outcome] = true_prob_sums[outcome] / valid_counts[outcome]
        else:
            # fallback: simple average of implied probs
            odds_list = outcome_odds[outcome]
            result[outcome] = sum(1.0 / o for o in odds_list) / len(odds_list) if odds_list else 0.0

    return result


def find_value_bets(parsed: dict) -> list:
    """
    Analyse each market in the parsed event and return a list of value bet dicts.
    """
    results = []
    home = parsed['home_team']
    away = parsed['away_team']
    fixture_id = parsed['fixture_id']

    for market_key, outcome_odds in parsed['markets'].items():
        if not outcome_odds:
            continue

        true_probs = remove_margin(outcome_odds)

        for outcome, true_prob in true_probs.items():
            odds_list = outcome_odds.get(outcome, [])
            if not odds_list:
                continue

            best_odds = max(odds_list)
            implied_prob = 1.0 / best_odds
            edge_pct = (true_prob - implied_prob) * 100

            if edge_pct >= MIN_EDGE_PCT:
                # Quarter Kelly
                if best_odds <= 1.0:
                    continue
                kelly_fraction = (true_prob * best_odds - 1.0) / (best_odds - 1.0) * 0.25
                kelly_fraction = max(0.0, kelly_fraction)
                stake = min(MAX_STAKE, max(MIN_STAKE, kelly_fraction * BANKROLL))

                results.append({
                    'fixture_id': fixture_id,
                    'match': f"{home} vs {away}",
                    'league': '',  # filled in run_pipeline
                    'market': market_key,
                    'selection': outcome,
                    'odds': best_odds,
                    'true_probability': true_prob,
                    'implied_probability': implied_prob,
                    'edge_pct': edge_pct,
                    'recommended_stake': stake,
                })

    return results


def build_parlays(value_bets: list) -> list:
    """
    Build 2–4 leg parlays from value_bets, only combining different fixtures.
    Returns a flat list of leg dicts with bet_type='parlay' and parlay_id set.
    """
    if len(value_bets) < MIN_PARLAY_LEGS:
        return []

    parlay_candidates = []
    today_str = datetime.now().strftime('%Y%m%d')

    for n_legs in range(MIN_PARLAY_LEGS, MAX_PARLAY_LEGS + 1):
        for combo in itertools.combinations(value_bets, n_legs):
            # Ensure all from different fixtures
            fixture_ids = [b['fixture_id'] for b in combo]
            if len(set(fixture_ids)) < n_legs:
                continue

            combined_odds = 1.0
            for b in combo:
                combined_odds *= b['odds']

            if combined_odds > MAX_COMBINED_ODDS:
                continue

            combined_edge = sum(b['edge_pct'] for b in combo)
            if combined_edge < MIN_EDGE_PCT * n_legs:
                continue

            parlay_candidates.append({
                'legs': combo,
                'combined_odds': combined_odds,
                'combined_edge': combined_edge,
                'n_legs': n_legs,
            })

    # Sort by combined_edge desc, take top 5
    parlay_candidates.sort(key=lambda x: x['combined_edge'], reverse=True)
    top_parlays = parlay_candidates[:5]

    result_legs = []
    for i, parlay in enumerate(top_parlays):
        parlay_id = f"parlay_{today_str}_{i}"

        # Quarter Kelly on parlay combined odds
        combined_odds = parlay['combined_odds']
        # Treat combined_edge / 100 as rough true_prob for parlay
        avg_true_prob = 1.0 / combined_odds * (1 + parlay['combined_edge'] / 100)
        avg_true_prob = min(0.99, avg_true_prob)

        if combined_odds > 1.0:
            kelly = (avg_true_prob * combined_odds - 1.0) / (combined_odds - 1.0) * 0.25
            kelly = max(0.0, kelly)
            stake = min(MAX_STAKE, max(MIN_STAKE, kelly * BANKROLL))
        else:
            stake = MIN_STAKE

        for leg in parlay['legs']:
            result_legs.append({
                **leg,
                'bet_type': 'parlay',
                'parlay_id': parlay_id,
                'recommended_stake': stake,
            })

    return result_legs


# ── Mock data ─────────────────────────────────────────────────────────────────

def generate_mock_data() -> list:
    """Generate realistic mock events when no API key is present."""
    mock_teams = [
        ('Arsenal', 'Chelsea'),
        ('Manchester City', 'Liverpool'),
        ('Real Madrid', 'Barcelona'),
        ('Bayern Munich', 'Borussia Dortmund'),
        ('Juventus', 'AC Milan'),
        ('PSG', 'Lyon'),
    ]
    events = []
    for home, away in mock_teams:
        # Slightly skewed probabilities to create value opportunities
        true_h = random.uniform(0.35, 0.55)
        true_d = random.uniform(0.20, 0.30)
        true_a = 1.0 - true_h - true_d

        bookmakers = []
        for bk_name in ['bet365', 'unibet', 'betway']:
            margin = random.uniform(1.04, 1.10)
            h_odds = round((1.0 / true_h) * random.uniform(0.92, 1.02), 2)
            d_odds = round((1.0 / true_d) * random.uniform(0.92, 1.02), 2)
            a_odds = round((1.0 / true_a) * random.uniform(0.92, 1.02), 2)
            bookmakers.append({
                'key': bk_name,
                'markets': [
                    {
                        'key': 'h2h',
                        'outcomes': [
                            {'name': home, 'price': h_odds},
                            {'name': 'Draw', 'price': d_odds},
                            {'name': away, 'price': a_odds},
                        ]
                    },
                    {
                        'key': 'totals',
                        'outcomes': [
                            {'name': 'Over 2.5', 'price': round(random.uniform(1.6, 2.2), 2)},
                            {'name': 'Under 2.5', 'price': round(random.uniform(1.6, 2.2), 2)},
                        ]
                    },
                    {
                        'key': 'btts',
                        'outcomes': [
                            {'name': 'Yes', 'price': round(random.uniform(1.5, 2.0), 2)},
                            {'name': 'No', 'price': round(random.uniform(1.5, 2.0), 2)},
                        ]
                    },
                ]
            })

        events.append({
            'id': f"mock_{home.replace(' ', '')}_{away.replace(' ', '')}",
            'home_team': home,
            'away_team': away,
            'commence_time': datetime.now(timezone.utc).isoformat(),
            'bookmakers': bookmakers,
        })
    return events


# ── Pipeline ──────────────────────────────────────────────────────────────────

def run_pipeline():
    """Main pipeline: fetch → analyse → save recommendations."""
    from src.db import add_recommendation

    all_value_bets = []
    n_sports_with_data = 0
    today_str = datetime.now().strftime('%Y-%m-%d')

    if not ODDS_API_KEY:
        logger.warning("No ODDS_API_KEY found — using mock data")
        mock_events = generate_mock_data()
        for i, sport in enumerate(SPORTS):
            league = SPORT_LABELS.get(sport, sport)
            # Use a subset of mock events per sport
            sport_events = mock_events[i % len(mock_events):i % len(mock_events) + 3]
            for event in sport_events:
                parsed = parse_bookmaker_odds(event)
                bets = find_value_bets(parsed)
                for b in bets:
                    b['league'] = league
                all_value_bets.extend(bets)
            if sport_events:
                n_sports_with_data += 1
    else:
        for sport in SPORTS:
            league = SPORT_LABELS.get(sport, sport)
            events = fetch_odds(sport)
            if not events:
                continue
            n_sports_with_data += 1
            for event in events:
                parsed = parse_bookmaker_odds(event)
                bets = find_value_bets(parsed)
                for b in bets:
                    b['league'] = league
                all_value_bets.extend(bets)

    # Build parlays
    parlay_legs = build_parlays(all_value_bets)

    # Save singles
    for bet in all_value_bets:
        add_recommendation(
            date=today_str,
            match=bet['match'],
            league=bet['league'],
            market=bet['market'],
            selection=bet['selection'],
            odds=bet['odds'],
            true_probability=bet['true_probability'],
            implied_probability=bet['implied_probability'],
            edge_pct=bet['edge_pct'],
            recommended_stake=bet['recommended_stake'],
            bet_type='single',
            parlay_id=None,
        )

    # Save parlay legs
    for leg in parlay_legs:
        add_recommendation(
            date=today_str,
            match=leg['match'],
            league=leg['league'],
            market=leg['market'],
            selection=leg['selection'],
            odds=leg['odds'],
            true_probability=leg['true_probability'],
            implied_probability=leg['implied_probability'],
            edge_pct=leg['edge_pct'],
            recommended_stake=leg['recommended_stake'],
            bet_type='parlay',
            parlay_id=leg['parlay_id'],
        )

    n_singles = len(all_value_bets)
    n_parlay_legs = len(parlay_legs)
    print(f"✅ Found {n_singles} single bets, {n_parlay_legs} parlay legs across {n_sports_with_data} sports")


# ── Settle ────────────────────────────────────────────────────────────────────

def settle_bets():
    """Check completed matches and settle open recommendations."""
    from src.db import list_recommendations, settle_recommendation

    open_recs = list_recommendations(status='open')
    if not open_recs:
        print("No open recommendations to settle.")
        return

    settled_count = 0

    for sport in SPORTS:
        if not ODDS_API_KEY:
            logger.warning(f"No API key — cannot settle {sport}")
            continue

        url = (
            f"{BASE_URL}/sports/{sport}/scores/"
            f"?apiKey={ODDS_API_KEY}&daysFrom=3"
        )
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            scores = resp.json()
        except Exception as e:
            logger.warning(f"Failed to fetch scores for {sport}: {e}")
            continue

        completed = [s for s in scores if s.get('completed')]

        for score_event in completed:
            home = score_event.get('home_team', '')
            away = score_event.get('away_team', '')
            match_name = f"{home} vs {away}"

            # Find open recs that match this fixture
            matching_recs = [r for r in open_recs if r['match'] == match_name]
            if not matching_recs:
                continue

            # Parse scores
            scores_data = score_event.get('scores') or []
            home_score = None
            away_score = None
            for s in scores_data:
                if s['name'] == home:
                    home_score = int(s['score'])
                elif s['name'] == away:
                    away_score = int(s['score'])

            if home_score is None or away_score is None:
                continue

            total_goals = home_score + away_score
            actual_result = f"{home_score}-{away_score}"

            for rec in matching_recs:
                selection = rec['selection']
                market = rec['market']
                won = False

                if market == 'h2h':
                    if selection == home:
                        won = home_score > away_score
                    elif selection == away:
                        won = away_score > home_score
                    elif selection == 'Draw':
                        won = home_score == away_score
                elif market == 'totals':
                    if 'Over' in selection:
                        try:
                            line = float(selection.split(' ')[1])
                            won = total_goals > line
                        except (IndexError, ValueError):
                            pass
                    elif 'Under' in selection:
                        try:
                            line = float(selection.split(' ')[1])
                            won = total_goals < line
                        except (IndexError, ValueError):
                            pass
                elif market == 'btts':
                    btts = home_score > 0 and away_score > 0
                    if selection == 'Yes':
                        won = btts
                    elif selection == 'No':
                        won = not btts

                settle_recommendation(rec['id'], actual_result, won)
                outcome_str = 'WON' if won else 'LOST'
                print(f"✅ Settled: {match_name} — {selection} — {outcome_str}")
                settled_count += 1

    if settled_count == 0:
        print("No matching completed fixtures found for open recommendations.")
    else:
        print(f"\n✅ Settled {settled_count} recommendation(s).")


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    from src.db import init_db
    init_db()

    parser = argparse.ArgumentParser(description='OddsBot — betting recommendation engine')
    parser.add_argument('--run', action='store_true', help='Fetch + analyse + save recommendations')
    parser.add_argument('--settle', action='store_true', help='Settle completed bets via scores API')
    args = parser.parse_args()

    if args.settle:
        settle_bets()
    else:
        # Default to run (also triggers with --run or no flag)
        run_pipeline()


if __name__ == '__main__':
    main()
