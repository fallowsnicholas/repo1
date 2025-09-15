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

# Page configuration
st.set_page_config(
    page_title="MLB EV Betting Tool",
    page_icon="⚾",
    layout="wide"
)

# Initialize session state
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = None
if 'opportunities' not in st.session_state:
    st.session_state.opportunities = pd.DataFrame()
if 'is_loading' not in st.session_state:
    st.session_state.is_loading = False

class MLBBettingTool:
    def __init__(self, odds_api_key, google_creds_json):
        self.odds_api_key = odds_api_key
        self.google_creds = json.loads(google_creds_json)
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

    def fetch_splash_data(self):
        """Fetch data from Splash Sports API"""
        url = "https://api.splashsports.com/props-service/api/props"
        params = {'limit': 1000, 'offset': 0, 'league': 'mlb'}
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Connection': 'keep-alive',
            'Referer': 'https://app.splashsports.com/',
            'Origin': 'https://app.splashsports.com',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site'
        }
        
        try:
            response = requests.get(url, params=params, headers=headers, timeout=30)
            if response.status_code == 200:
                data = response.json()
                props_list = data.get('data', [])
                mlb_props = [prop for prop in props_list if prop.get('league') == 'mlb']
                
                extracted_data = []
                for prop in mlb_props:
                    extracted_data.append({
                        'Name': prop.get('entity_name'),
                        'Market': prop.get('type'),
                        'Line': prop.get('line')
                    })
                
                return pd.DataFrame(extracted_data)
        except Exception as e:
            st.error(f"Error fetching Splash data: {e}")
            return pd.DataFrame()
    
    def get_todays_games_from_espn(self):
        """Get today's MLB games from ESPN API"""
        try:
            today = datetime.now().strftime('%Y%m%d')
            url = "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard"
            params = {'dates': today, 'limit': 50}
            
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            games = []
            if 'events' in data and data['events']:
                for event in data['events']:
                    try:
                        competition = event.get('competitions', [{}])[0]
                        competitors = competition.get('competitors', [])
                        
                        if len(competitors) >= 2:
                            home_team = None
                            away_team = None
                            
                            for competitor in competitors:
                                team = competitor.get('team', {})
                                team_name = team.get('displayName', '')
                                
                                if competitor.get('homeAway') == 'home':
                                    home_team = team_name
                                elif competitor.get('homeAway') == 'away':
                                    away_team = team_name
                            
                            if home_team and away_team:
                                game_info = {
                                    'espn_id': event.get('id'),
                                    'home_team': home_team,
                                    'away_team': away_team,
                                    'date': event.get('date'),
                                    'status': event.get('status', {}).get('type', {}).get('name', 'Unknown')
                                }
                                games.append(game_info)
                    except Exception:
                        continue
            
            active_games = [g for g in games if g['status'] in ['STATUS_SCHEDULED', 'STATUS_INPROGRESS']]
            return active_games
            
        except Exception as e:
            st.error(f"Error fetching ESPN games: {e}")
            return []

    def fetch_odds_data(self):
        """Fetch odds data using your existing logic"""
        try:
            espn_games = self.get_todays_games_from_espn()
            if not espn_games:
                st.warning("No games found from ESPN today")
                return pd.DataFrame()
            
            st.info(f"Found {len(espn_games)} games from ESPN")
            
            # Get all odds games for mapping
            odds_url = "https://api.the-odds-api.com/v4/sports/baseball_mlb/events"
            params = {
                'apiKey': self.odds_api_key,
                'regions': 'us',
                'markets': 'h2h',
                'oddsFormat': 'american'
            }
            
            response = requests.get(odds_url, params=params, timeout=15)
            if response.status_code != 200:
                st.error(f"Odds API error: {response.status_code}")
                return pd.DataFrame()
                
            odds_games = response.json()
            if not odds_games:
                st.warning("No odds games returned from API")
                return pd.DataFrame()
            
            st.info(f"Found {len(odds_games)} odds games")
            
            # Map ESPN to Odds API games
            matched_games = self.map_espn_to_odds_api(espn_games, odds_games)
            if not matched_games:
                st.warning("No games could be matched between ESPN and Odds API")
                return pd.DataFrame()
            
            st.info(f"Matched {len(matched_games)} games")
            
            # Fetch player props for matched games
            all_odds = []
            for i, game in enumerate(matched_games[:3]):  # Limit to first 3 games for testing
                game_id = game['id']
                st.info(f"Fetching props for game {i+1}/{len(matched_games[:3])}: {game['away_team']} @ {game['home_team']}")
                
                for market in self.MARKETS[:2]:  # Limit to first 2 markets for testing
                    props_data = self.get_player_props(game_id, market)
                    if props_data and props_data.get('bookmakers'):
                        for bookmaker in props_data['bookmakers']:
                            if bookmaker['key'] in self.BOOKS:
                                for market_data in bookmaker.get('markets', []):
                                    for outcome in market_data.get('outcomes', []):
                                        player_name = outcome.get('description', outcome.get('name', ''))
                                        selection = outcome.get('name', '')
                                        point = outcome.get('point', 0)
                                        odds = outcome.get('price', 0)
                                        
                                        if (player_name and 
                                            player_name not in ['Over', 'Under'] and
                                            selection in ['Over', 'Under'] and
                                            point and odds):
                                            
                                            all_odds.append({
                                                'Name': player_name.strip(),
                                                'Market': market,
                                                'Line': f"{selection} {point}",
                                                'Odds': f"{odds:+d}",
                                                'Book': bookmaker['title'],
                                                'Game': f"{game['away_team']} @ {game['home_team']}", 
                                                'Game_ID': game_id
                                            })
                    
                    time.sleep(0.2)  # Rate limiting
                
                time.sleep(0.5)  # Rate limiting between games
            
            st.success(f"Collected {len(all_odds)} total player props")
            return pd.DataFrame(all_odds)
            
        except Exception as e:
            st.error(f"Error in fetch_odds_data: {e}")
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

    def map_espn_to_odds_api(self, espn_games, odds_games):
        """Map ESPN games to Odds API game IDs"""
        team_mapping = {
            'Arizona Diamondbacks': ['Arizona Diamondbacks', 'Diamondbacks'],
            'Atlanta Braves': ['Atlanta Braves', 'Braves'],
            'Baltimore Orioles': ['Baltimore Orioles', 'Orioles'],
            'Boston Red Sox': ['Boston Red Sox', 'Red Sox'],
            'Chicago Cubs': ['Chicago Cubs', 'Cubs'],
            'Chicago White Sox': ['Chicago White Sox', 'White Sox'],
            'Cincinnati Reds': ['Cincinnati Reds', 'Reds'],
            'Cleveland Guardians': ['Cleveland Guardians', 'Guardians'],
            'Colorado Rockies': ['Colorado Rockies', 'Rockies'],
            'Detroit Tigers': ['Detroit Tigers', 'Tigers'],
            'Houston Astros': ['Houston Astros', 'Astros'],
            'Kansas City Royals': ['Kansas City Royals', 'Royals'],
            'Los Angeles Angels': ['Los Angeles Angels', 'LA Angels', 'Angels'],
            'Los Angeles Dodgers': ['Los Angeles Dodgers', 'LA Dodgers', 'Dodgers'],
            'Miami Marlins': ['Miami Marlins', 'Marlins'],
            'Milwaukee Brewers': ['Milwaukee Brewers', 'Brewers'],
            'Minnesota Twins': ['Minnesota Twins', 'Twins'],
            'New York Mets': ['New York Mets', 'NY Mets', 'Mets'],
            'New York Yankees': ['New York Yankees', 'NY Yankees', 'Yankees'],
            'Oakland Athletics': ['Oakland Athletics', 'Oakland A\'s', 'Athletics', 'A\'s'],
            'Philadelphia Phillies': ['Philadelphia Phillies', 'Phillies'],
            'Pittsburgh Pirates': ['Pittsburgh Pirates', 'Pirates'],
            'San Diego Padres': ['San Diego Padres', 'Padres'],
            'San Francisco Giants': ['San Francisco Giants', 'SF Giants', 'Giants'],
            'Seattle Mariners': ['Seattle Mariners', 'Mariners'],
            'St. Louis Cardinals': ['St. Louis Cardinals', 'St Louis Cardinals', 'Cardinals'],
            'Tampa Bay Rays': ['Tampa Bay Rays', 'Rays'],
            'Texas Rangers': ['Texas Rangers', 'Rangers'],
            'Toronto Blue Jays': ['Toronto Blue Jays', 'Blue Jays'],
            'Washington Nationals': ['Washington Nationals', 'Nationals']
        }

        def normalize_team_name(name):
            return name.lower().strip().replace('.', '').replace('\'', '')

        def find_team_match(name1, name2):
            norm1 = normalize_team_name(name1)
            norm2 = normalize_team_name(name2)

            if norm1 == norm2:
                return True

            for canonical, variations in team_mapping.items():
                canonical_norm = normalize_team_name(canonical)
                all_norms = {normalize_team_name(v) for v in variations} | {canonical_norm}

                if norm1 in all_norms and norm2 in all_norms:
                    return True

            return False

        matched_games = []
        for espn_game in espn_games:
            espn_home = espn_game['home_team']
            espn_away = espn_game['away_team']

            for odds_game in odds_games:
                odds_home = odds_game.get('home_team', '')
                odds_away = odds_game.get('away_team', '')

                if (find_team_match(espn_home, odds_home) and
                    find_team_match(espn_away, odds_away)):

                    matched_game = {
                        'id': odds_game['id'],
                        'home_team': odds_game['home_team'],
                        'away_team': odds_game['away_team'],
                        'commence_time': odds_game.get('commence_time'),
                        'espn_info': espn_game
                    }
                    matched_games.append(matched_game)
                    break

        return matched_games

    def get_player_props(self, game_id, market):
        """Get player props for a specific game and market"""
        endpoint = f"https://api.the-odds-api.com/v4/sports/baseball_mlb/events/{game_id}/odds"
        params = {
            'apiKey': self.odds_api_key,
            'regions': 'us',
            'markets': market,
            'oddsFormat': 'american'
        }
        
        try:
            response = requests.get(endpoint, params=params, timeout=15)
            if response.status_code == 200:
                return response.json()
            else:
                return None
        except Exception:
            return None
        """Run the complete analysis pipeline"""
        try:
            # Step 1: Fetch Splash data
            splash_df = self.fetch_splash_data()
            
            # Step 2: Fetch Odds data  
            odds_df = self.fetch_odds_data()
            
            # Step 3: Find matches and calculate EV
            opportunities = self.find_matches_and_calculate_ev(splash_df, odds_df)
            
            return opportunities
            
        except Exception as e:
            st.error(f"Error in analysis: {e}")
            return pd.DataFrame()

    def run_full_analysis(self):
        """Run the complete analysis pipeline"""
        try:
            # Step 1: Fetch Splash data
            st.info("Step 1: Fetching Splash Sports data...")
            splash_df = self.fetch_splash_data()
            if splash_df is None or splash_df.empty:
                st.error("No Splash Sports data retrieved")
                return pd.DataFrame()
            st.success(f"Splash data: {len(splash_df)} records")
            
            # Step 2: Fetch Odds data  
            st.info("Step 2: Fetching Odds API data...")
            odds_df = self.fetch_odds_data()
            if odds_df is None or odds_df.empty:
                st.error("No Odds API data retrieved")
                return pd.DataFrame()
            st.success(f"Odds data: {len(odds_df)} records")
            
            # Step 3: Find matches and calculate EV
            st.info("Step 3: Finding matches and calculating EV...")
            opportunities = self.find_matches_and_calculate_ev(splash_df, odds_df)
            if opportunities is None:
                opportunities = pd.DataFrame()
            
            return opportunities
            
        except Exception as e:
            st.error(f"Error in analysis: {e}")
            import traceback
            st.error(f"Full traceback: {traceback.format_exc()}")
            return pd.DataFrame()

