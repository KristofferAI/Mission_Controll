import streamlit as st
import sys
import os
import subprocess
import sqlite3
import pandas as pd
from datetime import datetime

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

DB_PATH = os.path.join(_ROOT, 'data', 'mc.db')

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_todays_recs():
    today = datetime.now().strftime('%Y-%m-%d')
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM recommendations WHERE date=? ORDER BY edge_pct DESC",
        (today,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_active_recs():
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM recommendations WHERE status='open' ORDER BY edge_pct DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_history():
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM recommendations WHERE status IN ('won','lost') ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_bankroll():
    conn = get_conn()
    row = conn.execute("SELECT balance FROM bankroll WHERE id=1").fetchone()
    conn.close()
    return float(row['balance']) if row else 1000.0

def format_selection(market, selection):
    if market == 'totals':
        # API returns "Over 2.5" or "Under 2.5" directly
        return selection
    elif market == 'h2h':
        return f"Vinner: {selection}"
    elif market == 'btts':
        return f"Begge scorer: {selection}"
    elif market == 'h2h_lay':
        return f"{selection} (lay)"
    return selection

def format_market(market):
    labels = {
        'totals': 'Over/Under 2.5 mål',
        'h2h': 'Kamputfall',
        'btts': 'Begge lag scorer',
        'h2h_lay': 'Lay kamputfall',
    }
    return labels.get(market, market)

def render():
    st.title("💰 Betting Tracker")

    # ── Knapper øverst ────────────────────────────────────────────────────────
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Hent nye anbefalinger", use_container_width=True):
            with st.spinner("Henter odds og analyserer..."):
                result = subprocess.run(
                    [sys.executable, 'odds_bot/main.py', '--run'],
                    cwd=_ROOT, capture_output=True, text=True
                )
            if result.returncode == 0:
                st.success(result.stdout)
                st.rerun()
            else:
                st.error(f"Feil: {result.stderr}")
    with col2:
        if st.button("✅ Settle fullførte kamper", use_container_width=True):
            with st.spinner("Sjekker resultater..."):
                result = subprocess.run(
                    [sys.executable, 'odds_bot/main.py', '--settle'],
                    cwd=_ROOT, capture_output=True, text=True
                )
            if result.returncode == 0:
                st.success(result.stdout)
                st.rerun()
            else:
                st.error(f"Feil: {result.stderr}")

    st.markdown("---")

    # ── Bankroll og statistikk ────────────────────────────────────────────────
    bankroll = get_bankroll()
    history = get_history()
    total_pnl = sum(r['pnl'] for r in history)
    wins = len([r for r in history if r['status'] == 'won'])
    losses = len([r for r in history if r['status'] == 'lost'])
    win_rate = (wins / len(history) * 100) if history else 0
    total_staked = sum(r['recommended_stake'] for r in history)
    roi = (total_pnl / total_staked * 100) if total_staked > 0 else 0

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("💰 Bankroll", f"{bankroll:,.0f} NOK")
    c2.metric("📈 Total PnL", f"{total_pnl:+.0f} NOK")
    c3.metric("🎯 Win Rate", f"{win_rate:.0f}%")
    c4.metric("✅ Seire / ❌ Tap", f"{wins} / {losses}")
    c5.metric("📊 ROI", f"{roi:+.1f}%")

    st.markdown("---")

    # ── Faner ─────────────────────────────────────────────────────────────────
    tab1, tab2, tab3 = st.tabs(["📅 Dagens anbefalinger", "🟡 Aktive bets", "📋 Historikk"])

    # ── TAB 1: Dagens anbefalinger ────────────────────────────────────────────
    with tab1:
        today_recs = get_todays_recs()
        singles = [r for r in today_recs if r['bet_type'] == 'single']
        parlays = {}
        for r in today_recs:
            if r['bet_type'] == 'parlay' and r['parlay_id']:
                parlays.setdefault(r['parlay_id'], []).append(r)

        if not today_recs:
            st.info("Ingen anbefalinger for i dag. Trykk 'Hent nye anbefalinger'.")
        else:
            # Topp 10 enkeltbets sortert på edge
            st.subheader(f"⚡ Topp enkeltbets ({len(singles)} funnet)")
            for r in singles[:10]:
                edge_color = "🟢" if r['edge_pct'] >= 5 else "🟡"
                sel = format_selection(r['market'], r['selection'])
                mkt = format_market(r['market'])
                with st.container(border=True):
                    col_a, col_b = st.columns([3, 1])
                    with col_a:
                        st.markdown(f"**{r['match']}**  \n{r['league']} · {mkt}")
                        st.markdown(f"**{sel}** @ odds {r['odds']:.2f}")
                        st.caption(
                            f"Sann sannsynlighet: {r['true_probability']*100:.1f}% | "
                            f"Bookmaker-sannsynlighet: {r['implied_probability']*100:.1f}% | "
                            f"Edge: {edge_color} {r['edge_pct']:.1f}%"
                        )
                    with col_b:
                        st.metric("Anbefalt innsats", f"{r['recommended_stake']:.0f} NOK")

            # Parlays
            if parlays:
                st.subheader(f"🎰 Parlays ({len(parlays)} forslag)")
                for pid, legs in parlays.items():
                    combined_odds = 1.0
                    for leg in legs:
                        combined_odds *= leg['odds']
                    avg_edge = sum(l['edge_pct'] for l in legs) / len(legs)
                    stake = legs[0]['recommended_stake']
                    with st.container(border=True):
                        st.markdown(f"**{len(legs)}-leg parlay** @ {combined_odds:.2f}x · Edge: {'🟢' if avg_edge >= 5 else '🟡'} {avg_edge:.1f}% · Innsats: {stake:.0f} NOK")
                        for leg in legs:
                            sel = format_selection(leg['market'], leg['selection'])
                            st.markdown(f"  - {leg['match']}: **{sel}** @ {leg['odds']:.2f}")

    # ── TAB 2: Aktive bets ────────────────────────────────────────────────────
    with tab2:
        active = get_active_recs()
        if not active:
            st.info("Ingen aktive bets akkurat nå.")
        else:
            st.markdown(f"**{len(active)} aktive bets**")
            for r in active:
                sel = format_selection(r['market'], r['selection'])
                with st.container(border=True):
                    col_a, col_b = st.columns([3, 1])
                    with col_a:
                        st.markdown(f"**{r['match']}** — {r['league']}")
                        st.markdown(f"{sel} @ {r['odds']:.2f}")
                        st.caption(f"Dato: {r['date']} · Edge: {r['edge_pct']:.1f}% · {r['bet_type']}")
                    with col_b:
                        st.metric("Innsats", f"{r['recommended_stake']:.0f} NOK")

    # ── TAB 3: Historikk ──────────────────────────────────────────────────────
    with tab3:
        if not history:
            st.info("Ingen avsluttede bets ennå.")
        else:
            rows = []
            for r in history:
                sel = format_selection(r['market'], r['selection'])
                rows.append({
                    'Dato': r['date'],
                    'Kamp': r['match'],
                    'Liga': r['league'],
                    'Bet': sel,
                    'Odds': r['odds'],
                    'Edge%': f"{r['edge_pct']:.1f}%",
                    'Innsats': f"{r['recommended_stake']:.0f} NOK",
                    'Resultat': r['actual_result'],
                    'Status': '✅ W' if r['status'] == 'won' else '❌ L',
                    'PnL': f"{r['pnl']:+.0f} NOK",
                })
            df = pd.DataFrame(rows)
            st.dataframe(df, width='stretch', hide_index=True)

            if len(history) > 1:
                st.subheader("📊 Kumulativ PnL")
                pnl_series = pd.Series([r['pnl'] for r in history[::-1]]).cumsum()
                st.line_chart(pnl_series)
