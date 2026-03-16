import streamlit as st
import sys
import os
from datetime import datetime, date, timedelta

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.db import (
    get_balance, set_balance, get_recommendation_summary,
    list_recommendations, init_db
)

# ── Custom CSS ──────────────────────────────────────────────────────────
st.markdown("""
<style>
    .bot-hero {
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
        border-radius: 16px;
        padding: 2rem;
        text-align: center;
        margin-bottom: 1.5rem;
    }
    
    .bot-hero-value {
        font-size: 3rem;
        font-weight: 800;
        color: white;
        margin: 0;
    }
    
    .bot-hero-label {
        font-size: 1rem;
        color: rgba(255, 255, 255, 0.9);
        margin-top: 0.5rem;
    }
    
    .bot-card {
        background: rgba(26, 26, 46, 0.8);
        border: 2px solid #22c55e;
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1rem;
    }
    
    .bot-card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1rem;
    }
    
    .bot-name {
        font-size: 1.5rem;
        font-weight: 700;
        color: #22c55e;
    }
    
    .bot-status {
        background: rgba(34, 197, 94, 0.2);
        color: #22c55e;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-size: 0.9rem;
        font-weight: 600;
    }
    
    .trade-card {
        background: rgba(99, 102, 241, 0.1);
        border: 1px solid #6366f133;
        border-radius: 12px;
        padding: 1rem;
        margin-bottom: 0.75rem;
    }
    
    .trade-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    .trade-win { border-left: 4px solid #22c55e; }
    .trade-loss { border-left: 4px solid #ef4444; }
    .trade-open { border-left: 4px solid #f59e0b; }
    
    .metric-card {
        background: rgba(26, 26, 46, 0.6);
        border-radius: 12px;
        padding: 1.25rem;
        text-align: center;
    }
    
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #f1f5f9;
    }
    
    .metric-label {
        font-size: 0.85rem;
        color: #94a3b8;
        margin-top: 0.25rem;
    }
</style>
""", unsafe_allow_html=True)


def render():
    init_db()
    
    st.title("🤖 Paper Trading Bot")
    st.caption("AI-drevet betting bot med 1000 NOK startkapital")
    
    # ── Hent data ───────────────────────────────────────────────────────────
    balance = get_balance()
    summary = get_recommendation_summary()
    
    # ── Bankroll Hero ───────────────────────────────────────────────────────
    pnl = summary['total_pnl']
    pnl_color = "#22c55e" if pnl >= 0 else "#ef4444"
    
    st.markdown(f"""
    <div class="bot-hero">
        <div class="bot-hero-value">{balance:,.0f} NOK</div>
        <div class="bot-hero-label">💰 Nåværende bankroll (Start: 1000 NOK)</div>
        <div style="font-size: 1.3rem; color: {pnl_color}; margin-top: 0.5rem; font-weight: 600;">
            {pnl:+.0f} NOK ({summary['roi_pct']:+.1f}%)
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # ── Stats ───────────────────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{summary['total_count']}</div>
            <div class="metric-label">Totalt bets</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        win_rate = summary['win_rate']
        wr_color = "#22c55e" if win_rate >= 50 else "#f59e0b" if win_rate >= 30 else "#ef4444"
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value" style="color: {wr_color};">{win_rate:.1f}%</div>
            <div class="metric-label">Win rate</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value" style="color: #22c55e;">{summary['win_count']}</div>
            <div class="metric-label">Seire</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value" style="color: #ef4444;">{summary['loss_count']}</div>
            <div class="metric-label">Tap</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # ── Bot Status ──────────────────────────────────────────────────────────
    st.markdown("""
    <div class="bot-card">
        <div class="bot-card-header">
            <div class="bot-name">🎯 ValueBet Bot</div>
            <div class="bot-status">🟢 AKTIV</div>
        </div>
        <div style="color: #94a3b8; margin-bottom: 1rem;">
            Plasserer automatiske value bets basert på edge > 3%. Bruker Kelly-kriterium for stake-sizing.
        </div>
        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 1rem;">
            <div style="text-align: center;">
                <div style="font-size: 1.5rem; font-weight: 700; color: #f1f5f9;">Quarter-Kelly</div>
                <div style="font-size: 0.8rem; color: #94a3b8;">Stake-strategi</div>
            </div>
            <div style="text-align: center;">
                <div style="font-size: 1.5rem; font-weight: 700; color: #f1f5f9;">3%</div>
                <div style="font-size: 0.8rem; color: #94a3b8;">Min edge</div>
            </div>
            <div style="text-align: center;">
                <div style="font-size: 1.5rem; font-weight: 700; color: #f1f5f9;">Paper</div>
                <div style="font-size: 0.8rem; color: #94a3b8;">Trading mode</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # ── Siste Trades ────────────────────────────────────────────────────────
    st.subheader("📋 Siste Paper Trades")
    
    today = date.today()
    week_ago = today - timedelta(days=7)
    
    recent_bets = list_recommendations(
        date_from=week_ago.isoformat(),
        date_to=today.isoformat()
    )[:20]  # Siste 20
    
    if not recent_bets:
        st.info("Ingen trades ennå. Boten vil plassere bets når den finver value opportunities.")
    else:
        for bet in recent_bets:
            status = bet['status']
            pnl = bet.get('pnl', 0)
            
            if status == 'won':
                card_class = "trade-card trade-win"
                status_emoji = "✅"
                pnl_text = f"+{pnl:.0f}"
                pnl_color = "#22c55e"
            elif status == 'lost':
                card_class = "trade-card trade-loss"
                status_emoji = "❌"
                pnl_text = f"{pnl:.0f}"
                pnl_color = "#ef4444"
            else:
                card_class = "trade-card trade-open"
                status_emoji = "🟡"
                pnl_text = "ÅPEN"
                pnl_color = "#f59e0b"
            
            st.markdown(f"""
            <div class="{card_class}">
                <div class="trade-header">
                    <div>
                        <strong>{status_emoji} {bet['match']}</strong><br>
                        <small style="color: #94a3b8;">{bet['selection']} @ {bet['odds']:.2f}x · {bet['league']}</small>
                    </div>
                    <div style="text-align: right;">
                        <strong style="color: {pnl_color};">{pnl_text}</strong><br>
                        <small style="color: #94a3b8;">{bet['recommended_stake']:.0f} NOK stake</small>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
