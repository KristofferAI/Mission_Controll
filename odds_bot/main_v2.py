"""
Odds Bot v2 - Profesjonell Value Betting Engine

Fokus på:
- Closing Line Value (CLV) - beste prediktor for profitability
- Line Shopping - alltid beste odds
- Low variance strategi - konsistente gevinster
- Anti-korrelerte parlays
- Strict risk management
"""
import os
import sys
import argparse
import itertools
import logging
import json
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict
import requests
from dotenv import load_dotenv

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

load_dotenv(os.path.join(_ROOT, '.env'))

# Import modules
try:
    from odds_bot.mock_data import fetch_mock_odds, MOCK_LEAGUES
    MOCK_DATA_AVAILABLE = True
except ImportError:
    MOCK_DATA_AVAILABLE = False

# ── Logging ────────────────────────────────────────────────────────────────
log_dir = os.path.join(_ROOT, 'data')
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, 'odds_bot.log')),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ── Konfigurasjon ───────────────────────────────────────────────────────────
# Bankroll & Risk Management
DEFAULT_BANKROLL = 1000.0
MAX_BET_PCT = 0.02           # Maks 2% av bankroll per bet
KELLY_FRACTION = 0.125       # 1/8 Kelly (konservativ)
MIN_EDGE_PCT = 3.0           # Minimum 3% edge
MIN_ODDS = 1.50              # Unngå lave odds
MAX_ODDS = 5.00              # Unngå for høye odds (varians)

# Parlay Settings
MAX_PARLAY_BETS = 3          # Maks 3-leg parlays
MIN_PARLAY_EDGE = 5.0        # Høyere edge krav for parlays
PARLAY_MAX_CORRELATION = 0.3 # Maks 30% korrelasjon mellom legs

# Quality Filters
MIN_BOOKMAKERS = 3           # Minst 3 bookmakere må ha odds
MAX_ODDS_DEVIATION = 0.15    # Maks 15% avvik mellom bookies

# Auto-betting
AUTO_PLACE_BETS = os.getenv('AUTO_PLACE_BETS', 'false').lower() == 'true'
PAPER_MODE = os.getenv('PAPER_MODE', 'true').lower() == 'true'

# API
USE_MOCK_DATA = os.getenv('USE_MOCK_DATA', 'true').lower() == 'true'
ODDS_API_KEY = os.getenv('ODDS_API_KEY', '')
BASE_URL = 'https://api.the-odds-api.com/v4'

# Sport mapping
SPORT_TO_LEAGUE = {
    'soccer_epl': 'Premier League',
    'soccer_uefa_champs_league': 'Champions League', 
    'soccer_uefa_europa_league': 'Europa League',
    'soccer_spain_la_liga': 'La Liga',
    'soccer_germany_bundesliga': 'Bundesliga',
    'soccer_italy_serie_a': 'Serie A',
}

# ── Data Classes ────────────────────────────────────────────────────────────
@dataclass
class BetOpportunity:
    """Représenterer en betting mulighet med metadata."""
    fixture_id: str
    match: str
    league: str
    market: str
    selection: str
    odds: float
    best_bookmaker: str
    all_odds: Dict[str, float]  # bookmaker -> odds
    true_probability: float
    implied_probability: float
    edge_pct: float
    ev: float
    commence_time: str
    line: Optional[float] = None  # For totals: 2.5, 3.5 etc
    clv: Optional[float] = None   # Closing Line Value
    
    def kelly_stake(self, bankroll: float) -> float:
        """Beregn Kelly-optimal stake."""
        if self.edge_pct <= 0 or self.odds <= 1:
            return 0.0
        
        # Kelly formula: (bp - q) / b
        # b = odds - 1, p = true_prob, q = 1-p
        b = self.odds - 1
        p = self.true_probability
        q = 1 - p
        
        kelly_pct = (b * p - q) / b
        
        # Apply fraction and limits
        stake = bankroll * kelly_pct * KELLY_FRACTION
        
        # Clamp to limits
        max_stake = bankroll * MAX_BET_PCT
        return max(0, min(stake, max_stake))
    
    def sharpe_ratio(self) -> float:
        """Beregn risk-adjusted return (Sharpe-liknende)."""
        if self.edge_pct <= 0:
            return 0.0
        
        # Variance estimat fra odds-spredning
        odds_list = list(self.all_odds.values())
        if len(odds_list) < 2:
            return self.edge_pct
        
        mean_odds = sum(odds_list) / len(odds_list)
        variance = sum((o - mean_odds) ** 2 for o in odds_list) / len(odds_list)
        
        if variance == 0:
            return self.edge_pct
        
        return self.edge_pct / (variance ** 0.5 + 0.1)