# Streamlit UI
st.title("⚾ MLB EV Betting Opportunities")
st.markdown("Find profitable betting opportunities by comparing Splash Sports and sportsbook odds")

# Sidebar for configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # API Keys
    odds_api_key = st.text_input("Odds API Key", type="password", help="Your Odds API key")
    google_creds = st.text_area("Google Credentials JSON", help="Paste your Google Service Account JSON here")
    
    st.header("🎛️ Filters")
    min_ev = st.slider("Minimum EV %", 0.0, 20.0, 1.0, 0.1)
    market_filter = st.selectbox("Market Filter", ["All"] + [
        'pitcher_strikeouts', 'pitcher_hits_allowed', 'pitcher_outs',
        'pitcher_earned_runs', 'batter_total_bases', 'batter_hits',
        'batter_runs_scored', 'batter_rbis', 'batter_singles'
    ])
    
    st.header("🔄 Actions")
    refresh_button = st.button("🔄 Refresh Data", type="primary")
    auto_refresh = st.checkbox("Auto-refresh (5 min)")

# Main content
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Last Updated", 
              st.session_state.last_refresh.strftime("%H:%M:%S") if st.session_state.last_refresh else "Never")

with col2:
    st.metric("Total Opportunities", len(st.session_state.opportunities))

with col3:
    if not st.session_state.opportunities.empty:
        avg_ev = st.session_state.opportunities['Splash_EV_Percentage'].mean()
        st.metric("Average EV", f"{avg_ev:.2%}")

