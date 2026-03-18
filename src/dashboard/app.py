import sys
import os
import streamlit as st

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

st.set_page_config(page_title="OddsBot", layout="wide", page_icon="🎯")

from src.dashboard.pages.dashboard import render
render()
