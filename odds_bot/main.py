#!/usr/bin/env python3
"""
Odds Bot - Auto-betting motor med Kelly-kalkulator, smart parlay-bygging,
automatisk resultat-sjekking og Telegram-varsler.
"""
import os
import sys
import argparse
import itertools
import logging
import json
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Tuple
import requests
from dotenv import load_dotenv

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

load_dotenv(os.path.join(_ROOT, '.env'))

# ── Logging konfigurasjon ───────────────────────────────────────────────────
log_dir = os.path.join(_ROOT, 'data')
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, 'odds_bot.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ── Konfigurasjon ────────────────────────────────────────────────────────────
ODDS_API_KEY = os.getenv('ODDS_API_KEY', '')
BASE_URL = 'https://api.the-odds-api.com/v4'

# Auto-betting config
AUTO_PLACE_BETS = os.getenv('AUTO_PLACE_BETS', 'true').lower() == 'true'
PAPER_MODE = os.getenv('PAPER_MODE', 'true').lower() == 'true'
DAILY_BET_LIMIT = int(os.getenv('DAILY_BET_LIMIT', '10'))
MIN_EDGE_FOR_AUTO = float(os.getenv('MIN_EDGE_FOR_AUTO', '3.0'))

# Kelly config
KELLY_FRACTION = float(os.getenv('KELLY_FRACTION', '0.25'))  # Quarter-Kelly
MIN_STAKE = 50.0
MAX_STAKE = 200.0
DEFAULT_BANKROLL = 1000.0

# Parlay config - FOKUS PÅ 10x+ ODDS PARLAYS
PARLAY_STAKE = 50.0
SINGLE_STAKE = 30.0
MIN_PARLAY_ODDS = 10.0    # Minst 10x odds
MAX_PARLAY_ODDS = 100.0   # Opptil 100x odds
MIN_LEGS = 2              # 2-leg parlays (10-25x odds)
MAX_LEGS = 4              # Maks 4 legs
TOP_PARLAYS = 8           # Vis 8 parlays

SPORTS = [
    'soccer_epl', 'soccer_uefa_champs_league', 'soccer_uefa_europa_league',
    'soccer_spain_la_liga', 'soccer_germany_bundesliga', 'soccer_italy_serie_a',
    'soccer_france_ligue_one', 'soccer_netherlands_eredivisie',
]
SPORT_LABELS = {
    'soccer_epl': 'Premier League',
    'soccer_uefa_champs_league': 'Champions League',
    'soccer_uefa_europa_league': 'Europa League',
    'soccer_spain_la_liga': 'La Liga',
    'soccer_germany_bundesliga': 'Bundesliga',
    'soccer_italy_serie_a': 'Serie A',
    'soccer_france_ligue_one': 'Ligue 1',
    'soccer_netherlands_eredivisie': 'Eredivisie',
}

# Telegram config
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')


# ── Kelly Kalkulator ────────────────────────────────────────────────────────
def get_bankroll() -> float:
    """Hent nåværende bankroll fra databasen."""
    try:
        from src.db import get_balance
        return get_balance()
    except Exception as e:
        logger.warning(f"Kunne ikke hente bankroll: {e}, bruker default {DEFAULT_BANKROLL}")
        return DEFAULT_BANKROLL


def kelly_criterion(true_prob: float, odds: float, fraction: float = KELLY_FRACTION) -> float:
    """
    Quarter-Kelly for konservativ sizing.
    Returnerer stake mellom MIN_STAKE og MAX_STAKE basert på bankroll.
    
    Args:
        true_prob: Beregnet sann sannsynlighet (0-1)
        odds: Odds fra bookmaker
        fraction: Kelly-fraksjon (default 0.25 = Quarter-Kelly)
    
    Returns:
        Stake i NOK
    """
    bankroll = get_bankroll()
    edge = (true_prob * odds) - 1
    
    if edge <= 0:
        logger.debug(f"Ingen positiv edge (edge={edge:.3f}), returnerer 0 stake")
        return 0
    
    kelly_pct = edge / (odds - 1)
    stake = bankroll * kelly_pct * fraction
    
    # Clamp til min/max
    final_stake = max(MIN_STAKE, min(MAX_STAKE, stake))
    logger.debug(f"Kelly: bankroll={bankroll:.0f}, edge={edge:.3f}, kelly_pct={kelly_pct:.3f}, stake={final_stake:.0f}")
    return final_stake


