# fetch_matchups.py - Step 1: Get matchups from ESPN with configurable date (Multi-Sport)
import requests
import json
import pandas as pd
from datetime import datetime, timedelta
import logging
import gspread
from google.oauth2.service_account import Credentials
import os
import argparse
# fetch_matchups.py - Step 1: Get matchups from ESPN with configurable date (Multi-Sport)
import requests
import json
import pandas as pd
from datetime import datetime, timedelta
import logging
import gspread
from google.oauth2.service_account import Credentials
import os
import argparse

# Add sports configuration import with fallback
try:
    from sports_config import get_sport_config
except ImportError:
    print("Warning: sports_config.py not found, using MLB defaults")
    get_sport_config = lambda x: None


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MatchupFetcher:
    def __init__(self, sport='MLB'):
        self.sport = sport.upper()
        self.days_offset = int(os.environ.get('DAYS_OFFSET', '0'))
        
        # Load sport-specific configuration
        config = get_sport_config(self.sport) if get_sport_config else None
        
        if config:
            # Use sport-specific settings
            self.espn_sport = config['espn_sport']
            self.espn_league = config['espn_league']
            self.spreadsheet_name = config['spreadsheet_name']
            print(f"✅ Loaded {self.sport} configuration")
        else:
            # Fallback to MLB defaults (keeps working if no config)
            self.espn_sport = 'baseball'
            self.espn_league = 'mlb'
            self.spreadsheet_name = 'MLB_Splash_Data'
            if self.sport != 'MLB':
                print(f"⚠️ No config for {self.sport}, using MLB defaults")
        
        # Build the ESPN API URL
        self.espn_base_url = f"https://site.api.espn.com/apis/site/v2/sports/{self.espn_sport}/{self.espn_league}"
        
    def fetch_todays_games(self):
        """Get games with configurable date offset"""
        print(f"⚾ STEP 1: FETCHING {self.sport} MATCHUPS")
        print("=" * 60)
        
        try:
            # Calculate target date with offset
            target_date = datetime.now() + timedelta(days=self.days_offset)
            today = target_date.strftime('%Y%m%d')
            date_display = target_date.strftime('%B %d, %Y')
            
            # Show what date we're fetching
            if self.days_offset == 0:
                print(f"📅 Fetching games for TODAY: {date_display}")
            elif self.days_offset == 1:
                print(f"📅 Fetching games for TOMORROW: {date_display}")
            elif self.days_offset > 0:
                print(f"📅 Fetching games for {self.days_offset} days from now: {date_display}")
            else:
                print(f"📅 Fetching games for {abs(self.days_offset)} days ago: {date_display}")
            
            url = f"{self.espn_base_url}/scoreboard"
            
            params = {'dates': today, 'limit': 50}
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            matchups = []
            
            if 'events' in data and data['events']:
                print(f"🏟️ Found {len(data['events'])} games scheduled for {date_display}:")
                print()
                
                for i, event in enumerate(data['events'], 1):
                    try:
                        matchup = self._parse_game_event(event)
                        if matchup:
                            matchups.append(matchup)
                            
                            # Display each matchup clearly
                            away_team = matchup['away_team']['name']
                            home_team = matchup['home_team']['name']
                            away_abbr = matchup['away_team']['abbreviation']
                            home_abbr = matchup['home_team']['abbreviation']
                            status = matchup['status']
                            venue = matchup['venue']
                            game_time = matchup.get('date', '')
                            
                            # Format game time if available
                            time_str = ""
                            if game_time:
                                try:
                                    dt = datetime.fromisoformat(game_time.replace('Z', '+00:00'))
                                    time_str = f" at {dt.strftime('%I:%M %p ET')}"
                                except:
                                    pass
                            
                            print(f"   {i:2d}. {away_team} ({away_abbr}) @ {home_team} ({home_abbr}){time_str}")
                            print(f"       Status: {status} | Venue: {venue}")
                            print()
                            
                    except Exception as e:
                        logger.error(f"Error parsing game: {e}")
                        continue
                        
            else:
                print(f"⚠️ No games found for {date_display}")
                print("💡 This is normal during off-season or off-days")
                print(f"💡 Try adjusting DAYS_OFFSET environment variable")
            
            print(f"✅ Successfully parsed {len(matchups)} game matchups")
            return matchups
            
        except Exception as e:
            logger.error(f"Error fetching ESPN games: {e}")
            print(f"❌ Failed to fetch games: {e}")
            return []
    
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
    
    def save_to_google_sheets(self, matchups):
        """Save matchup data to Google Sheets"""
        try:
            print(f"💾 Saving matchup data to Google Sheets: {self.spreadsheet_name}...")
            
            # Connect to Google Sheets
            scopes = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
            
            service_account_info = json.loads(os.environ['GOOGLE_SERVICE_ACCOUNT_CREDENTIALS'])
            credentials = Credentials.from_service_account_info(service_account_info, scopes=scopes)
            client = gspread.authorize(credentials)
            
            spreadsheet = client.open(self.spreadsheet_name)
            
            # Save game matchups
            self._save_matchups_sheet(spreadsheet, matchups)
            
            print(f"✅ Successfully saved matchup data to {self.spreadsheet_name}")
            
        except Exception as e:
            logger.error(f"Error saving to Google Sheets: {e}")
            raise
    
    def _save_matchups_sheet(self, spreadsheet, matchups):
        """Save game matchups to MATCHUPS sheet"""
        try:
            worksheet = spreadsheet.worksheet("MATCHUPS")
        except:
            worksheet = spreadsheet.add_worksheet(title="MATCHUPS", rows=100, cols=15)
        
        worksheet.clear()
        
        if matchups:
            # Calculate target date for display
            target_date = datetime.now() + timedelta(days=self.days_offset)
            date_display = target_date.strftime('%B %d, %Y')
            
            # Create headers
            headers = [
                'Game_ID', 'Date', 'Game_Time', 
                'Away_Team', 'Away_Abbr', 'Away_Team_ID',
                'Home_Team', 'Home_Abbr', 'Home_Team_ID',
                'Venue', 'Status', 'Matchup_Display', 'Fetched_At'
            ]
            
            # Flatten data for sheet
            flattened = []
            for game in matchups:
                # Create readable matchup display
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
            offset_text = ""
            if self.days_offset == 0:
                offset_text = "Today"
            elif self.days_offset == 1:
                offset_text = "Tomorrow"
            elif self.days_offset > 0:
                offset_text = f"{self.days_offset} days from now"
            else:
                offset_text = f"{abs(self.days_offset)} days ago"
            
            metadata = [
                [f'{self.sport} Matchups for {date_display}'],
                [f'Date Offset: {offset_text} (DAYS_OFFSET={self.days_offset})'],
                [f'Total Games: {len(matchups)}'],
                [f'Fetched At: {datetime.now().isoformat()}'],
                ['']  # Empty row
            ]
            
            # Combine metadata, headers, and data
            all_data = metadata + [headers] + flattened
            
            # Write to sheet
            worksheet.update(range_name='A1', values=all_data)
            
            print(f"📊 Saved {len(matchups)} matchups to MATCHUPS sheet")
            
        else:
            # Add a note if no games found
            target_date = datetime.now() + timedelta(days=self.days_offset)
            date_display = target_date.strftime('%B %d, %Y')
            
            worksheet.update(range_name='A1', values=[
                [f'No games found for {date_display}'],
                [f'Date Offset: DAYS_OFFSET={self.days_offset}'],
                [f'Fetched At: {datetime.now().isoformat()}'],
                [''],
                ['💡 Try adjusting DAYS_OFFSET in workflow settings']
            ])
            print("📝 Saved 'no games' notice to MATCHUPS sheet")

