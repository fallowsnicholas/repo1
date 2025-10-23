# fetch_matchups_multi_day.py - Fetch matchups for multiple days to capture all Splash props
"""
This script fetches matchups for the next N days (default 7) instead of just today.
This ensures we capture ALL games that might have Splash props, not just today's games.

Why this is needed:
- Splash Sports has props for games happening days in the future
- The old approach only fetched TODAY's games
- This caused mismatches: Splash had props for Day+4, but we only fetched odds for Day+0
- Result: Stale data, no matches

Solution:
- Fetch matchups for next 7 days
- Fetch odds for ALL those matchups
- Now we can match ALL Splash props regardless of game date
"""
import requests
import json
import pandas as pd
from datetime import datetime, timedelta
import logging
import gspread
from google.oauth2.service_account import Credentials
import os
import argparse
from sports_config import get_sport_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MultiDayMatchupFetcher:
    def __init__(self, sport='MLB', days_range=7):
        self.sport = sport.upper()
        self.days_range = days_range

        # Load sport-specific configuration
        config = get_sport_config(self.sport)
        self.espn_sport = config['espn_sport']
        self.espn_league = config['espn_league']
        self.spreadsheet_name = config['spreadsheet_name']

        # Build the ESPN API URL
        self.espn_base_url = f"https://site.api.espn.com/apis/site/v2/sports/{self.espn_sport}/{self.espn_league}"

        print(f"🏈 Initialized Multi-Day {self.sport} Matchup Fetcher")
        print(f"   Fetching matchups for next {self.days_range} days")
        print(f"   Spreadsheet: {self.spreadsheet_name}")

    def fetch_games_for_day(self, day_offset):
        """Fetch games for a specific day offset"""
        try:
            target_date = datetime.now() + timedelta(days=day_offset)
            date_str = target_date.strftime('%Y%m%d')
            date_display = target_date.strftime('%B %d, %Y')

            url = f"{self.espn_base_url}/scoreboard"
            params = {'dates': date_str, 'limit': 50}

            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()

            data = response.json()
            matchups = []

            if 'events' in data and data['events']:
                for event in data['events']:
                    try:
                        matchup = self._parse_game_event(event)
                        if matchup:
                            # Add which day this is for tracking
                            matchup['fetch_day_offset'] = day_offset
                            matchup['fetch_date'] = date_display
                            matchups.append(matchup)
                    except Exception as e:
                        logger.error(f"Error parsing game: {e}")
                        continue

            return matchups, date_display

        except Exception as e:
            logger.error(f"Error fetching games for day+{day_offset}: {e}")
            return [], None

    def _parse_game_event(self, event):
        """Parse individual game to extract teams and basic info"""
        try:
            competition = event.get('competitions', [{}])[0]
            competitors = competition.get('competitors', [])

            if len(competitors) < 2:
                return None

            # Extract teams
            teams = {}
            for competitor in competitors:
                team_info = competitor.get('team', {})
                home_away = competitor.get('homeAway', '')

                if home_away in ['home', 'away']:
                    teams[f'{home_away}_team'] = {
                        'name': team_info.get('displayName', ''),
                        'abbreviation': team_info.get('abbreviation', ''),
                        'id': team_info.get('id', ''),
                        'espn_id': team_info.get('id', '')
                    }

            if 'home_team' not in teams or 'away_team' not in teams:
                return None

            # Extract basic game info
            game_info = {
                'game_id': event.get('id', ''),
                'date': event.get('date', ''),
                'status': event.get('status', {}).get('type', {}).get('name', 'Unknown'),
                'venue': competition.get('venue', {}).get('fullName', 'Unknown'),
                'home_team': teams['home_team'],
                'away_team': teams['away_team']
            }

            return game_info

        except Exception as e:
            logger.error(f"Error parsing game event: {e}")
            return None

    def fetch_all_upcoming_matchups(self):
        """Fetch matchups for the next N days"""
        print(f"📅 FETCHING {self.sport} MATCHUPS FOR NEXT {self.days_range} DAYS")
        print("=" * 60)
        print(f"💡 Why: Splash has props for future games, not just today")
        print(f"💡 This ensures we capture ALL props in Splash\n")

        all_matchups = []
        day_summary = {}

        for day_offset in range(self.days_range):
            print(f"\n📆 Fetching Day +{day_offset}...")
            matchups, date_display = self.fetch_games_for_day(day_offset)

            if matchups:
                all_matchups.extend(matchups)
                day_summary[date_display] = len(matchups)
                print(f"   ✅ {date_display}: {len(matchups)} games")

                # Show matchups
                for matchup in matchups:
                    away = matchup['away_team']['abbreviation']
                    home = matchup['home_team']['abbreviation']
                    print(f"      • {away} @ {home}")
            else:
                print(f"   ⚪ {date_display}: No games")

        print(f"\n" + "=" * 60)
        print(f"📊 SUMMARY:")
        print(f"   Total games across {self.days_range} days: {len(all_matchups)}")
        print(f"   Days with games: {len([d for d in day_summary.values() if d > 0])}")
        print(f"\n   Breakdown by day:")
        for date, count in day_summary.items():
            print(f"      {date}: {count} games")

        return all_matchups

    def save_to_google_sheets(self, matchups):
        """Save all matchups to Google Sheets"""
        try:
            print(f"\n💾 Saving {len(matchups)} matchups to Google Sheets...")

            # Connect to Google Sheets
            scopes = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]

            service_account_info = json.loads(os.environ['GOOGLE_SERVICE_ACCOUNT_CREDENTIALS'])
            credentials = Credentials.from_service_account_info(service_account_info, scopes=scopes)
            client = gspread.authorize(credentials)

            spreadsheet = client.open(self.spreadsheet_name)

            # Get or create MATCHUPS worksheet
            try:
                worksheet = spreadsheet.worksheet("MATCHUPS")
            except:
                worksheet = spreadsheet.add_worksheet(title="MATCHUPS", rows=500, cols=15)

            worksheet.clear()

            if matchups:
                # Create headers
                headers = [
                    'Game_ID', 'Date', 'Game_Time', 'Game_Date_Display',
                    'Away_Team', 'Away_Abbr', 'Away_Team_ID',
                    'Home_Team', 'Home_Abbr', 'Home_Team_ID',
                    'Venue', 'Status', 'Matchup_Display', 'Fetched_At'
                ]

                # Flatten data for sheet
                flattened = []
                for game in matchups:
                    matchup_display = f"{game['away_team']['abbreviation']} @ {game['home_team']['abbreviation']}"

                    # Format game time
                    game_time = ""
                    if game.get('date'):
                        try:
                            dt = datetime.fromisoformat(game['date'].replace('Z', '+00:00'))
                            game_time = dt.strftime('%I:%M %p ET')
                        except:
                            game_time = game.get('date', '')

                    flattened.append([
                        game['game_id'],
                        game.get('date', ''),
                        game_time,
                        game.get('fetch_date', ''),
                        game['away_team']['name'],
                        game['away_team']['abbreviation'],
                        game['away_team']['espn_id'],
                        game['home_team']['name'],
                        game['home_team']['abbreviation'],
                        game['home_team']['espn_id'],
                        game['venue'],
                        game['status'],
                        matchup_display,
                        datetime.now().isoformat()
                    ])

                # Add metadata at top
                metadata = [
                    [f'{self.sport} Matchups (Next {self.days_range} Days)', ''],
                    ['Fetch Strategy', 'Multi-day fetch to capture all Splash props'],
                    ['Date Range', f'{datetime.now().strftime("%B %d")} to {(datetime.now() + timedelta(days=self.days_range-1)).strftime("%B %d, %Y")}'],
                    ['Total Games', len(matchups)],
                    ['Fetched At', datetime.now().isoformat()],
                    ['Why Multi-Day', 'Splash has props for future games, not just today'],
                    ['']  # Empty row
                ]

                # Combine metadata, headers, and data
                all_data = metadata + [headers] + flattened

                # Write to sheet
                worksheet.update(range_name='A1', values=all_data)

                print(f"✅ Saved {len(matchups)} matchups to MATCHUPS sheet")
                return True

            else:
                # Add a note if no games found
                worksheet.update(range_name='A1', values=[
                    [f'No games found for next {self.days_range} days'],
                    ['Fetched At', datetime.now().isoformat()],
                    ['', ''],
                    ['💡 This is unusual - check ESPN API status']
                ])
                print("📝 Saved 'no games' notice to MATCHUPS sheet")
                return False

        except Exception as e:
            logger.error(f"Error saving to Google Sheets: {e}")
            raise

