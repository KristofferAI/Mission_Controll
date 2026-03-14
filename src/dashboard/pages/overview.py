import streamlit as st
import pandas as pd
from src.db import get_balance, list_bots, list_bets, list_jobs


def render():
    st.title("🎯 Mission Controll — Overview")
    st.markdown("---")

    balance = get_balance()
    bots    = list_bots()
    bets    = list_bets()
    jobs    = list_jobs()

    open_bets    = [b for b in bets if b["status"] == "open"]
    settled      = [b for b in bets if b["status"] in ("won", "lost")]
    total_pnl    = sum(b["pnl"] for b in settled)
    active_bots  = len([b for b in bots if b["status"] != "idle"])
    pending_jobs = len([j for j in jobs if j["status"] == "pending"])
    win_rate     = (len([b for b in settled if b["status"] == "won"]) / len(settled) * 100) if settled else 0

    # ── KPI row ───────────────────────────────────────────────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("💰 Bankroll",     f"${balance:,.2f}")
    c2.metric("🤖 Bots",         len(bots), f"{active_bots} active")
    c3.metric("📋 Open Bets",    len(open_bets))
    c4.metric("📈 Total PnL",    f"${total_pnl:+.2f}")
    c5.metric("🎯 Win Rate",     f"{win_rate:.0f}%",
              f"{len(settled)} settled")

    st.markdown("---")

    # ── Bot registry snapshot ─────────────────────────────────────────────────
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("🤖 Bot Registry")
        if bots:
            df = pd.DataFrame(bots)[["name", "bot_type", "status", "run_count"]]
            df.columns = ["Name", "Type", "Status", "Runs"]
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No bots registered yet — head to the **Bots** tab to add one.")

    # ── Recent bets snapshot ──────────────────────────────────────────────────
    with col_b:
        st.subheader("💰 Recent Bets")
        if bets:
            df = pd.DataFrame(bets[:8])[
                ["match_id", "home_team", "away_team", "stake", "odds", "status", "pnl"]
            ]
            df.columns = ["Match", "Home", "Away", "Stake", "Odds", "Status", "PnL"]
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No bets placed yet — head to the **Bets** tab to start.")

    # ── Cumulative PnL chart ──────────────────────────────────────────────────
    if settled:
        st.markdown("---")
        st.subheader("📊 Cumulative PnL")
        pnl_series = pd.Series(
            [b["pnl"] for b in settled],
            name="Cumulative PnL"
        ).cumsum()
        st.line_chart(pnl_series)

    # ── Jobs snapshot ─────────────────────────────────────────────────────────
    if jobs:
        st.markdown("---")
        st.subheader(f"⚙️ Jobs — {pending_jobs} pending")
        df = pd.DataFrame(jobs[:5])[["title", "bot_name", "status", "created_at"]]
        df.columns = ["Job", "Bot", "Status", "Created"]
        st.dataframe(df, use_container_width=True, hide_index=True)
