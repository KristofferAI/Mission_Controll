import streamlit as st
import pandas as pd
from src.db import add_bot, list_bots, update_bot_status, delete_bot

BOT_TYPES = ["generic", "forecaster", "odds_aggregator", "arbitrage", "ml_model", "scraper"]

STATUS_COLOURS = {
    "idle":    "🔵",
    "running": "🟢",
    "error":   "🔴",
    "paused":  "🟡",
}


def render():
    st.title("🤖 Bot Registry")
    st.markdown("---")

    col_list, col_form = st.columns([2, 1])

    # ── Register form ─────────────────────────────────────────────────────────
    with col_form:
        st.subheader("➕ Register New Bot")
        with st.form("add_bot_form", clear_on_submit=True):
            name        = st.text_input("Bot Name *", placeholder="e.g. ForecastBot-01")
            bot_type    = st.selectbox("Type", BOT_TYPES)
            description = st.text_area("Description", placeholder="What does this bot do?")
            submitted   = st.form_submit_button("Register Bot", use_container_width=True)
            if submitted:
                if name.strip():
                    add_bot(name.strip(), bot_type, description)
                    st.success(f"✅ Bot **{name}** registered!")
                    st.rerun()
                else:
                    st.error("Bot name is required.")

    # ── Bot list ──────────────────────────────────────────────────────────────
    with col_list:
        bots = list_bots()
        st.subheader(f"All Bots ({len(bots)})")
        if not bots:
            st.info("No bots registered yet. Use the form to add your first bot.")
        else:
            for bot in bots:
                icon   = STATUS_COLOURS.get(bot["status"], "⚪")
                header = f"{icon} **{bot['name']}** — `{bot['bot_type']}` — {bot['status'].upper()}"
                with st.expander(header, expanded=False):
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Status",   bot["status"])
                    c2.metric("Runs",     bot["run_count"])
                    c3.metric("Last Run", bot["last_run"][:16] if bot["last_run"] else "Never")
                    if bot["description"]:
                        st.caption(bot["description"])
                    st.markdown("---")
                    a, b, c, d = st.columns(4)
                    if a.button("▶ Run",   key=f"run_{bot['id']}"):
                        update_bot_status(bot["id"], "running")
                        st.rerun()
                    if b.button("⏸ Pause", key=f"pause_{bot['id']}"):
                        update_bot_status(bot["id"], "paused")
                        st.rerun()
                    if c.button("⏹ Idle",  key=f"idle_{bot['id']}"):
                        update_bot_status(bot["id"], "idle")
                        st.rerun()
                    if d.button("🗑 Delete", key=f"del_{bot['id']}"):
                        delete_bot(bot["id"])
                        st.warning(f"Bot **{bot['name']}** deleted.")
                        st.rerun()