# ── Core Functions ──────────────────────────────────────────────────────────
def fetch_odds(sport: str) -> List[Dict]:
    """Hent odds med line shopping data."""
    league_name = SPORT_TO_LEAGUE.get(sport)
    if not league_name:
        return []
    
    if USE_MOCK_DATA and MOCK_DATA_AVAILABLE:
        logger.info(f"📊 Mock data for {league_name}")
        return fetch_mock_odds(league_name)
    
    # Real API (deaktivert pga kvote)
    return []


def calculate_true_probabilities(outcome_odds: Dict[str, List[Tuple[str, float]]]) -> Dict[str, float]:
    """
    Beregn sann sannsynlighet ved å fjerne bookmaker-margin.
    Returnerer også beste odds per outcome.
    """
    outcomes = list(outcome_odds.keys())
    if not outcomes:
        return {}
    
    # Finn beste odds for hver outcome
    best_odds = {}
    all_bookmaker_odds = defaultdict(dict)
    
    for outcome in outcomes:
        odds_list = outcome_odds[outcome]
        if not odds_list:
            continue
        
        # odds_list er liste av (bookmaker, odds) tupler
        best_odds[outcome] = max(o[1] for o in odds_list)
        for bookmaker, odds in odds_list:
            all_bookmaker_odds[outcome][bookmaker] = odds
    
    if len(best_odds) < 2:
        return {}
    
    # Calculate margin-free probabilities using power method
    # Finn implied probabilities fra beste odds
    implied = {o: 1.0 / best_odds[o] for o in best_odds}
    total_implied = sum(implied.values())
    
    # Remove margin proportionally
    true_probs = {o: implied[o] / total_implied for o in implied}
    
    return true_probs, best_odds, all_bookmaker_odds


def analyze_fixture(event: Dict, league: str) -> Optional[BetOpportunity]:
    """
    Analyser én kamp og returner beste bet hvis det finnes value.
    """
    home = event['home_team']
    away = event['away_team']
    fixture_id = event['id']
    commence = event['commence_time']
    
    # Samle alle odds per marked
    markets = defaultdict(lambda: defaultdict(list))  # market -> outcome -> [(bookie, odds)]
    bookmakers_present = set()
    
    for bk in event.get('bookmakers', []):
        bk_key = bk.get('key', 'unknown')
        bookmakers_present.add(bk_key)
        
        for m in bk.get('markets', []):
            market_key = m.get('key', 'unknown')
            
            for o in m.get('outcomes', []):
                outcome_name = o.get('name', '')
                odds = float(o.get('price', 0))
                
                # For totals, inkluder linje i navnet
                if market_key == 'totals' and o.get('point'):
                    outcome_name = f"{outcome_name} {o['point']}"
                
                if odds > 0:
                    markets[market_key][outcome_name].append((bk_key, odds))
    
    # Sjekk at vi har nok bookmakere
    if len(bookmakers_present) < MIN_BOOKMAKERS:
        return None
    
    best_bet = None
    best_score = 0
    
    # Analyser hvert marked
    for market_key, outcome_odds in markets.items():
        # Hopp over hvis for få outcomes
        if len(outcome_odds) < 2:
            continue
        
        # Beregn true probabilities
        calc_result = calculate_true_probabilities(outcome_odds)
        if not calc_result:
            continue
        
        true_probs, best_odds, all_odds = calc_result
        
        # Sjekk hver outcome for value
        for outcome, true_prob in true_probs.items():
            odds = best_odds.get(outcome, 0)
            if odds < MIN_ODDS or odds > MAX_ODDS:
                continue
            
            implied_prob = 1.0 / odds
            edge_pct = (true_prob - implied_prob) * 100
            ev = true_prob * odds - 1
            
            # Sjekk at edge er tilstrekkelig
            if edge_pct < MIN_EDGE_PCT:
                continue
            
            # Sjekk odds konsistens (unngå suspekte odds)
            odds_list = [o[1] for o in outcome_odds.get(outcome, [])]
            if len(odds_list) >= 2:
                odds_range = max(odds_list) - min(odds_list)
                avg_odds = sum(odds_list) / len(odds_list)
                if avg_odds > 0 and odds_range / avg_odds > MAX_ODDS_DEVIATION:
                    continue  # For mye variasjon = suspekt
            
            # Finn beste bookmaker
            best_bookie = max(
                ((b, o) for b, o in outcome_odds.get(outcome, [])),
                key=lambda x: x[1],
                default=('unknown', 0)
            )[0]
            
            # Beregn Sharpe-liknende score
            sharpe = edge_pct / (odds * 0.1)  # Normalisert
            
            if sharpe > best_score:
                best_score = sharpe
                
                # Parse line for totals
                line = None
                if market_key == 'totals':
                    parts = outcome.split()
                    if len(parts) >= 2:
                        try:
                            line = float(parts[-1])
                        except:
                            pass
                
                best_bet = BetOpportunity(
                    fixture_id=fixture_id,
                    match=f"{home} vs {away}",
                    league=league,
                    market=market_key,
                    selection=outcome,
                    odds=odds,
                    best_bookmaker=best_bookie,
                    all_odds={b: o for b, o in outcome_odds.get(outcome, [])},
                    true_probability=true_prob,
                    implied_probability=implied_prob,
                    edge_pct=edge_pct,
                    ev=ev,
                    commence_time=commence,
                    line=line
                )
    
    return best_bet


