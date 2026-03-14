"""
OddsBot Dashboard Page — ⚽ OddsBot
"""
import sys
import os
import subprocess

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import streamlit as st
import pandas as pd

from src.db import init_db, list_parlays, list_parlay_legs, list_learning_log


def render():
    st.title("⚽ OddsBot")
    st.caption("Football EV parlay analysis — Eliteserien & 1.divisjon")

    init_db()

    tab_parlays, tab_log, tab_value, tab_run = st.tabs([
        "🏆 Parlays", "📚 Learning Log", "💡 Value Bets", "🚀 Run Bot"
    ])

    # ── Tab: Parlays ─────────────────────────────────────────────────────────
    with tab_parlays:
        st.subheader("All Parlays")
        parlays = list_parlays()
        if not parlays:
            st.info("No parlays yet. Run the bot to generate some! 🤖")
        else:
            summary = pd.DataFrame([{
                "ID": p["id"],
                "Name": p["name"],
                "Status": p["status"],
                "Combined Odds": f"{p['combined_odds']:.2f}x",
                "Stake": f"NOK {p['stake']:.0f}",
                "PnL": f"NOK {p['pnl']:.2f}",
                "Created": p["created_at"][:16] if p["created_at"] else "",
            } for p in parlays])
            st.dataframe(summary, use_container_width=True, hide_index=True)

            st.markdown("---")
            st.subheader("Parlay Details")
            for p in parlays:
                status_icon = {"open": "🟡", "won": "🟢", "lost": "🔴"}.get(p["status"], "⚪")
                with st.expander(f"{status_icon} #{p['id']} — {p['name']} | {p['combined_odds']:.2f}x | {p['status'].upper()}"):
                    legs = list_parlay_legs(p["id"])
                    if legs:
                        legs_df = pd.DataFrame([{
                            "Match": f"{leg['home_team']} vs {leg['away_team']}",
                            "Bet Type": leg["bet_type"],
                            "Selection": leg["selection"],
                            "Odds": leg["odds"],
                            "Result": leg["result"],
                        } for leg in legs])
                        st.dataframe(legs_df, use_container_width=True, hide_index=True)
                    else:
                        st.caption("No legs recorded.")
                    if p.get("reasoning"):
                        st.caption(f"📝 {p['reasoning']}")
                    if p.get("settled_at"):
                        st.caption(f"Settled: {p['settled_at'][:16]}")

    # ── Tab: Learning Log ─────────────────────────────────────────────────────
    with tab_log:
        st.subheader("Learning Log")
        st.caption("What the bot has learned from past bets.")
        log = list_learning_log(limit=100)
        if not log:
            st.info("No learning data yet. Settle some parlays first! 📊")
        else:
            rows = []
            for entry in log:
                icon = "🟢" if entry["outcome"] == "won" else ("🔴" if entry["outcome"] == "lost" else "⚪")
                rows.append({
                    "Outcome": f"{icon} {entry['outcome']}",
                    "Match": f"{entry['home_team']} vs {entry['away_team']}",
                    "Bet Type": entry["bet_type"],
                    "Selection": entry["selection"],
                    "Odds": entry["odds"],
                    "Parlay ID": entry["parlay_id"],
                    "Learned At": entry["learned_at"][:16] if entry["learned_at"] else "",
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

            won = sum(1 for e in log if e["outcome"] == "won")
            lost = sum(1 for e in log if e["outcome"] == "lost")
            total = won + lost
            if total > 0:
                st.metric("Win Rate", f"{won}/{total} ({100*won//total}%)")

    # ── Tab: Value Bets ───────────────────────────────────────────────────────
    with tab_value:
        st.subheader("💡 Value Bets Explained")
        st.markdown("""
        **What is a Value Bet?**
        
        A value bet occurs when the bookmaker's implied probability is *lower* than the true estimated probability.
        
        **Formula:**
        - `Implied Probability = 1 / Odds`
        - `True Probability` = margin-adjusted probability from the full market
        - `Edge = True Prob − Implied Prob`
        - `EV = Edge × Odds`
        
        OddsBot only includes bets where **Edge > 5%** (configurable via `MIN_VALUE_THRESHOLD`).
        
        **Markets analyzed:**
        | Market | Description |
        |--------|-------------|
        | `match_winner` | Home / Draw / Away |
        | `over_1_5` | Total goals over 1.5 |
        | `btts` | Both teams score: Yes |
        | `clean_sheet` | Home team concedes 0 goals |
        | `dnb` | Draw No Bet (home or away) |
        """)

        st.markdown("---")
        st.subheader("Sample Value Bet Analysis")
        mock_vb = pd.DataFrame([
            {"Match": "Brann vs Molde", "Bet": "Over 1.5", "Odds": 1.45,
             "True Prob": "72%", "Implied Prob": "69%", "Edge": "3%", "EV": "0.044"},
            {"Match": "Rosenborg vs Viking", "Bet": "BTTS Yes", "Odds": 1.80,
             "True Prob": "60%", "Implied Prob": "56%", "Edge": "4%", "EV": "0.072"},
            {"Match": "Bodø/Glimt vs Lillestrøm", "Bet": "Home Win", "Odds": 1.60,
             "True Prob": "67%", "Implied Prob": "63%", "Edge": "4%", "EV": "0.064"},
        ])
        st.dataframe(mock_vb, use_container_width=True, hide_index=True)
        st.caption("*Sample data. Run the bot with a real API key for live analysis.*")

    # ── Tab: Run Bot ──────────────────────────────────────────────────────────
    with tab_run:
        st.subheader("🚀 Run OddsBot")
        st.markdown("""
        Triggers the full OddsBot pipeline:
        1. Fetch upcoming Norwegian football fixtures
        2. Analyze odds for value bets
        3. Build top parlays
        4. Place them as paper trades in the DB
        5. Send Telegram notification (if configured)
        """)

        col1, col2, col3 = st.columns(3)
        with col1:
            run_full = st.button("▶️ Run Full Pipeline", type="primary", use_container_width=True)
        with col2:
            run_settle = st.button("🏁 Settle Open Parlays", use_container_width=True)
        with col3:
            run_notify = st.button("📣 Send Telegram", use_container_width=True)

        output_area = st.empty()

        def run_command(flag: str):
            project_root = _ROOT
            cmd = [sys.executable, "-m", "odds_bot.main", flag]
            output_area.info(f"Running: `{' '.join(cmd)}`")
            try:
                proc = subprocess.Popen(
                    cmd,
                    cwd=project_root,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    env={**os.environ, "PYTHONPATH": project_root},
                )
                lines = []
                for line in proc.stdout:
                    lines.append(line.rstrip())
                    output_area.text_area("Output", "\n".join(lines), height=300)
                proc.wait()
                if proc.returncode == 0:
                    st.success("✅ Completed successfully!")
                else:
                    st.error(f"❌ Exited with code {proc.returncode}")
            except Exception as e:
                st.error(f"Error: {e}")

        if run_full:
            run_command("--run")
        if run_settle:
            run_command("--settle")
        if run_notify:
            run_command("--notify")

        st.markdown("---")
        st.subheader("Configuration")
        from odds_bot.config import (
            LEAGUE_IDS, SEASON, STAKE_PER_PARLAY, MIN_PARLAY_LEGS,
            MAX_PARLAY_LEGS, MAX_COMBINED_ODDS, MIN_VALUE_THRESHOLD, TOP_PARLAYS,
            API_FOOTBALL_KEY,
        )
        api_status = "✅ API Key Set" if API_FOOTBALL_KEY else "⚠️ No API Key (mock mode)"
        st.info(api_status)
        cfg = {
            "Leagues": str(LEAGUE_IDS),
            "Season": SEASON,
            "Stake per Parlay": f"NOK {STAKE_PER_PARLAY}",
            "Min Legs": MIN_PARLAY_LEGS,
            "Max Legs": MAX_PARLAY_LEGS,
            "Max Combined Odds": MAX_COMBINED_ODDS,
            "Min Value Threshold": MIN_VALUE_THRESHOLD,
            "Top Parlays": TOP_PARLAYS,
        }
        st.table(pd.DataFrame(list(cfg.items()), columns=["Setting", "Value"]))
