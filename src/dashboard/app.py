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
        /* Dark theme base */
        .stApp {
            background: linear-gradient(135deg, #0f0f1e 0%, #1a1a2e 50%, #16213e 100%);
        }
        
        /* Sidebar */
        section[data-testid="stSidebar"] { 
            background: linear-gradient(180deg, #0d1117 0%, #161c24 100%) !important;
            border-right: 1px solid #6366f122;
        }
        
        section[data-testid="stSidebar"] .stRadio > div {
            background: rgba(99, 102, 241, 0.1);
            border-radius: 8px;
            padding: 0.5rem;
        }
        
        section[data-testid="stSidebar"] .stRadio label {
            color: #94a3b8 !important;
            font-size: 0.95rem !important;
        }
        
        section[data-testid="stSidebar"] .stRadio label:hover {
            color: #22d3ee !important;
        }
        
        /* Headings */
        h1, h2, h3 { 
            background: linear-gradient(90deg, #6366f1, #22d3ee);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        /* Metric cards */
        div[data-testid="stMetric"] {
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            border: 1px solid #6366f144;
            border-radius: 12px;
            padding: 1rem;
        }
        
        div[data-testid="stMetric"] label {
            color: #94a3b8 !important;
        }
        
        div[data-testid="stMetric"] div {
            color: #f1f5f9 !important;
            font-weight: 600;
        }
        
        /* Expanders */
        details { 
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%) !important; 
            border: 1px solid #6366f144;
            border-radius: 12px;
        }
        
        /* Buttons */
        .stButton > button { 
            background: linear-gradient(90deg, #6366f1, #22d3ee) !important;
            border: none !important;
            border-radius: 8px !important;
            color: white !important;
            font-weight: 600 !important;
            transition: all 0.3s ease !important;
        }
        
        .stButton > button:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 10px 20px -5px rgba(99, 102, 241, 0.4) !important;
        }
        
        /* DataFrames */
        .stDataFrame {
            background: rgba(26, 26, 46, 0.6) !important;
            border-radius: 12px !important;
        }
        
        /* Info boxes */
        .stAlert {
            background: rgba(99, 102, 241, 0.1) !important;
            border: 1px solid #6366f144 !important;
            border-radius: 8px !important;
        }
        
        /* Selectbox and inputs */
        .stSelectbox > div > div,
        .stTextInput > div > div {
            background: rgba(26, 26, 46, 0.6) !important;
            border-color: #6366f144 !important;
            border-radius: 8px !important;
        }
        
        /* Slider */
        .stSlider > div > div {
            background: #6366f144 !important;
        }
        
        /* Caption */
        .stCaption {
            color: #94a3b8 !important;
        }
        
        /* Code blocks */
        .stCodeBlock {
            background: rgba(26, 26, 46, 0.8) !important;
            border: 1px solid #6366f144 !important;
            border-radius: 8px !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Sidebar navigation ───────────────────────────────────────────────────────
PAGES = {
    "🏠  Dashboard":    "dashboard",
    "💰  Bets":         "bets",
    "📊  Statistikk":   "stats",
    "⚙️  Innstillinger": "settings",
}

st.sidebar.markdown(
    """
    <div style="text-align: center; padding: 1rem 0;">
        <h2 style="margin: 0; background: linear-gradient(90deg, #6366f1, #22d3ee); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
            🎯 Mission Controll
        </h2>
        <p style="color: #94a3b8; font-size: 0.85rem; margin-top: 0.5rem;">
            Sports Betting · EV Edition
        </p>
    </div>
    """,
    unsafe_allow_html=True
)

st.sidebar.markdown("---")

choice = st.sidebar.radio("Navigate", list(PAGES.keys()), label_visibility="collapsed")
page_key = PAGES[choice]

st.sidebar.markdown("---")

# Quick status in sidebar
try:
    from src.db import get_balance, get_scheduler_status, get_daily_stats
    balance = get_balance()
    scheduler = get_scheduler_status()
    daily = get_daily_stats()
    
    st.sidebar.markdown("### 📊 Quick Stats")
    st.sidebar.metric("Bankroll", f"{balance:,.0f} NOK")
    st.sidebar.metric("Dagens PnL", f"{daily['daily_pnl']:+.0f} NOK")
    
    if scheduler.get('is_running'):
        st.sidebar.success("🟢 Scheduler aktiv")
    else:
        st.sidebar.error("🔴 Scheduler stoppet")
except:
    pass

st.sidebar.markdown("---")
st.sidebar.caption("Built with Streamlit + SQLite")

# ── Route to page ─────────────────────────────────────────────────────────────
if page_key == "dashboard":
    from src.dashboard.pages.dashboard import render
elif page_key == "bets":
    from src.dashboard.pages.bets import render
elif page_key == "stats":
    from src.dashboard.pages.stats import render
elif page_key == "settings":
    from src.dashboard.pages.settings import render

render()