def calculate_correlation(bet1: BetOpportunity, bet2: BetOpportunity) -> float:
    """
    Beregn korrelasjon mellom to bets (0-1).
    Høy korrelasjon = begge vinner/taper sammen.
    """
    # Samme lag = høy korrelasjon
    teams1 = set(bet1.match.replace(' vs ', ' ').split())
    teams2 = set(bet2.match.replace(' vs ', ' ').split())
    
    common_teams = teams1 & teams2
    if common_teams:
        return 0.7  # Samme kamp eller deler lag
    
    # Samme liga = moderat korrelasjon
    if bet1.league == bet2.league:
        return 0.3
    
    # Forskjellige ligaer = lav korrelasjon
    return 0.1


def build_smart_parlays(bets: List[BetOpportunity], max_parlays: int = 5) -> List[Dict]:
    """
    Bygg parlays med anti-korrelerte bets for å redusere varians.
    """
    if len(bets) < 2:
        return []
    
    # Sorter etter Sharpe ratio (quality)
    sorted_bets = sorted(bets, key=lambda b: b.sharpe_ratio(), reverse=True)
    
    parlays = []
    used_bets = set()
    
    # Generer 2-leg parlays først (lavest varians)
    for i, bet1 in enumerate(sorted_bets):
        if i in used_bets:
            continue
        
        # Finn beste partner (lavest korrelasjon, høyest edge)
        best_partner = None
        best_score = 0
        
        for j, bet2 in enumerate(sorted_bets[i+1:], i+1):
            if j in used_bets:
                continue
            
            corr = calculate_correlation(bet1, bet2)
            if corr > PARLAY_MAX_CORRELATION:
                continue
            
            combined_edge = bet1.edge_pct + bet2.edge_pct
            score = combined_edge * (1 - corr)  # Reward low correlation
            
            if score > best_score:
                best_score = score
                best_partner = j
        
        if best_partner is not None:
            bet2 = sorted_bets[best_partner]
            combined_odds = bet1.odds * bet2.odds
            
            if MIN_ODDS < combined_odds < 10:  # Rimelig parlay odds
                parlays.append({
                    'bets': [bet1, bet2],
                    'combined_odds': combined_odds,
                    'total_edge': bet1.edge_pct + bet2.edge_pct,
                    'correlation': calculate_correlation(bet1, bet2)
                })
                used_bets.add(i)
                used_bets.add(best_partner)
                
                if len(parlays) >= max_parlays:
                    break
    
    return parlays


def get_bankroll() -> float:
    """Hent nåværende bankroll."""
    try:
        from src.db import get_balance
        return get_balance()
    except:
        return DEFAULT_BANKROLL


