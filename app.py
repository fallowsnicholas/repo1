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
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        padding: 1rem 0;
        border-bottom: 2px solid #f0f2f6;
        margin-bottom: 2rem;
    }
    
    .metric-container {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin: 0.5rem 0;
    }
    
    .opportunity-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #28a745;
        margin: 0.5rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .high-ev {
        border-left-color: #28a745 !important;
        background: linear-gradient(90deg, #d4edda 0%, #f8f9fa 100%);
    }
    
    .medium-ev {
        border-left-color: #ffc107 !important;
        background: linear-gradient(90deg, #fff3cd 0%, #f8f9fa 100%);
    }
    
    .low-ev {
        border-left-color: #17a2b8 !important;
        background: linear-gradient(90deg, #d1ecf1 0%, #f8f9fa 100%);
    }
    
    .sidebar-section {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    
    .filter-section {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    }
    
    .status-success {
        color: #28a745;
        font-weight: bold;
    }
    
    .status-warning {
        color: #ffc107;
        font-weight: bold;
    }
    
    .status-error {
        color: #dc3545;
        font-weight: bold;
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
    if 'is_loading' not in st.session_state:
        st.session_state.is_loading = False
    if 'ev_calculator' not in st.session_state:
        st.session_state.ev_calculator = None

def check_environment():
    """Check if required environment variables are set"""
    google_creds = os.environ.get('GOOGLE_SERVICE_ACCOUNT_CREDENTIALS')
    
    if not google_creds:
        return False, "Missing GOOGLE_SERVICE_ACCOUNT_CREDENTIALS"
    
    return True, "Environment OK"

def create_opportunity_card(row):
    """Create an HTML card for an opportunity"""
    ev_pct = row['Splash_EV_Percentage']
    
    # Determine card style based on EV
    if ev_pct >= 0.05:
        card_class = "high-ev"
        ev_color = "#28a745"
    elif ev_pct >= 0.02:
        card_class = "medium-ev"
        ev_color = "#ffc107"
    else:
        card_class = "low-ev"
        ev_color = "#17a2b8"
    
    return f'''
    <div class="opportunity-card {card_class}">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <h4 style="margin: 0; color: #333;">{row['Player']}</h4>
                <p style="margin: 5px 0; color: #666;">{row['Market']} - {row['Bet_Type'].title()} {row['Line']}</p>
                <small style="color: #888;">Best Book: {row['Best_Sportsbook']} ({row['Best_Odds']:+d})</small>
            </div>
            <div style="text-align: right;">
                <h3 style="margin: 0; color: {ev_color};">{ev_pct:.2%}</h3>
                <p style="margin: 0; color: #666;">${row['Splash_EV_Dollars_Per_100']:.2f}/100</p>
                <small style="color: #888;">{row['Num_Books_Used']} books</small>
            </div>
        </div>
    </div>
    '''

def display_metrics(opportunities_df):
    """Display key metrics in the dashboard"""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        last_update = st.session_state.last_refresh.strftime("%H:%M:%S") if st.session_state.last_refresh else "Never"
        st.markdown(f'''
        <div class="metric-container">
            <h4>🕐 Last Updated</h4>
            <h2>{last_update}</h2>
        </div>
        ''', unsafe_allow_html=True)

    with col2:
        total_opps = len(opportunities_df)
        st.markdown(f'''
        <div class="metric-container">
            <h4>🎯 Opportunities</h4>
            <h2>{total_opps}</h2>
        </div>
        ''', unsafe_allow_html=True)

    with col3:
        if not opportunities_df.empty:
            avg_ev = opportunities_df['Splash_EV_Percentage'].mean()
            st.markdown(f'''
            <div class="metric-container">
                <h4>📊 Average EV</h4>
                <h2>{avg_ev:.2%}</h2>
            </div>
            ''', unsafe_allow_html=True)
        else:
            st.markdown(f'''
            <div class="metric-container">
                <h4>📊 Average EV</h4>
                <h2>--</h2>
            </div>
            ''', unsafe_allow_html=True)

    with col4:
        if not opportunities_df.empty:
            best_ev = opportunities_df['Splash_EV_Percentage'].max()
            st.markdown(f'''
            <div class="metric-container">
                <h4>🚀 Best EV</h4>
                <h2>{best_ev:.2%}</h2>
            </div>
            ''', unsafe_allow_html=True)
        else:
            st.markdown(f'''
            <div class="metric-container">
                <h4>🚀 Best EV</h4>
                <h2>--</h2>
            </div>
            ''', unsafe_allow_html=True)

def display_sidebar():
    """Display sidebar with configuration and controls"""
    with st.sidebar:
        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.markdown("### ⚙️ Configuration")
        
        # Environment status
        env_ok, env_msg = check_environment()
        status_class = "status-success" if env_ok else "status-error"
        status_icon = "✅" if env_ok else "❌"
        
        st.markdown(f"""
        **Environment Status:**
        - <span class="{status_class}">{status_icon} {env_msg}</span>
        """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Filters Section
        st.markdown('<div class="filter-section">', unsafe_allow_html=True)
        st.markdown("### 🎛️ Filters")
        
        min_ev = st.slider(
            "Minimum EV %", 
            0.0, 20.0, 1.0, 0.1, 
            help="Only show opportunities above this EV threshold"
        )
        
        # Available markets
        available_markets = [
            'pitcher_strikeouts', 'pitcher_hits_allowed', 'pitcher_outs',
            'pitcher_earned_runs', 'batter_total_bases', 'batter_hits',
            'batter_runs_scored', 'batter_rbis', 'batter_singles'
        ]
        
        market_filter = st.selectbox(
            "Market Filter", 
            ["All Markets"] + available_markets,
            help="Filter by specific market type"
        )
        
        min_books = st.slider(
            "Minimum Books", 
            1, 10, 3, 
            help="Minimum number of sportsbooks required for analysis"
        )
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Actions Section
        st.markdown("### 🔄 Actions")
        
        col1, col2 = st.columns(2)
        with col1:
            refresh_button = st.button("🔄 Refresh Data", type="primary", use_container_width=True)
        with col2:
            auto_refresh = st.checkbox("Auto-refresh", help="Refresh every 5 minutes")
        
        # Advanced Settings
        with st.expander("🔧 Advanced Settings"):
            save_to_sheets = st.checkbox("Save results to Google Sheets", value=False)
            min_true_prob = st.slider("Minimum True Probability", 0.1, 0.9, 0.5, 0.05)
            ev_threshold = st.slider("EV Threshold", 0.001, 0.1, 0.01, 0.001)
        
        # Info Section
        st.markdown("---")
        st.markdown("### ℹ️ About")
        st.markdown("""
        This tool finds profitable betting opportunities by:
        1. 📊 Reading Splash Sports fair odds
        2. 🎲 Comparing against sportsbook odds
        3. 📈 Calculating expected value (EV)
        4. 🎯 Highlighting best opportunities
        """)
        
        return {
            'refresh_button': refresh_button,
            'auto_refresh': auto_refresh,
            'min_ev': min_ev,
            'market_filter': market_filter,
            'min_books': min_books,
            'save_to_sheets': save_to_sheets,
            'min_true_prob': min_true_prob,
            'ev_threshold': ev_threshold
        }

def apply_filters(df, filters):
    """Apply user-defined filters to the opportunities dataframe"""
    if df.empty:
        return df
    
    filtered_df = df.copy()
    
    # EV filter
    filtered_df = filtered_df[filtered_df['Splash_EV_Percentage'] >= (filters['min_ev']/100)]
    
    # Market filter
    if filters['market_filter'] != "All Markets":
        filtered_df = filtered_df[filtered_df['Market'] == filters['market_filter']]
    
    # Books filter
    filtered_df = filtered_df[filtered_df['Num_Books_Used'] >= filters['min_books']]
    
    return filtered_df

def display_opportunities(filtered_df):
    """Display opportunities in different tabs"""
    if filtered_df.empty:
        st.warning("⚠️ No opportunities match your current filters. Try adjusting the filter criteria.")
        return
    
    st.markdown("---")
    st.subheader(f"🎯 {len(filtered_df)} Opportunities Found")
    
    # Create tabs for different views
    tab1, tab2, tab3 = st.tabs(["🎲 Opportunities", "📊 Analytics", "📈 Charts"])
    
    with tab1:
        # Display opportunities in cards
        for idx, row in filtered_df.head(10).iterrows():
            st.markdown(create_opportunity_card(row), unsafe_allow_html=True)
        
        if len(filtered_df) > 10:
            st.info(f"Showing top 10 of {len(filtered_df)} opportunities. Adjust filters to see more.")
    
    with tab2:
        # Analytics view with full table
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
        st.subheader("📊 Summary Statistics")
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Market Breakdown**")
            market_summary = filtered_df.groupby('Market').agg({
                'Splash_EV_Percentage': ['count', 'mean']
            }).round(3)
            market_summary.columns = ['Count', 'Avg EV']
            st.dataframe(market_summary)
        
        with col2:
            st.markdown("**Book Usage**")
            book_summary = filtered_df.groupby('Best_Sportsbook').size().sort_values(ascending=False)
            st.dataframe(book_summary.head(10))
    
    with tab3:
        # Charts view
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**EV Distribution**")
            st.bar_chart(filtered_df['Splash_EV_Percentage'])
        
        with col2:
            st.markdown("**Market Distribution**")
            market_counts = filtered_df['Market'].value_counts()
            st.bar_chart(market_counts)

def main():
    """Main application function"""
    # Initialize session state
    init_session_state()
    
    # Main App Header
    st.markdown('<div class="main-header">', unsafe_allow_html=True)
    st.title("⚾ MLB EV Betting Opportunities")
    st.markdown("**Find profitable betting opportunities by comparing Splash Sports and sportsbook odds**")
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Check environment
    env_ok, env_msg = check_environment()
    if not env_ok:
        st.error(f"❌ Environment Error: {env_msg}")
        st.info("Please ensure GOOGLE_SERVICE_ACCOUNT_CREDENTIALS is set in your environment.")
        st.stop()
    
    # Display sidebar and get user inputs
    filters = display_sidebar()
    
    # Initialize EV calculator if not already done
    if st.session_state.ev_calculator is None:
        with st.spinner("🔧 Initializing EV Calculator..."):
            try:
                st.session_state.ev_calculator = EVCalculator()
            except Exception as e:
                st.error(f"❌ Failed to initialize EV Calculator: {e}")
                st.stop()
    
    # Display current metrics
    display_metrics(st.session_state.opportunities)
    
    # Data fetching logic
    should_refresh = (
        filters['refresh_button'] or 
        (filters['auto_refresh'] and 
         (st.session_state.last_refresh is None or 
          (datetime.now() - st.session_state.last_refresh).seconds > 300))
    )
    
    if should_refresh:
        with st.spinner("🔄 Fetching and analyzing latest data... This may take a few minutes"):
            try:
                opportunities = st.session_state.ev_calculator.run_full_analysis(
                    save_to_sheets=filters['save_to_sheets']
                )
                
                st.session_state.opportunities = opportunities
                st.session_state.last_refresh = datetime.now()
                
                if not opportunities.empty:
                    st.success(f"✅ Found {len(opportunities)} opportunities!")
                    st.rerun()  # Refresh the page to show new data
                else:
                    st.warning("⚠️ No opportunities found in current data")
                    
            except Exception as e:
                st.error(f"❌ Error during data fetch: {e}")
    
    # Apply filters and display results
    if not st.session_state.opportunities.empty:
        filtered_df = apply_filters(st.session_state.opportunities, filters)
        display_opportunities(filtered_df)
    else:
        st.markdown("---")
        st.info("👆 Click 'Refresh Data' to start finding betting opportunities")
        
        # Show some helpful tips
        st.markdown("""
        ### 💡 Tips for Using This Tool
        
        1. **Start Fresh**: Click the refresh button to load the latest data
        2. **Filter Smart**: Use the sidebar filters to narrow down opportunities
        3. **Check Multiple Markets**: Different prop types may have varying EV
        4. **Monitor Timing**: Odds change throughout the day - timing matters
        5. **Bankroll Management**: Never bet more than you can afford to lose
        6. **Verify Data**: Always double-check odds before placing bets
        """)
    
    # Auto-refresh logic
    if filters['auto_refresh'] and st.session_state.last_refresh:
        time_since_refresh = (datetime.now() - st.session_state.last_refresh).seconds
        if time_since_refresh >= 300:  # 5 minutes
            st.rerun()
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; padding: 1rem;">
        <p><strong>Data Sources:</strong> Splash Sports API • The Odds API</p>
        <p><small>⚠️ This tool is for educational purposes. Always verify odds before placing bets.</small></p>
        <p><small>🔄 Data is processed through Google Sheets for reliability and consistency.</small></p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
