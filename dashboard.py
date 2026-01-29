"""
Geopolitical Insider Trading Detection - Web Dashboard

Real-time dashboard for monitoring trades, alerts, and pattern detection.
Run with: streamlit run dashboard.py
"""
import sys
import re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, timezone
from sqlalchemy import func, desc, extract, cast, Integer

from database.connection import init_db, get_db_session
from database.models import Trade, WalletMetrics, MarketResolution, WalletWinHistory
from analysis.patterns import (
    analyze_wallet,
    find_repeat_offenders,
    find_suspicious_networks
)
from analysis.win_scoring import SuspiciousWinScorer, WIN_ALERT_THRESHOLDS
from analysis.scoring import SuspicionScorer
from config import config


# Page configuration
st.set_page_config(
    page_title="Insider Trading Detection",
    page_icon="🕵️",
    layout="wide",
    initial_sidebar_state="expanded"
)


@st.cache_resource
def _init_database():
    """Initialize DB once, cached across Streamlit reruns. Returns True on success."""
    try:
        init_db(max_retries=3)
        return True
    except Exception as e:
        return str(e)


@st.cache_data(ttl=300)
def get_cached_breakdown(
    trade_id, bet_size_usd, wallet_address, timestamp_str,
    bet_price, bet_direction, market_category, market_liquidity_usd
):
    """Cache scoring breakdown to prevent recalculation on every rerun."""
    from datetime import datetime, timezone

    # Parse timestamp
    timestamp = None
    if timestamp_str:
        try:
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            timestamp = datetime.now(timezone.utc)

    trade_data = {
        'bet_size_usd': bet_size_usd,
        'wallet_address': wallet_address,
        'timestamp': timestamp,
        'bet_price': bet_price,
        'bet_direction': bet_direction,
    }
    market_data = {
        'is_geopolitical': market_category == 'GEOPOLITICS',
        'category': market_category,
        'liquidity_usd': market_liquidity_usd,
    }

    result = SuspicionScorer.calculate_score(trade_data, market_data)
    breakdown = result.get('breakdown', {})

    # Format for display
    breakdown_data = []
    for factor, data in breakdown.items():
        factor_name = factor.replace('_', ' ').title()
        reason = data['reason']
        breakdown_data.append({
            'Factor': factor_name,
            'Points': f"{data['score']}/{data['max']}",
            'Reason': reason[:50] + '...' if len(reason) > 50 else reason
        })

    return breakdown_data, result['raw_score'], result['total_score']


