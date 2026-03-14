import sys
import os

# Ensure project root is on the path
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import streamlit as st
from src.db import init_db

st.set_page_config(
    page_title="Mission Controll",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Initialise DB ────────────────────────────────────────────────────────────
init_db()

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
        /* Sidebar */
        section[data-testid="stSidebar"] { background: #0D1117; }
        /* Headings */
        h1, h2, h3 { color: #1E90FF !important; }
        /* Metric cards */
        div[data-testid="stMetric"] {
            background: #161C24;
            border-radius: 10px;
            padding: 0.8rem 1rem;
            border: 1px solid #1E90FF44;
        }
        /* Expanders */
        details { background: #161C24 !important; border-radius: 8px; }
        /* Buttons */
        .stButton > button { border-radius: 6px; }
        /* DataFrames */
        .stDataFrame { border-radius: 8px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Sidebar navigation ────────────────────────────────────────────────────────
PAGES = {
    "🎯  Overview":  "overview",
    "🤖  Bots":      "bots",
    "💰  Bets":      "bets",
    "⚙️  Jobs":      "jobs",
    "🔧  Settings":  "settings",
}

st.sidebar.image(
    "https://img.shields.io/badge/Mission_Controll-v0.1-1E90FF?style=for-the-badge",
    use_container_width=True,
)
st.sidebar.title("Mission Controll")
st.sidebar.caption("Paper Betting Office · MVP")
st.sidebar.markdown("---")

choice = st.sidebar.radio("Navigate", list(PAGES.keys()), label_visibility="collapsed")
page_key = PAGES[choice]

st.sidebar.markdown("---")
st.sidebar.caption("Built with Streamlit + SQLite")

# ── Route to page ─────────────────────────────────────────────────────────────
if page_key == "overview":
    from src.dashboard.pages.overview import render
elif page_key == "bots":
    from src.dashboard.pages.bots import render
elif page_key == "bets":
    from src.dashboard.pages.bets import render
elif page_key == "jobs":
    from src.dashboard.pages.jobs import render
elif page_key == "settings":
    from src.dashboard.pages.settings import render

render()