def get_daily_bet_count() -> int:
    """Hent antall bets plassert i dag."""
    try:
        from src.db import get_conn
        today = datetime.now().strftime('%Y-%m-%d')
        conn = get_conn()
        row = conn.execute(
            "SELECT COUNT(*) as count FROM recommendations WHERE date=? AND status IN ('open', 'won', 'lost')",
            (today,)
        ).fetchone()
        conn.close()
        return row['count'] if row else 0
    except Exception as e:
        logger.warning(f"Kunne ikke telle dagens bets: {e}")
        return 0


def can_place_bet() -> bool:
    """Sjekk om vi kan plassere flere bets i dag."""
    count = get_daily_bet_count()
    if count >= DAILY_BET_LIMIT:
        logger.info(f"Daglig limit nådd: {count}/{DAILY_BET_LIMIT} bets")
        return False
    return True


# ── Telegram Notifikasjoner ─────────────────────────────────────────────────
def send_telegram_message(message: str) -> bool:
    """Send melding til Telegram hvis konfigurert."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.debug("Telegram ikke konfigurert, hopper over varsling")
        return False
    
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text': message,
            'parse_mode': 'Markdown'
        }
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        logger.info("Telegram varsel sendt")
        return True
    except Exception as e:
        logger.warning(f"Kunne ikke sende Telegram varsel: {e}")
        return False


def notify_bet_placed(bet: Dict, stake: float, is_auto: bool = False):
    """Send varsel om nytt bet."""
    mode = "🤖 AUTO-PLACED" if is_auto else "👤 MANUELL"
    paper = "📄 PAPER MODE" if PAPER_MODE else "💰 REAL MONEY"
    message = (
        f"🎯 *Nytt bet plassert*\n\n"
        f"🏆 {bet['league']}\n"
        f"⚽ {bet['match']}\n"
        f"🎯 {bet['selection']} @ {bet['odds']:.2f}\n"
        f"📊 Edge: {bet['edge_pct']:.1f}%\n"
        f"💰 Stake: {stake:.0f} NOK\n\n"
        f"{mode} | {paper}"
    )
    send_telegram_message(message)
    logger.info(f"Bet plassert: {bet['match']} - {bet['selection']} @ {bet['odds']:.2f}")


def notify_settlement(match: str, selection: str, won: bool, pnl: float, actual: str):
    """Send varsel om bet resultat."""
    emoji = "✅ VUNNET" if won else "❌ TAPT"
    sign = "+" if pnl > 0 else ""
    message = (
        f"{emoji} *Bet resultat*\n\n"
        f"⚽ {match}\n"
        f"🎯 {selection}\n"
        f"🏁 Resultat: {actual}\n"
        f"💰 PnL: {sign}{pnl:.0f} NOK"
    )
    send_telegram_message(message)
    logger.info(f"Bet {match} - {selection}: {'WON' if won else 'LOST'} ({pnl:+.0f} NOK)")


def notify_daily_summary():
    """Send daglig sammendrag."""
    try:
        from src.db import get_recommendation_summary, get_balance
        summary = get_recommendation_summary()
        balance = get_balance()
        
        today = datetime.now().strftime('%Y-%m-%d')
        message = (
            f"📊 *Daglig sammendrag - {today}*\n\n"
            f"💰 Bankroll: {balance:.0f} NOK\n"
            f"📈 Total PnL: {summary['total_pnl']:+.0f} NOK\n"
            f"🎯 Win Rate: {summary['win_rate']:.1f}% ({summary['win_count']}/{summary['total_count']})\n"
            f"📊 ROI: {summary['roi_pct']:+.1f}%\n\n"
            f"_God dag for betting!_ 🚀"
        )
        send_telegram_message(message)
        logger.info("Daglig sammendrag sendt")
    except Exception as e:
        logger.error(f"Kunne ikke sende daglig sammendrag: {e}")


# ── Odds API ────────────────────────────────────────────────────────────────
def fetch_odds(sport: str) -> List[Dict]:
    """Hent odds for en sport fra The Odds API."""
    try:
        resp = requests.get(
            f"{BASE_URL}/sports/{sport}/odds/",
            params={'apiKey': ODDS_API_KEY, 'regions': 'eu',
                    'markets': 'h2h,totals', 'oddsFormat': 'decimal'},
            timeout=15
        )
        resp.raise_for_status()
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        future = [e for e in resp.json()
                  if datetime.fromisoformat(e['commence_time'].replace('Z', '+00:00')) >= today_start]
        logger.info(f"{SPORT_LABELS.get(sport, sport)}: {len(future)} kamper")
        return future
    except Exception as e:
        logger.warning(f"Feil ved henting av {sport}: {e}")
        return []


def remove_margin(outcome_odds: Dict[str, List[float]]) -> Dict[str, float]:
    """Fjern bookmaker-margin for å finne sann sannsynlighet."""
    outcomes = list(outcome_odds.keys())
    sums = {o: 0.0 for o in outcomes}
    counts = {o: 0 for o in outcomes}
    n = max(len(v) for v in outcome_odds.values())
    
    for i in range(n):
        bk = {o: outcome_odds[o][i] for o in outcomes if i < len(outcome_odds[o])}
        if len(bk) < len(outcomes):
            continue
        overround = sum(1.0 / p for p in bk.values())
        for o, p in bk.items():
            sums[o] += (1.0 / p) / overround
            counts[o] += 1
    
    return {o: sums[o] / counts[o] for o in outcomes if counts[o] > 0}


# ── Bet Analyse ─────────────────────────────────────────────────────────────
def get_best_bets_per_fixture(event: Dict, league: str) -> Optional[Dict]:
    """
    For hver kamp, returner det beste bet-kandidaten.
    Velger enten h2h eller totals basert på EV.
    """
    home = event['home_team']
    away = event['away_team']
    fixture_id = event['id']
    commence = event['commence_time']

    markets = {}
    for bk in event.get('bookmakers', []):
        for m in bk.get('markets', []):
            if m['key'] == 'h2h_lay':
                continue
            for o in m.get('outcomes', []):
                markets.setdefault(m['key'], {}).setdefault(
                    o['name'], []).append(float(o['price']))

    best_bet = None
    best_ev = -999

    for market_key, outcome_odds in markets.items():
        true_probs = remove_margin(outcome_odds)
        for outcome, true_prob in true_probs.items():
            odds_list = outcome_odds.get(outcome, [])
            if not odds_list:
                continue
            best_odds = max(odds_list)

            # Filtrer urealistiske odds
            if best_odds > 8.0 and market_key == 'totals':
                continue
            if best_odds < 1.3:
                continue

            implied_prob = 1.0 / best_odds
            edge_pct = (true_prob - implied_prob) * 100
            ev = true_prob * best_odds - 1

            if ev > best_ev:
                best_ev = ev
                best_bet = {
                    'fixture_id': fixture_id,
                    'match': f"{home} vs {away}",
                    'league': league,
                    'market': market_key,
                    'selection': outcome,
                    'odds': best_odds,
                    'true_probability': true_prob,
                    'implied_probability': implied_prob,
                    'edge_pct': edge_pct,
                    'commence_time': commence,
                }

    return best_bet


def format_selection(market: str, selection: str) -> str:
    """Formater bet-valg for visning."""
    if market == 'totals':
        return selection  # "Over 2.5" eller "Under 2.5"
    return selection  # Lagnavn for h2h


# ── Smart Parlay-bygging ────────────────────────────────────────────────────
def build_parlays(all_bets: List[Dict]) -> List[Dict]:
    """
    Bygg VALUE PARLAYS med 10x+ odds for maksimal avkastning:
    - 2-4 legs per parlay (fokus på 2-3 legs)
    - Maks 1 bet per liga (minimerer korrelasjon)
    - Kun forskjellige kamper
    - Kombinerte odds 10x-100x
    - Sortert etter kombinert edge
    - Perfekt for CL/EL/Cup-uker og helger
    """
    if len(all_bets) < MIN_LEGS:
        logger.warning(f"For få bets ({len(all_bets)}) for å bygge parlays")
        return []

    today_str = datetime.now().strftime('%Y%m%d')
    candidates = []

    # Prøv 2-leg, 3-leg, og 4-leg parlays
    for n in range(MIN_LEGS, min(MAX_LEGS + 1, len(all_bets) + 1)):
        for combo in itertools.combinations(all_bets, n):
            # Sjekk at alle er fra forskjellige kamper
            fixture_ids = [b['fixture_id'] for b in combo]
            if len(set(fixture_ids)) < n:
                continue
            
            # Sjekk at maks 1 bet per liga (viktig for å minimere korrelasjon)
            leagues = [b['league'] for b in combo]
            if len(leagues) != len(set(leagues)):
                continue

            # Beregn kombinerte odds og edge
            combined_odds = 1.0
            combined_edge = 0.0
            combined_true_prob = 1.0
            
            for b in combo:
                combined_odds *= b['odds']
                combined_edge += b['edge_pct']
                combined_true_prob *= b['true_probability']

            # Sjekk at odds er innenfor range (10x-100x)
            if not (MIN_PARLAY_ODDS <= combined_odds <= MAX_PARLAY_ODDS):
                continue
            
            # Sjekk at hver leg har minst 2% edge
            min_edge = min(b['edge_pct'] for b in combo)
            if min_edge < 2.0:
                continue

            candidates.append({
                'legs': list(combo),
                'combined_odds': combined_odds,
                'combined_ev': combined_edge,
                'combined_true_prob': combined_true_prob,
                'n_legs': n,
            })

    if not candidates:
        logger.warning("Ingen parlay-kandidater funnet med nåværende kriterier")
        return []

    # Sorter etter kombinert edge (høyest først)
    candidates.sort(key=lambda x: (x['combined_ev'], x['combined_odds']), reverse=True)
    
    logger.info(f"Fant {len(candidates)} parlay-kandidater")

    # Velg topp parlays med variasjon
    result = []
    used_parlays = set()
    
    # Grupper etter antall legs for variasjon
    two_legs = [c for c in candidates if c['n_legs'] == 2][:3]
    three_legs = [c for c in candidates if c['n_legs'] == 3][:3]
    four_legs = [c for c in candidates if c['n_legs'] == 4][:2]
    
    prioritized = two_legs + three_legs + four_legs

    for p in prioritized:
        if len(result) >= TOP_PARLAYS:
            break
            
        key = frozenset(b['fixture_id'] for b in p['legs'])
        if key in used_parlays:
            continue
        
        used_parlays.add(key)
        pid = f"parlay_{today_str}_{p['n_legs']}leg_{len(result)}"
        
        result.append({
            'parlay_id': pid,
            'legs': p['legs'],
            'combined_odds': p['combined_odds'],
            'combined_ev': p['combined_ev'],
            'combined_true_prob': p['combined_true_prob'],
            'stake': PARLAY_STAKE,
        })

    logger.info(f"Bygget {len(result)} parlays fra {len(all_bets)} kandidater")
    
    # Logg detaljer
    for p in result:
        legs_str = " + ".join(f"{b['match'][:20]}" for b in p['legs'])
        logger.info(f"  → {len(p['legs'])}-leg @ {p['combined_odds']:.1f}x | {legs_str}")
    
    return result


# ── Auto-plassering ─────────────────────────────────────────────────────────
def place_bet_auto(bet: Dict, stake: float, bet_type: str = 'single', parlay_id: str = None) -> bool:
    """
    Plasser et bet automatisk hvis AUTO_PLACE_BETS er aktivert.
    Logger alltid til database uansett.
    """
    from src.db import add_recommendation, log_betting_action
    
    today_str = datetime.now().strftime('%Y-%m-%d')
    
    # Sjekk om vi kan plassere flere bets
    if not can_place_bet():
        logger.info(f"Daglig limit nådd, skipper bet: {bet['match']}")
        return False
    
    # Sjekk min edge for auto-plassering
    if bet['edge_pct'] < MIN_EDGE_FOR_AUTO:
        logger.info(f"Edge for lav ({bet['edge_pct']:.1f}% < {MIN_EDGE_FOR_AUTO}%), skipper auto-place")
        return False
    
    # Trekke stake fra bankroll (paper trading)
    from src.db import get_balance, set_balance
    balance = get_balance()
    if balance < stake:
        logger.warning(f"Ikke nok bankroll ({balance:.0f} < {stake:.0f}), skipper bet")
        return False
    set_balance(balance - stake)
    logger.info(f"Stake {stake:.0f} NOK trukket fra bankroll. Gjenstår: {balance - stake:.0f} NOK")
    
    # Legg til i database
    rec_id = add_recommendation(
        date=today_str,
        match=bet['match'],
        league=bet['league'],
        market=bet['market'],
        selection=bet['selection'],
        odds=bet['odds'],
        true_probability=bet['true_probability'],
        implied_probability=bet['implied_probability'],
        edge_pct=bet['edge_pct'],
        recommended_stake=stake,
        bet_type=bet_type,
        parlay_id=parlay_id,
        commence_time=bet.get('commence_time'),
    )
    
    # Logg handlingen
    action = 'placed_auto' if AUTO_PLACE_BETS else 'placed_manual'
    log_betting_action(
        recommendation_id=rec_id,
        action=action,
        details=f"Stake: {stake:.0f} NOK trukket, Bankroll: {balance - stake:.0f} NOK, Edge: {bet['edge_pct']:.1f}%"
    )
    
    # Send varsel
    if AUTO_PLACE_BETS:
        notify_bet_placed(bet, stake, is_auto=True)
        logger.info(f"✅ Auto-plassert bet: {bet['match']} @ {bet['odds']:.2f}")
    else:
        logger.info(f"📋 Anbefaling lagret (manuell): {bet['match']} @ {bet['odds']:.2f}")
    
    return True


# ── Hoved Pipeline ──────────────────────────────────────────────────────────
def run_pipeline(auto_place: bool = None):
    """
    Hovedpipeline for å hente odds, finne value bets og plassere.
    
    Args:
        auto_place: Overstyr AUTO_PLACE_BETS config (default: None = bruk config)
    """
    from src.db import init_db, add_recommendation
    init_db()
    
    if auto_place is None:
        auto_place = AUTO_PLACE_BETS
    
    today_str = datetime.now().strftime('%Y-%m-%d')
    all_best_bets = []
    
    logger.info(f"Starter pipeline - Auto-place: {auto_place}, Paper mode: {PAPER_MODE}")

    # Hent odds for alle sports
    for sport in SPORTS:
        league = SPORT_LABELS[sport]
        events = fetch_odds(sport)
        for event in events:
            bet = get_best_bets_per_fixture(event, league)
            if bet:
                all_best_bets.append(bet)

    logger.info(f"Totalt {len(all_best_bets)} kandidater funnet")

    # Sorter etter edge og ta topp 15
    all_best_bets.sort(key=lambda x: x['edge_pct'], reverse=True)
    top_bets = all_best_bets[:15]

    # Bygg og plasser PARLAYS FØRST (hovedfokus)
    parlays = build_parlays(all_best_bets)
    parlay_placed_count = 0
    
    for p in parlays:
        if not can_place_bet():
            break
        
        for leg in p['legs']:
            stake = p['stake']  # Fast stake for parlays
            
            if auto_place and leg['edge_pct'] >= MIN_EDGE_FOR_AUTO:
                if place_bet_auto(leg, stake, 'parlay', p['parlay_id']):
                    parlay_placed_count += 1
            else:
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
                    recommended_stake=stake,
                    bet_type='parlay',
                    parlay_id=p['parlay_id'],
                    commence_time=leg.get('commence_time'),
                )

    # Plasser SINGLE BETS (sekundært - kun maks 3)
    singles_placed = 0
    for bet in top_bets[:3]:  # Kun 3 singles, resten er parlays
        if not can_place_bet():
            break
        
        # Sjekk om denne kampen allerede er i en parlay
        bet_in_parlay = any(
            any(leg['fixture_id'] == bet['fixture_id'] for leg in p['legs'])
            for p in parlays
        )
        if bet_in_parlay:
            continue
        
        # Bruk Kelly for stake
        stake = kelly_criterion(bet['true_probability'], bet['odds'])
        if stake <= 0:
            continue
        
        if auto_place and bet['edge_pct'] >= MIN_EDGE_FOR_AUTO:
            if place_bet_auto(bet, stake, 'single'):
                singles_placed += 1
        else:
            # Lagre som anbefaling uansett
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
                recommended_stake=stake,
                bet_type='single',
                parlay_id=None,
                commence_time=bet.get('commence_time'),
            )

    total_placed = singles_placed + parlay_placed_count
    logger.info(f"Pipeline fullført: {total_placed} auto-plasserte bets")
    
    print(f"\n{'='*60}")
    print(f"✅ PIPELINE FULLFØRT")
    print(f"{'='*60}")
    print(f"\n📊 Oppsummering:")
    print(f"   • {singles_placed} enkeltbets")
    print(f"   • {len(parlays)} PARLAYS (hovedfokus)")
    print(f"   • {parlay_placed_count} parlay-legs auto-plassert")
    print(f"   • {total_placed} totalt auto-plassert")
    
    if parlays:
        print(f"\n🎯 DAGENS PARLAYS (10x+ odds):")
        for i, p in enumerate(parlays, 1):
            legs_str = " + ".join(
                f"{b['match'].split(' vs ')[0]}"
                for b in p['legs']
            )
            potential = p['stake'] * p['combined_odds']
            print(f"\n   {i}. {len(p['legs'])}-leg @ {p['combined_odds']:.1f}x")
            print(f"      Innsats: {p['stake']:.0f} NOK")
            print(f"      Potensiell gevinst: {potential:.0f} NOK")
            print(f"      Kamper: {legs_str}")
    
    print(f"\n{'='*60}\n")
    
    return total_placed


# ── Resultat-sjekking ───────────────────────────────────────────────────────
def settle_bets(send_notifications: bool = True) -> int:
    """
    Sjekk resultater for åpne bets og oppdater status.
    
    Args:
        send_notifications: Send Telegram-varsler ved seier/tap
    
    Returns:
        Antall settled bets
    """
    from src.db import (
        list_recommendations, settle_recommendation, 
        get_balance, set_balance, update_performance_stats,
        log_betting_action
    )
    
    open_recs = list_recommendations(status='open')
    if not open_recs:
        logger.info("Ingen åpne bets å sjekke")
        return 0

    settled = 0
    learning_data = []
    
    for sport in SPORTS:
        try:
            resp = requests.get(
                f"{BASE_URL}/sports/{sport}/scores/",
                params={'apiKey': ODDS_API_KEY, 'daysFrom': 3},
                timeout=15
            )
            resp.raise_for_status()
            scores = resp.json()
        except Exception as e:
            logger.warning(f"Kunne ikke hente scores for {sport}: {e}")
            continue

        for s in scores:
            if not s.get('completed'):
                continue
            
            match_name = f"{s['home_team']} vs {s['away_team']}"
            matching = [r for r in open_recs if r['match'] == match_name]
            if not matching:
                continue

            scores_data = s.get('scores') or []
            home_score = next((int(x['score']) for x in scores_data if x['name'] == s['home_team']), None)
            away_score = next((int(x['score']) for x in scores_data if x['name'] == s['away_team']), None)
            if home_score is None or away_score is None:
                continue

            total_goals = home_score + away_score
            actual = f"{home_score}-{away_score}"

            for rec in matching:
                sel = rec['selection']
                mkt = rec['market']
                won = False

                if mkt == 'h2h':
                    if sel == s['home_team']:
                        won = home_score > away_score
                    elif sel == s['away_team']:
                        won = away_score > home_score
                    elif sel == 'Draw':
                        won = home_score == away_score
                elif mkt == 'totals':
                    try:
                        line = float(sel.split()[-1])
                        won = total_goals > line if 'Over' in sel else total_goals < line
                    except:
                        pass

                # Settle bet
                settle_recommendation(rec['id'], actual, won)
                
                # Hent PnL
                from src.db import get_conn
                conn = get_conn()
                row = conn.execute("SELECT pnl FROM recommendations WHERE id=?", (rec['id'],)).fetchone()
                pnl = row['pnl'] if row else 0
                conn.close()

                # Oppdater bankroll
                balance = get_balance()
                if won:
                    payout = rec['recommended_stake'] * rec['odds']
                    set_balance(balance + payout)
                    logger.info(f"Bankroll oppdatert: +{payout:.0f} NOK (seier)")
                
                # Logg handling
                log_betting_action(
                    recommendation_id=rec['id'],
                    action='settled',
                    details=f"Result: {'won' if won else 'lost'}, Actual: {actual}, PnL: {pnl:.0f}"
                )
                
                # Oppdater performance stats
                update_performance_stats(
                    league=rec['league'],
                    market=rec['market'],
                    won=won,
                    stake=rec['recommended_stake'],
                    pnl=pnl
                )
                
                # Samle læringsdata
                learning_data.append({
                    'league': rec['league'],
                    'market': rec['market'],
                    'edge_pct': rec['edge_pct'],
                    'odds': rec['odds'],
                    'won': won,
                })

                # Send varsel
                if send_notifications:
                    notify_settlement(match_name, sel, won, pnl, actual)
                
                logger.info(f"{'✅ WON' if won else '❌ LOST'}: {match_name} — {sel} ({actual})")
                settled += 1

    # Logg læring
    if learning_data:
        log_learning_data(learning_data)

    logger.info(f"Settlet {settled} bet(s)")
    print(f"\nSettlet {settled} bet(s)." if settled else "Ingen fullførte kamper ennå.")
    return settled


def log_learning_data(data: List[Dict]):
    """Logg læringsdata for å forbedre modellen over tid."""
    log_file = os.path.join(_ROOT, 'data', 'learning_log.jsonl')
    try:
        with open(log_file, 'a') as f:
            for entry in data:
                entry['timestamp'] = datetime.now().isoformat()
                f.write(json.dumps(entry) + '\n')
        logger.info(f"Logget {len(data)} læringsposter")
    except Exception as e:
        logger.warning(f"Kunne ikke logge læringsdata: {e}")


# ── Hoved-funksjon ───────────────────────────────────────────────────────────
def main():
    from src.db import init_db
    init_db()
    
    parser = argparse.ArgumentParser(description='Odds Bot - Auto-betting motor')
    parser.add_argument('--run', action='store_true', help='Kjør pipeline')
    parser.add_argument('--settle', action='store_true', help='Sjekk resultater')
    parser.add_argument('--auto', action='store_true', help='Aktiver auto-place (overstyrer config)')
    parser.add_argument('--no-auto', action='store_true', help='Deaktiver auto-place (overstyrer config)')
    parser.add_argument('--daily-summary', action='store_true', help='Send daglig sammendrag')
    args = parser.parse_args()
    
    # Bestem auto-place modus
    auto_place = None
    if args.auto:
        auto_place = True
    elif args.no_auto:
        auto_place = False
    
    if args.daily_summary:
        notify_daily_summary()
    elif args.settle:
        settle_bets()
    else:
        run_pipeline(auto_place=auto_place)


if __name__ == '__main__':
    main()
