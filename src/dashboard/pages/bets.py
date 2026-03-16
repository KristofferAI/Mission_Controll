import streamlit as st
import sys
import os
import subprocess
import sqlite3
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

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
        'totals': 'Over/Under',
        'h2h': 'Kamputfall',
        'btts': 'Begge lag scorer',
        'h2h_lay': 'Lay kamputfall',
    }
    return labels.get(market, market)


def get_edge_color(edge_pct):
    """Returner farge basert på edge."""
    if edge_pct >= 5:
        return "#22c55e"  # Grønn
    elif edge_pct >= 3:
        return "#eab308"  # Gul
    else:
        return "#6b7280"  # Grå


def get_status_badge(status):
    """Returner status badge."""
    badges = {
        'open': '🟡 ÅPEN',
        'won': '🟢 VUNNET',
        'lost': '🔴 TAPT',
        'placed_auto': '🤖 AUTO',
        'placed_manual': '👤 MANUELL',
    }
    return badges.get(status, status.upper())


def render():
    # ── Custom CSS for Dark Theme ───────────────────────────────────────────
    st.markdown("""
    <style>
        /* Dark theme overrides */
        .stApp {
            background: linear-gradient(135deg, #0f0f1e 0%, #1a1a2e 50%, #16213e 100%);
        }
        
        /* Metric cards */
        div[data-testid="stMetric"] {
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%) !important;
            border: 1px solid #6366f144 !important;
            border-radius: 12px !important;
            padding: 1rem !important;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
        }
        
        div[data-testid="stMetric"] label {
            color: #94a3b8 !important;
            font-size: 0.85rem !important;
        }
        
        div[data-testid="stMetric"] div {
            color: #f1f5f9 !important;
            font-size: 1.5rem !important;
            font-weight: 600 !important;
        }
        
        /* Buttons */
        .stButton > button {
            background: linear-gradient(90deg, #6366f1, #22d3ee) !important;
            border: none !important;
            color: white !important;
            font-weight: 600 !important;
            border-radius: 8px !important;
            padding: 0.75rem 1.5rem !important;
            transition: all 0.3s ease !important;
        }
        
        .stButton > button:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 10px 20px -5px rgba(99, 102, 241, 0.4) !important;
        }
        
        /* Container borders */
        div[data-testid="stVerticalBlock"] > div[style*="border"],
        .stContainer {
            border-color: #6366f144 !important;
            border-radius: 12px !important;
            background: rgba(26, 26, 46, 0.6) !important;
        }
        
        /* Tabs */
        .stTabs [data-baseweb="tab-list"] {
            background: rgba(26, 26, 46, 0.6) !important;
            border-radius: 8px !important;
            padding: 0.5rem !important;
        }
        
        .stTabs [data-baseweb="tab"] {
            color: #94a3b8 !important;
        }
        
        .stTabs [aria-selected="true"] {
            color: #22d3ee !important;
            background: rgba(99, 102, 241, 0.2) !important;
            border-radius: 6px !important;
        }
        
        /* DataFrames */
        .stDataFrame {
            background: rgba(26, 26, 46, 0.6) !important;
            border-radius: 12px !important;
        }
        
        /* Headers */
        h1, h2, h3 {
            background: linear-gradient(90deg, #6366f1, #22d3ee);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        /* Bet cards */
        .bet-card {
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            border: 1px solid #6366f144;
            border-radius: 12px;
            padding: 1rem;
            margin-bottom: 0.75rem;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
            transition: all 0.3s ease;
        }
        
        .bet-card:hover {
            border-color: #6366f188;
            transform: translateY(-2px);
        }
        
        .bet-card-title {
            font-size: 1.1rem;
            font-weight: 600;
            color: #f1f5f9;
            margin-bottom: 0.25rem;
        }
        
        .bet-card-subtitle {
            font-size: 0.85rem;
            color: #94a3b8;
            margin-bottom: 0.75rem;
        }
        
        .bet-card-line {
            border-top: 1px solid #6366f122;
            margin: 0.75rem 0;
        }
        
        .bet-card-details {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .bet-card-odds {
            font-size: 1.1rem;
            font-weight: 600;
            color: #22d3ee;
        }
        
        .bet-card-edge {
            font-size: 0.9rem;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            background: rgba(34, 197, 94, 0.2);
            color: #22c55e;
        }
        
        .bet-card-status {
            font-size: 0.75rem;
            font-weight: 600;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            background: rgba(99, 102, 241, 0.2);
            color: #818cf8;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # ── Tittel og Actions ───────────────────────────────────────────────────
    st.title("💰 Betting Tracker")
    
    # Auto-refresh toggle
    col_refresh = st.columns([1])[0]
    with col_refresh:
        if 'auto_refresh' not in st.session_state:
            st.session_state['auto_refresh'] = False
        
        refresh_col1, refresh_col2 = st.columns([1, 3])
        with refresh_col1:
            if st.button("🔄 Auto-refresh (30s)", use_container_width=True):
                st.session_state['auto_refresh'] = not st.session_state['auto_refresh']
                st.rerun()
        with refresh_col2:
            if st.session_state.get('auto_refresh'):
                st.info("⏱️ Auto-refresh aktiv - oppdaterer hvert 30. sekund", icon="🔄")
                import time
                time.sleep(30)
                st.rerun()
    
    # Actions
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🔄 Hent nye anbefalinger", use_container_width=True):
            with st.spinner("Henter odds og analyserer..."):
                result = subprocess.run(
                    [sys.executable, 'odds_bot/main.py', '--run'],
                    cwd=_ROOT, capture_output=True, text=True
                )
            if result.returncode == 0:
                st.success("✅ Odds hentet!")
                st.code(result.stdout)
                st.rerun()
            else:
                st.error(f"❌ Feil: {result.stderr}")
    with col2:
        if st.button("✅ Settle fullførte kamper", use_container_width=True):
            with st.spinner("Sjekker resultater..."):
                result = subprocess.run(
                    [sys.executable, 'odds_bot/main.py', '--settle'],
                    cwd=_ROOT, capture_output=True, text=True
                )
            if result.returncode == 0:
                st.success("✅ Resultater sjekket!")
                st.code(result.stdout)
                st.rerun()
            else:
                st.error(f"❌ Feil: {result.stderr}")
    with col3:
        if st.button("🤖 Start Auto-Scheduler", use_container_width=True):
            result = subprocess.run(
                [sys.executable, 'odds_bot/auto_scheduler.py', 'start'],
                cwd=_ROOT, capture_output=True, text=True
            )
            if result.returncode == 0:
                st.success("✅ Scheduler startet!")
            else:
                st.info(result.stdout)
    
    st.markdown("---")
    
    # ── Bankroll og statistikk ──────────────────────────────────────────────
    bankroll = get_bankroll()
    history = get_history()
    total_pnl = sum(r['pnl'] for r in history)
    wins = len([r for r in history if r['status'] == 'won'])
    losses = len([r for r in history if r['status'] == 'lost'])
    win_rate = (wins / len(history) * 100) if history else 0
    total_staked = sum(r['recommended_stake'] for r in history)
    roi = (total_pnl / total_staked * 100) if total_staked > 0 else 0
    
    # Metrikker med custom styling
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("💰 Bankroll", f"{bankroll:,.0f} NOK")
    c2.metric("📈 Total PnL", f"{total_pnl:+.0f} NOK", 
              delta=f"{roi:+.1f}% ROI" if total_staked > 0 else None)
    c3.metric("🎯 Win Rate", f"{win_rate:.0f}%")
    c4.metric("✅ / ❌", f"{wins} / {losses}")
    c5.metric("🎲 Totalt", f"{len(history)} bets")
    
    st.markdown("---")
    
    # ── Faner ───────────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4 = st.tabs(["📅 Dagens anbefalinger", "🟡 Aktive bets", "📋 Historikk", "📊 Analyse"])
    
    # ── TAB 1: Dagens anbefalinger ─────────────────────────────────────────
    with tab1:
        today_recs = get_todays_recs()
        singles = [r for r in today_recs if r['bet_type'] == 'single']
        parlays = {}
        for r in today_recs:
            if r['bet_type'] == 'parlay' and r['parlay_id']:
                parlays.setdefault(r['parlay_id'], []).append(r)
        
        if not today_recs:
            st.info("Ingen anbefalinger for i dag. Trykk 'Hent nye anbefalinger'.", icon="ℹ️")
        else:
            # Filtrering
            filter_col1, filter_col2, filter_col3 = st.columns(3)
            with filter_col1:
                leagues = sorted(list(set(r['league'] for r in today_recs)))
                selected_league = st.selectbox("🏆 Filtrer liga", ["Alle"] + leagues)
            with filter_col2:
                min_edge = st.slider("Min Edge %", 0.0, 10.0, 0.0, 0.5)
            with filter_col3:
                sort_by = st.selectbox("Sorter etter", ["Edge %", "Odds", "Stake"])
            
            # Filtrer singles
            filtered_singles = singles
            if selected_league != "Alle":
                filtered_singles = [r for r in filtered_singles if r['league'] == selected_league]
            filtered_singles = [r for r in filtered_singles if r['edge_pct'] >= min_edge]
            
            if sort_by == "Edge %":
                filtered_singles.sort(key=lambda x: x['edge_pct'], reverse=True)
            elif sort_by == "Odds":
                filtered_singles.sort(key=lambda x: x['odds'], reverse=True)
            elif sort_by == "Stake":
                filtered_singles.sort(key=lambda x: x['recommended_stake'], reverse=True)
            
            st.subheader(f"⚡ Topp enkeltbets ({len(filtered_singles)} funnet)")
            
            # Vis som bet cards
            for r in filtered_singles[:10]:
                edge_color = get_edge_color(r['edge_pct'])
                sel = format_selection(r['market'], r['selection'])
                mkt = format_market(r['market'])
                status_badge = get_status_badge(r['status'])
                
                st.markdown(f"""
                <div class="bet-card">
                    <div class="bet-card-title">🏆 {r['league']}</div>
                    <div class="bet-card-subtitle">{r['match']} · {mkt}</div>
                    <div class="bet-card-line"></div>
                    <div class="bet-card-details">
                        <div>
                            <span class="bet-card-odds">🎯 {sel} @ {r['odds']:.2f}</span>
                        </div>
                        <div style="display: flex; gap: 0.5rem;">
                            <span class="bet-card-edge">📊 Edge: {r['edge_pct']:.1f}%</span>
                            <span class="bet-card-status">💰 {r['recommended_stake']:.0f} NOK</span>
                            <span style="font-size: 0.75rem; padding: 0.25rem 0.5rem; border-radius: 4px; background: rgba(34, 211, 238, 0.2); color: #22d3ee;">{status_badge}</span>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
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
    
    # ── TAB 2: Aktive bets ─────────────────────────────────────────────────
    with tab2:
        active = get_active_recs()
        if not active:
            st.info("Ingen aktive bets akkurat nå.", icon="ℹ️")
        else:
            st.markdown(f"**{len(active)} aktive bets**")
            
            # Grupper etter parlay
            active_singles = [r for r in active if r['bet_type'] == 'single']
            active_parlays = {}
            for r in active:
                if r['bet_type'] == 'parlay' and r['parlay_id']:
                    active_parlays.setdefault(r['parlay_id'], []).append(r)
            
            # Vis singles
            if active_singles:
                st.subheader("Enkeltbets")
                for r in active_singles:
                    sel = format_selection(r['market'], r['selection'])
                    edge_color = get_edge_color(r['edge_pct'])
                    
                    st.markdown(f"""
                    <div class="bet-card">
                        <div class="bet-card-title">⚽ {r['match']}</div>
                        <div class="bet-card-subtitle">{r['league']} · {r['date']}</div>
                        <div class="bet-card-line"></div>
                        <div class="bet-card-details">
                            <div>
                                <span class="bet-card-odds">🎯 {sel} @ {r['odds']:.2f}</span>
                            </div>
                            <div style="display: flex; gap: 0.5rem;">
                                <span class="bet-card-edge">Edge: {r['edge_pct']:.1f}%</span>
                                <span class="bet-card-status">{r['recommended_stake']:.0f} NOK</span>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            
            # Vis parlays
            if active_parlays:
                st.subheader("Parlays")
                for pid, legs in active_parlays.items():
                    combined_odds = 1.0
                    for leg in legs:
                        combined_odds *= leg['odds']
                    
                    with st.container(border=True):
                        st.markdown(f"**{len(legs)}-leg parlay** @ {combined_odds:.2f}x")
                        for leg in legs:
                            sel = format_selection(leg['market'], leg['selection'])
                            st.markdown(f"  - {leg['match']}: {sel}")
    
    # ── TAB 3: Historikk ────────────────────────────────────────────────────
    with tab3:
        if not history:
            st.info("Ingen avsluttede bets ennå.", icon="ℹ️")
        else:
            # Søk og filtrering
            search_col1, search_col2 = st.columns([2, 1])
            with search_col1:
                search_term = st.text_input("🔍 Søk etter lag", "")
            with search_col2:
                date_range = st.selectbox("Periode", ["Siste 7 dager", "Siste 30 dager", "Alle"])
            
            filtered_history = history
            if search_term:
                filtered_history = [r for r in filtered_history if search_term.lower() in r['match'].lower()]
            
            if date_range == "Siste 7 dager":
                cutoff = datetime.now() - timedelta(days=7)
                filtered_history = [r for r in filtered_history if datetime.fromisoformat(r['created_at']) > cutoff]
            elif date_range == "Siste 30 dager":
                cutoff = datetime.now() - timedelta(days=30)
                filtered_history = [r for r in filtered_history if datetime.fromisoformat(r['created_at']) > cutoff]
            
            rows = []
            for r in filtered_history:
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
                    'Status': '✅' if r['status'] == 'won' else '❌',
                    'PnL': f"{r['pnl']:+.0f}",
                })
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)
    
    # ── TAB 4: Analyse ──────────────────────────────────────────────────────
    with tab4:
        if len(history) > 1:
            # PnL over tid med Plotly
            st.subheader("📊 Kumulativ PnL")
            
            # Forbered data
            history_sorted = sorted(history, key=lambda x: x['created_at'])
            dates = [datetime.fromisoformat(r['created_at']).strftime('%Y-%m-%d') for r in history_sorted]
            pnl_values = [r['pnl'] for r in history_sorted]
            cumulative_pnl = pd.Series(pnl_values).cumsum().tolist()
            
            # Plotly figur
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=dates,
                y=cumulative_pnl,
                fill='tozeroy',
                line=dict(color='#6366f1', width=2),
                name='Cumulative PnL',
                hovertemplate='Dato: %{x}<br>PnL: %{y:.0f} NOK<extra></extra>'
            ))
            
            fig.update_layout(
                title='Kumulativ PnL over tid',
                xaxis_title='Dato',
                yaxis_title='PnL (NOK)',
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#f1f5f9'),
                xaxis=dict(gridcolor='#6366f122'),
                yaxis=dict(gridcolor='#6366f122'),
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Performance per liga
            st.subheader("📈 Performance per Liga")
            league_stats = {}
            for r in history:
                league = r['league']
                if league not in league_stats:
                    league_stats[league] = {'bets': 0, 'wins': 0, 'pnl': 0}
                league_stats[league]['bets'] += 1
                if r['status'] == 'won':
                    league_stats[league]['wins'] += 1
                league_stats[league]['pnl'] += r['pnl']
            
            league_data = []
            for league, stats in sorted(league_stats.items(), key=lambda x: x[1]['pnl'], reverse=True):
                win_rate = (stats['wins'] / stats['bets'] * 100) if stats['bets'] > 0 else 0
                league_data.append({
                    'Liga': league,
                    'Bets': stats['bets'],
                    'Win Rate': f"{win_rate:.1f}%",
                    'PnL': f"{stats['pnl']:+.0f} NOK",
                })
            
            st.dataframe(pd.DataFrame(league_data), use_container_width=True, hide_index=True)
        else:
            st.info("Ikke nok data for analyse ennå. Minst 2 avsluttede bets trengs.", icon="ℹ️")
