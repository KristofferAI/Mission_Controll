import streamlit as st
import sys
import os
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, date, timedelta

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.db import (
    get_balance, get_recommendation_summary, get_recent_results,
    list_recommendations, get_daily_stats
)

# ── DARK PRO THEME ──────────────────────────────────────────────────────────
st.set_page_config(
    page_title="OddsBot Pro",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    /* GLOBAL DARK THEME */
    .stApp {
        background: #0a0a0f !important;
    }
    
    /* REMOVE STREAMLIT HEADER */
    header {visibility: hidden;}
    
    /* CUSTOM FONTS */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif !important;
    }
    
    /* MAIN CONTAINER */
    .main {
        max-width: 1400px !important;
        padding: 0 !important;
    }
    
    /* HERO SECTION */
    .hero-container {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border-bottom: 1px solid #2d2d44;
        padding: 2rem 3rem;
        margin: -1rem -1rem 2rem -1rem;
    }
    
    .hero-title {
        font-size: 2.5rem;
        font-weight: 800;
        background: linear-gradient(90deg, #00d4ff, #7c3aed);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
    }
    
    .hero-subtitle {
        color: #6b7280;
        font-size: 1rem;
        margin-top: 0.5rem;
    }
    
    /* METRIC CARDS */
    .metric-row {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 1rem;
        margin-bottom: 2rem;
    }
    
    .metric-card {
        background: linear-gradient(135deg, #1e1e2d 0%, #16162a 100%);
        border: 1px solid #2d2d44;
        border-radius: 16px;
        padding: 1.5rem;
        position: relative;
        overflow: hidden;
    }
    
    .metric-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: linear-gradient(90deg, #00d4ff, #7c3aed);
    }
    
    .metric-label {
        color: #6b7280;
        font-size: 0.875rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.5rem;
    }
    
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: #f3f4f6;
    }
    
    .metric-change {
        font-size: 0.875rem;
        font-weight: 600;
        margin-top: 0.25rem;
    }
    
    .positive { color: #22c55e; }
    .negative { color: #ef4444; }
    
    /* BET CARDS */
    .bet-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
        gap: 1rem;
    }
    
    .bet-card {
        background: linear-gradient(135deg, #1e1e2d 0%, #16162a 100%);
        border: 1px solid #2d2d44;
        border-radius: 12px;
        padding: 1.25rem;
        transition: all 0.2s ease;
    }
    
    .bet-card:hover {
        border-color: #3d3d5c;
        transform: translateY(-2px);
    }
    
    .bet-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 1rem;
    }
    
    .bet-match {
        font-weight: 600;
        color: #f3f4f6;
        font-size: 1rem;
    }
    
    .bet-league {
        color: #6b7280;
        font-size: 0.75rem;
        margin-top: 0.25rem;
    }
    
    .bet-odds {
        background: linear-gradient(135deg, #00d4ff, #0891b2);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 8px;
        font-weight: 700;
        font-size: 1.1rem;
    }
    
    .bet-body {
        border-top: 1px solid #2d2d44;
        padding-top: 1rem;
    }
    
    .bet-selection {
        font-size: 1.1rem;
        color: #f3f4f6;
        font-weight: 500;
        margin-bottom: 0.75rem;
    }
    
    .bet-stats {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 0.75rem;
    }
    
    .bet-stat {
        text-align: center;
    }
    
    .bet-stat-label {
        font-size: 0.7rem;
        color: #6b7280;
        text-transform: uppercase;
    }
    
    .bet-stat-value {
        font-size: 1rem;
        font-weight: 600;
        color: #f3f4f6;
    }
    
    /* SECTION HEADERS */
    .section-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin: 2rem 0 1rem 0;
        padding-bottom: 0.75rem;
        border-bottom: 1px solid #2d2d44;
    }
    
    .section-title {
        font-size: 1.25rem;
        font-weight: 700;
        color: #f3f4f6;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    /* STATUS BADGES */
    .badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    
    .badge-win {
        background: rgba(34, 197, 94, 0.2);
        color: #22c55e;
    }
    
    .badge-loss {
        background: rgba(239, 68, 68, 0.2);
        color: #ef4444;
    }
    
    .badge-open {
        background: rgba(245, 158, 11, 0.2);
        color: #f59e0b;
    }
    
    /* CHART CONTAINER */
    .chart-container {
        background: linear-gradient(135deg, #1e1e2d 0%, #16162a 100%);
        border: 1px solid #2d2d44;
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
    }
    
    /* EMPTY STATE */
    .empty-state {
        text-align: center;
        padding: 4rem 2rem;
        color: #6b7280;
    }
    
    /* BUTTONS */
    .stButton > button {
        background: linear-gradient(135deg, #00d4ff, #0891b2) !important;
        border: none !important;
        border-radius: 8px !important;
        color: white !important;
        font-weight: 600 !important;
        padding: 0.75rem 1.5rem !important;
        transition: all 0.2s ease !important;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 10px 20px -5px rgba(0, 212, 255, 0.3) !important;
    }
</style>
""", unsafe_allow_html=True)


# ── DATA FETCHING ───────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def load_data():
    """Last alle data med caching."""
    return {
        'balance': get_balance(),
        'summary': get_recommendation_summary(),
        'results': get_recent_results(limit=20),
        'recommendations': list_recommendations()[:50],
        'daily': get_daily_stats()
    }


# ── RENDER FUNCTIONS ────────────────────────────────────────────────────────
def render_hero(balance: float, summary: dict):
    """Render hero section med key metrics."""
    pnl = summary['total_pnl']
    roi = summary['roi_pct']
    
    pnl_class = 'positive' if pnl >= 0 else 'negative'
    pnl_sign = '+' if pnl >= 0 else ''
    
    st.markdown(f"""
    <div class="hero-container">
        <h1 class="hero-title">🎯 OddsBot Pro</h1>
        <p class="hero-subtitle">AI-drevet value betting med profesjonell risk management</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Metrics grid
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Bankroll</div>
            <div class="metric-value">{balance:,.0f} NOK</div>
            <div class="metric-change {pnl_class}">{pnl_sign}{pnl:,.0f} NOK</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        win_rate = summary['win_rate']
        wr_class = 'positive' if win_rate >= 50 else 'negative'
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Win Rate</div>
            <div class="metric-value" style="color: {'#22c55e' if win_rate >= 50 else '#ef4444'};">{win_rate:.1f}%</div>
            <div class="metric-change">{summary['win_count']}W / {summary['loss_count']}L</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        roi_class = 'positive' if roi >= 0 else 'negative'
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">ROI</div>
            <div class="metric-value {roi_class}">{roi:+.1f}%</div>
            <div class="metric-change">All-time return</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Active Bets</div>
            <div class="metric-value">{summary['total_count']}</div>
            <div class="metric-change">{summary.get('pending_count', 0)} pending</div>
        </div>
        """, unsafe_allow_html=True)


def render_performance_chart(results: list):
    """Render performance chart med Plotly."""
    if not results:
        return
    
    st.markdown('<div class="section-header"><div class="section-title">📈 Performance</div></div>', unsafe_allow_html=True)
    
    # Prepare data
    dates = []
    pnls = []
    cumulative = 0
    
    for r in reversed(results):
        dates.append(r.get('date', '')[:10])
        pnl = r.get('pnl', 0)
        cumulative += pnl
        pnls.append(cumulative)
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=dates,
        y=pnls,
        mode='lines+markers',
        name='Cumulative PnL',
        line=dict(color='#00d4ff', width=3),
        marker=dict(size=8, color='#00d4ff'),
        fill='tozeroy',
        fillcolor='rgba(0, 212, 255, 0.1)'
    ))
    
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#f3f4f6', family='Inter'),
        xaxis=dict(
            gridcolor='#2d2d44',
            showgrid=True,
            zeroline=False
        ),
        yaxis=dict(
            gridcolor='#2d2d44',
            showgrid=True,
            zeroline=True,
            zerolinecolor='#6b7280',
            zerolinewidth=1
        ),
        showlegend=False,
        margin=dict(l=0, r=0, t=0, b=0),
        height=300
    )
    
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    st.markdown('</div>', unsafe_allow_html=True)


def render_bet_card(bet: dict):
    """Render en bet card."""
    status = bet.get('status', 'open')
    
    if status == 'won':
        badge = '<span class="badge badge-win">✓ WON</span>'
        pnl = f"+{bet.get('pnl', 0):.0f}"
        pnl_color = '#22c55e'
    elif status == 'lost':
        badge = '<span class="badge badge-loss">✗ LOSS</span>'
        pnl = f"{bet.get('pnl', 0):.0f}"
        pnl_color = '#ef4444'
    else:
        badge = '<span class="badge badge-open">◉ OPEN</span>'
        pnl = "PENDING"
        pnl_color = '#f59e0b'
    
    edge = bet.get('edge_pct', 0)
    edge_color = '#22c55e' if edge >= 5 else '#f59e0b' if edge >= 3 else '#ef4444'
    
    st.markdown(f"""
    <div class="bet-card">
        <div class="bet-header">
            <div>
                <div class="bet-match">{bet['match']}</div>
                <div class="bet-league">🏆 {bet['league']} · {badge}</div>
            </div>
            <div class="bet-odds">{bet['odds']:.2f}x</div>
        </div>
        <div class="bet-body">
            <div class="bet-selection">{bet['selection']}</div>
            <div class="bet-stats">
                <div class="bet-stat">
                    <div class="bet-stat-label">Edge</div>
                    <div class="bet-stat-value" style="color: {edge_color};">{edge:.1f}%</div>
                </div>
                <div class="bet-stat">
                    <div class="bet-stat-label">Stake</div>
                    <div class="bet-stat-value">{bet.get('recommended_stake', 0):.0f} NOK</div>
                </div>
                <div class="bet-stat">
                    <div class="bet-stat-label">PnL</div>
                    <div class="bet-stat-value" style="color: {pnl_color};">{pnl}</div>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_active_bets(recommendations: list):
    """Render active bets section."""
    st.markdown('<div class="section-header"><div class="section-title">⚡ Active Bets</div></div>', unsafe_allow_html=True)
    
    active = [r for r in recommendations if r.get('status') in ('open', None, '')]
    
    if not active:
        st.markdown('<div class="empty-state">No active bets. Run the bot to find opportunities.</div>', unsafe_allow_html=True)
        return
    
    # Show first 6
    cols = st.columns(3)
    for i, bet in enumerate(active[:6]):
        with cols[i % 3]:
            render_bet_card(bet)


def render_recent_results(results: list):
    """Render recent results."""
    st.markdown('<div class="section-header"><div class="section-title">📊 Recent Results</div></div>', unsafe_allow_html=True)
    
    if not results:
        st.markdown('<div class="empty-state">No results yet.</div>', unsafe_allow_html=True)
        return
    
    cols = st.columns(3)
    for i, bet in enumerate(results[:6]):
        with cols[i % 3]:
            render_bet_card(bet)


# ── MAIN ────────────────────────────────────────────────────────────────────
def render():
    # Load data
    data = load_data()
    
    # Render sections
    render_hero(data['balance'], data['summary'])
    
    # Performance chart
    render_performance_chart(data['results'])
    
    # Two column layout for bets
    col1, col2 = st.columns([1, 1])
    
    with col1:
        render_active_bets(data['recommendations'])
    
    with col2:
        render_recent_results(data['results'])
    
    # Action buttons
    st.markdown('<div class="section-header"><div class="section-title">🎮 Actions</div></div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    
    with col2:
        if st.button("🤖 Run Bot", use_container_width=True):
            import subprocess
            with st.spinner("Running bot..."):
                result = subprocess.run(
                    ['python3', 'odds_bot/main_v2.py', '--run'],
                    capture_output=True,
                    text=True,
                    cwd=_ROOT
                )
                if result.returncode == 0:
                    st.success("Bot completed successfully!")
                    st.cache_data.clear()
                else:
                    st.error(f"Bot failed: {result.stderr}")
    
    with col3:
        st.button("⚙️ Settings", use_container_width=True, disabled=True)


# Run
if __name__ == '__main__':
    render()
