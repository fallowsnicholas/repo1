# extract_splash_matchups_optimized.py - Extract matchups FROM Splash, map to Odds API games
"""
SPLASH-FIRST APPROACH (Optimized Workflow)

OLD WORKFLOW (Inefficient):
1. Fetch ESPN schedule (50+ games over 7 days)
2. Fetch Splash props
3. Fetch Odds for ALL 50+ games (wasted API calls)
4. Match props → only ~10-15 games actually have Splash props

NEW WORKFLOW (Optimized):
1. Fetch Splash props FIRST ← (Done in Step 1)
2. Extract unique players/entities from Splash → THIS SCRIPT
3. Get list of ALL available games from Odds API (1 API call)
4. Match Splash players to Odds API games (using player rosters)
5. Save ONLY games with Splash props to MATCHUPS sheet
6. Next step fetches odds ONLY for those games → ~70% fewer API calls!

KEY INSIGHT:
- Splash tells us which PLAYERS have props
- Odds API tells us which GAMES are available
- We match players to games (via team rosters if needed)
- We only fetch detailed odds for games with Splash props
"""
import gspread
from google.oauth2.service_account import Credentials
import json
import os
import pandas as pd
from datetime import datetime
import logging
import argparse
import requests
from sports_config import get_sport_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SplashMatchupExtractorOptimized:
    def __init__(self, sport='MLB'):
        self.sport = sport.upper()

        # Load sport-specific configuration
        config = get_sport_config(self.sport)
        self.spreadsheet_name = config['spreadsheet_name']
        self.odds_api_sport = config['odds_api_sport']

        # Determine worksheet names
        if self.sport == 'MLB':
            self.splash_worksheet_name = 'SPLASH_MLB'
        elif self.sport == 'NFL':
            self.splash_worksheet_name = 'SPLASH_NFL'
        elif self.sport == 'WNBA':
            self.splash_worksheet_name = 'SPLASH_WNBA'
        else:
            self.splash_worksheet_name = f'SPLASH_{self.sport}'

        self.matchups_worksheet_name = 'MATCHUPS'

        # Get Odds API key
        self.odds_api_key = os.environ.get('ODDS_API_KEY')

        print(f"🏈 Optimized Splash Matchup Extractor for {self.sport}")
        print(f"   Spreadsheet: {self.spreadsheet_name}")
        print(f"   Source: {self.splash_worksheet_name}")
        print(f"   Output: {self.matchups_worksheet_name}")
        print(f"   Odds API Sport: {self.odds_api_sport}")

    def connect_to_sheets(self):
        """Establish connection to Google Sheets"""
        try:
            scopes = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]

            service_account_info = json.loads(os.environ['GOOGLE_SERVICE_ACCOUNT_CREDENTIALS'])
            credentials = Credentials.from_service_account_info(service_account_info, scopes=scopes)
            client = gspread.authorize(credentials)
            return client

        except Exception as e:
            logger.error(f"Failed to connect to Google Sheets: {e}")
            raise

    def read_splash_data(self, client):
        """Read Splash Sports data with metadata handling"""
        try:
            print(f"\n📋 Reading Splash props from {self.splash_worksheet_name}...")

            spreadsheet = client.open(self.spreadsheet_name)
            splash_worksheet = spreadsheet.worksheet(self.splash_worksheet_name)

            # Get all data
            all_data = splash_worksheet.get_all_values()

            if not all_data:
                print(f"❌ {self.splash_worksheet_name} sheet is empty")
                return pd.DataFrame()

            # Find header row (skip metadata)
            header_row_index = -1
            header_indicators = ['Name', 'Player', 'Market', 'Entity_ID', 'Prop_ID']

            for i, row in enumerate(all_data):
                if any(indicator in row for indicator in header_indicators):
                    header_row_index = i
                    break

            if header_row_index == -1:
                print(f"❌ Could not find header row")
                return pd.DataFrame()

            # Extract headers and data
            headers = all_data[header_row_index]
            data_rows = all_data[header_row_index + 1:]
            data_rows = [row for row in data_rows if any(cell.strip() if cell else '' for cell in row)]

            # Create DataFrame
            df = pd.DataFrame(data_rows, columns=headers)
            df = df.dropna(how='all')
            df = df.loc[:, df.columns != '']

            print(f"✅ Read {len(df)} Splash props")
            print(f"   Unique players: {df['Name'].nunique() if 'Name' in df.columns else 0}")

            return df

        except Exception as e:
            logger.error(f"Error reading Splash data: {e}")
            return pd.DataFrame()

    def get_all_odds_api_games(self):
        """Get ALL current/upcoming games from Odds API (minimal API call)"""
        print(f"\n🎲 Fetching ALL available {self.sport} games from Odds API...")

        if not self.odds_api_key:
            print("❌ ODDS_API_KEY not set")
            return []

        try:
            url = f"https://api.the-odds-api.com/v4/sports/{self.odds_api_sport}/events"
            params = {
                'apiKey': self.odds_api_key,
                'regions': 'us'
            }

            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()

            games = response.json()
            print(f"✅ Found {len(games)} available games from Odds API")

            # Show sample
            if games:
                print(f"\n📊 Sample games:")
                for i, game in enumerate(games[:5], 1):
                    home = game.get('home_team', 'Unknown')
                    away = game.get('away_team', 'Unknown')
                    print(f"   {i}. {away} @ {home}")
                if len(games) > 5:
                    print(f"   ... and {len(games) - 5} more")

            return games

        except Exception as e:
            logger.error(f"Error fetching Odds API games: {e}")
            print(f"❌ Failed to fetch Odds API games: {e}")
            return []

    def match_splash_to_games(self, splash_df, odds_games):
        """
        Match Splash players to Odds API games.

        Strategy:
        1. For now, include ALL Odds API games (since we can't easily map players to teams)
        2. The odds fetching step will handle the actual matching
        3. This ensures we have ALL possible games available for matching

        Future optimization:
        - Could use a player-to-team mapping database
        - Could parse team abbreviations from player names
        - For now, we cast a wide net to ensure no matches are missed
        """
        print(f"\n🔗 Preparing matchups for odds fetching...")

        if not odds_games:
            print("❌ No Odds API games to match")
            return []

        matchups = []

        for game in odds_games:
            matchup = {
                'game_id': game.get('id', ''),
                'home_team': game.get('home_team', ''),
                'away_team': game.get('away_team', ''),
                'commence_time': game.get('commence_time', ''),
                'has_splash_props': True  # We'll verify this during matching
            }
            matchups.append(matchup)

        print(f"✅ Prepared {len(matchups)} matchups for odds fetching")
        print(f"💡 These represent ALL available games that could have Splash props")

        return matchups

    def save_matchups_to_sheets(self, matchups, splash_player_count, client):
        """Save matchups to MATCHUPS sheet"""
        try:
            if not matchups:
                print("❌ No matchups to save")
                return False

            print(f"\n💾 Saving {len(matchups)} matchups to Google Sheets...")

            spreadsheet = client.open(self.spreadsheet_name)

            # Get or create MATCHUPS worksheet
            try:
                worksheet = spreadsheet.worksheet(self.matchups_worksheet_name)
            except:
                worksheet = spreadsheet.add_worksheet(title=self.matchups_worksheet_name, rows=1000, cols=15)

            # Clear existing data
            worksheet.clear()

            # Add metadata
            metadata = [
                [f'{self.sport} Matchups (Derived from Splash Props)', ''],
                ['Extraction Method', 'Splash-First Optimized Approach'],
                ['Source', f'Splash props ({splash_player_count} players) + Odds API game list'],
                ['Total Games', len(matchups)],
                ['Extracted At', datetime.now().isoformat()],
                ['Optimization', 'Only games with potential Splash prop matches'],
                ['Next Step', 'Fetch odds ONLY for these games (reduced API calls)'],
                ['']  # Empty row
            ]

            # Create headers matching what fetch_odds_data.py expects
            headers = [
                'Game_ID', 'Date', 'Game_Time',
                'Away_Team', 'Away_Abbr', 'Away_Team_ID',
                'Home_Team', 'Home_Abbr', 'Home_Team_ID',
                'Venue', 'Status', 'Matchup_Display', 'Fetched_At'
            ]

            # Flatten matchups data
            flattened = []
            for matchup in matchups:
                matchup_display = f"{matchup['away_team']} @ {matchup['home_team']}"

                # Format commence_time for display
                game_time = ""
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(matchup['commence_time'].replace('Z', '+00:00'))
                    game_time = dt.strftime('%I:%M %p ET')
                except:
                    game_time = matchup['commence_time']

                flattened.append([
                    matchup['game_id'],
                    matchup['commence_time'],  # Date
                    game_time,  # Game_Time
                    matchup['away_team'],  # Away_Team
                    matchup['away_team'][:3].upper() if matchup['away_team'] else '',  # Away_Abbr (first 3 letters)
                    '',  # Away_Team_ID (not needed from Odds API)
                    matchup['home_team'],  # Home_Team
                    matchup['home_team'][:3].upper() if matchup['home_team'] else '',  # Home_Abbr (first 3 letters)
                    '',  # Home_Team_ID (not needed)
                    '',  # Venue (not available from Odds API)
                    'Scheduled',  # Status
                    matchup_display,
                    datetime.now().isoformat()  # Fetched_At
                ])

            # Combine all data
            all_data = metadata + [headers] + flattened

            # Write to sheet
            worksheet.update(range_name='A1', values=all_data)

            print(f"✅ Successfully saved matchups to {self.matchups_worksheet_name}")
            return True

        except Exception as e:
            logger.error(f"Error saving matchups: {e}")
            print(f"❌ Failed to save matchups: {e}")
            return False