def main():
    """Main execution for Step 1 - configurable date and sport"""
    # Add argument parser for sport selection
    parser = argparse.ArgumentParser(description='Fetch sports matchups from ESPN')
    parser.add_argument('--sport', default='MLB', choices=['MLB', 'NFL', 'WNBA'],
                       help='Sport to fetch matchups for (default: MLB)')
    args = parser.parse_args()
    
    try:
        print(f"🏆 Fetching {args.sport} matchups...")
        fetcher = MatchupFetcher(sport=args.sport)
        
        # Show configuration
        if fetcher.days_offset != 0:
            print(f"⚙️ Configuration: DAYS_OFFSET = {fetcher.days_offset}")
        
        # Fetch games for configured date
        matchups = fetcher.fetch_todays_games()
        
        # Save to Google Sheets
        fetcher.save_to_google_sheets(matchups)
        
        target_date = datetime.now() + timedelta(days=fetcher.days_offset)
        print(f"\n🎯 STEP 1 COMPLETE:")
        print(f"   📅 Date: {target_date.strftime('%B %d, %Y')}")
        print(f"   🏟️ Games Found: {len(matchups)}")
        print(f"   💾 Data saved to {fetcher.spreadsheet_name} (MATCHUPS tab)")
        
        if matchups:
            print(f"\n📋 SUMMARY OF MATCHUPS:")
            for i, game in enumerate(matchups, 1):
                away = game['away_team']['abbreviation']
                home = game['home_team']['abbreviation']
                print(f"   {i:2d}. {away} @ {home}")
        
    except Exception as e:
        logger.error(f"Error in Step 1: {e}")
        print(f"❌ Step 1 failed: {e}")

