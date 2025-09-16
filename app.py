# app.py
import streamlit as st
import pandas as pd
from datetime import datetime
import time
import os
from ev_calculator import EVCalculator

# Page configuration
st.set_page_config(
    page_title="MLB EV Betting Tool",
    page_icon="⚾",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS inspired by Honda's clean design
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Global Styles */
    .main {
        padding: 0;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Hide Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display:none;}
    
    /* Header Navigation */
    .nav-header {
        background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%);
        padding: 1rem 2rem;
        margin: -1rem -1rem 2rem -1rem;
        color: white;
    }
    
    .nav-brand {
        font-size: 2rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
        letter-spacing: -0.025em;
    }
    
    .nav-subtitle {
        font-size: 1rem;
        font-weight: 400;
        opacity: 0.8;
        margin-bottom: 0;
    }
    
    /* Navigation Tabs */
    .nav-tabs {
        display: flex;
        background: white;
        border-bottom: 1px solid #e0e0e0;
        margin: 0 -1rem 2rem -1rem;
        padding: 0 2rem;
    }
    
    .nav-tab {
        padding: 1rem 2rem;
        font-weight: 500;
        color: #666;
        cursor: pointer;
        border-bottom: 3px solid transparent;
        transition: all 0.3s ease;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        font-size: 0.875rem;
    }
    
    .nav-tab.active {
        color: #333;
        border-bottom-color: #e31e24;
    }
    
    .nav-tab:hover {
        color: #333;
        background: #f8f8f8;
    }
    
    /* Metrics Section */
    .metrics-container {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 1.5rem;
        margin-bottom: 2rem;
    }
    
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 8px;
        box-shadow: 0 2px 12px rgba(0,0,0,0.08);
        border: 1px solid #f0f0f0;
        text-align: center;
    }
    
    .metric-label {
        font-size: 0.875rem;
        color: #666;
        font-weight: 500;
        margin-bottom: 0.5rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: #333;
        margin: 0;
    }
    
    /* Filters Section */
    .filters-container {
        background: white;
        padding: 1.5rem;
        border-radius: 8px;
        box-shadow: 0 2px 12px rgba(0,0,0,0.08);
        border: 1px solid #f0f0f0;
        margin-bottom: 2rem;
    }
    
    .filters-header {
        font-size: 1.125rem;
        font-weight: 600;
        color: #333;
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    
    .refresh-button {
        background: #e31e24;
        color: white;
        border: none;
        padding: 0.5rem 1rem;
        border-radius: 4px;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.3s ease;
    }
    
    .refresh-button:hover {
        background: #c41e24;
        transform: translateY(-1px);
    }
    
    /* Opportunity Cards */
    .opportunity-card {
        background: white;
        padding: 1.5rem;
        border-radius: 8px;
        box-shadow: 0 2px 12px rgba(0,0,0,0.08);
        border: 1px solid #f0f0f0;
        margin-bottom: 1rem;
        transition: all 0.3s ease;
    }
    
    .opportunity-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 20px rgba(0,0,0,0.12);
    }
    
    .opportunity-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 1rem;
    }
    
    .player-name {
        font-size: 1.25rem;
        font-weight: 600;
        color: #333;
        margin: 0;
    }
    
    .market-info {
        font-size: 0.875rem;
        color: #666;
        margin: 0.25rem 0 0 0;
    }
    
    .ev-value {
        font-size: 1.5rem;
        font-weight: 700;
        margin: 0;
    }
    
    .ev-high { color: #28a745; }
    .ev-medium { color: #ffc107; }
    .ev-low { color: #17a2b8; }
    
    .ev-details {
        font-size: 0.875rem;
        color: #666;
        margin: 0.25rem 0 0 0;
    }
    
    .book-info {
        font-size: 0.8rem;
        color: #888;
        margin: 0;
    }
    
    /* Status Indicator */
    .status-container {
        position: fixed;
        bottom: 1rem;
        left: 1rem;
        background: white;
        padding: 0.75rem;
        border-radius: 8px;
        box-shadow: 0 2px 12px rgba(0,0,0,0.08);
        border: 1px solid #f0f0f0;
        font-size: 0.75rem;
        color: #666;
        z-index: 1000;
    }
    
    .status-dot {
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        margin-right: 8px;
    }
    
    .status-green { background-color: #28a745; }
    .status-red { background-color: #dc3545; }
    
    /* Content Sections */
    .content-section {
        display: none;
        animation: fadeIn 0.3s ease;
    }
    
    .content-section.active {
        display: block;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    /* No data state */
    .no-data-container {
        text-align: center;
        padding: 4rem 2rem;
        color: #666;
    }
    
    .no-data-title {
        font-size: 1.5rem;
        font-weight: 600;
        margin-bottom: 1rem;
    }
    
    .no-data-text {
        font-size: 1rem;
        margin-bottom: 2rem;
    }
    
    /* Responsive */
    @media (max-width: 768px) {
        .nav-tabs {
            flex-wrap: wrap;
        }
        
        .metrics-container {
            grid-template-columns: repeat(2, 1fr);
        }
        
        .opportunity-header {
            flex-direction: column;
            gap: 1rem;
        }
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
def init_session_state():
    """Initialize session state variables"""
    if 'last_refresh' not in st.session_state:
        st.session_state.last_refresh = None
    if 'opportunities' not in st.session_state:
        st.session_state.opportunities = pd.DataFrame()
    if 'active_tab' not in st.session_state:
        st.session_state.active_tab = 'opportunities'
    if 'ev_calculator' not in st.session_state:
        st.session_state.ev_calculator = None
    if 'filters' not in st.session_state:
        st.session_state.filters = {
            'min_ev': 1.0,
            'market_filter': 'All Markets',
            'min_books': 3
        }

def check_environment():
    """Check if required environment variables are set"""
    google_creds = os.environ.get('GOOGLE_SERVICE_ACCOUNT_CREDENTIALS')
    return google_creds is not None

def render_header():
    """Render the main header section"""
    st.markdown("""
    <div class="nav-header">
        <div class="nav-brand">MLB EV Betting Tool</div>
        <div class="nav-subtitle">Find profitable betting opportunities by comparing Splash Sports and sportsbook odds</div>
    </div>
    """, unsafe_allow_html=True)

def render_navigation():
    """Render navigation tabs"""
    tabs = [
        ('opportunities', 'Opportunities'),
        ('analytics', 'Analytics'),
        ('charts', 'Charts')
    ]
    
    nav_html = '<div class="nav-tabs">'
    for tab_key, tab_name in tabs:
        active_class = 'active' if st.session_state.active_tab == tab_key else ''
        nav_html += f'<div class="nav-tab {active_class}" onclick="setActiveTab(\'{tab_key}\')">{tab_name}</div>'
    nav_html += '</div>'
    
    st.markdown(nav_html, unsafe_allow_html=True)
    
    # JavaScript for tab switching
    st.markdown("""
    <script>
    function setActiveTab(tabName) {
        // This would need to be handled via Streamlit components in a real implementation
        console.log('Switch to tab:', tabName);
    }
    </script>
    """, unsafe_allow_html=True)

def render_tab_buttons():
    """Render tab buttons using Streamlit columns"""
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("OPPORTUNITIES", key="tab_opportunities", use_container_width=True):
            st.session_state.active_tab = 'opportunities'
    
    with col2:
        if st.button("ANALYTICS", key="tab_analytics", use_container_width=True):
            st.session_state.active_tab = 'analytics'
    
    with col3:
        if st.button("CHARTS", key="tab_charts", use_container_width=True):
            st.session_state.active_tab = 'charts'

def render_metrics(opportunities_df):
    """Render key metrics"""
    last_update = st.session_state.last_refresh.strftime("%H:%M:%S") if st.session_state.last_refresh else "Never"
    total_opps = len(opportunities_df)
    avg_ev = opportunities_df['Splash_EV_Percentage'].mean() if not opportunities_df.empty else 0
    best_ev = opportunities_df['Splash_EV_Percentage'].max() if not opportunities_df.empty else 0
    
    st.markdown(f"""
    <div class="metrics-container">
        <div class="metric-card">
            <div class="metric-label">Last Updated</div>
            <div class="metric-value">{last_update}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Opportunities</div>
            <div class="metric-value">{total_opps}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Average EV</div>
            <div class="metric-value">{avg_ev:.2%}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Best EV</div>
            <div class="metric-value">{best_ev:.2%}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_filters():
    """Render filters section"""
    st.markdown('<div class="filters-container">', unsafe_allow_html=True)
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.markdown('<div class="filters-header">Filters & Settings</div>', unsafe_allow_html=True)
    
    with col2:
        refresh_clicked = st.button("Refresh Data", key="refresh_main", type="primary")
    
    # Filter controls
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        min_ev = st.slider("Minimum EV %", 0.0, 20.0, st.session_state.filters['min_ev'], 0.1)
        st.session_state.filters['min_ev'] = min_ev
    
    with col2:
        available_markets = [
            'pitcher_strikeouts', 'pitcher_hits_allowed', 'pitcher_outs',
            'pitcher_earned_runs', 'batter_total_bases', 'batter_hits',
            'batter_runs_scored', 'batter_rbis', 'batter_singles'
        ]
        market_filter = st.selectbox("Market Filter", ["All Markets"] + available_markets, 
                                   index=0 if st.session_state.filters['market_filter'] == 'All Markets' else 
                                   available_markets.index(st.session_state.filters['market_filter']) + 1)
        st.session_state.filters['market_filter'] = market_filter
    
    with col3:
        min_books = st.slider("Minimum Books", 1, 10, st.session_state.filters['min_books'])
        st.session_state.filters['min_books'] = min_books
    
    with col4:
        auto_refresh = st.checkbox("Auto-refresh (5 min)")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    return refresh_clicked, auto_refresh

def render_opportunity_card(row):
    """Render an individual opportunity card"""
    ev_pct = row['Splash_EV_Percentage']
    
    # Determine EV class
    if ev_pct >= 0.05:
        ev_class = "ev-high"
    elif ev_pct >= 0.02:
        ev_class = "ev-medium"
    else:
        ev_class = "ev-low"
    
    return f"""
    <div class="opportunity-card">
        <div class="opportunity-header">
            <div>
                <div class="player-name">{row['Player']}</div>
                <div class="market-info">{row['Market']} - {row['Bet_Type'].title()} {row['Line']}</div>
                <div class="book-info">Best Book: {row['Best_Sportsbook']} ({row['Best_Odds']:+d})</div>
            </div>
            <div style="text-align: right;">
                <div class="ev-value {ev_class}">{ev_pct:.2%}</div>
                <div class="ev-details">${row['Splash_EV_Dollars_Per_100']:.2f}/100</div>
                <div class="book-info">{row['Num_Books_Used']} books</div>
            </div>
        </div>
    </div>
    """

def render_opportunities_tab(filtered_df):
    """Render the opportunities tab content"""
    if filtered_df.empty:
        st.markdown("""
        <div class="no-data-container">
            <div class="no-data-title">No Opportunities Found</div>
            <div class="no-data-text">Try adjusting your filters or refresh the data to find betting opportunities.</div>
        </div>
        """, unsafe_allow_html=True)
        return
    
    st.markdown(f"### {len(filtered_df)} Opportunities Found")
    
    # Display top opportunities
    for idx, row in filtered_df.head(10).iterrows():
        st.markdown(render_opportunity_card(row), unsafe_allow_html=True)
    
    if len(filtered_df) > 10:
        st.info(f"Showing top 10 of {len(filtered_df)} opportunities. Adjust filters to see more.")

def render_analytics_tab(filtered_df):
    """Render the analytics tab content"""
    if filtered_df.empty:
        st.markdown("""
        <div class="no-data-container">
            <div class="no-data-title">No Data for Analysis</div>
            <div class="no-data-text">Refresh data to view analytics.</div>
        </div>
        """, unsafe_allow_html=True)
        return
    
    st.markdown("### Detailed Analytics")
    
    # Full data table
    st.dataframe(
        filtered_df.style.format({
            'True_Prob': '{:.1%}',
            'Splash_EV_Percentage': '{:.2%}',
            'Splash_EV_Dollars_Per_100': '${:.2f}',
        }),
        use_container_width=True,
        height=400
    )
    
    # Summary statistics
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Market Breakdown**")
        market_summary = filtered_df.groupby('Market').agg({
            'Splash_EV_Percentage': ['count', 'mean']
        }).round(3)
        market_summary.columns = ['Count', 'Avg EV']
        st.dataframe(market_summary)
    
    with col2:
        st.markdown("**Top Sportsbooks**")
        book_summary = filtered_df.groupby('Best_Sportsbook').size().sort_values(ascending=False)
        st.dataframe(book_summary.head(10))

def render_charts_tab(filtered_df):
    """Render the charts tab content"""
    if filtered_df.empty:
        st.markdown("""
        <div class="no-data-container">
            <div class="no-data-title">No Data for Charts</div>
            <div class="no-data-text">Refresh data to view charts.</div>
        </div>
        """, unsafe_allow_html=True)
        return
    
    st.markdown("### Data Visualizations")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**EV Distribution**")
        st.bar_chart(filtered_df['Splash_EV_Percentage'])
    
    with col2:
        st.markdown("**Market Distribution**")
        market_counts = filtered_df['Market'].value_counts()
        st.bar_chart(market_counts)
    
    # Additional charts
    st.markdown("**EV by Market**")
    market_ev = filtered_df.groupby('Market')['Splash_EV_Percentage'].mean().sort_values(ascending=False)
    st.bar_chart(market_ev)

def render_status_indicator():
    """Render the status indicator at bottom left"""
    env_ok = check_environment()
    
    status_dot = "status-green" if env_ok else "status-red"
    status_text = "Connected" if env_ok else "Disconnected"
    
    st.markdown(f"""
    <div class="status-container">
        <span class="status-dot {status_dot}"></span>
        API Status: {status_text}
    </div>
    """, unsafe_allow_html=True)

def apply_filters(df):
    """Apply filters to the opportunities dataframe"""
    if df.empty:
        return df
    
    filtered_df = df.copy()
    
    # Apply filters
    filtered_df = filtered_df[filtered_df['Splash_EV_Percentage'] >= (st.session_state.filters['min_ev']/100)]
    
    if st.session_state.filters['market_filter'] != "All Markets":
        filtered_df = filtered_df[filtered_df['Market'] == st.session_state.filters['market_filter']]
    
    filtered_df = filtered_df[filtered_df['Num_Books_Used'] >= st.session_state.filters['min_books']]
    
    return filtered_df

def main():
    """Main application function"""
    # Initialize session state
    init_session_state()
    
    # Check environment
    if not check_environment():
        st.error("Environment Error: Missing required credentials")
        st.stop()
    
    # Initialize EV calculator
    if st.session_state.ev_calculator is None:
        try:
            st.session_state.ev_calculator = EVCalculator()
        except Exception as e:
            st.error(f"Failed to initialize EV Calculator: {e}")
            st.stop()
    
    # Render UI components
    render_header()
    render_tab_buttons()
    render_metrics(st.session_state.opportunities)
    refresh_clicked, auto_refresh = render_filters()
    
    # Data refresh logic
    should_refresh = (
        refresh_clicked or 
        (auto_refresh and 
         (st.session_state.last_refresh is None or 
          (datetime.now() - st.session_state.last_refresh).seconds > 300))
    )
    
    if should_refresh:
        with st.spinner("Fetching and analyzing latest data..."):
            try:
                opportunities = st.session_state.ev_calculator.run_full_analysis()
                st.session_state.opportunities = opportunities
                st.session_state.last_refresh = datetime.now()
                
                if not opportunities.empty:
                    st.success(f"Found {len(opportunities)} opportunities!")
                    st.rerun()
                else:
                    st.warning("No opportunities found in current data")
                    
            except Exception as e:
                st.error(f"Error during data fetch: {e}")
    
    # Apply filters and render active tab
    filtered_df = apply_filters(st.session_state.opportunities)
    
    if st.session_state.active_tab == 'opportunities':
        render_opportunities_tab(filtered_df)
    elif st.session_state.active_tab == 'analytics':
        render_analytics_tab(filtered_df)
    elif st.session_state.active_tab == 'charts':
        render_charts_tab(filtered_df)
    
    # Render status indicator
    render_status_indicator()
    
    # Auto-refresh logic
    if auto_refresh and st.session_state.last_refresh:
        time_since_refresh = (datetime.now() - st.session_state.last_refresh).seconds
        if time_since_refresh >= 300:
            st.rerun()

if __name__ == "__main__":
    main()
