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

# Custom CSS with sport tabs and market filters
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
    
    /* Header with Sport Tabs */
    .nav-header {
        background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%);
        padding: 1rem 2rem;
        margin: -1rem -1rem 2rem -1rem;
        color: white;
        position: relative;
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
        margin-bottom: 1rem;
    }
    
    /* Sport Tabs in bottom left of header */
    .sport-tabs {
        display: flex;
        gap: 0.5rem;
        margin-top: 1rem;
    }
    
    .sport-tab {
        padding: 0.5rem 1rem;
        font-weight: 500;
        color: rgba(255, 255, 255, 0.7);
        cursor: pointer;
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 4px;
        transition: all 0.3s ease;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        font-size: 0.875rem;
        background: rgba(255, 255, 255, 0.05);
    }
    
    .sport-tab.active {
        color: white;
        background: rgba(255, 255, 255, 0.15);
        border-color: rgba(255, 255, 255, 0.4);
    }
    
    .sport-tab:hover {
        color: white;
        background: rgba(255, 255, 255, 0.1);
        border-color: rgba(255, 255, 255, 0.3);
    }
    
    .sport-tab.disabled {
        opacity: 0.4;
        cursor: not-allowed;
    }
    
    /* Market Filter Tabs */
    .market-tabs {
        display: flex;
        flex-wrap: wrap;
        background: white;
        border-bottom: 1px solid #e0e0e0;
        margin: 0 -1rem 2rem -1rem;
        padding: 0 2rem;
        gap: 2rem;
        align-items: center;
    }
    
    .market-tab {
        padding: 1rem 0;
        font-weight: 500;
        color: #666;
        cursor: pointer;
        border-bottom: 3px solid transparent;
        transition: all 0.3s ease;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        font-size: 0.875rem;
        white-space: nowrap;
        background: none;
        border-left: none;
        border-right: none;
        border-top: none;
    }
    
    .market-tab.active {
        color: #333;
        border-bottom-color: #e31e24;
    }
    
    .market-tab:hover {
        color: #333;
    }
    
    /* Special buttons */
    .special-tab {
        padding: 1rem 0;
        font-weight: 500;
        color: #666;
        cursor: pointer;
        border-bottom: 3px solid transparent;
        transition: all 0.3s ease;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        font-size: 0.875rem;
        margin-left: auto;
        background: none;
        border-left: none;
        border-right: none;
        border-top: none;
        position: relative;
    }
    
    .special-tab:hover {
        color: #333;
    }
    
    .filters-tab {
        color: #6b7280;
    }
    
    .filters-tab:hover {
        color: #4b5563;
    }
    
    .stats-tab {
        color: #3b82f6;
        margin-left: 2rem;
    }
    
    .stats-tab:hover {
        color: #2563eb;
    }
    
    /* Refresh Button in Header */
    .refresh-button-header {
        position: absolute;
        bottom: 1rem;
        right: 2rem;
        padding: 0.5rem 1rem;
        font-weight: 500;
        color: rgba(255, 255, 255, 0.9);
        cursor: pointer;
        border: 1px solid rgba(255, 255, 255, 0.3);
        border-radius: 4px;
        transition: all 0.3s ease;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        font-size: 0.75rem;
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
    }
    
    .refresh-button-header:hover {
        color: white;
        background: rgba(255, 255, 255, 0.2);
        border-color: rgba(255, 255, 255, 0.5);
        transform: translateY(-1px);
    }
    
    /* Dropdown/Popup Styles */
    .popup-overlay {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-color: transparent;
        z-index: 999;
    }
    
    .popup-content {
        position: absolute;
        background: white;
        padding: 1.5rem;
        border-radius: 8px;
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.15);
        border: 1px solid #e5e7eb;
        min-width: 300px;
        z-index: 1000;
    }
    
    .filters-popup {
        top: 100%;
        right: 12rem;
        margin-top: 0.5rem;
    }
    
    .stats-popup {
        top: 100%;
        right: 2rem;
        margin-top: 0.5rem;
    }
    
    .popup-header {
        font-size: 1rem;
        font-weight: 600;
        color: #333;
        margin-bottom: 1rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    /* Stats Modal Styles */
    .stats-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 1rem;
        margin-bottom: 1rem;
    }
    
    .stat-item {
        text-align: center;
        padding: 1rem;
        background: #f8f9fa;
        border-radius: 6px;
    }
    
    .stat-label {
        font-size: 0.875rem;
        color: #666;
        font-weight: 500;
        margin-bottom: 0.5rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .stat-value {
        font-size: 1.5rem;
        font-weight: 700;
        color: #333;
        margin: 0;
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
        .market-tabs {
            flex-wrap: wrap;
        }
        
        .sport-tabs {
            flex-wrap: wrap;
        }
        
        .opportunity-header {
            flex-direction: column;
            gap: 1rem;
        }
        
        .stats-grid {
            grid-template-columns: 1fr;
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
    if 'active_sport' not in st.session_state:
        st.session_state.active_sport = 'MLB'
    if 'active_market' not in st.session_state:
        st.session_state.active_market = 'All Markets'
    if 'ev_calculator' not in st.session_state:
        st.session_state.ev_calculator = None
    if 'show_filters_modal' not in st.session_state:
        st.session_state.show_filters_modal = False
    if 'show_stats_modal' not in st.session_state:
        st.session_state.show_stats_modal = False
    if 'filters' not in st.session_state:
        st.session_state.filters = {
            'min_ev': 1.0,
            'min_books': 3
        }

def check_environment():
    """Check if required environment variables are set"""
    google_creds = os.environ.get('GOOGLE_SERVICE_ACCOUNT_CREDENTIALS')
    return google_creds is not None

def render_header():
    """Render the main header section with sport tabs and refresh button"""
    st.markdown(f"""
    <div class="nav-header">
        <div class="nav-brand">EV Betting Tool</div>
        <div class="nav-subtitle">Find profitable betting opportunities by comparing Splash Sports and sportsbook odds</div>
        <div class="sport-tabs">
            <div class="sport-tab {'active' if st.session_state.active_sport == 'MLB' else ''}" onclick="setSport('MLB')">MLB</div>
            <div class="sport-tab disabled" title="Coming Soon">NFL</div>
            <div class="sport-tab disabled" title="Coming Soon">WNBA</div>
            <div class="sport-tab disabled" title="Coming Soon">NCAAF</div>
        </div>
        <div class="refresh-button-header" onclick="refreshData()">🔄 Refresh</div>
    </div>
    """, unsafe_allow_html=True)

def get_market_display_name(market_key):
    """Convert market key to display name"""
    market_mapping = {
        'All Markets': 'All Markets',
        'pitcher_strikeouts': 'Strikeouts',
        'pitcher_hits_allowed': 'Hits Allowed',
        'pitcher_outs': 'Outs',
        'pitcher_earned_runs': 'Earned Runs',
        'batter_total_bases': 'Total Bases',
        'batter_hits': 'Hits',
        'batter_runs_scored': 'Runs',
        'batter_rbis': 'RBIs',
        'batter_singles': 'Singles'
    }
    return market_mapping.get(market_key, market_key)

def render_market_tabs():
    """Render market filter tabs with Filters and Stats buttons"""
    # Available markets for MLB
    available_markets = [
        ('All Markets', 'All Markets'),
        ('Strikeouts', 'pitcher_strikeouts'),
        ('Hits Allowed', 'pitcher_hits_allowed'), 
        ('Outs', 'pitcher_outs'),
        ('Earned Runs', 'pitcher_earned_runs'),
        ('Total Bases', 'batter_total_bases'),
        ('Hits', 'batter_hits'),
        ('Runs', 'batter_runs_scored'),
        ('RBIs', 'batter_rbis'),
        ('Singles', 'batter_singles')
    ]
    
    # Create columns for market tabs and special buttons
    cols = st.columns(len(available_markets) + 2)
    
    # Market filter tabs (no button styling)
    for i, (display_name, market_key) in enumerate(available_markets):
        with cols[i]:
            # Use markdown button to remove styling
            button_class = "market-tab active" if st.session_state.active_market == market_key else "market-tab"
            if st.button(display_name, key=f"market_{market_key}", 
                        help=f"Filter by {display_name}",
                        use_container_width=True):
                st.session_state.active_market = market_key
                st.rerun()
    
    # Filters button
    with cols[-2]:
        if st.button("FILTERS", key="filters_btn", 
                    help="Adjust minimum EV and book count",
                    use_container_width=True):
            st.session_state.show_filters_modal = True
            st.rerun()
    
    # Stats button  
    with cols[-1]:
        if st.button("STATS", key="stats_btn",
                    help="View performance statistics", 
                    use_container_width=True):
            st.session_state.show_stats_modal = True
            st.rerun()

@st.fragment
def render_filters_popup():
    """Render the filters popup"""
    if st.session_state.show_filters_modal:
        # Overlay to catch clicks outside
        if st.button("", key="filters_overlay", 
                    help="Click to close filters",
                    use_container_width=True):
            st.session_state.show_filters_modal = False
            st.rerun()
        
        with st.container():
            st.markdown("**FILTERS**")
            
            # Filter controls in a more compact layout
            min_ev = st.slider("Minimum EV %", 0.0, 20.0, st.session_state.filters['min_ev'], 0.1, key="filter_ev")
            min_books = st.slider("Minimum Books", 1, 10, st.session_state.filters['min_books'], key="filter_books")
            
            # Update session state
            st.session_state.filters['min_ev'] = min_ev
            st.session_state.filters['min_books'] = min_books
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Apply", key="apply_filters", type="primary", use_container_width=True):
                    st.session_state.show_filters_modal = False
                    st.rerun()
            with col2:
                if st.button("Reset", key="reset_filters", use_container_width=True):
                    st.session_state.filters = {'min_ev': 1.0, 'min_books': 3}
                    st.rerun()

@st.fragment  
def render_stats_popup():
    """Render the stats popup"""
    if st.session_state.show_stats_modal:
        # Overlay to catch clicks outside
        if st.button("", key="stats_overlay",
                    help="Click to close stats", 
                    use_container_width=True):
            st.session_state.show_stats_modal = False
            st.rerun()
        
        with st.container():
            st.markdown("**STATISTICS**")
            
            # Calculate stats
            opportunities_df = st.session_state.opportunities
            last_update = st.session_state.last_refresh.strftime("%H:%M:%S") if st.session_state.last_refresh else "Never"
            total_opps = len(opportunities_df)
            avg_ev = opportunities_df['Splash_EV_Percentage'].mean() if not opportunities_df.empty else 0
            best_ev = opportunities_df['Splash_EV_Percentage'].max() if not opportunities_df.empty else 0
            
            # Display stats
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Last Updated", last_update)
                st.metric("Average EV", f"{avg_ev:.2%}")
            with col2:
                st.metric("Opportunities", total_opps)  
                st.metric("Best EV", f"{best_ev:.2%}")
            
            if st.button("Close", key="close_stats", type="primary", use_container_width=True):
                st.session_state.show_stats_modal = False
                st.rerun()

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
    
    # Get display name for market
    market_display = get_market_display_name(row['Market'])
    
    return f"""
    <div class="opportunity-card">
        <div class="opportunity-header">
            <div>
                <div class="player-name">{row['Player']}</div>
                <div class="market-info">{market_display} - {row['Bet_Type'].title()} {row['Line']}</div>
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

def render_opportunities(filtered_df):
    """Render opportunities"""
    st.markdown("### Current Opportunities")
    
    if filtered_df.empty:
        st.markdown("""
        <div class="no-data-container">
            <div class="no-data-title">No Opportunities Found</div>
            <div class="no-data-text">Try adjusting your filters or refresh the data to find betting opportunities.</div>
        </div>
        """, unsafe_allow_html=True)
        return
    
    st.markdown(f"**{len(filtered_df)} opportunities found**")
    
    # Display top opportunities
    for idx, row in filtered_df.head(20).iterrows():
        st.markdown(render_opportunity_card(row), unsafe_allow_html=True)
    
    if len(filtered_df) > 20:
        st.info(f"Showing top 20 of {len(filtered_df)} opportunities. Adjust filters to see more.")

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
    
    if st.session_state.active_market != "All Markets":
        filtered_df = filtered_df[filtered_df['Market'] == st.session_state.active_market]
    
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
    render_market_tabs()
    
    # Handle popups
    if st.session_state.show_filters_modal:
        render_filters_popup()
    
    if st.session_state.show_stats_modal:
        render_stats_popup()
    
    # Check for refresh button click in header (would need JavaScript integration)
    # For now, we'll add a hidden refresh button that can be triggered
    refresh_clicked = st.button("Hidden Refresh", key="hidden_refresh", 
                               help="This button is hidden but can be triggered by header button")
    
    # Apply filters and render opportunities
    filtered_df = apply_filters(st.session_state.opportunities)
    render_opportunities(filtered_df)
    
    # Data refresh logic
    if refresh_clicked:
        with st.spinner("Fetching and analyzing latest data..."):
            try:
                opportunities = st.session_state.ev_calculator.run_full_analysis()
                st.session_state.opportunities = opportunities
                st.session_state.last_refresh = datetime.now()
                
                if not opportunities.empty:
                    st.success(f"Found {len(opportunities)} opportunities!")
                    time.sleep(1)  # Brief pause to show success message
                    st.rerun()
                else:
                    st.warning("No opportunities found in current data")
                    
            except Exception as e:
                st.error(f"Error during data fetch: {e}")
    
    # Render status indicator
    render_status_indicator()

if __name__ == "__main__":
    main()
