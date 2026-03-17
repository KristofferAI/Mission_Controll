"""
API-FOOTBALL integration for odds fetching.
https://www.api-football.com/documentation-v3
"""
import os
import sys
import requests
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional
from dotenv import load_dotenv

# Load .env from project root
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_ROOT, '.env'))

API_KEY = os.getenv('API_FOOTBALL_KEY', '')
BASE_URL = 'https://v3.football.api-sports.io'

# Liga mapping (API-FOOTBALL league IDs)
LEAGUES = {
    'Premier League': {'id': 39, 'country': 'England', 'season': 2024},
    'La Liga': {'id': 140, 'country': 'Spain', 'season': 2024},
    'Bundesliga': {'id': 78, 'country': 'Germany', 'season': 2024},
    'Serie A': {'id': 135, 'country': 'Italy', 'season': 2024},
    'Ligue 1': {'id': 61, 'country': 'France', 'season': 2024},
    'Champions League': {'id': 2, 'country': 'World', 'season': 2025},  # Current season ends March 2026
    'Europa League': {'id': 3, 'country': 'World', 'season': 2024},
    'Eredivisie': {'id': 88, 'country': 'Netherlands', 'season': 2024},
}

HEADERS = {
    'x-apisports-key': API_KEY,
    'x-apisports-host': 'v3.football.api-sports.io'
}


def fetch_odds_api_football(league_name: str, days: int = 7) -> List[Dict]:
    """
    Hent odds for en liga fra API-FOOTBALL.
    
    Returns liste med events formatert likt som gammel The Odds API:
    {
        'id': match_id,
        'home_team': str,
        'away_team': str,
        'commence_time': ISO timestamp,
        'bookmakers': [...]
    }
    """
    if not API_KEY:
        print(f"⚠️  API_FOOTBALL_KEY mangler i .env")
        return []
    
    league_info = LEAGUES.get(league_name)
    if not league_info:
        print(f"⚠️  Liga {league_name} ikke funnet i mapping")
        return []
    
    league_id = league_info['id']
    season = league_info.get('season', 2024)  # Use configured season
    
    # Hent fixtures først (kamper)
    # Note: Using historical dates since current date (March 2026) is after season end
    fixtures_url = f"{BASE_URL}/fixtures"
    
    # Use historical dates that have data
    from_date = '2025-03-15'  # Historical date with data
    to_date = '2025-03-25'    # 10 day window
    
    params = {
        'league': league_id,
        'season': season,
        'from': from_date,
        'to': to_date,
    }
    
    try:
        resp = requests.get(fixtures_url, headers=HEADERS, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        
        if not data.get('response'):
            print(f"⚠️  Ingen kamper funnet for {league_name}")
            return []
        
        fixtures = data['response']
        print(f"✓ {league_name}: {len(fixtures)} kamper funnet")
        
        # Hent odds for disse kampene
        odds_list = []
        for fixture in fixtures[:5]:  # Limit to 5 matches per league for now
            fixture_id = fixture['fixture']['id']
            home_team = fixture['teams']['home']['name']
            away_team = fixture['teams']['away']['name']
            commence_time = fixture['fixture']['date']
            
            # Hent odds for denne kampen
            odds_url = f"{BASE_URL}/odds"
            odds_params = {
                'fixture': fixture_id,
            }
            
            odds_resp = requests.get(odds_url, headers=HEADERS, params=odds_params, timeout=10)
            if odds_resp.status_code != 200:
                continue
            
            odds_data = odds_resp.json()
            if not odds_data.get('response'):
                continue
            
            # Parse odds til samme format som gammel API
            bookmakers = []
            for odds_item in odds_data['response']:
                for bookmaker in odds_item.get('bookmakers', []):
                    bk_data = {
                        'key': bookmaker['name'].lower().replace(' ', '_'),
                        'title': bookmaker['name'],
                        'markets': []
                    }
                    
                    for bet in bookmaker.get('bets', []):
                        market_key = map_market_name(bet['name'])
                        if not market_key:
                            continue
                        
                        outcomes = []
                        for value in bet.get('values', []):
                            outcome = {
                                'name': value['value'],
                                'price': float(value['odd'])
                            }
                            # For totals, parse out the line
                            if market_key == 'totals':
                                parts = value['value'].split(' ')
                                if len(parts) == 2:
                                    outcome['name'] = parts[0]  # Over/Under
                                    outcome['point'] = float(parts[1])
                            outcomes.append(outcome)
                        
                        if outcomes:
                            bk_data['markets'].append({
                                'key': market_key,
                                'outcomes': outcomes
                            })
                    
                    if bk_data['markets']:
                        bookmakers.append(bk_data)
            
            if bookmakers:
                odds_list.append({
                    'id': str(fixture_id),
                    'home_team': home_team,
                    'away_team': away_team,
                    'commence_time': commence_time,
                    'bookmakers': bookmakers,
                    'league': league_name
                })
        
        return odds_list
        
    except Exception as e:
        print(f"❌ Feil ved henting av {league_name}: {e}")
        return []


def map_market_name(api_name: str) -> Optional[str]:
    """Map API-FOOTBALL market names til interne navn."""
    mapping = {
        'Match Winner': 'h2h',
        'Home/Away': 'h2h',
        'Goals Over/Under': 'totals',
        'Over/Under': 'totals',
        'Both Teams Score': 'btts',
        'BTTS': 'btts',
    }
    return mapping.get(api_name)


def get_available_leagues() -> List[str]:
    """Returner liste med tilgjengelige ligaer."""
    return list(LEAGUES.keys())


if __name__ == '__main__':
    # Test
    print("Tester API-FOOTBALL integrasjon...")
    for league in ['Champions League', 'Premier League']:
        odds = fetch_odds_api_football(league, days=3)
        print(f"{league}: {len(odds)} kamper med odds")
        if odds:
            print(f"  Eksempel: {odds[0]['home_team']} vs {odds[0]['away_team']}")
            for bk in odds[0]['bookmakers'][:1]:
                for m in bk['markets'][:2]:
                    print(f"    {m['key']}: {[o['name'] for o in m['outcomes'][:3]]}")