def place_bet_v2(bet: BetOpportunity, stake: float, bet_type: str = 'single') -> bool:
    """Plasser et bet med full logging."""
    try:
        from src.db import add_recommendation, get_balance, set_balance, log_betting_action
        
        bankroll = get_balance()
        
        # Valider at vi har nok bankroll
        if stake > bankroll * MAX_BET_PCT * 1.1:  # 10% buffer
            logger.warning(f"Stake {stake:.0f} overskrider limit for {bet.match}")
            return False
        
        # Lagre til database
        rec_id = add_recommendation(
            date=datetime.now().strftime('%Y-%m-%d'),
            match=bet.match,
            league=bet.league,
            market=bet.market,
            selection=bet.selection,
            odds=bet.odds,
            true_probability=bet.true_probability,
            implied_probability=bet.implied_probability,
            edge_pct=bet.edge_pct,
            recommended_stake=stake,
            bet_type=bet_type,
            commence_time=bet.commence_time
        )
        
        # Trekk stake fra bankroll (paper trading)
        if PAPER_MODE:
            set_balance(bankroll - stake)
        
        # Logg
        log_betting_action(
            rec_id,
            'placed',
            f"{bet_type.upper()} | {bet.selection} @ {bet.odds:.2f} | "
            f"Edge: {bet.edge_pct:.1f}% | Stake: {stake:.0f} NOK | "
            f"Book: {bet.best_bookmaker}"
        )
        
        logger.info(f"✅ {bet_type.upper()} plassert: {bet.match} @ {bet.odds:.2f}")
        return True
        
    except Exception as e:
        logger.error(f"Feil ved placing av bet: {e}")
        return False


# ── Main Pipeline ───────────────────────────────────────────────────────────
def run_pipeline_v2():
    """Kjør komplett betting pipeline."""
    logger.info("=" * 60)
    logger.info("🚀 OddsBot v2 - Profesjonell Pipeline Startet")
    logger.info("=" * 60)
    
    bankroll = get_bankroll()
    logger.info(f"💰 Bankroll: {bankroll:.0f} NOK")
    
    # Hent alle odds
    all_bets = []
    for sport in SPORT_TO_LEAGUE.keys():
        events = fetch_odds(sport)
        league = SPORT_TO_LEAGUE[sport]
        
        for event in events:
            bet = analyze_fixture(event, league)
            if bet:
                all_bets.append(bet)
    
    logger.info(f"📊 {len(all_bets)} value bets funnet")
    
    if not all_bets:
        logger.warning("Ingen bets funnet. Avslutter.")
        return
    
    # Sorter etter Sharpe ratio
    all_bets.sort(key=lambda b: b.sharpe_ratio(), reverse=True)
    
    # Vis top 10
    logger.info("\n🏆 Top 10 Value Bets:")
    for i, bet in enumerate(all_bets[:10], 1):
        logger.info(
            f"  {i}. {bet.match} | {bet.selection} @ {bet.odds:.2f} | "
            f"Edge: {bet.edge_pct:.1f}% | Sharpe: {bet.sharpe_ratio():.2f} | "
            f"Best: {bet.best_bookmaker}"
        )
    
    # Plasser top 5 single bets
    singles_placed = 0
    for bet in all_bets[:5]:
        stake = bet.kelly_stake(bankroll)
        if stake >= 10:  # Minst 10 NOK
            if place_bet_v2(bet, stake, 'single'):
                singles_placed += 1
                bankroll -= stake
    
    # Bygg og plasser parlays
    parlays = build_smart_parlays(all_bets[:15], max_parlays=3)
    parlays_placed = 0
    
    for parlay in parlays:
        # Bruk flat staking for parlays
        stake = min(50, bankroll * 0.01)  # 1% av bankroll eller 50 NOK
        
        if stake >= 10 and bankroll >= stake:
            # Plasser hver leg
            all_placed = True
            for bet in parlay['bets']:
                if not place_bet_v2(bet, stake / len(parlay['bets']), 'parlay'):
                    all_placed = False
            
            if all_placed:
                parlays_placed += 1
                bankroll -= stake
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("✅ Pipeline Fullført")
    logger.info("=" * 60)
    logger.info(f"📊 Singles: {singles_placed}")
    logger.info(f"📊 Parlays: {parlays_placed}")
    logger.info(f"💰 Gjenstående bankroll: {bankroll:.0f} NOK")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='OddsBot v2')
    parser.add_argument('--run', action='store_true', help='Kjør pipeline')
    args = parser.parse_args()
    
    if args.run:
        run_pipeline_v2()
    else:
        print("Bruk: python3 odds_bot/main_v2.py --run")
