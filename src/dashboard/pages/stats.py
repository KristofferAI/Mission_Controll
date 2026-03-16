import streamlit as st
import sys
import os
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from collections import defaultdict

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.db import (
    list_recommendations, get_performance_stats, get_performance_summary,
    get_recommendation_summary
)


def render():
    # ── Custom CSS ──────────────────────────────────────────────────────────
    st.markdown("""
    <style>
        .stApp {
            background: linear-gradient(135deg, #0f0f1e 0%, #1a1a2e 50%, #16213e 100%);
        }
        
        div[data-testid="stMetric"] {
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%) !important;
            border: 1px solid #6366f144 !important;
            border-radius: 12px !important;
        }
        
        div[data-testid="stMetric"] label {
            color: #94a3b8 !important;
        }
        
        div[data-testid="stMetric"] div {
            color: #f1f5f9 !important;
        }
        
        h1, h2, h3 {
            background: linear-gradient(90deg, #6366f1, #22d3ee);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
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
    </style>
    """, unsafe_allow_html=True)
    
    # ── Header ──────────────────────────────────────────────────────────────
    st.title("📊 Statistikk")
    st.markdown("Detaljert analyse av betting performance")
    
    # ── Hent data ───────────────────────────────────────────────────────────
    history = list_recommendations(status='won') + list_recommendations(status='lost')
    history.sort(key=lambda x: x['created_at'])
    
    summary = get_recommendation_summary()
    perf_summary = get_performance_summary()
    
    if not history:
        st.info("Ingen data ennå. Plasser og settle bets for å se statistikk.", icon="ℹ️")
        return
    
    # ── Top Level Metrics ───────────────────────────────────────────────────
    st.subheader("📈 Oversikt")
    
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Totale Bets", perf_summary['total_bets'])
    m2.metric("Win Rate", f"{perf_summary['win_rate']:.1f}%")
    m3.metric("ROI", f"{perf_summary['roi_pct']:+.1f}%")
    m4.metric("Total PnL", f"{perf_summary['total_pnl']:+.0f} NOK")
    m5.metric("Avg PnL/Bet", f"{perf_summary['total_pnl']/perf_summary['total_bets']:.0f} NOK" if perf_summary['total_bets'] > 0 else "0 NOK")
    
    st.markdown("---")
    
    # ── Faner ───────────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4 = st.tabs([
        "🏆 Per Liga", "🎯 Per Market", "📅 Heatmap", "📊 Edge vs ROI"
    ])
    
    # ── TAB 1: Performance per Liga ────────────────────────────────────────
    with tab1:
        st.subheader("Performance per Liga")
        
        # Beregn stats per liga
        league_stats = defaultdict(lambda: {'bets': 0, 'wins': 0, 'staked': 0, 'pnl': 0})
        
        for r in history:
            league = r['league']
            league_stats[league]['bets'] += 1
            if r['status'] == 'won':
                league_stats[league]['wins'] += 1
            league_stats[league]['staked'] += r['recommended_stake']
            league_stats[league]['pnl'] += r['pnl']
        
        # Lag DataFrame
        league_data = []
        for league, stats in sorted(league_stats.items(), key=lambda x: x[1]['pnl'], reverse=True):
            win_rate = (stats['wins'] / stats['bets'] * 100) if stats['bets'] > 0 else 0
            roi = (stats['pnl'] / stats['staked'] * 100) if stats['staked'] > 0 else 0
            league_data.append({
                'Liga': league,
                'Bets': stats['bets'],
                'Seire': stats['wins'],
                'Tap': stats['bets'] - stats['wins'],
                'Win Rate': f"{win_rate:.1f}%",
                'Innsats': f"{stats['staked']:.0f} NOK",
                'PnL': f"{stats['pnl']:+.0f} NOK",
                'ROI': f"{roi:+.1f}%",
            })
        
        df_leagues = pd.DataFrame(league_data)
        st.dataframe(df_leagues, use_container_width=True, hide_index=True)
        
        # Visualisering
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### PnL per Liga")
            
            fig = go.Figure()
            colors = ['#22c55e' if float(d['PnL'].replace('+', '').replace(' NOK', '')) >= 0 else '#ef4444' 
                     for d in league_data]
            
            fig.add_trace(go.Bar(
                x=[d['Liga'] for d in league_data],
                y=[float(d['PnL'].replace('+', '').replace(' NOK', '')) for d in league_data],
                marker_color=colors,
                text=[d['PnL'] for d in league_data],
                textposition='outside',
            ))
            
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#f1f5f9'),
                xaxis=dict(gridcolor='#6366f122', tickangle=-45),
                yaxis=dict(gridcolor='#6366f122', title='PnL (NOK)'),
                showlegend=False,
                margin=dict(b=100),
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("#### Win Rate per Liga")
            
            fig = go.Figure()
            
            fig.add_trace(go.Bar(
                x=[d['Liga'] for d in league_data],
                y=[float(d['Win Rate'].replace('%', '')) for d in league_data],
                marker_color='#22d3ee',
                text=[d['Win Rate'] for d in league_data],
                textposition='outside',
            ))
            
            fig.add_hline(y=50, line_dash="dash", line_color="#94a3b8", annotation_text="50%")
            
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#f1f5f9'),
                xaxis=dict(gridcolor='#6366f122', tickangle=-45),
                yaxis=dict(gridcolor='#6366f122', title='Win Rate %', range=[0, 100]),
                showlegend=False,
                margin=dict(b=100),
            )
            
            st.plotly_chart(fig, use_container_width=True)
    
    # ── TAB 2: Performance per Market ──────────────────────────────────────
    with tab2:
        st.subheader("Performance per Bet-Type (Market)")
        
        # Beregn stats per market
        market_stats = defaultdict(lambda: {'bets': 0, 'wins': 0, 'staked': 0, 'pnl': 0, 'edge_sum': 0})
        
        for r in history:
            market = r['market']
            market_stats[market]['bets'] += 1
            if r['status'] == 'won':
                market_stats[market]['wins'] += 1
            market_stats[market]['staked'] += r['recommended_stake']
            market_stats[market]['pnl'] += r['pnl']
            market_stats[market]['edge_sum'] += r['edge_pct']
        
        # Lag DataFrame
        market_data = []
        for market, stats in sorted(market_stats.items(), key=lambda x: x[1]['pnl'], reverse=True):
            win_rate = (stats['wins'] / stats['bets'] * 100) if stats['bets'] > 0 else 0
            roi = (stats['pnl'] / stats['staked'] * 100) if stats['staked'] > 0 else 0
            avg_edge = stats['edge_sum'] / stats['bets'] if stats['bets'] > 0 else 0
            market_data.append({
                'Market': market.upper(),
                'Bets': stats['bets'],
                'Seire': stats['wins'],
                'Tap': stats['bets'] - stats['wins'],
                'Win Rate': f"{win_rate:.1f}%",
                'Avg Edge': f"{avg_edge:.1f}%",
                'PnL': f"{stats['pnl']:+.0f} NOK",
                'ROI': f"{roi:+.1f}%",
            })
        
        df_markets = pd.DataFrame(market_data)
        st.dataframe(df_markets, use_container_width=True, hide_index=True)
        
        # Visualisering
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### PnL per Market")
            
            fig = px.pie(
                values=[float(d['PnL'].replace('+', '').replace(' NOK', '')) for d in market_data],
                names=[d['Market'] for d in market_data],
                hole=0.4,
                color_discrete_sequence=['#6366f1', '#22d3ee', '#22c55e', '#f59e0b'],
            )
            
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#f1f5f9'),
                showlegend=True,
                legend=dict(orientation='h', yanchor='bottom', y=-0.2),
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("#### Antall Bets per Market")
            
            fig = go.Figure()
            
            fig.add_trace(go.Bar(
                x=[d['Market'] for d in market_data],
                y=[d['Bets'] for d in market_data],
                marker_color='#8b5cf6',
                text=[d['Bets'] for d in market_data],
                textposition='outside',
            ))
            
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#f1f5f9'),
                xaxis=dict(gridcolor='#6366f122'),
                yaxis=dict(gridcolor='#6366f122', title='Antall Bets'),
                showlegend=False,
            )
            
            st.plotly_chart(fig, use_container_width=True)
    
    # ── TAB 3: Heatmap ─────────────────────────────────────────────────────
    with tab3:
        st.subheader("📅 Heatmap: Beste Dager og Tider")
        
        # Forbered data
        day_names = ['Man', 'Tir', 'Ons', 'Tor', 'Fre', 'Lør', 'Søn']
        hour_labels = [f"{h:02d}:00" for h in range(24)]
        
        # Heatmap: PnL per ukedag/time
        day_hour_pnl = defaultdict(lambda: defaultdict(float))
        day_hour_count = defaultdict(lambda: defaultdict(int))
        
        for r in history:
            dt = datetime.fromisoformat(r['created_at'])
            day = dt.weekday()
            hour = dt.hour
            day_hour_pnl[day][hour] += r['pnl']
            day_hour_count[day][hour] += 1
        
        # Lag heatmap data
        heatmap_data = []
        for day in range(7):
            row = []
            for hour in range(24):
                count = day_hour_count[day][hour]
                if count > 0:
                    avg_pnl = day_hour_pnl[day][hour] / count
                    row.append(avg_pnl)
                else:
                    row.append(None)
            heatmap_data.append(row)
        
        # Visualiser
        st.markdown("#### Gjennomsnittlig PnL per ukedag og time")
        
        fig = go.Figure(data=go.Heatmap(
            z=heatmap_data,
            x=hour_labels,
            y=day_names,
            colorscale=[
                [0, '#ef4444'],
                [0.5, '#1a1a2e'],
                [1, '#22c55e']
            ],
            hovertemplate='Dag: %{y}<br>Time: %{x}<br>Avg PnL: %{z:.0f} NOK<extra></extra>',
        ))
        
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#f1f5f9'),
            xaxis=dict(gridcolor='#6366f122', title='Time på døgnet'),
            yaxis=dict(gridcolor='#6366f122', title='Ukedag'),
            height=400,
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Heatmap: Antall bets
        st.markdown("#### Antall bets per ukedag og time")
        
        count_data = [[day_hour_count[day][hour] for hour in range(24)] for day in range(7)]
        
        fig2 = go.Figure(data=go.Heatmap(
            z=count_data,
            x=hour_labels,
            y=day_names,
            colorscale='Blues',
            hovertemplate='Dag: %{y}<br>Time: %{x}<br>Bets: %{z}<extra></extra>',
        ))
        
        fig2.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#f1f5f9'),
            xaxis=dict(gridcolor='#6366f122', title='Time på døgnet'),
            yaxis=dict(gridcolor='#6366f122', title='Ukedag'),
            height=400,
        )
        
        st.plotly_chart(fig2, use_container_width=True)
        
        # Beste og verste dager
        st.markdown("---")
        st.markdown("#### Dags-statistikk")
        
        day_stats = defaultdict(lambda: {'bets': 0, 'pnl': 0})
        for r in history:
            dt = datetime.fromisoformat(r['created_at'])
            day = day_names[dt.weekday()]
            day_stats[day]['bets'] += 1
            day_stats[day]['pnl'] += r['pnl']
        
        day_data = []
        for day in day_names:
            stats = day_stats[day]
            day_data.append({
                'Dag': day,
                'Bets': stats['bets'],
                'Total PnL': f"{stats['pnl']:+.0f} NOK",
                'Avg PnL': f"{stats['pnl']/stats['bets']:.0f} NOK" if stats['bets'] > 0 else "0 NOK",
            })
        
        st.dataframe(pd.DataFrame(day_data), use_container_width=True, hide_index=True)
    
    # ── TAB 4: Edge vs Actual ROI ──────────────────────────────────────────
    with tab4:
        st.subheader("📊 Edge vs Faktisk ROI")
        
        # Sammenligne forventet edge med faktisk resultat
        edge_buckets = {
            '0-2%': {'bets': 0, 'wins': 0, 'pnl': 0, 'staked': 0},
            '2-4%': {'bets': 0, 'wins': 0, 'pnl': 0, 'staked': 0},
            '4-6%': {'bets': 0, 'wins': 0, 'pnl': 0, 'staked': 0},
            '6%+': {'bets': 0, 'wins': 0, 'pnl': 0, 'staked': 0},
        }
        
        for r in history:
            edge = r['edge_pct']
            if edge < 2:
                bucket = '0-2%'
            elif edge < 4:
                bucket = '2-4%'
            elif edge < 6:
                bucket = '4-6%'
            else:
                bucket = '6%+'
            
            edge_buckets[bucket]['bets'] += 1
            if r['status'] == 'won':
                edge_buckets[bucket]['wins'] += 1
            edge_buckets[bucket]['pnl'] += r['pnl']
            edge_buckets[bucket]['staked'] += r['recommended_stake']
        
        # Lag data
        edge_data = []
        for bucket, stats in edge_buckets.items():
            if stats['bets'] > 0:
                win_rate = (stats['wins'] / stats['bets'] * 100)
                actual_roi = (stats['pnl'] / stats['staked'] * 100) if stats['staked'] > 0 else 0
                edge_data.append({
                    'Edge Bucket': bucket,
                    'Bets': stats['bets'],
                    'Win Rate': f"{win_rate:.1f}%",
                    'Faktisk ROI': f"{actual_roi:+.1f}%",
                    'PnL': f"{stats['pnl']:+.0f} NOK",
                })
        
        if edge_data:
            st.dataframe(pd.DataFrame(edge_data), use_container_width=True, hide_index=True)
            
            # Scatter plot: Expected edge vs Actual ROI
            st.markdown("#### Scatter: Forventet Edge vs Faktisk ROI")
            
            fig = go.Figure()
            
            # Scatter points
            for d in edge_data:
                bucket = d['Edge Bucket']
                bets = d['Bets']
                actual_roi = float(d['Faktisk ROI'].replace('%', '').replace('+', ''))
                
                # Forventet edge (midtpunkt i bucket)
                expected = {'0-2%': 1, '2-4%': 3, '4-6%': 5, '6%+': 7}[bucket]
                
                fig.add_trace(go.Scatter(
                    x=[expected],
                    y=[actual_roi],
                    mode='markers+text',
                    marker=dict(
                        size=bets * 10 + 20,
                        color='#22d3ee',
                        line=dict(color='#6366f1', width=2),
                    ),
                    text=[f"{bets} bets"],
                    textposition='top center',
                    name=bucket,
                ))
            
            # Diagonal line (y=x)
            fig.add_trace(go.Scatter(
                x=[0, 10],
                y=[0, 10],
                mode='lines',
                line=dict(color='#94a3b8', dash='dash'),
                name='Perfekt prediksjon',
            ))
            
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#f1f5f9'),
                xaxis=dict(gridcolor='#6366f122', title='Forventet Edge %', range=[0, 8]),
                yaxis=dict(gridcolor='#6366f122', title='Faktisk ROI %'),
                showlegend=False,
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            st.info("""
            **Tolkning:** 
            - Punkter over den stiplede linjen = Edge ble undervurdert (godt!)
            - Punkter under linjen = Edge ble overvurdert (dårlig)
            - Større sirkler = flere bets i denne kategorien
            """, icon="💡")
        else:
            st.info("Ikke nok data for edge-analyse ennå", icon="ℹ️")
        
        # Odds vs Win Rate
        st.markdown("---")
        st.markdown("#### Odds vs Faktisk Win Rate")
        
        odds_buckets = {
            '<1.5': {'bets': 0, 'wins': 0},
            '1.5-2.0': {'bets': 0, 'wins': 0},
            '2.0-3.0': {'bets': 0, 'wins': 0},
            '3.0+': {'bets': 0, 'wins': 0},
        }
        
        for r in history:
            odds = r['odds']
            if odds < 1.5:
                bucket = '<1.5'
            elif odds < 2.0:
                bucket = '1.5-2.0'
            elif odds < 3.0:
                bucket = '2.0-3.0'
            else:
                bucket = '3.0+'
            
            odds_buckets[bucket]['bets'] += 1
            if r['status'] == 'won':
                odds_buckets[bucket]['wins'] += 1
        
        odds_data = []
        for bucket, stats in odds_buckets.items():
            if stats['bets'] > 0:
                actual_wr = (stats['wins'] / stats['bets'] * 100)
                implied_wr = {'<1.5': 66.7, '1.5-2.0': 57.1, '2.0-3.0': 40, '3.0+': 25}[bucket]
                odds_data.append({
                    'Odds Range': bucket,
                    'Bets': stats['bets'],
                    'Faktisk Win Rate': f"{actual_wr:.1f}%",
                    'Implisert Win Rate': f"{implied_wr:.1f}%",
                })
        
        if odds_data:
            st.dataframe(pd.DataFrame(odds_data), use_container_width=True, hide_index=True)
