# fetch_odds_data.py
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
        self.espn_base_url = "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb"
        self.api_call_count = 0

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

    def get_todays_games_from_espn(self):
        """Get today's MLB games from ESPN API"""
        print("🏈 Fetching today's games from ESPN API...")

        try:
            today = datetime.now().strftime('%Y%m%d')
            url = f"{self.espn_base_url}/scoreboard"

            params = {'dates': today, 'limit': 50}
            self.api_call_count += 1
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
                    except Exception as e:
                        print(f"  Error parsing ESPN event: {e}")
                        continue
            else:
                print("⚠️ No events found in ESPN response for today.")

            active_games = [g for g in games if g['status'] in ['STATUS_SCHEDULED', 'STATUS_INPROGRESS']]
            print(f"✅ ESPN found {len(active_games)} active games for today")
            return active_games

        except Exception as e:
            print(f"❌ Unexpected error fetching games from ESPN: {e}")
            return []

    def get_all_odds_api_games(self):
        """Get ALL available games from Odds API for mapping"""
        endpoint = "/sports/baseball_mlb/events"
        params = {
            'regions': 'us',
            'markets': 'h2h',
            'oddsFormat': 'american'
        }
        return self._make_odds_api_request(endpoint, params)

    def map_espn_to_odds_api_games(self, espn_games):
        """Map ESPN games to Odds API game IDs"""
        print("🔗 Mapping ESPN games to Odds API games...")

        odds_games = self.get_all_odds_api_games()
        if not odds_games:
            print("❌ Failed to retrieve Odds API games for mapping.")
            return []

        # Team name mapping for better matching
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

            found_match = False
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
                    found_match = True
                    break

        print(f"🎯 Successfully matched {len(matched_games)}/{len(espn_games)} games")
        return matched_games

    def get_player_props(self, game_id: str, market: str):
        """Get player props for a specific game and market"""
        endpoint = f"/sports/baseball_mlb/events/{game_id}/odds"
        params = {
            'regions': 'us',
            'markets': market,
            'oddsFormat': 'american'
        }
        return self._make_odds_api_request(endpoint, params)

    def fetch_all_odds(self):
        """Main method: ESPN games -> Odds API props"""
        print("🚀 Starting ESPN-primary odds fetch...")

        espn_games = self.get_todays_games_from_espn()
        if not espn_games:
            print("❌ No games found from ESPN - aborting odds fetch.")
            return []

        matched_games = self.map_espn_to_odds_api_games(espn_games)
        if not matched_games:
            print("❌ No games could be matched to Odds API - aborting odds fetch.")
            return []

        print(f"📈 Fetching odds for {len(matched_games)} matched games...")
        all_odds = []

        for i, game in enumerate(matched_games, 1):
            game_id = game['id']
            home_team = game['home_team']
            away_team = game['away_team']

            print(f"\n({i}/{len(matched_games)}) Processing game: {away_team} @ {home_team}")

            for market in self.MARKETS:
                data = self.get_player_props(game_id, market)

                if data and data.get('bookmakers'):
                    props_count = 0
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

                                        all_odds.append({
                                            'Name': player_name.strip(),
                                            'Market': market,
                                            'Line': f"{selection} {point}",
                                            'Odds': f"{odds:+d}",
                                            'Book': bookmaker['title'],
                                            'Game': f"{away_team} @ {home_team}",
                                            'Game_ID': game_id
                                        })
                                        props_count += 1

                    if props_count > 0:
                         print(f"      Found {props_count} props for {market}")

                time.sleep(0.2)  # Rate limiting

            time.sleep(0.5)  # Rate limiting between games

        print(f"\n🎉 Collected {len(all_odds)} total player props!")
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

            print("✍️ Writing new data...")
            all_data = [df.columns.tolist()] + df.values.tolist()
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
    odds = fetcher.fetch_all_odds()
    
    if odds:
        df = pd.DataFrame(odds)
        df = df.drop_duplicates(subset=['Name', 'Market', 'Line', 'Book', 'Game'], keep='first')
        print(f"📊 Final DataFrame: {len(df)} rows after deduplication")
        
        fetcher.write_to_google_sheets(df)
    else:
        print("❌ No odds data collected")
        raise Exception("No odds data retrieved")

    print(f"\nTotal API calls made: {fetcher.api_call_count}")

if __name__ == "__main__":
    print("⚾ Starting MLB Odds Collection via GitHub Actions")
    run_odds_fetcher()