# Data fetching logic
if refresh_button or (auto_refresh and (st.session_state.last_refresh is None or 
    (datetime.now() - st.session_state.last_refresh).seconds > 300)):
    
    if not odds_api_key or not google_creds:
        st.error("Please provide both Odds API Key and Google Credentials in the sidebar")
    else:
        with st.spinner("Fetching latest data... This may take a few minutes"):
            try:
                tool = MLBBettingTool(odds_api_key, google_creds)
                opportunities = tool.run_full_analysis()
                
                st.session_state.opportunities = opportunities
                st.session_state.last_refresh = datetime.now()
                
                if not opportunities.empty:
                    st.success(f"Found {len(opportunities)} opportunities!")
                else:
                    st.warning("No opportunities found in current data")
                    
            except Exception as e:
                st.error(f"Error during data fetch: {e}")

# Display results
if not st.session_state.opportunities.empty:
    # Apply filters
    filtered_df = st.session_state.opportunities.copy()
    
    # EV filter
    filtered_df = filtered_df[filtered_df['Splash_EV_Percentage'] >= (min_ev/100)]
    
    # Market filter
    if market_filter != "All":
        filtered_df = filtered_df[filtered_df['Market'] == market_filter]
    
    if not filtered_df.empty:
        st.subheader(f"🎯 {len(filtered_df)} Opportunities Found")
        
        # Format the dataframe for display
        display_df = filtered_df.copy()
        display_df['True_Prob'] = display_df['True_Prob'].apply(lambda x: f"{x:.1%}")
        display_df['Splash_EV_Percentage'] = display_df['Splash_EV_Percentage'].apply(lambda x: f"{x:.2%}")
        display_df['Splash_EV_Dollars_Per_100'] = display_df['Splash_EV_Dollars_Per_100'].apply(lambda x: f"${x:.2f}")
        
        # Display with column configuration
        st.dataframe(
            display_df,
            use_container_width=True,
            column_config={
                "Splash_EV_Percentage": st.column_config.TextColumn("EV %"),
                "Splash_EV_Dollars_Per_100": st.column_config.TextColumn("EV per $100"),
                "True_Prob": st.column_config.TextColumn("Win Prob"),
                "Best_Odds": st.column_config.TextColumn("Best Odds")
            }
        )
        
        # Summary statistics
        st.subheader("📊 Summary Statistics")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            best_ev = filtered_df['Splash_EV_Percentage'].max()
            st.metric("Best EV", f"{best_ev:.2%}")
        
        with col2:
            avg_prob = filtered_df['True_Prob'].mean()
            st.metric("Avg Win Prob", f"{avg_prob:.1%}")
        
        with col3:
            total_books = filtered_df['Num_Books_Used'].sum()
            st.metric("Total Books Used", total_books)
        
        with col4:
            unique_players = filtered_df['Player'].nunique()
            st.metric("Unique Players", unique_players)
        
        # Market breakdown
        st.subheader("📈 Market Breakdown")
        market_summary = filtered_df.groupby('Market').agg({
            'Splash_EV_Percentage': ['count', 'mean']
        }).round(3)
        market_summary.columns = ['Count', 'Avg EV']
        market_summary['Avg EV'] = market_summary['Avg EV'].apply(lambda x: f"{x:.2%}")
        st.dataframe(market_summary)
        
    else:
        st.warning("No opportunities match your current filters")

else:
    st.info("👆 Click 'Refresh Data' to start finding betting opportunities")

# Footer
st.markdown("---")
st.markdown("*Data sources: Splash Sports API, The Odds API, ESPN API*")

# Auto-refresh logic
if auto_refresh and st.session_state.last_refresh:
    time_since_refresh = (datetime.now() - st.session_state.last_refresh).seconds
    if time_since_refresh < 300:  # Less than 5 minutes
        st.rerun()
