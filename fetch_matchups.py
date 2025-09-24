# fetch_matchups.py - Step 1: Get today's game matchups from ESPN
import requests
import json
import pandas as pd
from datetime import datetime
import logging
import gspread
from google.oauth2.service_account import Credentials
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MatchupFetcher:
    """Step 1: Fetch today's MLB matchups, teams, pitchers, and lineups from ESPN"""
    
    def __init__(self):
        self.espn_base_url = "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb"
        self.matchups = []
        
    def fetch_todays_games(self):
        """Get today's games with teams and basic info"""
        print("⚾ STEP 1: FETCHING TODAY'S MLB MATCHUPS")
        print("=" * 60)
        
        try:
            today = datetime.now().strftime('%Y%m%d')
            url = f"{self.espn_base_url}/scoreboard"
            
            params = {'dates': today, 'limit': 50}
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            matchups = []
            
            if 'events' in data and data['events']:
                print(f"📅 Found {len(data['events'])} games scheduled for today")
                
                for event in data['events']:
                    try:
                        matchup = self._parse_game_event(event)
                        if matchup:
                            matchups.append(matchup)
                    except Exception as e:
                        logger.error(f"Error parsing game: {e}")
                        continue
                        
            else:
                print("⚠️ No games found for today")
            
            self.matchups = matchups
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
                **teams
            }
            
            return game_info
            
        except Exception as e:
            logger.error(f"Error parsing game event: {e}")
            return None
    
    def get_team_rosters(self):
        """Get rosters for all teams playing today"""
        print(f"👥 Fetching team rosters for {len(self.matchups)} games...")
        
        team_ids_seen = set()
        all_players = []
        
        for matchup in self.matchups:
            # Get unique team IDs
            home_id = matchup['home_team']['espn_id']
            away_id = matchup['away_team']['espn_id']
            
            for team_id, team_info in [(home_id, matchup['home_team']), (away_id, matchup['away_team'])]:
                if team_id not in team_ids_seen:
                    team_ids_seen.add(team_id)
                    roster = self._fetch_team_roster(team_id, team_info)
                    if roster:
                        all_players.extend(roster)
        
        print(f"📋 Found {len(all_players)} total players across all teams")
        return all_players
    
    def _fetch_team_roster(self, team_id, team_info):
        """Fetch roster for a specific team"""
        try:
            url = f"{self.espn_base_url}/teams/{team_id}/roster"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            roster = []
            
            if 'athletes' in data:
                for athlete in data['athletes']:
                    position = athlete.get('position', {}).get('name', 'Unknown')
                    
                    # Focus on position players (batters) and pitchers
                    if position in ['Outfielder', 'Infielder', 'Catcher', 'Designated Hitter', 'Pitcher']:
                        player_info = {
                            'espn_id': athlete.get('id'),
                            'name': athlete.get('displayName', ''),
                            'position': position,
                            'team_name': team_info['name'],
                            'team_abbr': team_info['abbreviation'],
                            'team_espn_id': team_id,
                            'jersey_number': athlete.get('jersey', ''),
                            'is_pitcher': position == 'Pitcher',
                            'is_batter': position in ['Outfielder', 'Infielder', 'Catcher', 'Designated Hitter']
                        }
                        roster.append(player_info)
                        
            print(f"  📄 {team_info['abbreviation']}: {len(roster)} players")
            return roster
            
        except Exception as e:
            logger.error(f"Error fetching roster for team {team_id}: {e}")
            return []
    
    def create_pitcher_batter_matchups(self, all_players):
        """Create pitcher vs opposing batter matchup combinations"""
        print(f"🎯 Creating pitcher vs opposing batter matchups...")
        
        pitcher_matchups = []
        
        for matchup in self.matchups:
            game_id = matchup['game_id']
            home_team_id = matchup['home_team']['espn_id']
            away_team_id = matchup['away_team']['espn_id']
            
            # Get pitchers and batters for each team
            home_pitchers = [p for p in all_players if p['team_espn_id'] == home_team_id and p['is_pitcher']]
            away_pitchers = [p for p in all_players if p['team_espn_id'] == away_team_id and p['is_pitcher']]
            
            home_batters = [p for p in all_players if p['team_espn_id'] == home_team_id and p['is_batter']]
            away_batters = [p for p in all_players if p['team_espn_id'] == away_team_id and p['is_batter']]
            
            # Home pitchers vs Away batters
            for pitcher in home_pitchers:
                if away_batters:
                    pitcher_matchups.append({
                        'game_id': game_id,
                        'pitcher': pitcher,
                        'opposing_batters': away_batters[:5],  # Top 5 batters
                        'pitcher_team': matchup['home_team']['name'],
                        'opposing_team': matchup['away_team']['name'],
                        'matchup_type': 'home_pitcher_vs_away_batters'
                    })
            
            # Away pitchers vs Home batters  
            for pitcher in away_pitchers:
                if home_batters:
                    pitcher_matchups.append({
                        'game_id': game_id,
                        'pitcher': pitcher,
                        'opposing_batters': home_batters[:5],  # Top 5 batters
                        'pitcher_team': matchup['away_team']['name'],
                        'opposing_team': matchup['home_team']['name'],
                        'matchup_type': 'away_pitcher_vs_home_batters'
                    })
        
        print(f"⚾ Created {len(pitcher_matchups)} pitcher vs batter matchup combinations")
        return pitcher_matchups
    
    def save_to_google_sheets(self, matchups, all_players, pitcher_matchups):
        """Save all matchup data to Google Sheets for next steps"""
        try:
            print("💾 Saving matchup data to Google Sheets...")
            
            # Connect to Google Sheets
            scopes = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
            
            service_account_info = json.loads(os.environ['GOOGLE_SERVICE_ACCOUNT_CREDENTIALS'])
            credentials = Credentials.from_service_account_info(service_account_info, scopes=scopes)
            client = gspread.authorize(credentials)
            
            spreadsheet = client.open("MLB_Splash_Data")
            
            # Save game matchups
            self._save_matchups_sheet(spreadsheet, matchups)
            
            # Save all players
            self._save_players_sheet(spreadsheet, all_players)
            
            # Save pitcher vs batter matchups
            self._save_pitcher_matchups_sheet(spreadsheet, pitcher_matchups)
            
            print("✅ Successfully saved all matchup data to Google Sheets")
            
        except Exception as e:
            logger.error(f"Error saving to Google Sheets: {e}")
            raise
    
    def _save_matchups_sheet(self, spreadsheet, matchups):
        """Save game matchups to MATCHUPS sheet"""
        try:
            worksheet = spreadsheet.worksheet("MATCHUPS")
        except:
            worksheet = spreadsheet.add_worksheet(title="MATCHUPS", rows=100, cols=10)
        
        worksheet.clear()
        
        if matchups:
            # Flatten data for sheet
            flattened = []
            for game in matchups:
                flattened.append([
                    game['game_id'],
                    game['date'],
                    game['home_team']['name'],
                    game['home_team']['abbreviation'],
                    game['away_team']['name'], 
                    game['away_team']['abbreviation'],
                    game['venue'],
                    game['status'],
                    datetime.now().isoformat()
                ])
            
            headers = ['Game_ID', 'Date', 'Home_Team', 'Home_Abbr', 'Away_Team', 'Away_Abbr', 'Venue', 'Status', 'Fetched_At']
            worksheet.update(range_name='A1', values=[headers] + flattened)
    
    def _save_players_sheet(self, spreadsheet, all_players):
        """Save all players to PLAYERS sheet"""
        try:
            worksheet = spreadsheet.worksheet("PLAYERS")
        except:
            worksheet = spreadsheet.add_worksheet(title="PLAYERS", rows=1000, cols=10)
        
        worksheet.clear()
        
        if all_players:
            # Convert to sheet format
            player_rows = []
            for player in all_players:
                player_rows.append([
                    player['name'],
                    player['position'],
                    player['team_name'],
                    player['team_abbr'],
                    player['team_espn_id'],
                    player['espn_id'],
                    player['is_pitcher'],
                    player['is_batter'],
                    datetime.now().isoformat()
                ])
            
            headers = ['Player_Name', 'Position', 'Team_Name', 'Team_Abbr', 'Team_ESPN_ID', 'Player_ESPN_ID', 'Is_Pitcher', 'Is_Batter', 'Fetched_At']
            worksheet.update(range_name='A1', values=[headers] + player_rows)
    
    def _save_pitcher_matchups_sheet(self, spreadsheet, pitcher_matchups):
        """Save pitcher vs batter matchups to PITCHER_MATCHUPS sheet"""
        try:
            worksheet = spreadsheet.worksheet("PITCHER_MATCHUPS") 
        except:
            worksheet = spreadsheet.add_worksheet(title="PITCHER_MATCHUPS", rows=1000, cols=15)
        
        worksheet.clear()
        
        if pitcher_matchups:
            matchup_rows = []
            for matchup in pitcher_matchups:
                pitcher = matchup['pitcher']
                batter_names = [b['name'] for b in matchup['opposing_batters']]
                
                matchup_rows.append([
                    matchup['game_id'],
                    pitcher['name'],
                    pitcher['team_name'],
                    matchup['opposing_team'],
                    len(matchup['opposing_batters']),
                    '; '.join(batter_names),
                    matchup['matchup_type'],
                    datetime.now().isoformat()
                ])
            
            headers = ['Game_ID', 'Pitcher_Name', 'Pitcher_Team', 'Opposing_Team', 'Num_Opposing_Batters', 'Batter_Names', 'Matchup_Type', 'Created_At']
            worksheet.update(range_name='A1', values=[headers] + matchup_rows)

def main():
    """Main execution for Step 1"""
    try:
        fetcher = MatchupFetcher()
        
        # Step 1a: Get today's games
        matchups = fetcher.fetch_todays_games()
        
        if not matchups:
            print("❌ No games found - cannot proceed")
            return
        
        # Step 1b: Get team rosters
        all_players = fetcher.get_team_rosters()
        
        if not all_players:
            print("❌ No players found - cannot proceed")
            return
        
        # Step 1c: Create pitcher vs batter matchups
        pitcher_matchups = fetcher.create_pitcher_batter_matchups(all_players)
        
        # Step 1d: Save everything to Google Sheets
        fetcher.save_to_google_sheets(matchups, all_players, pitcher_matchups)
        
        print("\n🎯 STEP 1 COMPLETE:")
        print(f"   Games: {len(matchups)}")
        print(f"   Players: {len(all_players)}")
        print(f"   Pitcher Matchups: {len(pitcher_matchups)}")
        print("   Data saved to Google Sheets for next steps")
        
    except Exception as e:
        logger.error(f"Error in Step 1: {e}")
        print(f"❌ Step 1 failed: {e}")

if __name__ == "__main__":
    main()
