"""
Mock odds data for testing when API quota is exhausted or no fixtures available.
"""
import random
from datetime import datetime, timedelta

# Mock data for testing
MOCK_LEAGUES = {
    'Champions League': [
        ('Real Madrid', 'Manchester City'),
        ('Bayern Munich', 'Arsenal'),
        ('Barcelona', 'PSG'),
        ('Inter Milan', 'Atletico Madrid'),
    ],
    'Premier League': [
        ('Liverpool', 'Manchester United'),
        ('Arsenal', 'Chelsea'),
        ('Manchester City', 'Tottenham'),
        ('Aston Villa', 'Newcastle'),
    ],
    'La Liga': [
        ('Real Madrid', 'Barcelona'),
        ('Atletico Madrid', 'Sevilla'),
        ('Real Sociedad', 'Athletic Bilbao'),
    ],
    'Bundesliga': [
        ('Bayern Munich', 'Borussia Dortmund'),
        ('Bayer Leverkusen', 'RB Leipzig'),
        ('Eintracht Frankfurt', 'Wolfsburg'),
    ],
    'Serie A': [
        ('Inter Milan', 'Juventus'),
        ('AC Milan', 'Napoli'),
        ('Roma', 'Lazio'),
    ],
}


def generate_mock_odds(league_name: str, days: int = 7):
    """Generer mock odds data for testing."""
    teams = MOCK_LEAGUES.get(league_name, [])
    if not teams:
        return []
    
    matches = []
    base_time = datetime.now()
    
    for i, (home, away) in enumerate(teams):
        # Generate future match time
        match_time = base_time + timedelta(days=i, hours=(i * 2) % 24)
        
        # Generate realistic odds
        home_win_odds = round(random.uniform(1.8, 3.5), 2)
        draw_odds = round(random.uniform(3.0, 4.0), 2)
        away_win_odds = round(random.uniform(2.0, 4.5), 2)
        
        # Totals odds
        over_25_odds = round(random.uniform(1.7, 2.2), 2)
        under_25_odds = round(random.uniform(1.7, 2.1), 2)
        
        match = {
            'id': f'mock_{league_name.replace(" ", "_")}_{i}',
            'home_team': home,
            'away_team': away,
            'commence_time': match_time.isoformat() + 'Z',
            'league': league_name,
            'bookmakers': [
                {
                    'key': 'bet365',
                    'title': 'Bet365',
                    'markets': [
                        {
                            'key': 'h2h',
                            'outcomes': [
                                {'name': home, 'price': home_win_odds},
                                {'name': 'Draw', 'price': draw_odds},
                                {'name': away, 'price': away_win_odds},
                            ]
                        },
                        {
                            'key': 'totals',
                            'outcomes': [
                                {'name': 'Over', 'point': 2.5, 'price': over_25_odds},
                                {'name': 'Under', 'point': 2.5, 'price': under_25_odds},
                            ]
                        }
                    ]
                },
                {
                    'key': 'unibet',
                    'title': 'Unibet',
                    'markets': [
                        {
                            'key': 'h2h',
                            'outcomes': [
                                {'name': home, 'price': round(home_win_odds * random.uniform(0.95, 1.05), 2)},
                                {'name': 'Draw', 'price': draw_odds},
                                {'name': away, 'price': round(away_win_odds * random.uniform(0.95, 1.05), 2)},
                            ]
                        },
                        {
                            'key': 'totals',
                            'outcomes': [
                                {'name': 'Over', 'point': 2.5, 'price': round(over_25_odds * random.uniform(0.95, 1.05), 2)},
                                {'name': 'Under', 'point': 2.5, 'price': round(under_25_odds * random.uniform(0.95, 1.05), 2)},
                            ]
                        }
                    ]
                }
            ]
        }
        matches.append(match)
    
    return matches


def fetch_mock_odds(league_name: str, days: int = 7):
    """Wrapper for mock odds - same interface as real API."""
    print(f"📊 Mock data aktivert for {league_name}")
    return generate_mock_odds(league_name, days)


if __name__ == '__main__':
    # Test
    print("Testing mock data...")
    for league in ['Champions League', 'Premier League']:
        odds = generate_mock_odds(league)
        print(f"{league}: {len(odds)} kamper")
        if odds:
            print(f"  {odds[0]['home_team']} vs {odds[0]['away_team']}")
            print(f"  Time: {odds[0]['commence_time']}")
            for bk in odds[0]['bookmakers'][:1]:
                for m in bk['markets'][:2]:
                    print(f"    {m['key']}: {[o['name'] for o in m['outcomes']]}")
