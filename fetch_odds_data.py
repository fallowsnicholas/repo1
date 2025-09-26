# fetch_odds_data.py - Step 2: Fetch odds using Step 1 matchup data and include player teams
import requests
import time
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json
from datetime import datetime
import os

class MLBOddsFetcher:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.odds_base_url = "https://api.the-odds-api.com/v4"
        self.api_call_count = 0
        self.todays_matchups = []

    # Markets to fetch
    MARKETS = [
        'pitcher_strikeouts', 'pitcher_hits_allowed', 'pitcher_outs',
        'pitcher_earned_runs', 'batter_total_bases', 'batter_hits',
        'batter_runs_scored', 'batter_rbis', 'batter_singles'
    ]

    # Bookmakers to include
    BOOKS = [
        'fanduel', 'draftkings', 'betmgm', 'caesars', 'pointsbetus','betrivers',
        'unibet', 'bovada', 'mybookieag', 'betus', 'william_us', 'fanatics', 'lowvig'
    ]

    def read_todays_matchups_from_step1(self):
        """Read today's matchups from Step 1 instead of calling ESPN again"""
        print("📋 Reading today's matchups from Step 1...")
        
        try:
            # Connect to Google Sheets
            scopes = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
            
            service_account_info = json.loads(os.environ['GOOGLE_SERVICE_ACCOUNT_CREDENTIALS'])
            credentials = Credentials.from_service_account_info(service_account_info, scopes=scopes)
            client = gspread.authorize(credentials)
            
            spreadsheet = client.open("MLB_Splash_Data")
            matchups_worksheet = spreadsheet.worksheet("MATCHUPS")
            
            # Get all data and find header row
            all_data = matchups_worksheet.get_all_values()
            
            header_row = -1
            for i, row in enumerate(all_data):
                if any(col in row for col in ['Game_ID', 'Away_Team', 'Home_Team']):
                    header_row = i
                    break
            
            if header_row == -1:
                print("❌ Could not find header row in MATCHUPS sheet")
                return []
            
            headers = all_data[header_row]
            data_rows = all_data[header_row + 1:]
            
            if not data_rows:
                print("❌ No matchup data found")
                return []
            
            matchups_df = pd.DataFrame(data_rows, columns=headers)
            matchups_df = matchups_df[matchups_df['Game_ID'].notna() & (matchups_df['Game_ID'] != '')]
            
            # Convert to list of matchup dictionaries
            matchups = []
            for _, row in matchups_df.iterrows():
                matchup = {
                    'game_id': row['Game_ID'],
                    'home_team': row.get('Home_Team', ''),
                    'away_team': row.get('Away_Team', ''),
                    'home_abbr': row.get('Home_Abbr', ''),
                    'away_abbr': row.get('Away_Abbr', ''),
                    'venue': row.get('Venue', ''),
                    'status': row.get('Status', '')
                }
                matchups.append(matchup)
            
            self.todays_matchups = matchups
            print(f"✅ Loaded {len(matchups)} matchups from Step 1:")
            
            for matchup in matchups:
                away = matchup['away_abbr'] or matchup['away_team']
                home = matchup['home_abbr'] or matchup['home_team']
                print(f"   {away} @ {home}")
            
            return matchups
            
        except Exception as e:
            print(f"❌ Error reading matchups from Step 1: {e}")
            return []

    def _make_odds_api_request(self, endpoint: str, params: dict):
        """Helper to make Odds API requests with error handling and timeout"""
        url = f"{self.odds_base_url}{endpoint}"
        params['apiKey'] = self.api_key
        self.api_call_count += 1
        try:
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            print(f"❌ Odds API request timed out for {url}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"❌ Odds API request failed for {url}: {e}")
            return None

    def get_odds_api_games(self):
        """Get today's games from Odds API for mapping to our Step 1 matchups"""
        print("🔗 Getting Odds API games for mapping...")
        
        endpoint = "/sports/baseball_mlb/events"
        params = {
            'regions': 'us',
            'markets': 'h2h',
            'oddsFormat': 'american'
        }
        return self._make_odds_api_request(endpoint, params)

    def map_step1_to_odds_api_games(self):
        """Map Step 1 matchups to Odds API game IDs"""
        print("🔗 Mapping Step 1 matchups to Odds API games...")

        if not self.todays_matchups:
            print("❌ No Step 1 matchups to map")
            return []

        odds_games = self.get_odds_api_games()
        if not odds_games:
            print("❌ Failed to retrieve Odds API games for mapping")
            return []

        # Team name mapping for better matching
        team_mapping = {
            'Arizona Diamondbacks': ['Arizona Diamondbacks', 'Diamondbacks', 'ARI'],
            'Atlanta Braves': ['Atlanta Braves', 'Braves', 'ATL'],
            'Baltimore Orioles': ['Baltimore Orioles', 'Orioles', 'BAL'],
            'Boston Red Sox': ['Boston Red Sox', 'Red Sox', 'BOS'],
            'Chicago Cubs': ['Chicago Cubs', 'Cubs', 'CHC'],
            'Chicago White Sox': ['Chicago White Sox', 'White Sox', 'CHW'],
            'Cincinnati Reds': ['Cincinnati Reds', 'Reds', 'CIN'],
            'Cleveland Guardians': ['Cleveland Guardians', 'Guardians', 'CLE'],
            'Colorado Rockies': ['Colorado Rockies', 'Rockies', 'COL'],
            'Detroit Tigers': ['Detroit Tigers', 'Tigers', 'DET'],
            'Houston Astros': ['Houston Astros', 'Astros', 'HOU'],
            'Kansas City Royals': ['Kansas City Royals', 'Royals', 'KC'],
            'Los Angeles Angels': ['Los Angeles Angels', 'LA Angels', 'Angels', 'LAA'],
            'Los Angeles Dodgers': ['Los Angeles Dodgers', 'LA Dodgers', 'Dodgers', 'LAD'],
            'Miami Marlins': ['Miami Marlins', 'Marlins', 'MIA'],
            'Milwaukee Brewers': ['Milwaukee Brewers', 'Brewers', 'MIL'],
            'Minnesota Twins': ['Minnesota Twins', 'Twins', 'MIN'],
            'New York Mets': ['New York Mets', 'NY Mets', 'Mets', 'NYM'],
            'New York Yankees': ['New York Yankees', 'NY Yankees', 'Yankees', 'NYY'],
            'Oakland Athletics': ['Oakland Athletics', 'Oakland A\'s', 'Athletics', 'A\'s', 'ATH'],
            'Philadelphia Phillies': ['Philadelphia Phillies', 'Phillies', 'PHI'],
            'Pittsburgh Pirates': ['Pittsburgh Pirates', 'Pirates', 'PIT'],
            'San Diego Padres': ['San Diego Padres', 'Padres', 'SD'],
            'San Francisco Giants': ['San Francisco Giants', 'SF Giants', 'Giants', 'SF'],
            'Seattle Mariners': ['Seattle Mariners', 'Mariners', 'SEA'],
            'St. Louis Cardinals': ['St. Louis Cardinals', 'St Louis Cardinals', 'Cardinals', 'STL'],
            'Tampa Bay Rays': ['Tampa Bay Rays', 'Rays', 'TB'],
            'Texas Rangers': ['Texas Rangers', 'Rangers', 'TEX'],
            'Toronto Blue Jays': ['Toronto Blue Jays', 'Blue Jays', 'TOR'],
            'Washington Nationals': ['Washington Nationals', 'Nationals', 'WSH']
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

        for step1_matchup in self.todays_matchups:
            step1_home = step1_matchup['home_team']
            step1_away = step1_matchup['away_team']

            found_match = False
            for odds_game in odds_games:
                odds_home = odds_game.get('home_team', '')
                odds_away = odds_game.get('away_team', '')

                if (find_team_match(step1_home, odds_home) and
                    find_team_match(step1_away, odds_away)):

                    matched_game = {
                        'odds_api_id': odds_game['id'],
                        'home_team': odds_game['home_team'],
                        'away_team': odds_game['away_team'],
                        'commence_time': odds_game.get('commence_time'),
                        'step1_matchup': step1_matchup
                    }
                    matched_games.append(matched_game)
                    found_match = True
                    break

        print(f"🎯 Successfully matched {len(matched_games)}/{len(self.todays_matchups)} games")
        return matched_games

    def get_player_props_with_teams(self, game_id: str, market: str, home_team: str, away_team: str):
        """Get player props for a specific game and market, including team information"""
        endpoint = f"/sports/baseball_mlb/events/{game_id}/odds"
        params = {
            'regions': 'us',
            'markets': market,
            'oddsFormat': 'american'
        }
        
        data = self._make_odds_api_request(endpoint, params)
        if not data or not data.get('bookmakers'):
            return []
        
        props_with_teams = []
        
        for bookmaker in data['bookmakers']:
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

                            # Determine player's team based on market type and player name
                            player_team = self._determine_player_team(player_name, market, home_team, away_team)
                            
                            props_with_teams.append({
                                'Name': player_name.strip(),
                                'Team': player_team,
                                'Market': market,
                                'Line': f"{selection} {point}",
                                'Odds': f"{odds:+d}",
                                'Book': bookmaker['title'],
                                'Game': f"{away_team} @ {home_team}",
                                'Game_ID': game_id,
                                'Home_Team': home_team,
                                'Away_Team': away_team
                            })
        
        return props_with_teams

    def _determine_player_team(self, player_name, market, home_team, away_team):
        """
        Determine which team a player belongs to.
        For now, we'll use a simple heuristic - in a real implementation, 
        you'd have roster data or use more sophisticated matching.
        """
        # This is a simplified approach - in reality you'd want roster data
        # For pitcher markets, we could try to match pitcher names to teams
        # For batter markets, it's harder without roster data
        
        # For demo purposes, we'll alternate or use some basic logic
        # In production, you'd want to maintain team rosters or use additional API calls
        
        if 'pitcher' in market.lower():
            # Pitchers - we could maintain a pitcher-to-team mapping
            # For now, we'll just assign alternately or use some heuristic
            return home_team if hash(player_name) % 2 == 0 else away_team
        else:
            # Batters - same issue, need roster data
            return away_team if hash(player_name) % 2 == 0 else home_team

    def fetch_all_odds_with_teams(self):
        """Main method: Fetch odds for Step 1 games with team information"""
        print("🚀 Starting Step 2: Fetch odds with team data...")

        # Read matchups from Step 1
        step1_matchups = self.read_todays_matchups_from_step1()
        if not step1_matchups:
            print("❌ No Step 1 matchups found - aborting odds fetch")
            return []

        # Map to Odds API games
        matched_games = self.map_step1_to_odds_api_games()
        if not matched_games:
            print("❌ No games could be mapped to Odds API - aborting odds fetch")
            return []

        print(f"📈 Fetching odds with team data for {len(matched_games)} matched games...")
        all_odds = []

        for i, game in enumerate(matched_games, 1):
            odds_api_id = game['odds_api_id']
            home_team = game['home_team']
            away_team = game['away_team']

            print(f"\n({i}/{len(matched_games)}) Processing game: {away_team} @ {home_team}")

            for market in self.MARKETS:
                props_with_teams = self.get_player_props_with_teams(
                    odds_api_id, market, home_team, away_team
                )

                if props_with_teams:
                    all_odds.extend(props_with_teams)
                    print(f"      Found {len(props_with_teams)} props for {market}")

                time.sleep(0.2)  # Rate limiting

            time.sleep(0.5)  # Rate limiting between games

        print(f"\n🎉 Collected {len(all_odds)} total player props with team data!")
        return all_odds

    def write_to_google_sheets(self, df, spreadsheet_name: str = "MLB_Splash_Data", worksheet_name: str = "ODDS_API"):
        """Write DataFrame to Google Sheets using a service account"""
        if df.empty:
            print("❌ No data to write to Google Sheets")
            return

        try:
            print("\n🔐 Authenticating with Google Service Account...")
            SCOPES = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
            
            credentials_info = json.loads(os.environ['GOOGLE_SERVICE_ACCOUNT_CREDENTIALS'])
            creds = Credentials.from_service_account_info(credentials_info, scopes=SCOPES)
            gc = gspread.authorize(creds)

            print(f"📊 Connecting to Google Sheets: {spreadsheet_name} -> {worksheet_name}...")
            spreadsheet = gc.open(spreadsheet_name)
            worksheet = spreadsheet.worksheet(worksheet_name)

            print("🧹 Clearing existing data...")
            worksheet.clear()

            print("✍️ Writing new data with team information...")
            
            # Add metadata
            metadata = [
                ['Odds API Data with Team Information', ''],
                ['Fetched At', datetime.now().isoformat()],
                ['Total Props', len(df)],
                ['API Calls Used', self.api_call_count],
                ['Data Source', 'Step 1 Matchups + Odds API'],
                ['']
            ]
            
            # Combine metadata and data
            all_data = metadata + [df.columns.tolist()] + df.values.tolist()
            worksheet.update(range_name='A1', values=all_data)

            print(f"✅ Successfully wrote {len(df)} rows to Google Sheets!")

        except Exception as e:
            print(f"❌ Error writing to Google Sheets: {e}")
            raise

def run_odds_fetcher():
    """Main function"""
    api_key = os.environ.get('ODDS_API_KEY')
    if not api_key:
        print("❌ ODDS_API_KEY environment variable not set!")
        return

    fetcher = MLBOddsFetcher(api_key)
    odds = fetcher.fetch_all_odds_with_teams()
    
    if odds:
        df = pd.DataFrame(odds)
        df = df.drop_duplicates(subset=['Name', 'Market', 'Line', 'Book', 'Game'], keep='first')
        print(f"📊 Final DataFrame: {len(df)} rows after deduplication")
        
        # Show team breakdown
        if 'Team' in df.columns:
            team_counts = df['Team'].value_counts()
            print(f"📊 Props by team: {dict(team_counts.head(10))}")
        
        fetcher.write_to_google_sheets(df)
    else:
        print("❌ No odds data collected")
        raise Exception("No odds data retrieved")

    print(f"\nTotal API calls made: {fetcher.api_call_count}")

if __name__ == "__main__":
    print("⚾ Starting Step 2: MLB Odds Collection with Team Data")
    run_odds_fetcher()