def main():
    """Main execution - fetch matchups for next N days"""
    parser = argparse.ArgumentParser(description='Fetch multi-day matchups from ESPN')
    parser.add_argument('--sport', default='MLB', choices=['MLB', 'NFL', 'WNBA'],
                       help='Sport to fetch matchups for (default: MLB)')
    parser.add_argument('--days', type=int, default=7,
                       help='Number of days to fetch (default: 7)')
    args = parser.parse_args()

    try:
        print(f"🚀 Multi-Day Matchup Fetcher for {args.sport}")
        print(f"📅 Fetching next {args.days} days of games\n")

        fetcher = MultiDayMatchupFetcher(sport=args.sport, days_range=args.days)

        # Fetch matchups for all days
        matchups = fetcher.fetch_all_upcoming_matchups()

        if not matchups:
            print("\n⚠️ No matchups found for any day in range")
            print("💡 This might be normal during off-season")
            # Still save to sheets (will save empty notice)
            fetcher.save_to_google_sheets(matchups)
            exit(0)

        # Save to Google Sheets
        success = fetcher.save_to_google_sheets(matchups)

        if success:
            print(f"\n✅ STEP 1 COMPLETE!")
            print(f"   📊 Fetched {len(matchups)} games across {args.days} days")
            print(f"   💾 Saved to {fetcher.spreadsheet_name} (MATCHUPS tab)")
            print(f"\n💡 Next: Step 2 will fetch odds for ALL these matchups")
            print(f"   This ensures we can match ALL props in Splash!")
        else:
            print("\n⚠️ No matchups to save")
            exit(0)

    except Exception as e:
        logger.error(f"Error in multi-day matchup fetching: {e}")
        print(f"❌ Step 1 failed: {e}")
        exit(1)

if __name__ == "__main__":
    main()
