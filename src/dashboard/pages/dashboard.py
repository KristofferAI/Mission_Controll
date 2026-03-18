import streamlit as st
import sys
import os
from datetime import datetime

# Path setup
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)

from src.db import get_balance, list_recommendations, init_db

# Initialize
init_db()
st.set_page_config(page_title="OddsBot", layout="wide")

# Simple dark theme CSS
st.markdown("""
<style>
    .stApp { background: #0a0a0a; }
    h1 { color: #00d4ff; }
    .stButton>button { 
        background: #00d4ff; 
        color: black; 
        border-radius: 8px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Title
st.title("🎯 OddsBot Dashboard")

# Bankroll
col1, col2, col3 = st.columns(3)
bankroll = get_balance()
profit = bankroll - 1000

with col1:
    st.metric("Bankroll", f"{bankroll:.0f} NOK", f"{profit:+.0f}")

# Get all bets
bets = list_recommendations()
open_bets = [b for b in bets if b.get('status') == 'open']
settled = [b for b in bets if b.get('status') in ('won', 'lost')]

with col2:
    st.metric("Open Bets", len(open_bets))

with col3:
    wins = len([b for b in settled if b.get('status') == 'won'])
    total = len(settled)
    wr = (wins / total * 100) if total > 0 else 0
    st.metric("Win Rate", f"{wr:.0f}%", f"{wins}/{total}")

# Open Bets
st.subheader("⚡ Open Bets")
if open_bets:
    for bet in open_bets[:10]:
        with st.container():
            c1, c2, c3 = st.columns([3, 2, 1])
            with c1:
                st.write(f"**{bet.get('match', 'Unknown')}**")
                st.caption(f"{bet.get('league', 'Unknown')} | {bet.get('selection', 'Unknown')}")
            with c2:
                st.write(f"Odds: {bet.get('odds', 0):.2f}x")
                st.caption(f"Edge: {bet.get('edge_pct', 0):.1f}%")
            with c3:
                st.write(f"{bet.get('recommended_stake', 0):.0f} NOK")
            st.divider()
else:
    st.info("No open bets. Run the bot to place bets.")

# Actions
st.subheader("🎮 Actions")
col1, col2 = st.columns(2)

with col1:
    if st.button("🤖 Run Bot", use_container_width=True):
        import subprocess
        with st.spinner("Running..."):
            result = subprocess.run(
                ['python3', 'odds_bot/main.py'],
                capture_output=True,
                text=True,
                cwd=_ROOT
            )
            st.code(result.stdout)
            st.rerun()

with col2:
    if st.button("🔄 Refresh", use_container_width=True):
        st.rerun()

# Settled bets
if settled:
    st.subheader("📊 Recent Results")
    for bet in settled[:5]:
        emoji = "✅" if bet.get('status') == 'won' else "❌"
        pnl = bet.get('pnl', 0)
        st.write(f"{emoji} {bet.get('match', 'Unknown')} | {pnl:+.0f} NOK")
