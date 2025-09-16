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
    initial_sidebar_state="collapsed"
)

# Custom CSS inspired by Honda's clean design
st.markdown("""
<style>
    /* Hide default Streamlit elements */
    .stDeployButton {display:none;}
    footer {visibility: hidden;}
    .stDecoration {display:none;}
    
    /* Main container styling */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1200px;
    }
    
    /* Header styling similar to Honda */
    .main-header {
        text-align: left;
        padding: 2rem 0 3rem 0;
        border-bottom: 1px solid #e0e0e0;
        margin-bottom: 2rem;
    }
    
    .main-title {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        font-size: 3rem;
        font-weight: 300;
        color: #1a1a1a;
        margin: 0;
        line-height: 1.2;
    }
    
    .main-subtitle {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        font-size: 1.1rem;
        color: #666;
        margin-top: 0.5rem;
        font-weight: 400;
    }
    
    /* Top navigation tabs like Honda */
    .nav-tabs {
        display: flex;
        border-bottom: 1px solid #e0e0e0;
        margin-bottom: 2rem;
        gap: 0;
    }
    
    .nav-tab {
        padding: 1rem 2rem;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        font-size: 0.95rem;
        font-weight: 500;
        color: #666;
        border: none;
        background: none;
        cursor: pointer;
        border-bottom: 3px solid transparent;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        transition: all 0.3s ease;
    }
    
    .nav-tab:hover {
        color: #1a1a1a;
        border-bottom-color: #ccc;
    }
    
    .nav-tab.active {
        color: #1a1a1a;
        border-bottom-color: #1a1a1a;
    }
    
    /* Clean metrics styling */
    .metrics-container {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 2rem;
        margin: 2rem 0;
        padding: 2rem 0;
        border-bottom: 1px solid #f0f0f0;
    }
    
    .metric-item {
        text-align: center;
    }
    
    .metric-value {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        font-size: 2.5rem;
        font-weight: 300;
        color: #1a1a1a;
        margin: 0;
    }
    
    .metric-label {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        font-size: 0.9rem;
        color: #666;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-top: 0.5rem;
    }
    
    /* Minimal opportunity cards */
    .opportunity-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 1.5rem 0;
        border-bottom: 1px solid #f0f0f0;
        transition: background-color 0.2s ease;
    }
    
    .opportunity-item:hover {
        background-color: #fafafa;
        margin: 0 -1rem;
        padding: 1.5rem 1rem;
    }
    
    .opportunity-info h4 {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        font-size: 1.2rem;
        font-weight: 500;
        color: #1a1a1a;
        margin: 0 0 0.25rem 0;
    }
    
    .opportunity-info p {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        font-size: 0.9rem;
        color: #666;
        margin: 0;
    }
    
    .opportunity-ev {
        text-align: right;
    }
    
    .ev-value {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        font-size: 1.5rem;
        font-weight: 500;
        color: #1a1a1a;
        margin: 0;
    }
    
    .ev-details {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        font-size: 0.8rem;
        color: #666;
        margin-top: 0.25rem;
    }
    
    /* Status indicators */
    .status-bar {
        position: fixed;
        bottom: 1rem;
        left: 1rem;
        display: flex;
        align-items: center;
        gap: 1rem;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        font-size: 0.8rem;
        color: #666;
        background: rgba(255, 255, 255, 0.9);
        padding: 0.5rem 1rem;
        border-radius: 20px;
        backdrop-filter: blur(10px);
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    }
    
    .status-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        display: inline-block;
    }
    
    .status-green { background-color: #28a745; }
    .status-red { background-color: #dc3545; }
    
    /* Clean buttons */
    .refresh-button {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        background: #1a1a1a;
        color: white;
        border: none;
        padding: 0.75rem 2rem;
        font-size: 0.9rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        cursor: pointer;
        transition: background-color 0.3s ease;
        margin-bottom: 2rem;
    }
    
    .refresh-button:hover {
        background: #333;
    }
    
    /* Filters section */
    .filters-container {
        display: flex;
        gap: 2rem;
        align-items: center;
        margin-bottom: 2rem;
        padding: 1rem 0;
        border-bottom: 1px solid #f0f0f0;
    }
    
    .filter-item {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
    }
    
    .filter-label {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        font-size: 0.8rem;
        color: #666;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    /* Clean table styling */
    .dataframe {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif !important;
        border: none !important;
    }
    
    .dataframe th {
        background-color: #fafafa !important;
        font-weight: 500 !important;
        font-size: 0.8rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
        color: #666 !important;
        border: none !important;
        border-bottom: 1px solid #e0e0e0 !important;
    }
    
    .dataframe td {
        border: none !important;
        border-bottom: 1px solid #f0f0f0 !important;
        font-size: 0.9rem !important;
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
if 'active_tab' not in st.session_state:
    st.session_state.active_tab = 'opportunities'

class MLBBettingTool:
    def __init__(self, odds_api_key=None, google_creds_json=None):
        # Get from Streamlit secrets or environment variables
        if odds_api_key:
            self.odds_api_key = odds_api_key
        else:
            try:
                self.odds_api_key = st.secrets.get("ODDS_API_KEY") or os.environ.get('ODDS_API_KEY')
            except:
                self.odds_api_key = os.environ.get('ODDS_API_KEY')
        
        if google_creds_json:
            self.google_creds = json.loads(google_creds_json)
        else:
            try:
                creds_str = st.secrets.get("GOOGLE_SERVICE_ACCOUNT_CREDENTIALS") or os.environ.get('GOOGLE_SERVICE_ACCOUNT_CREDENTIALS', '{}')
                self.google_creds = json.loads(creds_str) if isinstance(creds_str, str) else creds_str
            except:
                self.google_creds = json.loads(os.environ.get('GOOGLE_SERVICE_ACCOUNT_CREDENTIALS', '{}'))
        
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
            with st.spinner("Loading Splash data..."):
                spreadsheet = client.open("MLB_Splash_Data")
                splash_worksheet = spreadsheet.worksheet("SPLASH_MLB")
                splash_data = splash_worksheet.get_all_records()
                splash_df = pd.DataFrame(splash_data)
            
            # Read Odds data
            with st.spinner("Loading Odds data..."):
                odds_worksheet = spreadsheet.worksheet("ODDS_API")
                odds_data = odds_worksheet.get_all_records()
                odds_df = pd.DataFrame(odds_data)
            
            if splash_df.empty or odds_df.empty:
                st.warning("One or both datasets are empty. Try refreshing the data first.")
                return pd.DataFrame()
            
            # Find matches and calculate EV
            with st.spinner("Calculating opportunities..."):
                opportunities = self.find_matches_and_calculate_ev(splash_df, odds_df)
            
            return opportunities
            
        except Exception as e:
            st.error(f"Error reading from Google Sheets: {e}")
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
            
        except Exception e:
            st.error(f"Error in analysis: {e}")
            return pd.DataFrame()

# Check credentials
def has_credentials():
    try:
        api_key = st.secrets.get("ODDS_API_KEY") or os.environ.get('ODDS_API_KEY')
        creds = st.secrets.get("GOOGLE_SERVICE_ACCOUNT_CREDENTIALS") or os.environ.get('GOOGLE_SERVICE_ACCOUNT_CREDENTIALS')
        return bool(api_key and creds)
    except:
        return bool(os.environ.get('ODDS_API_KEY') and os.environ.get('GOOGLE_SERVICE_ACCOUNT_CREDENTIALS'))

# Main Header
st.markdown('<div class="main-header">', unsafe_allow_html=True)
st.markdown('<h1 class="main-title">MLB EV Betting</h1>', unsafe_allow_html=True)
st.markdown('<p class="main-subtitle">Find profitable betting opportunities by comparing market odds</p>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# Navigation Tabs
st.markdown('''
<div class="nav-tabs">
    <div class="nav-tab active" onclick="setActiveTab('opportunities')">OPPORTUNITIES</div>
    <div class="nav-tab" onclick="setActiveTab('analytics')">ANALYTICS</div>
    <div class="nav-tab" onclick="setActiveTab('charts')">CHARTS</div>
</div>
''', unsafe_allow_html=True)

# Tab selection using buttons (since we can't use real JS)
col1, col2, col3, col4, col5 = st.columns([1,1,1,6,1])
with col1:
    if st.button("OPPORTUNITIES", key="tab1", help="View betting opportunities"):
        st.session_state.active_tab = 'opportunities'
with col2:
    if st.button("ANALYTICS", key="tab2", help="View detailed analytics"):
        st.session_state.active_tab = 'analytics'
with col3:
    if st.button("CHARTS", key="tab3", help="View charts and graphs"):
        st.session_state.active_tab = 'charts'

# Check credentials and show error if missing
if not has_credentials():
    st.error("Missing required credentials. Please ensure API keys are configured.")
    st.stop()

# Key Metrics
if not st.session_state.opportunities.empty:
    st.markdown('<div class="metrics-container">', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        last_update = st.session_state.last_refresh.strftime("%H:%M") if st.session_state.last_refresh else "Never"
        st.markdown(f'''
        <div class="metric-item">
            <div class="metric-value">{last_update}</div>
            <div class="metric-label">Last Updated</div>
        </div>
        ''', unsafe_allow_html=True)
    
    with col2:
        total_opps = len(st.session_state.opportunities)
        st.markdown(f'''
        <div class="metric-item">
            <div class="metric-value">{total_opps}</div>
            <div class="metric-label">Opportunities</div>
        </div>
        ''', unsafe_allow_html=True)
    
    with col3:
        avg_ev = st.session_state.opportunities['Splash_EV_Percentage'].mean()
        st.markdown(f'''
        <div class="metric-item">
            <div class="metric-value">{avg_ev:.1%}</div>
            <div class="metric-label">Average EV</div>
        </div>
        ''', unsafe_allow_html=True)
    
    with col4:
        best_ev = st.session_state.opportunities['Splash_EV_Percentage'].max()
        st.markdown(f'''
        <div class="metric-item">
            <div class="metric-value">{best_ev:.1%}</div>
            <div class="metric-label">Best EV</div>
        </div>
        ''', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

# Filters
st.markdown('<div class="filters-container">', unsafe_allow_html=True)
col1, col2, col3, col4 = st.columns([2, 2, 2, 4])

with col1:
    min_ev = st.slider("MIN EV %", 0.0, 20.0, 1.0, 0.1, label_visibility="visible")

with col2:
    market_filter = st.selectbox("MARKET", ["All Markets"] + [
        'pitcher_strikeouts', 'pitcher_hits_allowed', 'pitcher_outs',
        'pitcher_earned_runs', 'batter_total_bases', 'batter_hits',
        'batter_runs_scored', 'batter_rbis', 'batter_singles'
    ], label_visibility="visible")

with col3:
    min_books = st.slider("MIN BOOKS", 1, 10, 3, label_visibility="visible")

with col4:
    if st.button("REFRESH DATA", key="refresh", help="Load latest data"):
        with st.spinner("Loading data..."):
            try:
                tool = MLBBettingTool()
                opportunities = tool.run_full_analysis()
                
                st.session_state.opportunities = opportunities
                st.session_state.last_refresh = datetime.now()
                
                if not opportunities.empty:
                    st.success(f"Found {len(opportunities)} opportunities")
                else:
                    st.warning("No opportunities found")
                    
            except Exception as e:
                st.error(f"Error loading data: {e}")

st.markdown('</div>', unsafe_allow_html=True)

# Display content based on active tab
if st.session_state.active_tab == 'opportunities':
    if not st.session_state.opportunities.empty:
        # Apply filters
        filtered_df = st.session_state.opportunities.copy()
        filtered_df = filtered_df[filtered_df['Splash_EV_Percentage'] >= (min_ev/100)]
        
        if market_filter != "All Markets":
            filtered_df = filtered_df[filtered_df['Market'] == market_filter]
        
        filtered_df = filtered_df[filtered_df['Num_Books_Used'] >= min_books]
        
        if not filtered_df.empty:
            # Display opportunities as clean list
            for idx, row in filtered_df.head(15).iterrows():
                st.markdown(f'''
                <div class="opportunity-item">
                    <div class="opportunity-info">
                        <h4>{row['Player']}</h4>
                        <p>{row['Market']} • {row['Bet_Type'].title()} {row['Line']} • {row['Best_Sportsbook']} ({row['Best_Odds']:+d})</p>
                    </div>
                    <div class="opportunity-ev">
                        <div class="ev-value">{row['Splash_EV_Percentage']:.2%}</div>
                        <div class="ev-details">${row['Splash_EV_Dollars_Per_100']:.2f} per $100</div>
                    </div>
                </div>
                ''', unsafe_allow_html=True)
        else:
            st.write("No opportunities match current filters.")
    else:
        st.write("Click 'REFRESH DATA' to load opportunities.")

elif st.session_state.active_tab == 'analytics':
    if not st.session_state.opportunities.empty:
        # Apply same filters
        filtered_df = st.session_state.opportunities.copy()
        filtered_df = filtered_df[filtered_df['Splash_EV_Percentage'] >= (min_ev/100)]
        
        if market_filter != "All Markets":
            filtered_df = filtered_df[filtered_df['Market'] == market_filter]
        
        filtered_df = filtered_df[filtered_df['Num_Books_Used'] >= min_books]
        
        if not filtered_df.empty:
            # Clean table display
            display_df = filtered_df.copy()
            display_df['True_Prob'] = display_df['True_Prob'].apply(lambda x: f"{x:.1%}")
            display_df['Splash_EV_Percentage'] = display_df['Splash_EV_Percentage'].apply(lambda x: f"{x:.2%}")
            display_df['Splash_EV_Dollars_Per_100'] = display_df['Splash_EV_Dollars_Per_100'].apply(lambda x: f"${x:.2f}")
            
            st.dataframe(display_df, use_container_width=True, height=600)
        else:
            st.write("No data matches current filters.")
    else:
        st.write("No data available.")

elif st.session_state.active_tab == 'charts':
    if not st.session_state.opportunities.empty:
        # Apply same filters
        filtered_df = st.session_state.opportunities.copy()
        filtered_df = filtered_df[filtered_df['Splash_EV_Percentage'] >= (min_ev/100)]
        
        if market_filter != "All Markets":
            filtered_df = filtered_df[filtered_df['Market'] == market_filter]
        
        filtered_df = filtered_df[filtered_df['Num_Books_Used'] >= min_books]
        
        if not filtered_df.empty:
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("EV Distribution")
                st.bar_chart(filtered_df['Splash_EV_Percentage'])
            
            with col2:
                st.subheader("Market Breakdown")
                market_counts = filtered_df['Market'].value_counts()
                st.bar_chart(market_counts)
        else:
            st.write("No data matches current filters.")
    else:
        st.write("No data available.")

# Status bar at bottom left
try:
    api_status = "status-green" if (st.secrets.get("ODDS_API_KEY") or os.environ.get('ODDS_API_KEY')) else "status-red"
    creds_status = "status-green" if (st.secrets.get("GOOGLE_SERVICE_ACCOUNT_CREDENTIALS") or os.environ.get('GOOGLE_SERVICE_ACCOUNT_CREDENTIALS')) else "status-red"
except:
    api_status = "status-green" if os.environ.get('ODDS_API_KEY') else "status-red"
    creds_status = "status-green" if os.environ.get('GOOGLE_SERVICE_ACCOUNT_CREDENTIALS') else "status-red"

st.markdown(f'''
<div class="status-bar">
    <div style="display: flex; align-items: center; gap: 0.5rem;">
        <div class="status-dot {api_status}"></div>
        <span>Odds API</span>
    </div>
    <div style="display: flex; align-items: center; gap: 0.5rem;">
        <div class="status-dot {creds_status}"></div>
        <span>Google Sheets</span>
    </div>
</div>
''', unsafe_allow_html=True)
