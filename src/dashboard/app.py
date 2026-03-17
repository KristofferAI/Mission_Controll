import sys
import os

# Ensure project root is on the path
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import streamlit as st
from src.db import init_db

# ── Initialise DB ────────────────────────────────────────────────────────────
init_db()

# ── Sidebar navigation ───────────────────────────────────────────────────────
PAGES = {
    "🎯  Dashboard Pro":  "dashboard_pro",
    "📊  Analytics":       "stats",
    "⚙️  Settings":        "settings",
}

st.sidebar.markdown(
    """
    <div style="text-align: center; padding: 1rem 0;">
        <h2 style="margin: 0; color: #00d4ff; font-family: Inter, sans-serif;">
            🎯 OddsBot Pro
        </h2>
        <p style="color: #6b7280; font-size: 0.85rem; margin-top: 0.5rem;">
            Professional Value Betting
        </p>
    </div>
    """,
    unsafe_allow_html=True
)

st.sidebar.markdown("---")

choice = st.sidebar.radio("Navigate", list(PAGES.keys()), label_visibility="collapsed")
page_key = PAGES[choice]

st.sidebar.markdown("---")

# Quick status
try:
    from src.db import get_balance, get_recommendation_summary
    balance = get_balance()
    summary = get_recommendation_summary()
    
    st.sidebar.markdown(f"""
    <div style="background: linear-gradient(135deg, #1e1e2d, #16162a); 
                border-radius: 12px; padding: 1rem; border: 1px solid #2d2d44;">
        <div style="font-size: 0.75rem; color: #6b7280; text-transform: uppercase;">Bankroll</div>
        <div style="font-size: 1.5rem; font-weight: 700; color: #f3f4f6;">{balance:,.0f} NOK</div>
        <div style="font-size: 0.875rem; color: {'#22c55e' if summary['total_pnl'] >= 0 else '#ef4444'};">
            {summary['total_pnl']:+.0f} NOK ({summary['roi_pct']:+.1f}%)
        </div>
    </div>
    """, unsafe_allow_html=True)
except:
    pass

st.sidebar.markdown("---")
st.sidebar.caption("v2.0 · Professional Edition")

# ── Route to page ─────────────────────────────────────────────────────────────
if page_key == "dashboard_pro":
    from src.dashboard.pages.dashboard_pro import render
elif page_key == "stats":
    from src.dashboard.pages.stats import render
elif page_key == "settings":
    from src.dashboard.pages.settings import render

render()