def main():
    """Main dashboard application.

    Uses a single database session for the entire page render to avoid
    opening multiple concurrent connections per Streamlit re-run.
    """
    db_status = _init_database()
    if db_status is not True:
        st.error(f"Database connection failed: {db_status}")
        st.info("The dashboard will retry on next page refresh.")
        _init_database.clear()
        return

    # Sidebar navigation
    st.sidebar.title("🕵️ Insider Trading Detection")
    st.sidebar.markdown("---")

    page = st.sidebar.radio(
        "Navigation",
        [
            "🏠 Overview",
            "🚨 Alert Feed",
            "🏆 Suspicious Winners",
            "📊 Trade History",
            "👤 Wallet Analysis",
            "🕸️ Network Patterns",
            "📈 Statistics",
            "⚙️ Settings"
        ]
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown("### System Status")

    with get_db_session() as session:
        # Sidebar stats
        total_trades = session.query(func.count(Trade.id)).scalar() or 0
        suspicious_trades = session.query(func.count(Trade.id)).filter(
            Trade.suspicion_score >= config.SUSPICION_THRESHOLD_WATCH
        ).scalar() or 0

        st.sidebar.metric("Total Trades", f"{total_trades:,}")
        st.sidebar.metric("Suspicious Trades", f"{suspicious_trades:,}")
        st.sidebar.metric("Detection Rate",
                          f"{(suspicious_trades/total_trades*100) if total_trades > 0 else 0:.1f}%")

        # Route to selected page (reusing the same session)
        if page == "🏠 Overview":
            show_overview(session)
        elif page == "🚨 Alert Feed":
            show_alerts(session)
        elif page == "🏆 Suspicious Winners":
            show_suspicious_winners(session)
        elif page == "📊 Trade History":
            show_trade_history(session)
        elif page == "👤 Wallet Analysis":
            show_wallet_analysis()
        elif page == "🕸️ Network Patterns":
            show_network_patterns()
        elif page == "📈 Statistics":
            show_statistics(session)
        elif page == "⚙️ Settings":
            show_settings()


def show_overview(session):
    """Overview page with key metrics and recent activity"""
    st.title("🏠 Overview Dashboard")

    if True:  # preserve indentation level for minimal diff
        # Key metrics
        total_trades = session.query(func.count(Trade.id)).scalar() or 0
        watch_count = session.query(func.count(Trade.id)).filter(
            Trade.suspicion_score >= config.SUSPICION_THRESHOLD_WATCH,
            Trade.suspicion_score < config.SUSPICION_THRESHOLD_SUSPICIOUS
        ).scalar() or 0
        suspicious_count = session.query(func.count(Trade.id)).filter(
            Trade.suspicion_score >= config.SUSPICION_THRESHOLD_SUSPICIOUS,
            Trade.suspicion_score < config.SUSPICION_THRESHOLD_CRITICAL
        ).scalar() or 0
        critical_count = session.query(func.count(Trade.id)).filter(
            Trade.suspicion_score >= config.SUSPICION_THRESHOLD_CRITICAL
        ).scalar() or 0

        # Display metrics
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Trades", f"{total_trades:,}")
        with col2:
            st.metric("🟡 Watch", f"{watch_count:,}")
        with col3:
            st.metric("🟠 Suspicious", f"{suspicious_count:,}")
        with col4:
            st.metric("🔴 Critical", f"{critical_count:,}")

        st.markdown("---")

        # Recent alerts
        st.subheader("📢 Recent Alerts")

        recent_alerts = session.query(Trade).filter(
            Trade.suspicion_score >= config.SUSPICION_THRESHOLD_WATCH
        ).order_by(desc(Trade.timestamp)).limit(10).all()

        if recent_alerts:
            for trade in recent_alerts:
                alert_level = get_alert_level(trade.suspicion_score)
                emoji = {"WATCH": "🟡", "SUSPICIOUS": "🟠", "CRITICAL": "🔴"}.get(alert_level, "⚪")

                with st.expander(
                    f"{emoji} {alert_level} - {trade.market_title[:60]}... "
                    f"(Score: {trade.suspicion_score}/100)"
                ):
                    col1, col2 = st.columns([2, 1])

                    with col1:
                        st.write(f"**Market:** {trade.market_title}")
                        st.write(f"**Wallet:** `{trade.wallet_address[:10]}...{trade.wallet_address[-6:]}`")
                        st.write(f"**Time:** {trade.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}")

                    with col2:
                        st.metric("Bet Size", f"${trade.bet_size_usd:,.2f}")
                        st.metric("Suspicion Score", f"{trade.suspicion_score}/100")
                        st.write(f"**Direction:** {trade.bet_direction}")
                        st.write(f"**Price:** {trade.bet_price:.2f}")
        else:
            st.info("No alerts yet. System is monitoring for suspicious trades.")

        st.markdown("---")

        # Activity chart (last 24 hours) - using SQL aggregation for efficiency
        st.subheader("📊 Activity (Last 24 Hours)")

        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

        # Use SQL aggregation grouped by date + hour for accurate per-hour buckets
        hourly_stats = session.query(
            func.date(Trade.timestamp).label('trade_date'),
            extract('hour', Trade.timestamp).label('hour'),
            func.count(Trade.id).label('trade_count'),
            func.sum(Trade.bet_size_usd).label('volume')
        ).filter(
            Trade.timestamp >= cutoff
        ).group_by(
            func.date(Trade.timestamp),
            extract('hour', Trade.timestamp)
        ).order_by(
            func.date(Trade.timestamp),
            extract('hour', Trade.timestamp)
        ).all()

        if hourly_stats:
            hourly_data = []
            for stat in hourly_stats:
                hour_val = int(stat.hour) if stat.hour is not None else 0
                trade_date = stat.trade_date
                # Combine date + hour into a proper datetime for the x-axis
                if trade_date:
                    dt = datetime(trade_date.year, trade_date.month, trade_date.day, hour_val)
                else:
                    today = datetime.now(timezone.utc).date()
                    dt = datetime(today.year, today.month, today.day, hour_val)
                hourly_data.append({
                    'Hour': dt,
                    'Trades': stat.trade_count or 0,
                    'Volume': float(stat.volume) if stat.volume else 0
                })

            hourly = pd.DataFrame(hourly_data)

            fig = px.bar(hourly, x='Hour', y='Trades',
                        title='Trades per Hour',
                        labels={'Trades': 'Number of Trades'})
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No trades in the last 24 hours.")


def show_alerts(session):
    """Alert feed page with pagination"""
    st.title("🚨 Alert Feed")

    # Filters
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        min_score = st.slider("Minimum Score", 0, 100,
                             config.SUSPICION_THRESHOLD_WATCH)
    with col2:
        days_back = st.selectbox("Time Period", [1, 7, 30, 90, 365], index=1)
    with col3:
        sort_by = st.selectbox("Sort By", ["Newest", "Highest Score", "Largest Bet"])
    with col4:
        page_size = st.selectbox("Per Page", [25, 50, 100], index=0)

    # Pagination state
    if 'alert_page' not in st.session_state:
        st.session_state.alert_page = 0

    if True:  # preserve indentation level for minimal diff
        cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)

        # Build base query
        base_query = session.query(Trade).filter(
            Trade.suspicion_score >= min_score,
            Trade.timestamp >= cutoff
        )

        # Get total count efficiently (without loading all records)
        total_count = base_query.count()

        if sort_by == "Newest":
            base_query = base_query.order_by(desc(Trade.timestamp))
        elif sort_by == "Highest Score":
            base_query = base_query.order_by(desc(Trade.suspicion_score))
        else:
            base_query = base_query.order_by(desc(Trade.bet_size_usd))

        # Calculate pagination
        total_pages = max(1, (total_count + page_size - 1) // page_size)
        st.session_state.alert_page = min(st.session_state.alert_page, total_pages - 1)

        # Fetch only the current page
        offset = st.session_state.alert_page * page_size
        alerts = base_query.offset(offset).limit(page_size).all()

        # Display count and pagination info
        start_idx = offset + 1
        end_idx = min(offset + page_size, total_count)
        st.write(f"**Showing {start_idx}-{end_idx} of {total_count} alerts**")

        # Pagination controls
        if total_pages > 1:
            pcol1, pcol2, pcol3, pcol4, pcol5 = st.columns([1, 1, 2, 1, 1])
            with pcol1:
                if st.button("⏮️ First", disabled=st.session_state.alert_page == 0):
                    st.session_state.alert_page = 0
                    st.rerun()
            with pcol2:
                if st.button("◀️ Prev", disabled=st.session_state.alert_page == 0):
                    st.session_state.alert_page -= 1
                    st.rerun()
            with pcol3:
                st.write(f"Page {st.session_state.alert_page + 1} of {total_pages}")
            with pcol4:
                if st.button("Next ▶️", disabled=st.session_state.alert_page >= total_pages - 1):
                    st.session_state.alert_page += 1
                    st.rerun()
            with pcol5:
                if st.button("Last ⏭️", disabled=st.session_state.alert_page >= total_pages - 1):
                    st.session_state.alert_page = total_pages - 1
                    st.rerun()

        if alerts:
            # Display as table
            df = pd.DataFrame([{
                'Time': t.timestamp.strftime('%Y-%m-%d %H:%M') if t.timestamp else 'N/A',
                'Market': (t.market_title[:50] + '...' if len(t.market_title or '') > 50
                          else (t.market_title or 'Unknown')),
                'Wallet': f"{t.wallet_address[:10]}...{t.wallet_address[-6:]}" if t.wallet_address else 'Unknown',
                'Bet Size': f"${t.bet_size_usd:,.0f}" if t.bet_size_usd else '$0',
                'Score': t.suspicion_score or 0,
                'Level': get_alert_level(t.suspicion_score)
            } for t in alerts])

            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No alerts found with the selected filters.")


def show_trade_history(session):
    """Trade history page with detailed breakdown"""
    st.title("📊 Trade History")

    # Search and filters
    col1, col2 = st.columns([3, 1])

    with col1:
        search = st.text_input("Search markets or wallets", "")
    with col2:
        limit = st.selectbox("Show", [20, 50, 100, 500], index=1)

    if True:  # preserve indentation level for minimal diff
        query = session.query(Trade)

        if search:
            # Validate and sanitize input
            # Remove any null bytes and limit length
            search_clean = search.replace('\x00', '').strip()[:200]

            if not search_clean:
                st.warning("Invalid search input")
            else:
                # Escape SQL wildcard characters for LIKE search
                # This prevents wildcard injection while allowing legitimate searches
                search_escaped = (search_clean
                    .replace('\\', '\\\\')
                    .replace('%', '\\%')
                    .replace('_', '\\_'))

                # Use parameterized pattern - SQLAlchemy handles the rest
                search_pattern = f"%{search_escaped}%"

                # SQLAlchemy properly parameterizes these values
                query = query.filter(
                    (Trade.market_title.ilike(search_pattern, escape='\\')) |
                    (Trade.wallet_address.ilike(search_pattern, escape='\\'))
                )

        trades = query.order_by(desc(Trade.timestamp)).limit(limit).all()

        if trades:
            for trade in trades:
                with st.expander(
                    f"{trade.timestamp.strftime('%Y-%m-%d %H:%M')} - "
                    f"{trade.market_title[:60]}... - "
                    f"Score: {trade.suspicion_score}/100"
                ):
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        st.write("**Trade Details**")
                        st.write(f"Wallet: `{trade.wallet_address}`")
                        st.write(f"Bet Size: ${trade.bet_size_usd:,.2f}")
                        st.write(f"Direction: {trade.bet_direction}")
                        st.write(f"Price: {trade.bet_price:.2f}")

                    with col2:
                        st.write("**Market Info**")
                        st.write(f"Market: {trade.market_title}")
                        st.write(f"Category: {trade.market_category or 'Unknown'}")
                        st.write(f"Market ID: `{trade.market_id}`")

                    with col3:
                        st.write("**Scoring**")
                        st.metric("Total Score", f"{trade.suspicion_score or 0}/100")
                        st.write(f"Alert Level: {get_alert_level(trade.suspicion_score)}")

                    # Show scoring breakdown (use cached calculation)
                    st.markdown("**Scoring Breakdown**")
                    try:
                        breakdown_data, raw_score, total_score = get_cached_breakdown(
                            trade.id,
                            trade.bet_size_usd or 0,
                            trade.wallet_address or '',
                            trade.timestamp.isoformat() if trade.timestamp else '',
                            trade.bet_price or 0.5,
                            trade.bet_direction or 'YES',
                            trade.market_category or '',
                            trade.market_liquidity_usd or 0,
                        )

                        st.dataframe(
                            pd.DataFrame(breakdown_data),
                            use_container_width=True,
                            hide_index=True
                        )
                        st.caption(f"Raw: {raw_score}/135 -> Normalized: {total_score}/100")
                    except Exception as e:
                        st.warning(f"Could not calculate breakdown: {e}")
        else:
            st.info("No trades found.")


def show_wallet_analysis():
    """Wallet analysis and profiling page"""
    st.title("👤 Wallet Analysis")

    wallet_input = st.text_input(
        "Enter wallet address",
        placeholder="0x742d35Cc6634C0532925a3b844Bc9e7595f0a3f1"
    )

    if wallet_input:
        # Validate Ethereum address format (0x + 40 hex characters)
        if not wallet_input.startswith('0x') or len(wallet_input) != 42:
            st.error("Invalid Ethereum address format")
            return
        if not re.match(r'^0x[a-fA-F0-9]{40}$', wallet_input):
            st.error("Invalid Ethereum address: contains non-hexadecimal characters")
            return

        with st.spinner("Analyzing wallet..."):
            analysis = analyze_wallet(wallet_input)

            if not analysis['profile']:
                st.warning("No trading history found for this wallet.")
                return

            profile = analysis['profile']

            # Profile overview
            st.subheader("📊 Wallet Profile")

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("Total Trades", profile.total_trades)
                st.metric("Suspicious Trades", profile.suspicious_trades)
            with col2:
                st.metric("Avg Score", f"{profile.avg_suspicion_score:.1f}/100")
                st.metric("Win Rate", f"{profile.win_rate:.1%}")
            with col3:
                st.metric("Avg Bet Size", f"${profile.avg_bet_size:,.2f}")
                st.metric("Markets Traded", profile.markets_traded)
            with col4:
                st.metric("Wallet Age", f"{profile.wallet_age_days} days")
                st.metric("Off-Hours %", f"{profile.off_hours_ratio:.1%}")

            # Temporal patterns
            if analysis['temporal_patterns']:
                st.subheader("⏰ Temporal Patterns")
                for pattern in analysis['temporal_patterns']:
                    st.info(
                        f"**{pattern.pattern_type.upper()}**: {pattern.description} "
                        f"(Confidence: {pattern.confidence_score:.1%})"
                    )

            # Win rate anomaly
            if analysis['win_rate_anomaly']:
                st.subheader("⚠️ Win Rate Anomaly Detected")
                anomaly = analysis['win_rate_anomaly']
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric("Observed", f"{anomaly['observed_win_rate']:.1%}")
                with col2:
                    st.metric("Expected", f"{anomaly['baseline_win_rate']:.1%}")
                with col3:
                    st.metric("Anomaly Score", f"{anomaly['anomaly_score']:.1f}/100")


def show_suspicious_winners(session):
    """Suspicious winners page - wallets with abnormal win patterns"""
    st.title("🏆 Suspicious Winners")

    st.markdown("""
    This page shows wallets with abnormally high win rates on prediction markets.
    A high win score suggests potential insider knowledge.
    """)

    if True:  # preserve indentation level for minimal diff
        # Check if we have resolution data
        resolution_count = session.query(func.count(MarketResolution.id)).scalar() or 0
        win_history_count = session.query(func.count(WalletWinHistory.id)).scalar() or 0

        if resolution_count == 0:
            st.warning(
                "No market resolutions tracked yet. "
                "Run the resolution monitor to detect market outcomes."
            )
            st.info(
                "Market resolutions are inferred from price data when markets close. "
                "The system detects when winning outcome price approaches ~1.0."
            )

            # Show explanation
            with st.expander("How Suspicious Win Detection Works"):
                st.markdown("""
                **Step 1: Resolution Detection**
                - Monitor Polymarket for closed markets
                - Infer outcomes from final prices (winner → ~1.0)

                **Step 2: Win/Loss Calculation**
                - Match trades to market resolutions
                - Calculate profit/loss for each trade

                **Step 3: Suspicious Win Scoring**
                - Analyze win patterns per wallet
                - Factors: Win rate, timing, geopolitical focus
                - Score from 0-100

                **Alert Thresholds:**
                - 🏆 WATCH_WIN: 50+ points
                - 💰 SUSPICIOUS_WIN: 70+ points
                - 🎯 CRITICAL_WIN: 85+ points
                """)
            return

        # Stats row
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Resolved Markets", resolution_count)

        with col2:
            st.metric("Trade Outcomes", win_history_count)

        with col3:
            # Wallets with high win scores
            suspicious_count = session.query(func.count(WalletMetrics.wallet_address)).filter(
                WalletMetrics.suspicious_win_score >= WIN_ALERT_THRESHOLDS['WATCH_WIN']
            ).scalar() or 0
            st.metric("Suspicious Wallets", suspicious_count)

        with col4:
            # Average win rate
            avg_win_rate = session.query(func.avg(WalletMetrics.win_rate)).filter(
                WalletMetrics.win_rate.isnot(None)
            ).scalar() or 0
            st.metric("Avg Win Rate", f"{avg_win_rate:.1%}" if avg_win_rate else "N/A")

        st.markdown("---")

        # Filter options
        col1, col2 = st.columns(2)

        with col1:
            min_score = st.slider(
                "Minimum Win Score",
                min_value=0,
                max_value=100,
                value=WIN_ALERT_THRESHOLDS['WATCH_WIN']
            )

        with col2:
            min_trades = st.number_input(
                "Minimum Resolved Trades",
                min_value=1,
                max_value=50,
                value=5
            )

        # Get suspicious wallets
        wallets = session.query(WalletMetrics).filter(
            WalletMetrics.suspicious_win_score >= min_score,
            WalletMetrics.winning_trades + WalletMetrics.losing_trades >= min_trades
        ).order_by(
            desc(WalletMetrics.suspicious_win_score)
        ).limit(50).all()

        if wallets:
            st.subheader(f"🎯 Top Suspicious Winners ({len(wallets)} found)")

            # Create dataframe
            df_data = []
            for w in wallets:
                total_resolved = (w.winning_trades or 0) + (w.losing_trades or 0)
                win_rate = w.win_rate or 0

                # Determine alert level
                score = w.suspicious_win_score or 0
                if score >= WIN_ALERT_THRESHOLDS['CRITICAL_WIN']:
                    alert_level = "🎯 CRITICAL"
                elif score >= WIN_ALERT_THRESHOLDS['SUSPICIOUS_WIN']:
                    alert_level = "💰 SUSPICIOUS"
                elif score >= WIN_ALERT_THRESHOLDS['WATCH_WIN']:
                    alert_level = "🏆 WATCH"
                else:
                    alert_level = "-"

                df_data.append({
                    'Alert': alert_level,
                    'Wallet': f"{w.wallet_address[:10]}...{w.wallet_address[-6:]}",
                    'Win Score': score,
                    'Win Rate': f"{win_rate:.1%}",
                    'Wins': w.winning_trades or 0,
                    'Losses': w.losing_trades or 0,
                    'Total P&L': f"${w.total_profit_loss_usd or 0:,.2f}",
                    'Geo Wins': w.geopolitical_wins or 0,
                    'Geo Acc': f"{w.geopolitical_accuracy:.1%}" if w.geopolitical_accuracy else "N/A"
                })

            df = pd.DataFrame(df_data)
            st.dataframe(df, use_container_width=True, hide_index=True)

            # Detail view for selected wallet
            st.markdown("---")
            st.subheader("📋 Wallet Details")

            wallet_options = [f"{w.wallet_address[:10]}...{w.wallet_address[-6:]}" for w in wallets]
            selected_idx = st.selectbox("Select wallet for details", range(len(wallet_options)),
                                        format_func=lambda i: wallet_options[i])

            if selected_idx is not None:
                selected_wallet = wallets[selected_idx]

                col1, col2 = st.columns(2)

                with col1:
                    st.markdown("**Performance Stats:**")
                    st.write(f"- Win Rate: {selected_wallet.win_rate:.1%}" if selected_wallet.win_rate else "- Win Rate: N/A")
                    st.write(f"- Wins: {selected_wallet.winning_trades or 0}")
                    st.write(f"- Losses: {selected_wallet.losing_trades or 0}")
                    st.write(f"- Total P&L: ${selected_wallet.total_profit_loss_usd or 0:,.2f}")
                    st.write(f"- Max Win Streak: {selected_wallet.win_streak_max or 0}")

                with col2:
                    st.markdown("**Geopolitical Focus:**")
                    st.write(f"- Geo Trades: {selected_wallet.geopolitical_trades or 0}")
                    st.write(f"- Geo Wins: {selected_wallet.geopolitical_wins or 0}")
                    st.write(f"- Geo Accuracy: {selected_wallet.geopolitical_accuracy:.1%}" if selected_wallet.geopolitical_accuracy else "- Geo Accuracy: N/A")
                    st.write(f"- Early Wins (<48h): {selected_wallet.early_win_count or 0}")

                # Win history for this wallet
                st.markdown("**Recent Win History:**")
                history = session.query(WalletWinHistory).filter(
                    WalletWinHistory.wallet_address == selected_wallet.wallet_address
                ).order_by(
                    desc(WalletWinHistory.created_at)
                ).limit(20).all()

                if history:
                    history_data = [{
                        'Result': '✅ WIN' if h.trade_result == 'WIN' else '❌ LOSS',
                        'Market': (h.market_title or '')[:40] + '...' if h.market_title and len(h.market_title) > 40 else (h.market_title or 'Unknown'),
                        'Bet': f"${h.bet_size_usd:,.2f}",
                        'Direction': h.bet_direction,
                        'P&L': f"${h.profit_loss_usd or 0:,.2f}",
                        'Timing': f"{h.hours_before_resolution:.1f}h" if h.hours_before_resolution else "N/A",
                        'Geo': '🌍' if h.is_geopolitical else ''
                    } for h in history]

                    st.dataframe(pd.DataFrame(history_data), use_container_width=True, hide_index=True)
                else:
                    st.info("No win history records for this wallet.")
        else:
            st.info(f"No wallets found with win score >= {min_score} and >= {min_trades} resolved trades.")

        # Recent resolutions
        st.markdown("---")
        st.subheader("📅 Recent Market Resolutions")

        resolutions = session.query(MarketResolution).order_by(
            desc(MarketResolution.resolved_at)
        ).limit(10).all()

        if resolutions:
            res_data = [{
                'Outcome': f"{'✅ YES' if r.winning_outcome == 'YES' else '❌ NO' if r.winning_outcome == 'NO' else '⚪ VOID'}",
                'Market ID': f"{r.market_id[:20]}...",
                'Confidence': f"{r.confidence:.1%}",
                'Resolved': r.resolved_at.strftime('%Y-%m-%d %H:%M') if r.resolved_at else 'N/A',
                'Source': r.resolution_source
            } for r in resolutions]

            st.dataframe(pd.DataFrame(res_data), use_container_width=True, hide_index=True)
        else:
            st.info("No market resolutions yet.")


def show_network_patterns():
    """Network patterns and coordinated trading page"""
    st.title("🕸️ Network Patterns")

    days = st.slider("Days to analyze", 1, 30, 7)

    with st.spinner("Detecting patterns..."):
        # Repeat offenders
        st.subheader("🔁 Repeat Offenders")
        offenders = find_repeat_offenders(days=days)

        if offenders:
            df = pd.DataFrame([{
                'Wallet': f"{o.wallet_address[:10]}...{o.wallet_address[-6:]}",
                'Total Trades': o.total_trades,
                'Suspicious': o.suspicious_trades,
                'Avg Score': f"{o.avg_suspicion_score:.1f}",
                'Age (days)': o.wallet_age_days
            } for o in offenders[:20]])

            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No repeat offenders found.")

        # Network patterns
        st.subheader("🕸️ Coordinated Trading Networks")
        networks = find_suspicious_networks(days=days)

        if networks:
            for i, network in enumerate(networks[:10], 1):
                with st.expander(
                    f"Network {i}: {network.market_title[:50]}... "
                    f"({len(network.wallets)} wallets)"
                ):
                    col1, col2 = st.columns(2)

                    with col1:
                        st.write(f"**Market:** {network.market_title}")
                        st.write(f"**Wallets:** {len(network.wallets)}")
                        st.write(f"**Trades:** {network.trade_count}")

                    with col2:
                        st.write(f"**Volume:** ${network.total_volume:,.2f}")
                        st.write(f"**Avg Score:** {network.avg_suspicion_score:.1f}")
                        st.write(f"**Pattern:** {network.pattern_type}")
        else:
            st.info("No coordinated trading networks detected.")


def show_statistics(session):
    """Statistics and charts page with efficient queries"""
    st.title("📈 Statistics")

    # Time period selector
    days_back = st.selectbox("Time Period", [7, 30, 90, 365], index=1,
                             format_func=lambda x: f"Last {x} days")

    if True:  # preserve indentation level for minimal diff
        cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)

        # Get total count first
        total_count = session.query(func.count(Trade.id)).filter(
            Trade.timestamp >= cutoff
        ).scalar() or 0

        if total_count == 0:
            st.info("No data available for this time period.")
            return

        st.write(f"**Analyzing {total_count:,} trades from the last {days_back} days**")

        # Score distribution - use SQL aggregation for efficiency
        st.subheader("Score Distribution")
        score_dist = session.query(
            (func.floor(Trade.suspicion_score / 5) * 5).label('score_bucket'),
            func.count(Trade.id).label('count')
        ).filter(
            Trade.timestamp >= cutoff,
            Trade.suspicion_score.isnot(None)
        ).group_by(
            func.floor(Trade.suspicion_score / 5) * 5
        ).order_by('score_bucket').all()

        if score_dist:
            score_df = pd.DataFrame([
                {'Score Range': f"{int(s.score_bucket)}-{int(s.score_bucket)+4}", 'Count': s.count}
                for s in score_dist if s.score_bucket is not None
            ])
            fig = px.bar(score_df, x='Score Range', y='Count',
                        title='Suspicion Score Distribution',
                        labels={'Count': 'Number of Trades'})
            st.plotly_chart(fig, use_container_width=True)

        # Bet size statistics - use SQL aggregation
        st.subheader("Bet Size Statistics")
        bet_stats = session.query(
            func.min(Trade.bet_size_usd).label('min_bet'),
            func.max(Trade.bet_size_usd).label('max_bet'),
            func.avg(Trade.bet_size_usd).label('avg_bet'),
            func.sum(Trade.bet_size_usd).label('total_volume')
        ).filter(
            Trade.timestamp >= cutoff
        ).first()

        if bet_stats:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Min Bet", f"${bet_stats.min_bet or 0:,.0f}")
            with col2:
                st.metric("Max Bet", f"${bet_stats.max_bet or 0:,.0f}")
            with col3:
                st.metric("Avg Bet", f"${bet_stats.avg_bet or 0:,.0f}")
            with col4:
                st.metric("Total Volume", f"${bet_stats.total_volume or 0:,.0f}")

        # Daily activity timeline - use SQL aggregation
        st.subheader("Activity Timeline")
        daily_stats = session.query(
            func.date(Trade.timestamp).label('date'),
            func.count(Trade.id).label('trade_count'),
            func.sum(Trade.bet_size_usd).label('volume')
        ).filter(
            Trade.timestamp >= cutoff
        ).group_by(
            func.date(Trade.timestamp)
        ).order_by('date').all()

        if daily_stats:
            daily_df = pd.DataFrame([
                {'Date': s.date, 'Trades': s.trade_count, 'Volume': float(s.volume) if s.volume else 0}
                for s in daily_stats
            ])

            fig = px.line(daily_df, x='Date', y='Trades',
                         title='Daily Trading Activity',
                         labels={'Date': 'Date', 'Trades': 'Number of Trades'})
            st.plotly_chart(fig, use_container_width=True)

        # Alert level distribution
        st.subheader("Alert Level Distribution")
        alert_dist = session.query(
            Trade.alert_level,
            func.count(Trade.id).label('count')
        ).filter(
            Trade.timestamp >= cutoff,
            Trade.alert_level.isnot(None)
        ).group_by(Trade.alert_level).all()

        if alert_dist:
            alert_df = pd.DataFrame([
                {'Level': a.alert_level or 'NORMAL', 'Count': a.count}
                for a in alert_dist
            ])
            fig = px.pie(alert_df, values='Count', names='Level',
                        title='Alert Level Distribution')
            st.plotly_chart(fig, use_container_width=True)