if __name__ == "__main__":
    main()
# Add sports configuration import with fallback
try:
    from sports_config import get_sport_config
except ImportError:
    print("Warning: sports_config.py not found, using MLB defaults")
    get_sport_config = lambda x: None


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MatchupFetcher:
    def __init__(self, sport='MLB'):
        self.sport = sport.upper()
        self.days_offset = int(os.environ.get('DAYS_OFFSET', '0'))
        
        # Load sport-specific configuration
        config = get_sport_config(self.sport) if get_sport_config else None
        
        if config:
            # Use sport-specific settings
            self.espn_sport = config['espn_sport']
            self.espn_league = config['espn_league']
            self.spreadsheet_name = config['spreadsheet_name']
            print(f"✅ Loaded {self.sport} configuration")
        else:
            # Fallback to MLB defaults (keeps working if no config)
            self.espn_sport = 'baseball'
            self.espn_league = 'mlb'
            self.spreadsheet_name = 'MLB_Splash_Data'
            if self.sport != 'MLB':
                print(f"⚠️ No config for {self.sport}, using MLB defaults")
        
        # Build the ESPN API URL
        self.espn_base_url = f"https://site.api.espn.com/apis/site/v2/sports/{self.espn_sport}/{self.espn_league}"
        
    def fetch_todays_games(self):
        """Get games with configurable date offset"""
        print(f"⚾ STEP 1: FETCHING {self.sport} MATCHUPS")
        print("=" * 60)
        
        try:
            # Calculate target date with offset
            target_date = datetime.now() + timedelta(days=self.days_offset)
            today = target_date.strftime('%Y%m%d')
            date_display = target_date.strftime('%B %d, %Y')
            
            # Show what date we're fetching
            if self.days_offset == 0:
                print(f"📅 Fetching games for TODAY: {date_display}")
            elif self.days_offset == 1:
                print(f"📅 Fetching games for TOMORROW: {date_display}")
            elif self.days_offset > 0:
                print(f"📅 Fetching games for {self.days_offset} days from now: {date_display}")
            else:
                print(f"📅 Fetching games for {abs(self.days_offset)} days ago: {date_display}")
            
            url = f"{self.espn_base_url}/scoreboard"
            
            params = {'dates': today, 'limit': 50}
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            matchups = []
            
            if 'events' in data and data['events']:
                print(f"🏟️ Found {len(data['events'])} games scheduled for {date_display}:")
                print()
                
                for i, event in enumerate(data['events'], 1):
                    try:
                        matchup = self._parse_game_event(event)
                        if matchup:
                            matchups.append(matchup)
                            
                            # Display each matchup clearly
                            away_team = matchup['away_team']['name']
                            home_team = matchup['home_team']['name']
                            away_abbr = matchup['away_team']['abbreviation']
                            home_abbr = matchup['home_team']['abbreviation']
                            status = matchup['status']
                            venue = matchup['venue']
                            game_time = matchup.get('date', '')
                            
                            # Format game time if available
                            time_str = ""
                            if game_time:
                                try:
                                    dt = datetime.fromisoformat(game_time.replace('Z', '+00:00'))
                                    time_str = f" at {dt.strftime('%I:%M %p ET')}"
                                except:
                                    pass
                            
                            print(f"   {i:2d}. {away_team} ({away_abbr}) @ {home_team} ({home_abbr}){time_str}")
                            print(f"       Status: {status} | Venue: {venue}")
                            print()
                            
                    except Exception as e:
                        logger.error(f"Error parsing game: {e}")
                        continue
                        
            else:
                print(f"⚠️ No games found for {date_display}")
                print("💡 This is normal during off-season or off-days")
                print(f"💡 Try adjusting DAYS_OFFSET environment variable")
            
            print(f"✅ Successfully parsed {len(matchups)} game matchups")
            return matchups
            
        except Exception as e:
            logger.error(f"Error fetching ESPN games: {e}")
            print(f"❌ Failed to fetch games: {e}")
            return []
    
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
    
    def save_to_google_sheets(self, matchups):
        """Save matchup data to Google Sheets"""
        try:
            print(f"💾 Saving matchup data to Google Sheets: {self.spreadsheet_name}...")
            
            # Connect to Google Sheets
            scopes = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
            
            service_account_info = json.loads(os.environ['GOOGLE_SERVICE_ACCOUNT_CREDENTIALS'])
            credentials = Credentials.from_service_account_info(service_account_info, scopes=scopes)
            client = gspread.authorize(credentials)
            
            spreadsheet = client.open(self.spreadsheet_name)
            
            # Save game matchups
            self._save_matchups_sheet(spreadsheet, matchups)
            
            print(f"✅ Successfully saved matchup data to {self.spreadsheet_name}")
            
        except Exception as e:
            logger.error(f"Error saving to Google Sheets: {e}")
            raise
    
    def _save_matchups_sheet(self, spreadsheet, matchups):
        """Save game matchups to MATCHUPS sheet"""
        try:
            worksheet = spreadsheet.worksheet("MATCHUPS")
        except:
            worksheet = spreadsheet.add_worksheet(title="MATCHUPS", rows=100, cols=15)
        
        worksheet.clear()
        
        if matchups:
            # Calculate target date for display
            target_date = datetime.now() + timedelta(days=self.days_offset)
            date_display = target_date.strftime('%B %d, %Y')
            
            # Create headers
            headers = [
                'Game_ID', 'Date', 'Game_Time', 
                'Away_Team', 'Away_Abbr', 'Away_Team_ID',
                'Home_Team', 'Home_Abbr', 'Home_Team_ID',
                'Venue', 'Status', 'Matchup_Display', 'Fetched_At'
            ]
            
            # Flatten data for sheet
            flattened = []
            for game in matchups:
                # Create readable matchup display
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
            offset_text = ""
            if self.days_offset == 0:
                offset_text = "Today"
            elif self.days_offset == 1:
                offset_text = "Tomorrow"
            elif self.days_offset > 0:
                offset_text = f"{self.days_offset} days from now"
            else:
                offset_text = f"{abs(self.days_offset)} days ago"
            
            metadata = [
                [f'{self.sport} Matchups for {date_display}'],
                [f'Date Offset: {offset_text} (DAYS_OFFSET={self.days_offset})'],
                [f'Total Games: {len(matchups)}'],
                [f'Fetched At: {datetime.now().isoformat()}'],
                ['']  # Empty row
            ]
            
            # Combine metadata, headers, and data
            all_data = metadata + [headers] + flattened
            
            # Write to sheet
            worksheet.update(range_name='A1', values=all_data)
            
            print(f"📊 Saved {len(matchups)} matchups to MATCHUPS sheet")
            
        else:
            # Add a note if no games found
            target_date = datetime.now() + timedelta(days=self.days_offset)
            date_display = target_date.strftime('%B %d, %Y')
            
            worksheet.update(range_name='A1', values=[
                [f'No games found for {date_display}'],
                [f'Date Offset: DAYS_OFFSET={self.days_offset}'],
                [f'Fetched At: {datetime.now().isoformat()}'],
                [''],
                ['💡 Try adjusting DAYS_OFFSET in workflow settings']
            ])
            print("📝 Saved 'no games' notice to MATCHUPS sheet")

