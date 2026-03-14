import streamlit as st
from src.db import get_balance, set_balance, list_bots, list_bets, list_jobs


def render():
    st.title("🔧 Settings")
    st.markdown("---")

    # ── Bankroll control ──────────────────────────────────────────────────────
    st.subheader("💰 Bankroll")
    current = get_balance()
    st.metric("Current Balance", f"${current:,.2f}")
    with st.form("bankroll_form"):
        new_bal = st.number_input("Set Bankroll ($)", min_value=0.0,
                                   value=float(current), step=10.0)
        if st.form_submit_button("💾 Update Bankroll", use_container_width=True):
            set_balance(new_bal)
            st.success(f"Bankroll updated to **${new_bal:,.2f}**")
            st.rerun()

    st.markdown("---")

    # ── Stats ─────────────────────────────────────────────────────────────────
    st.subheader("📊 Database Stats")
    bots = list_bots()
    bets = list_bets()
    jobs = list_jobs()
    c1, c2, c3 = st.columns(3)
    c1.metric("Bots",  len(bots))
    c2.metric("Bets",  len(bets))
    c3.metric("Jobs",  len(jobs))

    st.markdown("---")

    # ── Reset ─────────────────────────────────────────────────────────────────
    st.subheader("⚠️ Danger Zone")
    st.warning("Resetting the bankroll does not erase bets or bots — it only resets the balance.")
    if st.button("🔄 Reset Bankroll to $1,000", type="secondary"):
        set_balance(1000.0)
        st.success("Bankroll reset to $1,000.")
        st.rerun()

    st.markdown("---")
    st.subheader("ℹ️ About")
    st.info(
        "**Mission Controll** v0.1 MVP\n\n"
        "Paper Betting Office — built with Python, Streamlit, and SQLite.\n\n"
        "Dark theme with `#1E90FF` accent. Generic multi-bot registry. "
        "Single flat repo."
    )
