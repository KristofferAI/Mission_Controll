import streamlit as st
import sys
import os
import subprocess
from datetime import datetime

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
    
    /* Hero stats cards */
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
    
    /* Odds Category Cards */
    .odds-category {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border: 2px solid #6366f144;
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
    }
    
    .odds-category-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1rem;
        padding-bottom: 0.75rem;
        border-bottom: 1px solid #6366f122;
    }
    
    .odds-category-title {
        font-size: 1.3rem;
        font-weight: 600;
        color: #f1f5f9;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    .odds-category-count {
        background: #6366f1;
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 500;
    }
    
    /* Bet Card */
    .bet-card {
        background: rgba(99, 102, 241, 0.1);
        border: 1px solid #6366f133;
        border-radius: 12px;
        padding: 1rem;
        margin-bottom: 0.75rem;
        transition: all 0.2s;
    }
    
    .bet-card:hover {
        border-color: #6366f1;
        background: rgba(99, 102, 241, 0.15);
    }
    
    .bet-card-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 0.5rem;
    }
    
    .bet-match {
        font-weight: 600;
        color: #f1f5f9;
        font-size: 1.1rem;
    }
    
    .bet-league {
        font-size: 0.8rem;
        color: #94a3b8;
    }
    
    .bet-odds {
        background: linear-gradient(135deg, #6366f1, #8b5cf6);
        color: white;
        padding: 0.35rem 0.75rem;
        border-radius: 8px;
        font-weight: 700;
        font-size: 1.1rem;
    }
    
    .bet-details {
        display: flex;
        gap: 1rem;
        margin-top: 0.75rem;
        flex-wrap: wrap;
    }
    
    .bet-detail {
        display: flex;
        align-items: center;
        gap: 0.35rem;
        font-size: 0.85rem;
        color: #94a3b8;
    }
    
    .bet-detail-value {
        color: #f1f5f9;
        font-weight: 500;
    }
    
    .edge-high { color: #22c55e; font-weight: 600; }
    .edge-medium { color: #f59e0b; font-weight: 600; }
    .edge-low { color: #94a3b8; }
    
    /* No bets message */
    .no-bets {
        text-align: center;
        padding: 2rem;
        color: #94a3b8;
    }
    
    /* Quick action buttons */
    .quick-action {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border: 1px solid #6366f144;
        border-radius: 12px;
        padding: 1rem;
        text-align: center;
        transition: all 0.3s ease;
        cursor: pointer;
    }
    
    .quick-action:hover {
        border-color: #6366f1;
        transform: translateY(-2px);
        box-shadow: 0 8px 20px -5px rgba(99, 102, 241, 0.3);
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
    
    .top-bet-banner {
        background: linear-gradient(135deg, rgba(99, 102, 241, 0.2) 0%, rgba(34, 211, 238, 0.1) 100%);
        border: 2px solid #6366f1;
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 2rem;
        text-align: center;
    }
    
    .top-bet-title {
        font-size: 0.9rem;
        color: #6366f1;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 0.5rem;
    }
    
    .top-bet-match {
        font-size: 1.5rem;
        font-weight: 700;
        color: #f1f5f9;
        margin-bottom: 0.5rem;
    }
    
    .top-bet-details {
        font-size: 1.1rem;
        color: #94a3b8;
    }
</style>
""", unsafe_allow_html=True)


def categorize_by_odds(recommendations):
    """Kategoriser bets etter odds-størrelse."""
    categories = {
        'low': [],      # 1.5 - 3.0 (Sikre)
        'medium': [],   # 3.0 - 10.0 (Balansert)
        'high': [],     # 10.0 - 50.0 (Value)
        'extreme': []   # 50.0+ (Longshots)
    }
    
    for r in recommendations:
        odds = r.get('odds', 0)
        if odds < 3.0:
            categories['low'].append(r)
        elif odds < 10.0:
            categories['medium'].append(r)
        elif odds < 50.0:
            categories['high'].append(r)
        else:
            categories['extreme'].append(r)
    
    return categories


def format_market(market, selection):
    """Formater market og selection for visning."""
    if market == 'h2h':
        return f"Vinner: {selection}"
    elif market == 'totals':
        return selection
    elif market == 'btts':
        return f"Begge scorer: {selection}"
    return f"{market}: {selection}"


def render_bet_card(bet, is_top=False):
    """Render en bet card."""
    edge = bet.get('edge_pct', 0)
    edge_class = 'edge-high' if edge >= 5 else 'edge-medium' if edge >= 2 else 'edge-low'
    edge_emoji = '🟢' if edge >= 5 else '🟡' if edge >= 2 else '⚪'
    
    st.markdown(f"""
    <div class="bet-card{' top-bet' if is_top else ''}">
        <div class="bet-card-header">
            <div>
                <div class="bet-match">{bet['match']}</div>
                <div class="bet-league">{bet['league']}</div>
            </div>
            <div class="bet-odds">{bet['odds']:.2f}x</div>
        </div>
        <div style="margin: 0.5rem 0; color: #f1f5f9;">
            {format_market(bet['market'], bet['selection'])}
        </div>
        <div class="bet-details">
            <div class="bet-detail">
                <span>Edge:</span>
                <span class="bet-detail-value {edge_class}">{edge_emoji} {edge:.1f}%</span>
            </div>
            <div class="bet-detail">
                <span>Stake:</span>
                <span class="bet-detail-value">{bet['recommended_stake']:.0f} NOK</span>
            </div>
            <div class="bet-detail">
                <span>Type:</span>
                <span class="bet-detail-value">{bet.get('bet_type', 'single').upper()}</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_odds_category(title, emoji, bets, color):
    """Render en odds-kategori."""
    if not bets:
        return
    
    count = len(bets)
    st.markdown(f"""
    <div class="odds-category">
        <div class="odds-category-header">
            <div class="odds-category-title">
                <span>{emoji}</span>
                <span>{title}</span>
            </div>
            <div class="odds-category-count">{count} bets</div>
        </div>
    """, unsafe_allow_html=True)
    
    # Sorter etter edge
    sorted_bets = sorted(bets, key=lambda x: x.get('edge_pct', 0), reverse=True)
    
    # Vis topp 5 i denne kategorien
    for bet in sorted_bets[:5]:
        render_bet_card(bet)
    
    st.markdown("</div>", unsafe_allow_html=True)


def render():
    init_db()
    
    # ── Header ──────────────────────────────────────────────────────────────
    st.title("🏠 Sports-Bets Dashboard")
    st.caption("AI-drevet betting-analyse med fokus på value bets")
    
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
    
    # ── DAGENS BESTE BETS ───────────────────────────────────────────────────
    st.header("📅 Dagens Beste Bets")
    
    # Hent dagens anbefalinger
    from datetime import date
    today_str = date.today().isoformat()
    todays_recs = list_recommendations(date_from=today_str, date_to=today_str, status='open')
    
    if not todays_recs:
        st.warning("⚠️ Ingen bets for i dag. Trykk '🔄 Hent Odds' for å hente nye anbefalinger.")
    else:
        # Finn top bet (høyest edge)
        top_bet = max(todays_recs, key=lambda x: x.get('edge_pct', 0))
        
        # Vis top bet banner
        st.markdown(f"""
        <div class="top-bet-banner">
            <div class="top-bet-title">⭐ TOPP BET IDAG</div>
            <div class="top-bet-match">{top_bet['match']}</div>
            <div class="top-bet-details">
                {format_market(top_bet['market'], top_bet['selection'])} @ {top_bet['odds']:.2f}x | 
                Edge: {top_bet['edge_pct']:.1f}% | 
                Stake: {top_bet['recommended_stake']:.0f} NOK
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Kategoriser etter odds
        categories = categorize_by_odds(todays_recs)
        
        # Vis kategorier
        col_left, col_right = st.columns(2)
        
        with col_left:
            render_odds_category("🔒 Sikre Bets (1.5-3.0x)", "🛡️", categories['low'], "#22c55e")
            render_odds_category("🎯 Value Bets (10-50x)", "💎", categories['high'], "#8b5cf6")
        
        with col_right:
            render_odds_category("⚖️ Balansert (3-10x)", "⚡", categories['medium'], "#6366f1")
            render_odds_category("🚀 Longshots (50x+)", "🌟", categories['extreme'], "#f59e0b")
    
    st.markdown("---")
    
    # ── SISTE RESULTATER ─────────────────────────────────────────────────────
    st.header("🎯 Siste Resultater")
    
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
