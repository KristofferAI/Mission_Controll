import streamlit as st
import sys
import os
import subprocess
from datetime import datetime, date

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.db import (
    get_balance, get_recommendation_summary, get_daily_stats,
    get_recent_results, get_scheduler_status, list_recommendations,
    init_db
)

# ── Custom CSS ──────────────────────────────────────────────────────────
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #0f0f1e 0%, #1a1a2e 50%, #16213e 100%);
    }
    
    /* HERO SECTION */
    .hero-card {
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
        border-radius: 16px;
        padding: 1.5rem;
        text-align: center;
        box-shadow: 0 10px 40px -10px rgba(99, 102, 241, 0.5);
    }
    
    .hero-card-secondary {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border: 1px solid #6366f144;
        border-radius: 16px;
        padding: 1.5rem;
        text-align: center;
    }
    
    .hero-value {
        font-size: 2.5rem;
        font-weight: 700;
        color: white;
        margin: 0;
    }
    
    .hero-label {
        font-size: 0.9rem;
        color: rgba(255, 255, 255, 0.8);
        margin-top: 0.5rem;
    }
    
    .hero-value-secondary {
        font-size: 2rem;
        font-weight: 600;
        color: #f1f5f9;
        margin: 0;
    }
    
    /* PARLAY CARDS - HOVEDFOKUS */
    .parlay-card {
        background: linear-gradient(135deg, rgba(245, 158, 11, 0.15) 0%, rgba(245, 158, 11, 0.05) 100%);
        border: 2px solid #f59e0b;
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
    }
    
    .parlay-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1rem;
        padding-bottom: 0.75rem;
        border-bottom: 1px solid #f59e0b44;
    }
    
    .parlay-title {
        font-size: 1.3rem;
        font-weight: 700;
        color: #f59e0b;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    .parlay-odds {
        background: linear-gradient(135deg, #f59e0b, #fbbf24);
        color: #000;
        padding: 0.5rem 1rem;
        border-radius: 10px;
        font-weight: 800;
        font-size: 1.4rem;
    }
    
    .parlay-leg {
        background: rgba(26, 26, 46, 0.8);
        border: 1px solid #f59e0b33;
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 0.75rem;
    }
    
    .parlay-leg-match {
        font-weight: 600;
        color: #f1f5f9;
        font-size: 1.1rem;
        margin-bottom: 0.25rem;
    }
    
    .parlay-leg-league {
        font-size: 0.8rem;
        color: #94a3b8;
        margin-bottom: 0.5rem;
    }
    
    .parlay-leg-bet {
        background: linear-gradient(90deg, rgba(245, 158, 11, 0.2), transparent);
        padding: 0.5rem 0.75rem;
        border-radius: 6px;
        border-left: 3px solid #f59e0b;
        color: #f1f5f9;
        font-weight: 500;
    }
    
    .parlay-footer {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-top: 1rem;
        padding-top: 1rem;
        border-top: 1px solid #f59e0b44;
    }
    
    /* SINGLE BET CARDS */
    .bet-card {
        background: rgba(99, 102, 241, 0.1);
        border: 1px solid #6366f133;
        border-radius: 12px;
        padding: 1.25rem;
        margin-bottom: 0.75rem;
    }
    
    .bet-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 0.75rem;
    }
    
    .bet-match {
        font-weight: 700;
        color: #f1f5f9;
        font-size: 1.15rem;
    }
    
    .bet-league {
        font-size: 0.8rem;
        color: #94a3b8;
        margin-top: 0.25rem;
    }
    
    .bet-odds {
        background: linear-gradient(135deg, #6366f1, #8b5cf6);
        color: white;
        padding: 0.4rem 0.8rem;
        border-radius: 8px;
        font-weight: 700;
        font-size: 1.1rem;
    }
    
    .bet-description {
        background: linear-gradient(90deg, rgba(99, 102, 241, 0.2), transparent);
        padding: 0.75rem;
        border-radius: 8px;
        border-left: 3px solid #6366f1;
        margin: 0.75rem 0;
    }
    
    .bet-description-text {
        color: #f1f5f9;
        font-size: 1rem;
        font-weight: 500;
    }
    
    .bet-details {
        display: flex;
        gap: 1.5rem;
        flex-wrap: wrap;
        margin-top: 0.75rem;
    }
    
    .bet-detail {
        display: flex;
        flex-direction: column;
        gap: 0.2rem;
    }
    
    .bet-detail-label {
        font-size: 0.75rem;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .bet-detail-value {
        color: #f1f5f9;
        font-weight: 600;
        font-size: 1rem;
    }
    
    .edge-high { color: #22c55e; }
    .edge-medium { color: #f59e0b; }
    .edge-low { color: #94a3b8; }
    
    /* Section Headers */
    .section-header {
        background: linear-gradient(90deg, rgba(99, 102, 241, 0.2), transparent);
        padding: 1rem 1.25rem;
        border-radius: 12px;
        border-left: 4px solid #6366f1;
        margin: 1.5rem 0 1rem 0;
    }
    
    .section-title {
        font-size: 1.4rem;
        font-weight: 700;
        color: #f1f5f9;
        margin: 0;
    }
    
    .section-subtitle {
        font-size: 0.9rem;
        color: #94a3b8;
        margin-top: 0.25rem;
    }
    
    /* No bets message */
    .no-bets {
        text-align: center;
        padding: 3rem;
        color: #94a3b8;
        background: rgba(26, 26, 46, 0.5);
        border-radius: 16px;
        border: 2px dashed #6366f133;
    }
    
    /* Result cards */
    .result-card {
        background: rgba(26, 26, 46, 0.6);
        border-radius: 8px;
        padding: 0.75rem 1rem;
        margin-bottom: 0.5rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-left: 3px solid;
    }
    
    .result-win { border-left-color: #22c55e; }
    .result-loss { border-left-color: #ef4444; }
    
    .status-indicator {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 500;
    }
    
    .status-running {
        background: rgba(34, 197, 94, 0.2);
        color: #22c55e;
    }
    
    .status-stopped {
        background: rgba(239, 68, 68, 0.2);
        color: #ef4444;
    }
    
    h1, h2, h3 {
        background: linear-gradient(90deg, #6366f1, #22d3ee);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
</style>
""", unsafe_allow_html=True)


def format_bet_description(market, selection, home_team, away_team):
    """
    Formater bet-beskrivelse TYDELIG så bruker forstår nøyaktig hva som skal bettes.
    """
    if market == 'h2h':
        if selection == home_team:
            return f"🏠 Hjemmeseier: {home_team} slår {away_team}"
        elif selection == away_team:
            return f"✈️ Borteseier: {away_team} slår {home_team}"
        elif selection.lower() in ['draw', 'uavgjort']:
            return f"🤝 Uavgjort mellom {home_team} og {away_team}"
        else:
            return f"🏆 Vinner: {selection}"
    
    elif market == 'totals':
        # "Over 2.5" eller "Under 2.5"
        if 'over' in selection.lower():
            line = selection.split()[-1]
            return f"⬆️ Over {line} mål totalt (mer enn {line} mål i kampen)"
        elif 'under' in selection.lower():
            line = selection.split()[-1]
            return f"⬇️ Under {line} mål totalt (færre enn {line} mål i kampen)"
        return selection
    
    elif market == 'btts':
        if selection.lower() in ['yes', 'ja']:
            return f"⚽ Begge lag scorer minst ett mål"
        else:
            return f"🚫 Ikke begge lag scorer"
    
    elif market == 'h2h_lay':
        return f"❌ {selection} vinner IKKE (lay bet)"
    
    return f"{market}: {selection}"


def parse_match_teams(match_str):
    """Parse hjemme- og bortelag fra match-string."""
    if ' vs ' in match_str:
        parts = match_str.split(' vs ')
        return parts[0].strip(), parts[1].strip()
    return match_str, ""


def render_bet_card(bet, is_parlay_leg=False):
    """Render en bet card med TYDELIG beskrivelse."""
    home, away = parse_match_teams(bet['match'])
    description = format_bet_description(bet['market'], bet['selection'], home, away)
    
    edge = bet.get('edge_pct', 0)
    edge_class = 'edge-high' if edge >= 5 else 'edge-medium' if edge >= 2 else 'edge-low'
    edge_text = f"{edge:.1f}%"
    
    card_class = "parlay-leg" if is_parlay_leg else "bet-card"
    
    st.markdown(f"""
    <div class="{card_class}">
        <div class="bet-header">
            <div>
                <div class="bet-match">{bet['match']}</div>
                <div class="bet-league">{bet['league']}</div>
            </div>
            <div class="bet-odds">{bet['odds']:.2f}x</div>
        </div>
        <div class="bet-description">
            <div class="bet-description-text">{description}</div>
        </div>
        <div class="bet-details">
            <div class="bet-detail">
                <div class="bet-detail-label">Edge</div>
                <div class="bet-detail-value {edge_class}">{edge_text}</div>
            </div>
            <div class="bet-detail">
                <div class="bet-detail-label">Sannsynlighet</div>
                <div class="bet-detail-value">{bet['true_probability']*100:.1f}%</div>
            </div>
            <div class="bet-detail">
                <div class="bet-detail-label">Stake</div>
                <div class="bet-detail-value">{bet['recommended_stake']:.0f} NOK</div>
            </div>
            <div class="bet-detail">
                <div class="bet-detail-label">Type</div>
                <div class="bet-detail-value">{bet.get('bet_type', 'single').upper()}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_parlay_card(parlay_id, legs, all_recs):
    """Render en parlay card med alle legs."""
    parlay_recs = [r for r in all_recs if r.get('parlay_id') == parlay_id]
    if not parlay_recs:
        return
    
    # Beregn kombinerte odds
    combined_odds = 1.0
    for leg in parlay_recs:
        combined_odds *= leg.get('odds', 1)
    
    total_stake = parlay_recs[0].get('recommended_stake', 50) if parlay_recs else 50
    combined_edge = sum(r.get('edge_pct', 0) for r in parlay_recs) / len(parlay_recs) if parlay_recs else 0
    
    st.markdown(f"""
    <div class="parlay-card">
        <div class="parlay-header">
            <div class="parlay-title">🎯 PARLAY - {len(parlay_recs)} kamper</div>
            <div class="parlay-odds">{combined_odds:.1f}x</div>
        </div>
    """, unsafe_allow_html=True)
    
    # Vis hver leg
    for leg in parlay_recs:
        home, away = parse_match_teams(leg['match'])
        description = format_bet_description(leg['market'], leg['selection'], home, away)
        
        st.markdown(f"""
        <div class="parlay-leg">
            <div class="parlay-leg-match">{leg['match']}</div>
            <div class="parlay-leg-league">{leg['league']}</div>
            <div class="parlay-leg-bet">{description} @ {leg['odds']:.2f}x</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Footer med oppsummering
    potential_win = total_stake * combined_odds
    st.markdown(f"""
        <div class="parlay-footer">
            <div>
                <div style="color: #94a3b8; font-size: 0.85rem;">Total innsats</div>
                <div style="color: #f1f5f9; font-weight: 600;">{total_stake:.0f} NOK</div>
            </div>
            <div>
                <div style="color: #94a3b8; font-size: 0.85rem;">Gevinst ved vinn</div>
                <div style="color: #22c55e; font-weight: 700; font-size: 1.1rem;">{potential_win:.0f} NOK</div>
            </div>
            <div>
                <div style="color: #94a3b8; font-size: 0.85rem;">Snitt edge</div>
                <div style="color: #f59e0b; font-weight: 600;">{combined_edge:.1f}%</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render():
    init_db()
    
    # ── Header ──────────────────────────────────────────────────────────────
    st.title("🏠 Sports-Bets Dashboard")
    st.caption("AI-drevet betting med fokus på VALUE PARLAYS")
    
    # ── Hent data ───────────────────────────────────────────────────────────
    balance = get_balance()
    summary = get_recommendation_summary()
    daily = get_daily_stats()
    scheduler = get_scheduler_status()
    
    # ── Scheduler Status ───────────────────────────────────────────────────
    scheduler_col1, scheduler_col2 = st.columns([1, 3])
    with scheduler_col1:
        if scheduler.get('is_running'):
            st.markdown('<span class="status-indicator status-running">🟢 Scheduler Kjører</span>', unsafe_allow_html=True)
        else:
            st.markdown('<span class="status-indicator status-stopped">🔴 Scheduler Stoppet</span>', unsafe_allow_html=True)
    with scheduler_col2:
        if scheduler.get('last_run'):
            last_run = scheduler['last_run'][:16] if scheduler['last_run'] else 'Aldri'
            st.caption(f"Siste kjøring: {last_run}")
    
    st.markdown("---")
    
    # ── Hero Stats ──────────────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="hero-card">
            <div class="hero-value">{balance:,.0f}</div>
            <div class="hero-label">💰 Bankroll (NOK)</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        pnl_color = "#22c55e" if summary['total_pnl'] >= 0 else "#ef4444"
        st.markdown(f"""
        <div class="hero-card-secondary">
            <div class="hero-value-secondary" style="color: {pnl_color};">{summary['total_pnl']:+.0f}</div>
            <div style="font-size: 0.85rem; color: #94a3b8; margin-top: 0.5rem;">📈 Total PnL</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="hero-card-secondary">
            <div class="hero-value-secondary">{summary['win_rate']:.1f}%</div>
            <div style="font-size: 0.85rem; color: #94a3b8; margin-top: 0.5rem;">🎯 Win Rate</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        roi_color = "#22c55e" if summary['roi_pct'] >= 0 else "#ef4444"
        st.markdown(f"""
        <div class="hero-card-secondary">
            <div class="hero-value-secondary" style="color: {roi_color};">{summary['roi_pct']:+.1f}%</div>
            <div style="font-size: 0.85rem; color: #94a3b8; margin-top: 0.5rem;">📊 ROI</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # ── Quick Actions ───────────────────────────────────────────────────────
    qa_col1, qa_col2, qa_col3, qa_col4 = st.columns(4)
    
    with qa_col1:
        if st.button("🔄 Hent Odds", use_container_width=True):
            with st.spinner("Henter odds..."):
                result = subprocess.run(
                    [sys.executable, 'odds_bot/main.py', '--run'],
                    cwd=_ROOT, capture_output=True, text=True
                )
            if result.returncode == 0:
                st.success("✅ Odds hentet!")
                st.rerun()
            else:
                st.error(f"❌ Feil: {result.stderr}")
    
    with qa_col2:
        if st.button("✅ Settle", use_container_width=True):
            with st.spinner("Sjekker resultater..."):
                result = subprocess.run(
                    [sys.executable, 'odds_bot/main.py', '--settle'],
                    cwd=_ROOT, capture_output=True, text=True
                )
            if result.returncode == 0:
                st.success("✅ Resultater sjekket!")
                st.rerun()
            else:
                st.error(f"❌ Feil: {result.stderr}")
    
    with qa_col3:
        if st.button("🤖 Start Scheduler", use_container_width=True):
            result = subprocess.run(
                [sys.executable, 'odds_bot/auto_scheduler.py', 'start'],
                cwd=_ROOT, capture_output=True, text=True
            )
            if "startet" in result.stdout.lower():
                st.success("✅ Scheduler startet!")
            else:
                st.info(result.stdout)
    
    with qa_col4:
        if st.button("🛑 Stopp Scheduler", use_container_width=True):
            result = subprocess.run(
                [sys.executable, 'odds_bot/auto_scheduler.py', 'stop'],
                cwd=_ROOT, capture_output=True, text=True
            )
            st.success("✅ Scheduler stoppet!")
    
    st.markdown("---")
    
    # ── DAGENS PARLAYS (HOVEDFOKUS) ─────────────────────────────────────────
    st.markdown("""
    <div class="section-header">
        <div class="section-title">🎯 DAGENS PARLAYS</div>
        <div class="section-subtitle">Kombinasjoner av value bets for maksimal avkastning</div>
    </div>
    """, unsafe_allow_html=True)
    
    today_str = date.today().isoformat()
    todays_recs = list_recommendations(date_from=today_str, date_to=today_str, status='open')
    
    # Finn alle unike parlay_ids
    parlay_ids = set()
    for r in todays_recs:
        if r.get('parlay_id'):
            parlay_ids.add(r['parlay_id'])
    
    if parlay_ids:
        # Vis parlays
        for parlay_id in sorted(parlay_ids):
            render_parlay_card(parlay_id, None, todays_recs)
    else:
        st.markdown("""
        <div class="no-bets">
            <div style="font-size: 2rem; margin-bottom: 1rem;">🎯</div>
            <div style="font-size: 1.1rem; font-weight: 600; margin-bottom: 0.5rem;">Ingen parlays for i dag</div>
            <div>Trykk "🔄 Hent Odds" for å generere nye parlays</div>
        </div>
        """, unsafe_allow_html=True)
    
    # ── DAGENS SINGLE BETS ─────────────────────────────────────────────────
    st.markdown("""
    <div class="section-header">
        <div class="section-title">⚡ DAGENS SINGLE BETS</div>
        <div class="section-subtitle">Enkeltbets for de som foretrekker lavere risiko</div>
    </div>
    """, unsafe_allow_html=True)
    
    singles = [r for r in todays_recs if not r.get('parlay_id')]
    
    if singles:
        # Sorter etter edge
        singles = sorted(singles, key=lambda x: x.get('edge_pct', 0), reverse=True)
        
        # Vis topp 5 singles
        for bet in singles[:5]:
            render_bet_card(bet)
        
        if len(singles) > 5:
            st.caption(f"... og {len(singles) - 5} flere single bets")
    else:
        st.markdown("""
        <div class="no-bets">
            <div style="font-size: 2rem; margin-bottom: 1rem;">⚡</div>
            <div style="font-size: 1.1rem; font-weight: 600; margin-bottom: 0.5rem;">Ingen single bets for i dag</div>
        </div>
        """, unsafe_allow_html=True)
    
    # ── SISTE RESULTATER ────────────────────────────────────────────────────
    st.markdown("""
    <div class="section-header">
        <div class="section-title">📋 SISTE RESULTATER</div>
        <div class="section-subtitle">Siste settled bets</div>
    </div>
    """, unsafe_allow_html=True)
    
    recent_results = get_recent_results(limit=5)
    
    if not recent_results:
        st.info("Ingen resultater ennå. Bets må fullføres og settles.")
    else:
        for r in recent_results:
            status_class = "result-win" if r['status'] == 'won' else "result-loss"
            status_emoji = "✅" if r['status'] == 'won' else "❌"
            pnl = r['pnl']
            pnl_sign = "+" if pnl > 0 else ""
            odds = r.get('odds', 0)
            
            st.markdown(f"""
            <div class="result-card {status_class}">
                <div>
                    <strong>{status_emoji} {r['match']}</strong><br>
                    <small style="color: #94a3b8;">{r['selection']} @ {odds:.2f}x</small>
                </div>
                <div style="text-align: right;">
                    <strong style="color: {'#22c55e' if pnl > 0 else '#ef4444'};">{pnl_sign}{pnl:.0f}</strong><br>
                    <small style="color: #94a3b8;">{r['actual_result']}</small>
                </div>
            </div>
            """, unsafe_allow_html=True)
