import streamlit as st
import sys
import os
from datetime import datetime

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)

from src.db import get_balance, list_recommendations, get_recommendation_summary, init_db
import plotly.graph_objects as go

# Dark theme CSS
st.markdown("""
<style>
    .stApp { background: #0d0d12; color: #e0e0e0; }
    h1 { color: #00d4ff; font-size: 2.5rem !important; }
    .stButton>button { 
        background: linear-gradient(90deg, #00d4ff, #0099cc);
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: bold;
        padding: 0.75rem 2rem;
    }
    .metric-card {
        background: #1a1a24;
        border-radius: 12px;
        padding: 1.5rem;
        border: 1px solid #2a2a3a;
    }
    .bet-card {
        background: #1a1a24;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
        border-left: 3px solid #00d4ff;
    }
    .parlay-card {
        background: linear-gradient(135deg, #1a1a24, #1f1f2e);
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        border: 1px solid #3a3a5a;
    }
</style>
""", unsafe_allow_html=True)

def render():
    st.title("🎯 OddsBot Dashboard")
    
    # Get data
    init_db()
    summary = get_recommendation_summary()
    bankroll = get_balance()
    profit = bankroll - 1000
    bets = list_recommendations()
    open_bets = [b for b in bets if b.get('status') == 'open']
    settled = [b for b in bets if b.get('status') in ('won', 'lost')]
    
    # Top metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div style="color: #888; font-size: 0.9rem;">Bankroll</div>
            <div style="font-size: 2rem; font-weight: bold; color: {'#22c55e' if profit >= 0 else '#ef4444'};">
                {bankroll:.0f} NOK
            </div>
            <div style="color: {'#22c55e' if profit >= 0 else '#ef4444'}; font-size: 0.9rem;">
                {profit:+.0f} NOK
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        win_rate = summary['win_rate']
        st.markdown(f"""
        <div class="metric-card">
            <div style="color: #888; font-size: 0.9rem;">Win Rate</div>
            <div style="font-size: 2rem; font-weight: bold; color: {'#22c55e' if win_rate >= 50 else '#ef4444'};">
                {win_rate:.1f}%
            </div>
            <div style="color: #888; font-size: 0.9rem;">
                {summary['win_count']}W / {summary['loss_count']}L
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div style="color: #888; font-size: 0.9rem;">Open Bets</div>
            <div style="font-size: 2rem; font-weight: bold; color: #00d4ff;">
                {len(open_bets)}
            </div>
            <div style="color: #888; font-size: 0.9rem;">
                {len(bets)} total
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        roi = summary['roi_pct']
        st.markdown(f"""
        <div class="metric-card">
            <div style="color: #888; font-size: 0.9rem;">ROI</div>
            <div style="font-size: 2rem; font-weight: bold; color: {'#22c55e' if roi >= 0 else '#ef4444'};">
                {roi:+.1f}%
            </div>
            <div style="color: #888; font-size: 0.9rem;">
                All time
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Performance Chart
    if settled:
        st.subheader("📈 Performance")
        
        cumulative = []
        running_total = 0
        for bet in reversed(settled):
            running_total += bet.get('pnl', 0)
            cumulative.append(running_total)
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            y=cumulative,
            mode='lines+markers',
            line=dict(color='#00d4ff', width=3),
            marker=dict(size=6, color='#00d4ff'),
            fill='tozeroy',
            fillcolor='rgba(0, 212, 255, 0.1)'
        ))
        
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#e0e0e0'),
            xaxis=dict(showgrid=False, showticklabels=False),
            yaxis=dict(gridcolor='#2a2a3a', zerolinecolor='#444'),
            margin=dict(l=0, r=0, t=0, b=0),
            height=250
        )
        
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    
    # Run Bot Button
    st.subheader("🎮 Actions")
    if st.button("🤖 Run Bot (Settle & Place New Bets)", use_container_width=True):
        import subprocess
        with st.spinner("Running bot..."):
            result = subprocess.run(
                ['python3', 'odds_bot/main.py'],
                capture_output=True,
                text=True,
                cwd=_ROOT
            )
            st.code(result.stdout)
            st.rerun()
    
    # Tabs for Singles and Parlays
    tab1, tab2 = st.tabs(["⚡ Singles", "🎯 Parlays (Coming Soon)"])
    
    with tab1:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader(f"Open Bets ({len(open_bets)})")
            if open_bets:
                for bet in open_bets[:10]:
                    st.markdown(f"""
                    <div class="bet-card">
                        <div style="display: flex; justify-content: space-between;">
                            <span style="font-weight: bold;">{bet.get('match', 'Unknown')}</span>
                            <span style="color: #00d4ff; font-weight: bold;">{bet.get('odds', 0):.2f}x</span>
                        </div>
                        <div style="color: #888; font-size: 0.85rem; margin-top: 0.25rem;">
                            {bet.get('league', 'Unknown')} • <b>{bet.get('selection', 'Unknown')}</b> • {bet.get('edge_pct', 0):.1f}% edge
                        </div>
                        <div style="color: #666; font-size: 0.8rem; margin-top: 0.25rem;">
                            Stake: {bet.get('recommended_stake', 0):.0f} NOK
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("No open bets. Run the bot to place bets.")
        
        with col2:
            st.subheader(f"Recent Results ({len(settled)})")
            if settled:
                for bet in settled[:10]:
                    pnl = bet.get('pnl', 0)
                    emoji = "✅" if pnl > 0 else "❌"
                    color = "#22c55e" if pnl > 0 else "#ef4444"
                    st.markdown(f"""
                    <div class="bet-card" style="border-left-color: {color};">
                        <div style="display: flex; justify-content: space-between;">
                            <span>{emoji} <b>{bet.get('match', 'Unknown')}</b></span>
                            <span style="color: {color}; font-weight: bold;">{pnl:+.0f} NOK</span>
                        </div>
                        <div style="color: #888; font-size: 0.8rem; margin-top: 0.25rem;">
                            {bet.get('selection', 'Unknown')} @ {bet.get('odds', 0):.2f}x
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("No settled bets yet.")
    
    with tab2:
        st.markdown("""
        <div class="parlay-card">
            <h3 style="color: #00d4ff; margin-top: 0;">🎯 Parlays Coming Soon</h3>
            <p>Parlays combine multiple bets for higher odds and bigger payouts.</p>
            <ul>
                <li>2-3 leg parlays with anti-correlation</li>
                <li>Minimum 5% combined edge</li>
                <li>Higher risk, higher reward</li>
            </ul>
            <p style="color: #888; font-size: 0.9rem;">Status: <span style="color: #f59e0b;">🚧 Under Development</span></p>
        </div>
        """, unsafe_allow_html=True)