def main():
    """Main execution for Step 1 - configurable date and sport"""
    # Add argument parser for sport selection
    parser = argparse.ArgumentParser(description='Fetch sports matchups from ESPN')
    parser.add_argument('--sport', default='MLB', choices=['MLB', 'NFL', 'WNBA'],
                       help='Sport to fetch matchups for (default: MLB)')
    args = parser.parse_args()
    
    try:
        print(f"🏆 Fetching {args.sport} matchups...")
        fetcher = MatchupFetcher(sport=args.sport)
        
        # Show configuration
        if fetcher.days_offset != 0:
            print(f"⚙️ Configuration: DAYS_OFFSET = {fetcher.days_offset}")
        
        # Fetch games for configured date
        matchups = fetcher.fetch_todays_games()
        
        # Save to Google Sheets
        fetcher.save_to_google_sheets(matchups)
        
        target_date = datetime.now() + timedelta(days=fetcher.days_offset)
        print(f"\n🎯 STEP 1 COMPLETE:")
        print(f"   📅 Date: {target_date.strftime('%B %d, %Y')}")
        print(f"   🏟️ Games Found: {len(matchups)}")
        print(f"   💾 Data saved to {fetcher.spreadsheet_name} (MATCHUPS tab)")
        
        if matchups:
            print(f"\n📋 SUMMARY OF MATCHUPS:")
            for i, game in enumerate(matchups, 1):
                away = game['away_team']['abbreviation']
                home = game['home_team']['abbreviation']
                print(f"   {i:2d}. {away} @ {home}")
        
    except Exception as e:
        logger.error(f"Error in Step 1: {e}")
        print(f"❌ Step 1 failed: {e}")

if __name__ == "__main__":
    main()