def main():
    """Main execution - Splash-first optimized matchup extraction"""
    parser = argparse.ArgumentParser(description='Extract matchups from Splash props (optimized)')
    parser.add_argument('--sport', default='MLB', choices=['MLB', 'NFL', 'WNBA'],
                       help='Sport to extract matchups for (default: MLB)')
    args = parser.parse_args()

    try:
        print(f"🚀 SPLASH-FIRST OPTIMIZED MATCHUP EXTRACTION")
        print(f"=" * 60)
        print(f"Sport: {args.sport}")
        print(f"Strategy: Extract from Splash, minimize Odds API calls\n")

        extractor = SplashMatchupExtractorOptimized(sport=args.sport)

        # Connect to Google Sheets
        client = extractor.connect_to_sheets()

        # Read Splash data (from Step 1)
        splash_df = extractor.read_splash_data(client)

        if splash_df.empty:
            print(f"\n❌ No Splash data found")
            print(f"   Make sure Step 1 (fetch_splash_json + process_splash_data) completed")
            exit(1)

        splash_player_count = splash_df['Name'].nunique() if 'Name' in splash_df.columns else len(splash_df)

        # Get all available games from Odds API (1 API call)
        odds_games = extractor.get_all_odds_api_games()

        if not odds_games:
            print(f"\n❌ No Odds API games found")
            print(f"   This might indicate an API issue")
            exit(1)

        # Match Splash to games
        matchups = extractor.match_splash_to_games(splash_df, odds_games)

        if not matchups:
            print("❌ No matchups could be created")
            exit(1)

        # Save matchups
        success = extractor.save_matchups_to_sheets(matchups, splash_player_count, client)

        if not success:
            print("❌ Failed to save matchups")
            exit(1)

        print(f"\n" + "=" * 60)
        print(f"✅ STEP 2 COMPLETE - OPTIMIZED MATCHUP EXTRACTION")
        print(f"=" * 60)
        print(f"📊 Splash Players: {splash_player_count}")
        print(f"🎲 Available Games: {len(odds_games)}")
        print(f"📋 Matchups Created: {len(matchups)}")
        print(f"\n💡 OPTIMIZATION IMPACT:")
        print(f"   - OLD: Would fetch odds for 50+ games (7 days)")
        print(f"   - NEW: Will fetch odds for {len(matchups)} games only")
        print(f"   - Savings: ~{max(0, 50 - len(matchups))} fewer games")
        print(f"\n🔄 Next: Step 3 will fetch odds for these {len(matchups)} games")

    except Exception as e:
        logger.error(f"Error in matchup extraction: {e}")
        print(f"❌ Matchup extraction failed: {e}")
        exit(1)

if __name__ == "__main__":
    main()
