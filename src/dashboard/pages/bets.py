import streamlit as st
import pandas as pd
from src.db import place_bet, settle_bet, list_bets, list_bots, get_balance


def render():
    st.title("💰 Bets Ledger")
    st.markdown("---")

    balance = get_balance()
    bots    = list_bots()
    bets    = list_bets()

    # KPI row
    open_bets = [b for b in bets if b["status"] == "open"]
    settled   = [b for b in bets if b["status"] in ("won", "lost")]
    total_pnl = sum(b["pnl"] for b in settled)
    wins      = len([b for b in settled if b["status"] == "won"])

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💰 Bankroll",  f"${balance:,.2f}")
    c2.metric("📋 Open Bets", len(open_bets))
    c3.metric("✅ Wins",       wins)
    c4.metric("📈 PnL",        f"${total_pnl:+.2f}")

    st.markdown("---")
    col_list, col_form = st.columns([2, 1])

    # ── Place bet form ────────────────────────────────────────────────────────
    with col_form:
        st.subheader("🎯 Place New Bet")
        if not bots:
            st.warning("Register a bot first in the **Bots** tab.")
        else:
            with st.form("place_bet_form", clear_on_submit=True):
                bot_opts = {b["name"]: b["id"] for b in bots}
                sel_bot  = st.selectbox("Bot", list(bot_opts.keys()))
                match_id = st.text_input("Match ID", placeholder="EPL-2026-001")
                home     = st.text_input("Home Team",  placeholder="Arsenal")
                away     = st.text_input("Away Team",  placeholder="Chelsea")
                stake    = st.number_input("Stake ($)", min_value=1.0,
                                           max_value=max(1.0, float(balance)),
                                           value=10.0, step=1.0)
                odds     = st.number_input("Odds",     min_value=1.01,
                                           value=2.0, step=0.05)
                pred     = st.selectbox("Predicted Outcome", ["home", "draw", "away"])
                sub      = st.form_submit_button("Place Bet", use_container_width=True)
                if sub:
                    try:
                        place_bet(bot_opts[sel_bot], match_id, home, away, stake, odds, pred)
                        st.success(f"✅ Bet placed: {home} vs {away} — ${stake:.0f} @ {odds}")
                        st.rerun()
                    except ValueError as e:
                        st.error(str(e))

    # ── Bet list ──────────────────────────────────────────────────────────────
    with col_list:
        if open_bets:
            st.subheader(f"⏳ Open Bets ({len(open_bets)})")
            for bet in open_bets:
                label = f"#{bet['id']} — {bet['home_team']} vs {bet['away_team']} | ${bet['stake']:.0f} @ {bet['odds']}"
                with st.expander(label):
                    c1, c2 = st.columns(2)
                    c1.write(f"**Predicted:** {bet['predicted_outcome']}")
                    c2.write(f"**Match ID:** {bet['match_id']}")
                    actual = st.selectbox("Actual Result", ["home", "draw", "away"],
                                          key=f"actual_{bet['id']}")
                    if st.button("✅ Settle", key=f"settle_{bet['id']}"):
                        settle_bet(bet["id"], actual)
                        st.success("Bet settled!")
                        st.rerun()

        if settled:
            st.markdown("---")
            st.subheader(f"📊 Settled Bets ({len(settled)})")
            df = pd.DataFrame(settled)[[
                "id", "home_team", "away_team", "stake", "odds",
                "predicted_outcome", "actual_outcome", "status", "pnl"
            ]]
            df.columns = ["#", "Home", "Away", "Stake", "Odds", "Pred", "Actual", "Result", "PnL"]
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.markdown(f"**Total PnL: ${total_pnl:+.2f}**")
