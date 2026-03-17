"""
Mock odds data for testing - Format compatible with main_v2.py
"""
import random
from datetime import datetime, timedelta

MOCK_LEAGUES = {
    'Premier League': [
        ('Liverpool', 'Manchester United'),
        ('Arsenal', 'Chelsea'),
        ('Manchester City', 'Tottenham'),
        ('Aston Villa', 'Newcastle'),
    ],
    'Champions League': [
        ('Real Madrid', 'Manchester City'),
        ('Bayern Munich', 'Arsenal'),
        ('Barcelona', 'PSG'),
        ('Inter Milan', 'Atletico Madrid'),
    ],
    'La Liga': [
        ('Real Madrid', 'Barcelona'),
        ('Atletico Madrid', 'Sevilla'),
    ],
    'Bundesliga': [
        ('Bayern Munich', 'Borussia Dortmund'),
        ('Bayer Leverkusen', 'RB Leipzig'),
    ],
    'Serie A': [
        ('Inter Milan', 'Juventus'),
        ('AC Milan', 'Napoli'),
    ],
}

BOOKMAKERS = ['bet365', 'unibet', 'pinnacle', 'williamhill']


def fetch_mock_odds(league_name: str, days: int = 7):
    """Generer mock odds i formatet main_v2.py forventer."""
    teams = MOCK_LEAGUES.get(league_name, [])
    if not teams:
        return []
    
    matches = []
    base_time = datetime.now()
    
    for i, (home, away) in enumerate(teams):
        match_time = base_time + timedelta(days=i, hours=(i * 3) % 24)
        fixture_id = f"mock_{league_name.replace(' ', '_')}_{i}"
        
        # Generate realistic probabilities
        home_strength = random.uniform(0.4, 0.7)
        away_strength = random.uniform(0.3, 0.6)
        draw_prob = 0.25
        total = home_strength + away_strength + 0.5
        home_prob = home_strength / total * (1 - draw_prob)
        away_prob = (1 - draw_prob) - home_prob
        
        # Calculate true odds
        true_odds = {
            home: round(1.0 / home_prob, 2),
            away: round(1.0 / away_prob, 2),
            'Draw': round(1.0 / draw_prob, 2)
        }
        
        # Generate bookmaker odds with variance
        bookmakers = []
        for bk in BOOKMAKERS:
            bk_odds = []
            for outcome, odds in true_odds.items():
                # Add margin and variance
                margin = random.uniform(0.03, 0.07)
                variance = random.uniform(0.95, 1.08)  # Create value opportunities
                final_odds = round(odds * variance / (1 + margin), 2)
                bk_odds.append({'name': outcome, 'price': final_odds})
            
            bookmakers.append({
                'key': bk,
                'title': bk.title(),
                'markets': [{
                    'key': 'h2h',
                    'outcomes': bk_odds
                }]
            })
        
        # Add totals market
        line = 2.5
        over_prob = random.uniform(0.45, 0.55)
        under_prob = 1 - over_prob
        
        for bk in BOOKMAKERS[:2]:  # Add to first 2 bookies
            over_odds = round((1.0 / over_prob) * random.uniform(0.95, 1.1), 2)
            under_odds = round((1.0 / under_prob) * random.uniform(0.95, 1.1), 2)
            
            for bookie in bookmakers:
                if bookie['key'] == bk:
                    bookie['markets'].append({
                        'key': 'totals',
                        'outcomes': [
                            {'name': 'Over', 'point': line, 'price': over_odds},
                            {'name': 'Under', 'point': line, 'price': under_odds}
                        ]
                    })
                    break
        
        matches.append({
            'id': fixture_id,
            'home_team': home,
            'away_team': away,
            'commence_time': match_time.isoformat() + 'Z',
            'league': league_name,
            'bookmakers': bookmakers
        })
    
    return matches


if __name__ == '__main__':
    # Test
    print("Testing mock data...")
    for league in ['Premier League', 'Champions League']:
        odds = fetch_mock_odds(league)
        print(f"\n{league}: {len(odds)} kamper")
        if odds:
            match = odds[0]
            print(f"  {match['home_team']} vs {match['away_team']}")
            for bk in match['bookmakers'][:2]:
                outcomes = ', '.join([f"{o['name']}@{o['price']}" for o in bk['markets'][0]['outcomes'][:3]])
                print(f"    {bk['title']}: {outcomes}")
