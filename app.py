import streamlit as st
import requests
import json
import pandas as pd
from datetime import datetime
import gspread
from gspread_dataframe import set_with_dataframe
from google.oauth2.service_account import Credentials
import time
import numpy as np
import os

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
    
    .status-indicator {
        display: inline-block;
        width: 12px;
        height: 12px;
        border-radius: 50%;
        margin-right: 8px;
    }
    
    .status-green { background-color: #28a745; }
    .status-yellow { background-color: #ffc107; }
    .status-red { background-color: #dc3545; }
    
    .filter-section {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = None
if 'opportunities' not in st.session_state:
    st.session_state.opportunities = pd.DataFrame()
if 'is_loading' not in st.session_state:
    st.session_state.is_loading = False

class MLBBettingTool:
    def __init__(self, odds_api_key=None, google_creds_json=None):
        # Get from environment variables if not provided
        self.odds_api_key = odds_api_key or os.environ.get('ODDS_API_KEY')
        self.google_creds = json.loads(google_creds_json) if google_creds_json else json.loads(os.environ.get('GOOGLE_SERVICE_ACCOUNT_CREDENTIALS', '{}'))
        self.api_call_count = 0
        
        # Markets and books from your original code
        self.MARKETS = [
            'pitcher_strikeouts', 'pitcher_hits_allowed', 'pitcher_outs',
            'pitcher_earned_runs', 'batter_total_bases', 'batter_hits',
            'batter_runs_scored', 'batter_rbis', 'batter_singles'
        ]
        
        self.BOOKS = [
            'fanduel', 'draftkings', 'betmgm', 'caesars', 'pointsbetus','betrivers',
            'unibet', 'bovada', 'mybookieag', 'betus', 'william_us', 'fanatics', 'lowvig'
        ]
        
        # Market mapping
        self.market_mapping = {
            'strikeouts': 'pitcher_strikeouts',
            'earned_runs': 'pitcher_earned_runs',
            'hits': 'batter_hits',
            'hits_allowed': 'pitcher_hits_allowed',
            'hits_plus_runs_plus_RBIs': 'hits_plus_runs_plus_RBIs',
            'runs': 'batter_runs_scored',
            'batter_singles': 'batter_singles',
            'total_bases': 'batter_total_bases',
            'RBIs': 'batter_rbis',
            'total_outs': 'pitcher_outs'
        }

    def read_data_from_sheets(self):
        """Read data from Google Sheets instead of APIs"""
        try:
            # Setup Google Sheets connection
            scopes = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
            
            credentials = Credentials.from_service_account_info(
                self.google_creds, scopes=scopes)
            client = gspread.authorize(credentials)
            
            # Read Splash data
            with st.spinner("📊 Reading Splash data from Google Sheets..."):
                spreadsheet = client.open("MLB_Splash_Data")
                splash_worksheet = spreadsheet.worksheet("SPLASH_MLB")
                splash_data = splash_worksheet.get_all_records()
                splash_df = pd.DataFrame(splash_data)
            
            # Read Odds data
            with st.spinner("🎲 Reading Odds data from Google Sheets..."):
                odds_worksheet = spreadsheet.worksheet("ODDS_API")
                odds_data = odds_worksheet.get_all_records()
                odds_df = pd.DataFrame(odds_data)
            
            if splash_df.empty or odds_df.empty:
                st.warning("⚠️ One or both datasets are empty. Try refreshing the data first.")
                return pd.DataFrame()
            
            # Find matches and calculate EV
            with st.spinner("🔍 Finding matches and calculating EV..."):
                opportunities = self.find_matches_and_calculate_ev(splash_df, odds_df)
            
            return opportunities
            
        except Exception as e:
            st.error(f"❌ Error reading from Google Sheets: {e}")
            return pd.DataFrame()

    def find_matches_and_calculate_ev(self, splash_df, odds_df):
        """Find matches and calculate EV opportunities"""
        if splash_df.empty or odds_df.empty:
            return pd.DataFrame()
        
        # Add bet_type column to odds_df
        def extract_bet_info(line_str):
            line_str = str(line_str).strip()
            if line_str.lower().startswith('over '):
                return 'over', line_str.lower().replace('over ', '')
            elif line_str.lower().startswith('under '):
                return 'under', line_str.lower().replace('under ', '')
            else:
                return 'unknown', line_str

        odds_df['bet_type'] = odds_df['Line'].apply(lambda x: extract_bet_info(x)[0])
        odds_df['Line'] = odds_df['Line'].apply(lambda x: extract_bet_info(x)[1])
        
        # Map markets
        reverse_mapping = {v: k for k, v in self.market_mapping.items()}
        odds_df['mapped_market'] = odds_df['Market'].map(reverse_mapping)
        
        # Convert to same type
        splash_df['Line'] = splash_df['Line'].astype(str)
        odds_df['Line'] = odds_df['Line'].astype(str)
        
        # Find matches
        matching_rows = []
        for _, splash_row in splash_df.iterrows():
            matches = odds_df[
                (odds_df['Name'] == splash_row['Name']) &
                (odds_df['mapped_market'] == splash_row['Market']) &
                (odds_df['Line'] == splash_row['Line'])
            ]
            if not matches.empty:
                matching_rows.append(matches)
        
        if not matching_rows:
            return pd.DataFrame()
        
        df_matching = pd.concat(matching_rows, ignore_index=True)
        df_matching = df_matching.drop('mapped_market', axis=1)
        
        # Calculate EV
        return self.calculate_splash_sports_ev(df_matching)

    def american_to_implied_prob(self, odds):
        """Convert American odds to implied probability"""
        if odds > 0:
            return 100 / (odds + 100)
        else:
            return abs(odds) / (abs(odds) + 100)

    def calculate_splash_sports_ev(self, df, min_books=3, min_true_prob=0.50, ev_threshold=0.01):
        """Calculate EV for Splash Sports PvP betting"""
        if df.empty:
            return pd.DataFrame()
        
        df = df.copy()
        df['Odds'] = pd.to_numeric(df['Odds'], errors='coerce')
        df = df[(df['Odds'] >= -2000) & (df['Odds'] <= 2000)]
        df = df.drop_duplicates(subset=['Name', 'Market', 'Line', 'Book', 'bet_type'], keep='first')
        df['Implied_Prob'] = df['Odds'].apply(self.american_to_implied_prob)
        
        results = []
        grouped = df.groupby(['Name', 'Market', 'Line', 'bet_type'])
        
        for (player, market, line, bet_type), group in grouped:
            if len(group) < min_books:
                continue
            
            avg_implied_prob = group['Implied_Prob'].mean()
            true_prob = avg_implied_prob * 0.95  # Remove vig
            true_prob = max(0.01, min(0.99, true_prob))
            
            if true_prob < min_true_prob:
                continue
            
            splash_ev_dollars = 100 * (true_prob - 0.50)
            splash_ev_percentage = splash_ev_dollars / 100
            
            if splash_ev_percentage > ev_threshold:
                results.append({
                    'Player': player,
                    'Market': market,
                    'Line': line,
                    'Bet_Type': bet_type,
                    'True_Prob': true_prob,
                    'Splash_EV_Percentage': splash_ev_percentage,
                    'Splash_EV_Dollars_Per_100': splash_ev_dollars,
                    'Num_Books_Used': len(group),
                    'Best_Sportsbook': group.loc[group['Odds'].idxmax(), 'Book'] if any(group['Odds'] > 0) else group.loc[group['Odds'].idxmin(), 'Book'],
                    'Best_Odds': group['Odds'].max() if any(group['Odds'] > 0) else group['Odds'].min()
                })
        
        if results:
            ev_df = pd.DataFrame(results)
            ev_df = ev_df.sort_values('Splash_EV_Percentage', ascending=False)
            return ev_df
        else:
            return pd.DataFrame()

    def run_full_analysis(self):
        """Run the complete analysis pipeline using Google Sheets data"""
        try:
            opportunities = self.read_data_from_sheets()
            return opportunities
            
        except Exception as e:
            st.error(f"❌ Error in analysis: {e}")
            import traceback
            st.error(f"Full traceback: {traceback.format_exc()}")
            return pd.DataFrame()

# Main App Header
st.markdown('<div class="main-header">', unsafe_allow_html=True)
st.title("⚾ MLB EV Betting Opportunities")
st.markdown("**Find profitable betting opportunities by comparing Splash Sports and sportsbook odds**")
st.markdown('</div>', unsafe_allow_html=True)

# Sidebar Configuration
with st.sidebar:
    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.markdown("### ⚙️ Configuration")
    
    # Status indicators
    api_key_status = "✅" if os.environ.get('ODDS_API_KEY') else "❌"
    creds_status = "✅" if os.environ.get('GOOGLE_SERVICE_ACCOUNT_CREDENTIALS') else "❌"
    
    st.markdown(f"""
    **Environment Status:**
    - {api_key_status} Odds API Key
    - {creds_status} Google Credentials
    """)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Filters Section
    st.markdown('<div class="filter-section">', unsafe_allow_html=True)
    st.markdown("### 🎛️ Filters")
    
    min_ev = st.slider("Minimum EV %", 0.0, 20.0, 1.0, 0.1, help="Only show opportunities above this EV threshold")
    
    market_filter = st.selectbox("Market Filter", ["All Markets"] + [
        'pitcher_strikeouts', 'pitcher_hits_allowed', 'pitcher_outs',
        'pitcher_earned_runs', 'batter_total_bases', 'batter_hits',
        'batter_runs_scored', 'batter_rbis', 'batter_singles'
    ], help="Filter by specific market type")
    
    min_books = st.slider("Minimum Books", 1, 10, 3, help="Minimum number of sportsbooks required for analysis")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Actions Section
    st.markdown("### 🔄 Actions")
    
    col1, col2 = st.columns(2)
    with col1:
        refresh_button = st.button("🔄 Refresh Data", type="primary", use_container_width=True)
    with col2:
        auto_refresh = st.checkbox("Auto-refresh", help="Refresh every 5 minutes")
    
    # Info Section
    st.markdown("---")
    st.markdown("### ℹ️ About")
    st.markdown("""
    This tool finds profitable betting opportunities by:
    1. 📊 Comparing Splash Sports fair odds
    2. 🎲 Against multiple sportsbooks
    3. 📈 Calculating expected value (EV)
    4. 🎯 Highlighting best opportunities
    """)

# Main Dashboard
if not os.environ.get('ODDS_API_KEY') or not os.environ.get('GOOGLE_SERVICE_ACCOUNT_CREDENTIALS'):
    st.error("❌ Missing required environment variables. Please ensure ODDS_API_KEY and GOOGLE_SERVICE_ACCOUNT_CREDENTIALS are set in your repository secrets.")
    st.stop()

# Key Metrics Row
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
    total_opps = len(st.session_state.opportunities)
    st.markdown(f'''
    <div class="metric-container">
        <h4>🎯 Opportunities</h4>
        <h2>{total_opps}</h2>
    </div>
    ''', unsafe_allow_html=True)

with col3:
    if not st.session_state.opportunities.empty:
        avg_ev = st.session_state.opportunities['Splash_EV_Percentage'].mean()
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
    if not st.session_state.opportunities.empty:
        best_ev = st.session_state.opportunities['Splash_EV_Percentage'].max()
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

# Data fetching logic
if refresh_button or (auto_refresh and (st.session_state.last_refresh is None or 
    (datetime.now() - st.session_state.last_refresh).seconds > 300)):
    
    with st.spinner("🔄 Fetching latest data... This may take a few minutes"):
        try:
            tool = MLBBettingTool()
            opportunities = tool.run_full_analysis()
            
            st.session_state.opportunities = opportunities
            st.session_state.last_refresh = datetime.now()
            
            if not opportunities.empty:
                st.success(f"✅ Found {len(opportunities)} opportunities!")
            else:
                st.warning("⚠️ No opportunities found in current data")
                
        except Exception as e:
            st.error(f"❌ Error during data fetch: {e}")

# Display Results
if not st.session_state.opportunities.empty:
    # Apply filters
    filtered_df = st.session_state.opportunities.copy()
    
    # EV filter
    filtered_df = filtered_df[filtered_df['Splash_EV_Percentage'] >= (min_ev/100)]
    
    # Market filter
    if market_filter != "All Markets":
        filtered_df = filtered_df[filtered_df['Market'] == market_filter]
    
    # Books filter
    filtered_df = filtered_df[filtered_df['Num_Books_Used'] >= min_books]
    
    if not filtered_df.empty:
        st.markdown("---")
        st.subheader(f"🎯 {len(filtered_df)} Opportunities Found")
        
        # Create tabs for different views
        tab1, tab2, tab3 = st.tabs(["🎲 Opportunities", "📊 Analytics", "📈 Charts"])
        
        with tab1:
            # Display opportunities in cards
            for idx, row in filtered_df.head(10).iterrows():
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
                
                st.markdown(f'''
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
                ''', unsafe_allow_html=True)
            
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
    
    else:
        st.warning("⚠️ No opportunities match your current filters. Try adjusting the filter criteria.")

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
    """)

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 1rem;">
    <p><strong>Data Sources:</strong> Splash Sports API • The Odds API • ESPN API</p>
    <p><small>⚠️ This tool is for educational purposes. Always verify odds before placing bets.</small></p>
</div>
""", unsafe_allow_html=True)

# Auto-refresh logic
if auto_refresh and st.session_state.last_refresh:
    time_since_refresh = (datetime.now() - st.session_state.last_refresh).seconds
    if time_since_refresh >= 300:  # 5 minutes
        st.rerun()