def show_settings():
    """Settings and configuration page"""
    st.title("⚙️ Settings")

    st.subheader("Alert Thresholds")

    col1, col2, col3 = st.columns(3)

    with col1:
        watch = st.number_input("WATCH", value=config.SUSPICION_THRESHOLD_WATCH,
                                min_value=0, max_value=100)
    with col2:
        suspicious = st.number_input("SUSPICIOUS", value=config.SUSPICION_THRESHOLD_SUSPICIOUS,
                                    min_value=0, max_value=100)
    with col3:
        critical = st.number_input("CRITICAL", value=config.SUSPICION_THRESHOLD_CRITICAL,
                                  min_value=0, max_value=100)

    st.info("Note: Threshold changes require restarting the monitoring service.")

    st.markdown("---")

    st.subheader("System Information")
    st.write(f"**Min Bet Size:** ${config.MIN_BET_SIZE_USD:,.0f}")
    st.write(f"**Poll Interval:** {config.POLL_INTERVAL_SECONDS}s")
    st.write(f"**Telegram Configured:** {'Yes' if config.TELEGRAM_CHAT_ID else 'No'}")
    st.write(f"**Database:** SQLite (local)")


def get_alert_level(score: int) -> str:
    """Get alert level from score"""
    if score is None:
        return "UNKNOWN"
    if score >= config.SUSPICION_THRESHOLD_CRITICAL:
        return "CRITICAL"
    elif score >= config.SUSPICION_THRESHOLD_SUSPICIOUS:
        return "SUSPICIOUS"
    elif score >= config.SUSPICION_THRESHOLD_WATCH:
        return "WATCH"
    else:
        return "NORMAL"


if __name__ == "__main__":
    main()
