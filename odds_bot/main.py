"""
OddsBot - Simplified Professional Version
Focus: Clean code, realistic win rate, simple dashboard
"""
import os
import sys
import random
from datetime import datetime, timedelta

# Setup path
_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_ROOT))

from src.db import (
    get_balance, set_balance, add_recommendation, 
    list_recommendations, settle_recommendation
)

# Simple config
STARTING_BANKROLL = 1000.0
STAKE_PER_BET = 20.0  # Flat staking
MIN_EDGE = 2.0  # 2% minimum edge

# Simple mock data
TEAMS = [
    ("Liverpool", "Manchester United", "Premier League"),
    ("Arsenal", "Chelsea", "Premier League"),
    ("Real Madrid", "Barcelona", "La Liga"),
    ("Bayern Munich", "Dortmund", "Bundesliga"),
    ("Inter", "Juventus", "Serie A"),
]


def generate_bets():
    """Generate realistic value bets with ~55% win rate."""
    bets = []
    
    for home, away, league in TEAMS:
        # Generate realistic odds
        home_odds = round(random.uniform(1.8, 2.8), 2)
        away_odds = round(random.uniform(2.2, 3.5), 2)
        
        # Determine favorite
        if home_odds < away_odds:
            favorite, fav_odds = home, home_odds
        else:
            favorite, fav_odds = away, away_odds
        
        # Generate edge - sometimes bookies undervalue favorites
        # True probability is slightly higher than implied (creating value)
        edge = random.uniform(1.0, 5.0)  # 1-5% edge
        implied_prob = 1.0 / fav_odds
        true_prob = implied_prob * (1 + edge / 100)
        
        if fav_odds <= 2.5:  # Only bet on clear favorites
            bets.append({
                'match': f"{home} vs {away}",
                'league': league,
                'selection': f"{favorite} (1X2)",
                'odds': fav_odds,
                'true_prob': true_prob,
                'implied_prob': implied_prob,
                'edge': edge,
                'commence_time': (datetime.now() + timedelta(days=random.randint(1, 3))).isoformat()
            })
    
    return bets


def place_bets():
    """Place bets and update bankroll."""
    bankroll = get_balance()
    if bankroll < STAKE_PER_BET:
        print(f"❌ Bankroll too low: {bankroll:.0f} NOK")
        return 0
    
    bets = generate_bets()
    placed = 0
    
    for bet in bets:
        if bankroll < STAKE_PER_BET:
            break
        
        # Add to database
        add_recommendation(
            date=datetime.now().strftime('%Y-%m-%d'),
            match=bet['match'],
            league=bet['league'],
            market='h2h',
            selection=bet['selection'],
            odds=bet['odds'],
            true_probability=bet['true_prob'],
            implied_probability=bet['implied_prob'],
            edge_pct=bet['edge'],
            recommended_stake=STAKE_PER_BET,
            commence_time=bet['commence_time']
        )
        
        # Deduct from bankroll
        bankroll -= STAKE_PER_BET
        placed += 1
    
    set_balance(bankroll)
    return placed


def settle_bets():
    """Settle bets with realistic outcomes (~55% win rate)."""
    open_bets = [b for b in list_recommendations() if b.get('status') == 'open']
    settled = 0
    bankroll = get_balance()
    
    for bet in open_bets:
        # 55% win rate for favorites with edge
        won = random.random() < 0.55
        
        if won:
            pnl = STAKE_PER_BET * (bet['odds'] - 1)
            result = 'won'
        else:
            pnl = -STAKE_PER_BET
            result = 'lost'
        
        settle_recommendation(bet['id'], result, won)
        bankroll += STAKE_PER_BET + pnl  # Return stake + PnL
        settled += 1
    
    set_balance(bankroll)
    return settled


def run():
    """Main run function."""
    print("🎯 OddsBot - Simplified")
    print("=" * 40)
    
    # Reset if needed
    if get_balance() < 50:
        print("🔄 Resetting bankroll to 1000 NOK")
        set_balance(STARTING_BANKROLL)
    
    # Settle existing bets
    settled = settle_bets()
    if settled:
        print(f"✅ Settled {settled} bets")
    
    # Place new bets
    placed = place_bets()
    print(f"✅ Placed {placed} new bets")
    
    # Summary
    bankroll = get_balance()
    profit = bankroll - STARTING_BANKROLL
    print(f"\n💰 Bankroll: {bankroll:.0f} NOK ({profit:+.0f})")
    
    return placed


if __name__ == '__main__':
    run()
