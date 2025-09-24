# matchup_fetcher.py
import requests
import json
import pandas as pd
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class MLBMatchupFetcher:
    """
    Fetch MLB game matchups, starting pitchers, and lineups from ESPN API
    """
    
    def __init__(self):
        self.espn_base_url = "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb"
        self.matchups = []
        
    def get_todays_games_with_lineups(self):
        """Get today's games with detailed matchup information"""
        print("📅 Fetching today's MLB games with lineups from ESPN...")
        
        try:
            today = datetime.now().strftime('%Y%m%d')
            url = f"{self.espn_base_url}/scoreboard"
            
            params = {'dates': today, 'limit': 50}
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            matchups = []
            
            if 'events' in data and data['events']:
                for event in data['events']:
                    try:
                        matchup = self._parse_game_matchup(event)
                        if matchup:
                            matchups.append(matchup)
                    except Exception as e:
                        logger.error(f"Error parsing game: {e}")
                        continue
            
            print(f"✅ Found {len(matchups)} game matchups")
            self.matchups = matchups
            return matchups
            
        except Exception as e:
            logger.error(f"Error fetching ESPN games: {e}")
            return []
    
    def _parse_game_matchup(self, event):
        """Parse individual game event to extract matchup information"""
        try:
            competition = event.get('competitions', [{}])[0]
            competitors = competition.get('competitors', [])
            
            if len(competitors) < 2:
                return None
            
            # Extract teams
            home_team = None
            away_team = None
            
            for competitor in competitors:
                team_info = competitor.get('team', {})
                team_name = team_info.get('displayName', '')
                team_abbr = team_info.get('abbreviation', '')
                
                if competitor.get('homeAway') == 'home':
                    home_team = {
                        'name': team_name,
                        'abbreviation': team_abbr,
                        'id': team_info.get('id')
                    }
                elif competitor.get('homeAway') == 'away':
                    away_team = {
                        'name': team_name, 
                        'abbreviation': team_abbr,
                        'id': team_info.get('id')
                    }
            
            if not home_team or not away_team:
                return None
            
            # Extract game info
            game_info = {
                'game_id': event.get('id'),
                'date': event.get('date'),
                'status': event.get('status', {}).get('type', {}).get('name', 'Unknown'),
                'home_team': home_team,
                'away_team': away_team,
                'venue': competition.get('venue', {}).get('fullName', 'Unknown')
            }
            
            # Try to get starting pitchers and lineups
            game_info.update(self._get_starting_pitchers(event))
            game_info.update(self._get_lineups(event))
            
            return game_info
            
        except Exception as e:
            logger.error(f"Error parsing game matchup: {e}")
            return None
    
    def _get_starting_pitchers(self, event):
        """Extract starting pitchers from event data"""
        pitchers = {'home_pitcher': None, 'away_pitcher': None}
        
        try:
            # ESPN sometimes has pitcher info in different places
            # This is a simplified approach - might need enhancement
            competition = event.get('competitions', [{}])[0]
            
            # Check for pitcher information in competition details
            if 'details' in competition:
                details = competition['details']
                # ESPN structure varies - this is a basic implementation
                # You might need to enhance this based on actual ESPN response structure
        
        except Exception as e:
            logger.error(f"Error extracting starting pitchers: {e}")
        
        return pitchers
    
    def _get_lineups(self, event):
        """Extract batting lineups (top 5 hitters) for each team"""
        lineups = {
            'home_lineup': self._get_default_lineup_positions(),
            'away_lineup': self._get_default_lineup_positions()
        }
        
        try:
            # ESPN doesn't always provide lineup data in scoreboard endpoint
            # For now, we'll use standard positions and enhance later if needed
            pass
            
        except Exception as e:
            logger.error(f"Error extracting lineups: {e}")
        
        return lineups
    
    def _get_default_lineup_positions(self):
        """Return default lineup positions when actual lineup unavailable"""
        return [
            {'position': 1, 'name': 'Unknown', 'id': None},
            {'position': 2, 'name': 'Unknown', 'id': None},
            {'position': 3, 'name': 'Unknown', 'id': None},
            {'position': 4, 'name': 'Unknown', 'id': None},
            {'position': 5, 'name': 'Unknown', 'id': None}
        ]
    
    def get_team_roster(self, team_id):
        """Get roster for specific team to help with lineup identification"""
        try:
            url = f"{self.espn_base_url}/teams/{team_id}/roster"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            roster = []
            
            if 'athletes' in data:
                for athlete in data['athletes']:
                    if athlete.get('position', {}).get('name') in ['Outfielder', 'Infielder', 'Catcher', 'Designated Hitter']:
                        roster.append({
                            'id': athlete.get('id'),
                            'name': athlete.get('displayName'),
                            'position': athlete.get('position', {}).get('name')
                        })
            
            return roster
            
        except Exception as e:
            logger.error(f"Error fetching team roster for {team_id}: {e}")
            return []
    
    def create_pitcher_batter_matchups(self):
        """Create pitcher vs opposing batter matchup mapping"""
        print("🎯 Creating pitcher vs batter matchup mappings...")
        
        pitcher_matchups = []
        
        for game in self.matchups:
            try:
                # Home pitcher vs Away batters
                if game.get('home_pitcher') and game['away_lineup']:
                    pitcher_matchups.append({
                        'game_id': game['game_id'],
                        'pitcher': game['home_pitcher'],
                        'pitcher_team': game['home_team']['name'],
                        'opposing_team': game['away_team']['name'],
                        'opposing_batters': game['away_lineup'][:5],  # Top 5 batters
                        'matchup_type': 'home_pitcher_vs_away_batters'
                    })
                
                # Away pitcher vs Home batters  
                if game.get('away_pitcher') and game['home_lineup']:
                    pitcher_matchups.append({
                        'game_id': game['game_id'],
                        'pitcher': game['away_pitcher'],
                        'pitcher_team': game['away_team']['name'],
                        'opposing_team': game['home_team']['name'],
                        'opposing_batters': game['home_lineup'][:5],  # Top 5 batters
                        'matchup_type': 'away_pitcher_vs_home_batters'
                    })
                        
            except Exception as e:
                logger.error(f"Error creating matchups for game {game.get('game_id')}: {e}")
                continue
        
        print(f"📊 Created {len(pitcher_matchups)} pitcher vs batter matchups")
        return pitcher_matchups
    
    def save_matchups_to_csv(self, filename="mlb_matchups.csv"):
        """Save matchup data to CSV for debugging"""
        if not self.matchups:
            print("❌ No matchups to save")
            return
        
        try:
            # Flatten matchup data for CSV
            flattened_data = []
            for game in self.matchups:
                flattened_data.append({
                    'game_id': game['game_id'],
                    'date': game['date'],
                    'home_team': game['home_team']['name'],
                    'away_team': game['away_team']['name'],
                    'home_pitcher': game.get('home_pitcher', {}).get('name', 'Unknown') if game.get('home_pitcher') else 'Unknown',
                    'away_pitcher': game.get('away_pitcher', {}).get('name', 'Unknown') if game.get('away_pitcher') else 'Unknown',
                    'venue': game['venue'],
                    'status': game['status']
                })
            
            df = pd.DataFrame(flattened_data)
            df.to_csv(filename, index=False)
            print(f"💾 Saved matchup data to {filename}")
            
        except Exception as e:
            logger.error(f"Error saving matchups to CSV: {e}")
    
    def run_matchup_fetch(self):
        """Run complete matchup fetching process"""
        print("⚾ MLB MATCHUP FETCHING")
        print("=" * 50)
        
        # Get games and matchups
        games = self.get_todays_games_with_lineups()
        
        if not games:
            print("❌ No games found")
            return None
        
        # Create pitcher vs batter matchups
        pitcher_matchups = self.create_pitcher_batter_matchups()
        
        # Save for debugging
        self.save_matchups_to_csv()
        
        print(f"\n🎯 SUMMARY:")
        print(f"   Games found: {len(games)}")
        print(f"   Pitcher matchups: {len(pitcher_matchups)}")
        
        return {
            'games': games,
            'pitcher_matchups': pitcher_matchups
        }

def main():
    """Test matchup fetching"""
    fetcher = MLBMatchupFetcher()
    results = fetcher.run_matchup_fetch()
    
    if results:
        print("\n📋 Sample Game:")
        if results['games']:
            print(json.dumps(results['games'][0], indent=2, default=str))

if __name__ == "__main__":
    main()
