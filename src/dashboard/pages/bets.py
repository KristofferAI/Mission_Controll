import sys
import os
import subprocess
from datetime import datetime, date, timedelta

import streamlit as st
import pandas as pd

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.db import init_db, list_recommendations, get_recommendation_summary

init_db()

MARKET_LABELS = {
    'h2h': '1X2',
    'totals': 'Over/Under',
    'btts': 'Both Teams Score',
}


def edge_badge(edge_pct: float) -> str:
    if edge_pct >= 5:
        return (
            f'<span style="background:#1a7a3a;color:#fff;padding:2px 8px;'
            f'border-radius:4px;font-size:0.85em">🟢 {edge_pct:.1f}%</span>'
        )
    else:
        return (
            f'<span style="background:#7a6a00;color:#fff;padding:2px 8px;'
            f'border-radius:4px;font-size:0.85em">🟡 {edge_pct:.1f}%</span>'
        )


def render():
    st.title("💰 Betting Recommendations")

    # ── Action buttons ────────────────────────────────────────────────────────
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("🔄 Fetch new recommendations", type="primary"):
            with st.spinner("Fetching odds and finding value bets..."):
                result = subprocess.run(
                    ['python3', 'odds_bot/main.py', '--run'],
                    cwd='/Users/kristoffer/projects/Mission_Controll',
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
            if result.returncode == 0:
                st.success(result.stdout or "✅ Done!")
            else:
                st.error(f"Error: {result.stderr}")
            st.rerun()

    with col2:
        if st.button("✅ Settle completed bets"):
            with st.spinner("Checking results..."):
                result = subprocess.run(
                    ['python3', 'odds_bot/main.py', '--settle'],
                    cwd='/Users/kristoffer/projects/Mission_Controll',
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
            if result.returncode == 0:
                st.success(result.stdout or "✅ Done!")
            else:
                st.error(f"Error: {result.stderr}")
            st.rerun()

    st.markdown("---")

    # ── Today's recommendations ───────────────────────────────────────────────
    today_str = date.today().isoformat()
    todays_recs = list_recommendations(date_from=today_str, date_to=today_str)

    st.subheader(f"📅 Today's Recommendations ({today_str})")

    if not todays_recs:
        st.info("No recommendations for today yet. Click 'Fetch new recommendations' to get started.")
    else:
        # Group by bet_type for display
        singles = [r for r in todays_recs if r['bet_type'] == 'single']
        parlays_by_id = {}
        for r in todays_recs:
            if r['bet_type'] == 'parlay':
                pid = r['parlay_id'] or 'unknown'
                parlays_by_id.setdefault(pid, []).append(r)

        if singles:
            st.markdown("**Single Bets**")
            cols_per_row = 3
            for i in range(0, len(singles), cols_per_row):
                cols = st.columns(cols_per_row)
                for j, rec in enumerate(singles[i:i + cols_per_row]):
                    with cols[j]:
                        market_label = MARKET_LABELS.get(rec['market'], rec['market'])
                        st.markdown(
                            f"""
                            <div style="background:#161C24;border:1px solid #1E90FF44;border-radius:10px;padding:1rem;margin-bottom:0.5rem">
                                <div style="font-size:1.05em;font-weight:bold;color:#1E90FF">{rec['match']}</div>
                                <div style="color:#aaa;font-size:0.85em">{rec['league']} · {market_label}</div>
                                <div style="margin:0.5rem 0">
                                    <b>{rec['selection']}</b> @ <b>{rec['odds']:.2f}</b>
                                </div>
                                {edge_badge(rec['edge_pct'])}
                                <div style="margin-top:0.5rem;color:#ccc">
                                    Stake: <b>{rec['recommended_stake']:.0f} NOK</b>
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

        if parlays_by_id:
            st.markdown("**Parlays**")
            for pid, legs in parlays_by_id.items():
                combined_odds = 1.0
                for leg in legs:
                    combined_odds *= leg['odds']
                avg_edge = sum(l['edge_pct'] for l in legs) / len(legs)
                stake = legs[0]['recommended_stake']
                matches_str = " + ".join(
                    f"{l['selection']} ({l['match'].split(' vs ')[0]})" for l in legs
                )
                st.markdown(
                    f"""
                    <div style="background:#161C24;border:1px solid #FFD70044;border-radius:10px;padding:1rem;margin-bottom:0.5rem">
                        <div style="font-size:1.0em;font-weight:bold;color:#FFD700">🎰 Parlay — {len(legs)} legs @ {combined_odds:.2f}x</div>
                        <div style="color:#ccc;margin:0.4rem 0">{matches_str}</div>
                        {edge_badge(avg_edge)}
                        <div style="margin-top:0.5rem;color:#ccc">Stake: <b>{stake:.0f} NOK</b></div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    st.markdown("---")

    # ── History table ─────────────────────────────────────────────────────────
    st.subheader("📊 Bet History")

    filter_col1, filter_col2, filter_col3 = st.columns([1, 1, 1])
    with filter_col1:
        status_filter = st.selectbox("Status", ["all", "open", "won", "lost"])
    with filter_col2:
        date_from = st.date_input("From", value=date.today() - timedelta(days=30))
    with filter_col3:
        date_to = st.date_input("To", value=date.today())

    all_recs = list_recommendations(
        status=None if status_filter == "all" else status_filter,
        date_from=str(date_from),
        date_to=str(date_to),
    )

    if all_recs:
        df = pd.DataFrame(all_recs)
        display_cols = [
            'date', 'match', 'league', 'selection', 'odds',
            'edge_pct', 'recommended_stake', 'bet_type', 'status', 'pnl',
        ]
        df = df[[c for c in display_cols if c in df.columns]]
        df['odds'] = df['odds'].apply(lambda x: f"{float(x):.2f}")
        df['edge_pct'] = df['edge_pct'].apply(lambda x: f"{float(x):.1f}%")
        df['recommended_stake'] = df['recommended_stake'].apply(lambda x: f"{float(x):.0f} NOK")
        df['pnl'] = df['pnl'].apply(lambda x: f"{float(x):+.0f} NOK")
        for col in df.columns:
            df[col] = df[col].astype(str)
        df.columns = ['Date', 'Match', 'League', 'Selection', 'Odds', 'Edge%', 'Stake', 'Type', 'Status', 'PnL']
        st.dataframe(df)
    else:
        st.info("No bets found for the selected filters.")

    st.markdown("---")

    # ── Summary ───────────────────────────────────────────────────────────────
    st.subheader("📈 Summary")
    summary = get_recommendation_summary()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Staked", f"{summary['total_staked']:.0f} NOK")
    m2.metric("Total PnL", f"{summary['total_pnl']:+.0f} NOK")
    m3.metric("Win Rate", f"{summary['win_rate']:.1f}%")
    m4.metric("ROI", f"{summary['roi_pct']:+.1f}%")
