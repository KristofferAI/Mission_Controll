import streamlit as st
import sys
import os
import subprocess
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.db import (
    get_balance, get_recommendation_summary, get_daily_stats,
    get_recent_results, get_scheduler_status, list_recommendations,
    get_performance_summary
)


def render():
    # ── Custom CSS ──────────────────────────────────────────────────────────
    st.markdown("""
    <style>
        .stApp {
            background: linear-gradient(135deg, #0f0f1e 0%, #1a1a2e 50%, #16213e 100%);
        }
        
        /* Hero stats cards */
        .hero-card {
            background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
            border-radius: 16px;
            padding: 1.5rem;
            text-align: center;
            box-shadow: 0 10px 40px -10px rgba(99, 102, 241, 0.5);
        }
        
        .hero-card-secondary {
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            border: 1px solid #6366f144;
            border-radius: 16px;
            padding: 1.5rem;
            text-align: center;
        }
        
        .hero-value {
            font-size: 2.5rem;
            font-weight: 700;
            color: white;
            margin: 0;
        }
        
        .hero-label {
            font-size: 0.9rem;
            color: rgba(255, 255, 255, 0.8);
            margin-top: 0.5rem;
        }
        
        .hero-value-secondary {
            font-size: 2rem;
            font-weight: 600;
            color: #f1f5f9;
            margin: 0;
        }
        
        .hero-label-secondary {
            font-size: 0.85rem;
            color: #94a3b8;
            margin-top: 0.5rem;
        }
        
        /* Quick action buttons */
        .quick-action {
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            border: 1px solid #6366f144;
            border-radius: 12px;
            padding: 1rem;
            text-align: center;
            transition: all 0.3s ease;
            cursor: pointer;
        }
        
        .quick-action:hover {
            border-color: #6366f1;
            transform: translateY(-2px);
            box-shadow: 0 8px 20px -5px rgba(99, 102, 241, 0.3);
        }
        
        /* Recent results */
        .result-card {
            background: rgba(26, 26, 46, 0.6);
            border-radius: 8px;
            padding: 0.75rem 1rem;
            margin-bottom: 0.5rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-left: 3px solid;
        }
        
        .result-win {
            border-left-color: #22c55e;
        }
        
        .result-loss {
            border-left-color: #ef4444;
        }
        
        /* Scheduler status */
        .status-indicator {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.5rem 1rem;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 500;
        }
        
        .status-running {
            background: rgba(34, 197, 94, 0.2);
            color: #22c55e;
        }
        
        .status-stopped {
            background: rgba(239, 68, 68, 0.2);
            color: #ef4444;
        }
        
        h1, h2, h3 {
            background: linear-gradient(90deg, #6366f1, #22d3ee);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # ── Header ──────────────────────────────────────────────────────────────
    st.title("🏠 Dashboard")
    
    # ── Hent data ───────────────────────────────────────────────────────────
    balance = get_balance()
    summary = get_recommendation_summary()
    daily = get_daily_stats()
    recent_results = get_recent_results(limit=5)
    scheduler = get_scheduler_status()
    
    # ── Scheduler Status ───────────────────────────────────────────────────
    scheduler_col1, scheduler_col2 = st.columns([1, 3])
    with scheduler_col1:
        if scheduler.get('is_running'):
            st.markdown('<span class="status-indicator status-running">🟢 Scheduler Kjører</span>', unsafe_allow_html=True)
        else:
            st.markdown('<span class="status-indicator status-stopped">🔴 Scheduler Stoppet</span>', unsafe_allow_html=True)
    with scheduler_col2:
        if scheduler.get('last_run'):
            last_run = scheduler['last_run'][:16] if scheduler['last_run'] else 'Aldri'
            st.caption(f"Siste kjøring: {last_run}")
    
    st.markdown("---")
    
    # ── Hero Stats ──────────────────────────────────────────────────────────
    st.subheader("📊 Oversikt")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="hero-card">
            <div class="hero-value">{balance:,.0f}</div>
            <div class="hero-label">💰 Bankroll (NOK)</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        pnl_color = "#22c55e" if summary['total_pnl'] >= 0 else "#ef4444"
        st.markdown(f"""
        <div class="hero-card-secondary">
            <div class="hero-value-secondary" style="color: {pnl_color};">{summary['total_pnl']:+.0f}</div>
            <div class="hero-label-secondary">📈 Total PnL (NOK)</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="hero-card-secondary">
            <div class="hero-value-secondary">{summary['win_rate']:.1f}%</div>
            <div class="hero-label-secondary">🎯 Win Rate</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        roi_color = "#22c55e" if summary['roi_pct'] >= 0 else "#ef4444"
        st.markdown(f"""
        <div class="hero-card-secondary">
            <div class="hero-value-secondary" style="color: {roi_color};">{summary['roi_pct']:+.1f}%</div>
            <div class="hero-label-secondary">📊 ROI</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # ── Dagens stats ────────────────────────────────────────────────────────
    st.subheader("📅 I dag")
    
    today_col1, today_col2, today_col3, today_col4 = st.columns(4)
    with today_col1:
        st.metric("Plassert", daily['bets_placed'])
    with today_col2:
        st.metric("✅ Seire", daily['bets_won'])
    with today_col3:
        st.metric("❌ Tap", daily['bets_lost'])
    with today_col4:
        daily_pnl_color = "normal" if daily['daily_pnl'] >= 0 else "inverse"
        st.metric("Dagens PnL", f"{daily['daily_pnl']:+.0f} NOK", delta_color=daily_pnl_color)
    
    st.markdown("---")
    
    # ── Quick Actions ───────────────────────────────────────────────────────
    st.subheader("⚡ Quick Actions")
    
    qa_col1, qa_col2, qa_col3, qa_col4 = st.columns(4)
    
    with qa_col1:
        if st.button("🔄 Hent Odds", use_container_width=True):
            with st.spinner("Henter odds..."):
                result = subprocess.run(
                    [sys.executable, 'odds_bot/main.py', '--run'],
                    cwd=_ROOT, capture_output=True, text=True
                )
            if result.returncode == 0:
                st.success("✅ Odds hentet!")
                st.rerun()
            else:
                st.error(f"❌ Feil: {result.stderr}")
    
    with qa_col2:
        if st.button("✅ Settle", use_container_width=True):
            with st.spinner("Sjekker resultater..."):
                result = subprocess.run(
                    [sys.executable, 'odds_bot/main.py', '--settle'],
                    cwd=_ROOT, capture_output=True, text=True
                )
            if result.returncode == 0:
                st.success("✅ Resultater sjekket!")
                st.rerun()
            else:
                st.error(f"❌ Feil: {result.stderr}")
    
    with qa_col3:
        if st.button("🤖 Start Scheduler", use_container_width=True):
            result = subprocess.run(
                [sys.executable, 'odds_bot/auto_scheduler.py', 'start'],
                cwd=_ROOT, capture_output=True, text=True
            )
            if "startet" in result.stdout.lower():
                st.success("✅ Scheduler startet!")
            else:
                st.info(result.stdout)
    
    with qa_col4:
        if st.button("🛑 Stopp Scheduler", use_container_width=True):
            result = subprocess.run(
                [sys.executable, 'odds_bot/auto_scheduler.py', 'stop'],
                cwd=_ROOT, capture_output=True, text=True
            )
            st.success("✅ Scheduler stoppet!")
    
    st.markdown("---")
    
    # ── Siste resultater og graf ────────────────────────────────────────────
    col_left, col_right = st.columns([1, 2])
    
    with col_left:
        st.subheader("🎯 Siste Resultater")
        
        if not recent_results:
            st.info("Ingen resultater ennå", icon="ℹ️")
        else:
            for r in recent_results:
                status_class = "result-win" if r['status'] == 'won' else "result-loss"
                status_emoji = "✅" if r['status'] == 'won' else "❌"
                pnl = r['pnl']
                pnl_sign = "+" if pnl > 0 else ""
                
                st.markdown(f"""
                <div class="result-card {status_class}">
                    <div>
                        <strong>{status_emoji} {r['match']}</strong><br>
                        <small style="color: #94a3b8;">{r['selection']} @ {r['odds']:.2f}</small>
                    </div>
                    <div style="text-align: right;">
                        <strong style="color: {'#22c55e' if pnl > 0 else '#ef4444'};">{pnl_sign}{pnl:.0f}</strong><br>
                        <small style="color: #94a3b8;">{r['actual_result']}</small>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    
    with col_right:
        st.subheader("📈 Bankroll Over Tid")
        
        # Hent historikk for graf
        history = list_recommendations(status='won') + list_recommendations(status='lost')
        history.sort(key=lambda x: x['created_at'])
        
        if len(history) < 2:
            st.info("Ikke nok data for graf ennå", icon="ℹ️")
        else:
            # Beregn kumulativ bankroll
            dates = [datetime.fromisoformat(r['created_at']).strftime('%Y-%m-%d %H:%M') for r in history]
            pnl_values = [r['pnl'] for r in history]
            cumulative = []
            current = balance - sum(pnl_values)  # Start bankroll
            for pnl in pnl_values:
                current += pnl
                cumulative.append(current)
            
            # Plotly figur
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=dates,
                y=cumulative,
                fill='tozeroy',
                line=dict(color='#6366f1', width=2),
                name='Bankroll',
                hovertemplate='%{x}<br>Bankroll: %{y:.0f} NOK<extra></extra>'
            ))
            
            # Legg til horizontal line for start bankroll
            fig.add_hline(
                y=1000,
                line_dash="dash",
                line_color="#94a3b8",
                annotation_text="Start (1000)",
                annotation_position="right"
            )
            
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#f1f5f9'),
                xaxis=dict(gridcolor='#6366f122', showgrid=True),
                yaxis=dict(gridcolor='#6366f122', showgrid=True),
                margin=dict(l=40, r=40, t=40, b=40),
                showlegend=False,
            )
            
            st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # ── Performance Breakdown ───────────────────────────────────────────────
    st.subheader("📊 Performance Breakdown")
    
    perf_col1, perf_col2 = st.columns(2)
    
    with perf_col1:
        st.markdown("#### Per Liga")
        # Hent performance per liga fra database
        perf_summary = get_performance_summary()
        
        # Hent per-liga stats fra recommendations
        league_stats = {}
        history = list_recommendations(status='won') + list_recommendations(status='lost')
        for r in history:
            league = r['league']
            if league not in league_stats:
                league_stats[league] = {'bets': 0, 'wins': 0, 'pnl': 0}
            league_stats[league]['bets'] += 1
            if r['status'] == 'won':
                league_stats[league]['wins'] += 1
            league_stats[league]['pnl'] += r['pnl']
        
        if league_stats:
            # Lag horisontal bar chart
            leagues = list(league_stats.keys())
            pnls = [league_stats[l]['pnl'] for l in leagues]
            
            colors = ['#22c55e' if p >= 0 else '#ef4444' for p in pnls]
            
            fig = go.Figure(data=[
                go.Bar(
                    y=leagues,
                    x=pnls,
                    orientation='h',
                    marker_color=colors,
                    text=[f"{p:+.0f}" for p in pnls],
                    textposition='outside',
                )
            ])
            
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#f1f5f9'),
                xaxis=dict(gridcolor='#6366f122', title='PnL (NOK)'),
                yaxis=dict(gridcolor='#6366f122'),
                margin=dict(l=150, r=40, t=20, b=40),
                showlegend=False,
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Ingen data", icon="ℹ️")
    
    with perf_col2:
        st.markdown("#### Win Rate per Liga")
        
        if league_stats:
            leagues = list(league_stats.keys())
            win_rates = [(league_stats[l]['wins'] / league_stats[l]['bets'] * 100) for l in leagues]
            bets = [league_stats[l]['bets'] for l in leagues]
            
            fig = go.Figure(data=[
                go.Bar(
                    y=leagues,
                    x=win_rates,
                    orientation='h',
                    marker_color='#22d3ee',
                    text=[f"{w:.0f}% ({b} bets)" for w, b in zip(win_rates, bets)],
                    textposition='outside',
                )
            ])
            
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#f1f5f9'),
                xaxis=dict(gridcolor='#6366f122', title='Win Rate %', range=[0, 100]),
                yaxis=dict(gridcolor='#6366f122'),
                margin=dict(l=150, r=40, t=20, b=40),
                showlegend=False,
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Ingen data", icon="ℹ️")
