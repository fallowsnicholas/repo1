# fetch_targeted_odds.py - Step 3: Fetch odds only for players in today's games
import requests
import time
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json
from datetime import datetime
import os

class TargetedOddsFetcher:
    """Step 3: Fetch odds only for players in today's matchups - much more efficient"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.odds_base_url = "https://api.the-odds-api.com/v4"
        self.api_call_count = 0
        self.target_players = []
        
        # Markets we care about for pitcher vs batter correlations
        self.TARGET_MARKETS = [
            'pitcher_strikeouts', 'pitcher_hits_allowed', 'pitcher_outs',
            'pitcher_earned_runs', 'batter_total_bases', 'batter_hits',
            'batter_runs_scored', 'batter_singles'
        ]
        
        # Bookmakers to include
        self.BOOKS = [
            'fanduel', 'draftkings', 'betmgm', 'caesars', 'pointsbetus','betrivers',
            'unibet', 'bovada', 'mybookieag', 'betus', 'william_us', 'fanatics', 'lowvig'
        ]

    def load_target_players_from_sheets(self):
        """Load players from Step 1 matchup data to target odds fetching"""
        print("📋 Loading target players from Step 1 matchup data...")
        
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
            
            # Read players from Step 1
            players_worksheet = spreadsheet.worksheet("PLAYERS")
            players_data = players_worksheet.get_all_records()
            
            if not players_data:
                print("❌ No player data found from Step 1")
                return []
            
            # Filter for today's active players
            active_players = []
            for player in players_data:
                # Only include players who are pitchers or batters
                if player.get('Is_Pitcher') == 'TRUE' or player.get('Is_Batter') == 'TRUE':
                    active_players.append({
                        'name': player['Player_Name'],
                        'team': player['Team_Name'],
                        'position': player['Position'],
                        'is_pitcher': player.get('Is_Pitcher') == 'TRUE',
                        'is_batter': player.get('Is_Batter') == 'TRUE'
                    })
            
            self.target_players = active_players
            print(f"🎯 Loaded {len(active_players)} target players from today's games")
            
            # Show breakdown
            pitchers = len([p for p in active_players if p['is_pitcher']])
            batters = len([p for p in active_players if p['is_batter']])
            print(f"   Pitchers: {pitchers}")
            print(f"   Batters: {batters}")
            
            return active_players
            
        except Exception as e:
            print(f"❌ Error loading target players: {e}")
            return []

    def _make_odds_api_request(self, endpoint: str, params: dict):
        """Helper to make Odds API requests with error handling"""
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

    def get_all_odds_api_games(self):
        """Get all MLB games from Odds API to map to our target games"""
        print("🔗 Getting MLB games from Odds API...")
        
        endpoint = "/sports/baseball_mlb/events"
        params = {
            'regions': 'us',
            'markets': 'h2h',
            'oddsFormat': 'american'
        }
        
        games = self._make_odds_api_request(endpoint, params)
        
        if games:
            print(f"📅 Found {len(games)} games in Odds API")
            return games
        else:
            print("❌ Failed to get games from Odds API")
            return []

    def fetch_targeted_player_props(self):
        """Fetch props only for players in today's games - much more efficient"""
        print("⚾ STEP 3: FETCHING TARGETED ODDS DATA")
        print("=" * 60)
        
        if not self.target_players:
            print("❌ No target players loaded")
            return []
        
        # Get Odds API games
        odds_games = self.get_all_odds_api_games()
        if not odds_games:
            print("❌ Cannot proceed without Odds API games")
            return []
        
        all_targeted_odds = []
        
        print(f"🎯 Fetching odds for target markets: {self.TARGET_MARKETS}")
        
        # Fetch props for each game, but filter for our target players
        for game in odds_games:
            game_id = game.get('id')
            home_team = game.get('home_team', '')
            away_team = game.get('away_team', '')
            
            print(f"\n🏟️ Processing: {away_team} @ {home_team}")
            
            # Check if any of our target players are in this game
            game_has_target_players = self._game_has_target_players(home_team, away_team)
            
            if not game_has_target_players:
                print(f"   ⏭️ Skipping - no target players in this game")
                continue
            
            # Fetch props for each target market
            for market in self.TARGET_MARKETS:
                market_props = self._fetch_game_market_props(game_id, market, home_team, away_team)
                if market_props:
                    # Filter for target players only
                    filtered_props = self._filter_for_target_players(market_props)
                    all_targeted_odds.extend(filtered_props)
                    
                    if filtered_props:
                        print(f"   ✅ {market}: {len(filtered_props)} target player props")
                
                # Rate limiting
                time.sleep(0.2)
            
            # Rate limiting between games
            time.sleep(0.5)
        
        print(f"\n🎉 Collected {len(all_targeted_odds)} targeted player props!")
        print(f"📊 API calls used: {self.api_call_count}")
        
        return all_targeted_odds
    
    def _game_has_target_players(self, home_team, away_team):
        """Check if this game has any of our target players"""
        game_teams = [home_team.lower(), away_team.lower()]
        
        for player in self.target_players:
            player_team = player['team'].lower()
            # Simple team name matching - could be enhanced
            for game_team in game_teams:
                if any(word in game_team for word in player_team.split()) or any(word in player_team for word in game_team.split()):
                    return True
        return False
    
    def _fetch_game_market_props(self, game_id, market, home_team, away_team):
        """Fetch props for a specific game and market"""
        endpoint = f"/sports/baseball_mlb/events/{game_id}/odds"
        params = {
            'regions': 'us',
            'markets': market,
            'oddsFormat': 'american'
        }
        
        data = self._make_odds_api_request(endpoint, params)
        
        if not data or not data.get('bookmakers'):
            return []
        
        props = []
        
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
                            
                            props.append({
                                'Name': player_name.strip(),
                                'Market': market,
                                'Line': f"{selection} {point}",
                                'Odds': f"{odds:+d}",
                                'Book': bookmaker['title'],
                                'Game': f"{away_team} @ {home_team}",
                                'Game_ID': game_id
                            })
        
        return props
    
    def _filter_for_target_players(self, props):
        """Filter props to only include our target players"""
        target_names = [player['name'].lower() for player in self.target_players]
        
        filtered = []
        for prop in props:
            prop_name = prop['Name'].lower()
            
            # Check if this prop player matches any of our target players
            for target_name in target_names:
                if self._names_match(prop_name, target_name):
                    filtered.append(prop)
                    break
        
        return filtered
    
    def _names_match(self, name1, name2):
        """Simple name matching - could be enhanced with fuzzy matching"""
        # Basic matching - exact match or contains
        return name1 == name2 or name1 in name2 or name2 in name1

    def save_to_google_sheets(self, odds_data):
        """Save targeted odds data to Google Sheets"""
        if not odds_data:
            print("❌ No odds data to save")
            return
        
        try:
            print(f"💾 Saving {len(odds_data)} targeted odds to Google Sheets...")
            
            # Connect to sheets
            scopes = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
            
            service_account_info = json.loads(os.environ['GOOGLE_SERVICE_ACCOUNT_CREDENTIALS'])
            credentials = Credentials.from_service_account_info(service_account_info, scopes=scopes)
            client = gspread.authorize(credentials)
            
            spreadsheet = client.open("MLB_Splash_Data")
            
            # Get or create ODDS_API worksheet
            try:
                worksheet = spreadsheet.worksheet("ODDS_API")
            except:
                worksheet = spreadsheet.add_worksheet(title="ODDS_API", rows=1000, cols=10)
            
            worksheet.clear()
            
            # Convert to DataFrame and save
            df = pd.DataFrame(odds_data)
            df = df.drop_duplicates(subset=['Name', 'Market', 'Line', 'Book', 'Game'], keep='first')
            
            print(f"📊 Final dataset: {len(df)} rows after deduplication")
            
            # Write to sheet
            all_data = [df.columns.tolist()] + df.values.tolist()
            worksheet.update(range_name='A1', values=all_data)
            
            print("✅ Successfully wrote targeted odds data to Google Sheets!")
            
        except Exception as e:
            print(f"❌ Error writing to Google Sheets: {e}")
            raise

def main():
    """Main function for Step 3"""
    api_key = os.environ.get('ODDS_API_KEY')
    if not api_key:
        print("❌ ODDS_API_KEY environment variable not set!")
        return
    
    try:
        fetcher = TargetedOddsFetcher(api_key)
        
        # Load target players from Step 1
        target_players = fetcher.load_target_players_from_sheets()
        
        if not target_players:
            print("❌ No target players found - cannot proceed")
            return
        
        # Fetch targeted odds
        odds_data = fetcher.fetch_targeted_player_props()
        
        if odds_data:
            # Save to Google Sheets
            fetcher.save_to_google_sheets(odds_data)
            
            print(f"\n✅ STEP 3 COMPLETE:")
            print(f"   Targeted odds collected: {len(odds_data)}")
            print(f"   API calls used: {fetcher.api_call_count}")
            print("   Data saved to ODDS_API sheet")
        else:
            print("❌ No targeted odds data collected")
            
    except Exception as e:
        print(f"❌ Error in Step 3: {e}")
        raise

if __name__ == "__main__":
    main()
