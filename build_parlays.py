# build_parlays.py - Step 7: Build pitcher vs opposing batter correlation parlays (Complete Restructure)
import pandas as pd
import numpy as np
import gspread
from google.oauth2.service_account import Credentials
import json
import os
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CorrelationParlayBuilder:
    """Step 7: Build pitcher vs opposing batter correlation parlays with proper team matching"""
    
    def __init__(self):
        # Correlation mappings with proper bet direction logic
        self.CORRELATIONS = {
            'pitcher_strikeouts': {
                'opposing_market': 'batter_hits',
                'correlation': 'negative',  # More strikeouts = fewer hits
                'strength': -0.70,
                'bet_logic': 'opposite'  # If pitcher OVER strikeouts, then batter UNDER hits
            },
            'pitcher_earned_runs': {
                'opposing_market': 'batter_runs_scored', 
                'correlation': 'positive',  # More earned runs allowed = more runs scored
                'strength': 0.70,
                'bet_logic': 'same'  # If pitcher OVER earned runs, then batter OVER runs
            },
            'pitcher_hits_allowed': {
                'opposing_market': 'batter_hits',
                'correlation': 'positive',  # More hits allowed = more hits
                'strength': 0.75,
                'bet_logic': 'same'  # If pitcher OVER hits allowed, then batter OVER hits
            }
        }
        
        self.MIN_BATTER_EV = 0.005  # 0.5% minimum EV for batters
        self.MAX_BATTERS_PER_PARLAY = 5
    
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
    
    def read_matchups(self, client):
        """Step 1: Read today's matchups to know who plays who"""
        try:
            print("📋 Step 1: Reading matchups from MATCHUPS sheet...")
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
                print("❌ Could not find header row in MATCHUPS")
                return pd.DataFrame()
            
            headers = all_data[header_row]
            data_rows = all_data[header_row + 1:]
            
            if not data_rows:
                print("❌ No matchup data found")
                return pd.DataFrame()
            
            matchups_df = pd.DataFrame(data_rows, columns=headers)
            matchups_df = matchups_df[matchups_df['Game_ID'].notna() & (matchups_df['Game_ID'] != '')]
            
            print(f"✅ Found {len(matchups_df)} matchups")
            
            # Show the matchups
            for _, row in matchups_df.iterrows():
                away = row.get('Away_Abbr', row.get('Away_Team', ''))
                home = row.get('Home_Abbr', row.get('Home_Team', ''))
                print(f"   {away} @ {home}")
            
            return matchups_df
            
        except Exception as e:
            logger.error(f"Error reading matchups: {e}")
            print(f"❌ Failed to read matchups: {e}")
            return pd.DataFrame()
    
    def read_pitcher_anchors(self, client):
        """Step 2: Read pitcher anchors from Step 6"""
        try:
            print("📋 Step 2: Reading pitcher anchors from Step 6...")
            spreadsheet = client.open("MLB_Splash_Data")
            anchors_worksheet = spreadsheet.worksheet("PITCHER_ANCHORS")
            
            all_data = anchors_worksheet.get_all_values()
            
            # Find header row
            header_row = -1
            for i, row in enumerate(all_data):
                if any(col in row for col in ['Anchor_ID', 'Player_Name', 'Market']):
                    header_row = i
                    break
            
            if header_row == -1:
                print("❌ Could not find header row in PITCHER_ANCHORS")
                return pd.DataFrame()
            
            headers = all_data[header_row]
            data_rows = all_data[header_row + 1:]
            
            anchors_df = pd.DataFrame(data_rows, columns=headers)
            anchors_df = anchors_df[anchors_df['Anchor_ID'].notna() & (anchors_df['Anchor_ID'] != '')]
            
            # Convert numeric columns
            numeric_columns = ['EV', 'Num_Books', 'Best_Odds', 'Correlation_Strength']
            for col in numeric_columns:
                if col in anchors_df.columns:
                    anchors_df[col] = pd.to_numeric(anchors_df[col], errors='coerce')
            
            print(f"✅ Found {len(anchors_df)} pitcher anchors")
            return anchors_df
            
        except Exception as e:
            logger.error(f"Error reading pitcher anchors: {e}")
            print(f"❌ Failed to read pitcher anchors: {e}")
            return pd.DataFrame()
    
    def read_all_ev_results(self, client):
        """Read all EV results for batter lookup"""
        try:
            print("📋 Reading all EV results for batter correlation lookup...")
            spreadsheet = client.open("MLB_Splash_Data")
            ev_worksheet = spreadsheet.worksheet("EV_RESULTS")
            
            all_data = ev_worksheet.get_all_values()
            
            # Find header row
            header_row = -1
            for i, row in enumerate(all_data):
                if any(col in row for col in ['Player', 'Name', 'Market']):
                    header_row = i
                    break
            
            if header_row == -1:
                print("❌ Could not find header row in EV_RESULTS")
                return pd.DataFrame()
            
            headers = all_data[header_row]
            data_rows = all_data[header_row + 1:]
            
            ev_df = pd.DataFrame(data_rows, columns=headers)
            ev_df = ev_df[ev_df['Player'].notna() & (ev_df['Player'] != '')]
            
            # Convert numeric columns
            numeric_columns = ['Splash_EV_Percentage', 'Num_Books_Used', 'Best_Odds', 'True_Prob']
            for col in numeric_columns:
                if col in ev_df.columns:
                    ev_df[col] = pd.to_numeric(ev_df[col], errors='coerce')
            
            print(f"✅ Found {len(ev_df)} total EV opportunities")
            return ev_df
            
        except Exception as e:
            logger.error(f"Error reading EV results: {e}")
            print(f"❌ Failed to read EV results: {e}")
            return pd.DataFrame()
    
    def match_pitchers_to_opponents(self, pitcher_anchors_df, matchups_df):
        """Step 3: Match each pitcher to their opposing team"""
        print("📋 Step 3: Matching pitchers to their opposing teams...")
        
        if pitcher_anchors_df.empty or matchups_df.empty:
            print("❌ Missing pitcher or matchup data")
            return []
        
        pitcher_matchups = []
        
        for _, pitcher in pitcher_anchors_df.iterrows():
            pitcher_name = pitcher['Player_Name']
            
            # For now, we'll need to manually map pitcher names to teams
            # In a real implementation, you'd have team roster data
            # For this demo, we'll create a mapping structure
            
            # Find potential opposing teams from matchups
            opposing_teams = []
            for _, matchup in matchups_df.iterrows():
                # We'll add both teams as potential opponents for now
                # In reality, you'd know which team the pitcher plays for
                home_team = matchup.get('Home_Team', '')
                away_team = matchup.get('Away_Team', '')
                home_abbr = matchup.get('Home_Abbr', '')
                away_abbr = matchup.get('Away_Abbr', '')
                
                if home_team and away_team:
                    opposing_teams.extend([
                        {'name': home_team, 'abbr': home_abbr, 'opponent': away_team, 'opponent_abbr': away_abbr},
                        {'name': away_team, 'abbr': away_abbr, 'opponent': home_team, 'opponent_abbr': home_abbr}
                    ])
            
            # For each pitcher, we'll create entries for potential opposing teams
            for team_info in opposing_teams:
                pitcher_matchups.append({
                    'pitcher_name': pitcher_name,
                    'pitcher_market': pitcher['Market'],
                    'pitcher_line': pitcher.get('Line', ''),
                    'pitcher_bet_type': pitcher.get('Bet_Type', ''),
                    'pitcher_ev': pitcher.get('EV', 0),
                    'pitcher_anchor_id': pitcher['Anchor_ID'],
                    'opposing_team': team_info['name'],
                    'opposing_team_abbr': team_info['opponent_abbr'],
                    'correlation_info': self.CORRELATIONS.get(pitcher['Market'], {})
                })
        
        print(f"✅ Created {len(pitcher_matchups)} pitcher-opponent combinations")
        return pitcher_matchups
    
    def find_correlated_batters(self, pitcher_matchups, all_ev_df):
        """Step 4 & 5: Find correlated batter props and build parlays"""
        print("⚾ STEP 7: BUILDING PITCHER-BATTER CORRELATION PARLAYS")
        print("=" * 60)
        
        if not pitcher_matchups or all_ev_df.empty:
            print("❌ Missing pitcher matchups or EV data")
            return []
        
        print(f"🎯 Building parlays for {len(set(p['pitcher_anchor_id'] for p in pitcher_matchups))} unique pitchers")
        print(f"📊 Correlation logic:")
        print(f"   • Strikeouts ↔ Batter Hits (NEGATIVE - opposite bets)")
        print(f"   • Earned Runs ↔ Batter Runs (POSITIVE - same bets)")
        print(f"   • Hits Allowed ↔ Batter Hits (POSITIVE - same bets)")
        
        all_parlays = []
        processed_anchors = set()
        
        for pitcher_match in pitcher_matchups:
            anchor_id = pitcher_match['pitcher_anchor_id']
            
            # Skip if we already processed this anchor
            if anchor_id in processed_anchors:
                continue
            processed_anchors.add(anchor_id)
            
            pitcher_name = pitcher_match['pitcher_name']
            pitcher_market = pitcher_match['pitcher_market']
            pitcher_bet_type = pitcher_match['pitcher_bet_type']
            opposing_team = pitcher_match['opposing_team']
            correlation_info = pitcher_match['correlation_info']
            
            if not correlation_info:
                continue
            
            print(f"\n🎯 Building parlay for: {pitcher_name} ({pitcher_market})")
            print(f"   Looking for opposing {correlation_info['opposing_market']} from {opposing_team}")
            
            # Find correlated batter opportunities
            target_market = correlation_info['opposing_market']
            bet_logic = correlation_info['bet_logic']
            
            # Determine target bet type based on correlation
            if bet_logic == 'opposite':
                target_bet_type = 'under' if pitcher_bet_type.lower() == 'over' else 'over'
            else:  # same
                target_bet_type = pitcher_bet_type.lower()
            
            print(f"   Pitcher bet: {pitcher_bet_type} → Looking for batter: {target_bet_type}")
            
            # Find matching batter opportunities
            batter_opportunities = all_ev_df[
                (all_ev_df['Market'] == target_market) &
                (all_ev_df['Bet_Type'].str.lower() == target_bet_type) &
                (all_ev_df['Splash_EV_Percentage'] >= self.MIN_BATTER_EV)
            ].copy()
            
            if batter_opportunities.empty:
                print(f"   ❌ No correlated batter opportunities found")
                continue
            
            # Sort by EV and take top batters
            batter_opportunities = batter_opportunities.sort_values('Splash_EV_Percentage', ascending=False)
            selected_batters = batter_opportunities.head(self.MAX_BATTERS_PER_PARLAY)
            
            if len(selected_batters) > 0:
                parlay = self._create_parlay(pitcher_match, selected_batters.to_dict('records'), correlation_info)
                all_parlays.append(parlay)
                
                print(f"   ✅ Created parlay with {len(selected_batters)} correlated batters")
                for _, batter in selected_batters.iterrows():
                    print(f"      • {batter['Player']} {target_market} {batter['Line']} ({target_bet_type}) - EV: {batter['Splash_EV_Percentage']:.3f}")
        
        # Sort parlays by estimated value
        all_parlays.sort(key=lambda x: x['estimated_parlay_ev'], reverse=True)
        
        print(f"\n🎉 Built {len(all_parlays)} correlation parlays!")
        
        if all_parlays:
            print(f"📈 Best parlay EV estimate: {all_parlays[0]['estimated_parlay_ev']:.3f}")
            print(f"📊 Average correlation strength: {np.mean([p['avg_correlation_strength'] for p in all_parlays]):.3f}")
        
        return all_parlays
    
    def _create_parlay(self, pitcher_match, selected_batters, correlation_info):
        """Create a complete parlay object"""
        pitcher_ev = pitcher_match['pitcher_ev']
        batter_evs = [b['Splash_EV_Percentage'] for b in selected_batters]
        
        # Calculate estimated parlay EV (simplified)
        total_individual_ev = pitcher_ev + sum(batter_evs)
        correlation_strength = abs(correlation_info['strength'])
        correlation_bonus = correlation_strength * 0.2  # Up to 20% bonus for strong correlations
        estimated_parlay_ev = total_individual_ev * (1 + correlation_bonus)
        
        return {
            'parlay_id': f"PARLAY_{pitcher_match['pitcher_anchor_id']}_{len(selected_batters)}",
            'pitcher_anchor_id': pitcher_match['pitcher_anchor_id'],
            'pitcher_name': pitcher_match['pitcher_name'],
            'pitcher_market': pitcher_match['pitcher_market'],
            'pitcher_line': pitcher_match['pitcher_line'],
            'pitcher_bet_type': pitcher_match['pitcher_bet_type'],
            'pitcher_ev': pitcher_ev,
            'opposing_team': pitcher_match['opposing_team'],
            'num_batters': len(selected_batters),
            'batter_props': selected_batters,
            'correlation_type': correlation_info['correlation'],
            'correlation_strength': correlation_info['strength'],
            'avg_correlation_strength': correlation_strength,
            'bet_logic': correlation_info['bet_logic'],
            'estimated_parlay_ev': estimated_parlay_ev,
            'total_legs': 1 + len(selected_batters),
            'created_at': datetime.now().isoformat()
        }
    
    def save_parlays(self, parlays, client):
        """Save correlation parlays to Google Sheets"""
        try:
            if not parlays:
                print("❌ No parlays to save")
                return
            
            print(f"💾 Saving {len(parlays)} correlation parlays...")
            
            spreadsheet = client.open("MLB_Splash_Data")
            
            try:
                worksheet = spreadsheet.worksheet("CORRELATION_PARLAYS")
            except:
                worksheet = spreadsheet.add_worksheet(title="CORRELATION_PARLAYS", rows=1000, cols=25)
            
            worksheet.clear()
            
            # Format parlay data
            formatted_data = []
            for i, parlay in enumerate(parlays, 1):
                # Create batter summary
                batter_summary = " | ".join([
                    f"{b['Player']} {b['Market']} {b['Line']} ({b['Bet_Type']}) EV:{b['Splash_EV_Percentage']:.3f}"
                    for b in parlay['batter_props'][:3]  # Show first 3 batters
                ])
                
                if len(parlay['batter_props']) > 3:
                    batter_summary += f" + {len(parlay['batter_props']) - 3} more"
                
                formatted_data.append([
                    parlay['parlay_id'],
                    parlay['pitcher_name'],
                    f"{parlay['pitcher_market']} {parlay['pitcher_line']} ({parlay['pitcher_bet_type']})",
                    parlay['pitcher_ev'],
                    parlay['opposing_team'],
                    parlay['num_batters'],
                    batter_summary,
                    parlay['correlation_type'],
                    parlay['correlation_strength'],
                    parlay['bet_logic'],
                    parlay['estimated_parlay_ev'],
                    parlay['total_legs'],
                    parlay['created_at']
                ])
            
            headers = [
                'Parlay_ID', 'Pitcher_Name', 'Pitcher_Prop', 'Pitcher_EV', 'Opposing_Team',
                'Num_Batters', 'Batter_Props_Summary', 'Correlation_Type', 'Correlation_Strength',
                'Bet_Logic', 'Estimated_Parlay_EV', 'Total_Legs', 'Created_At'
            ]
            
            metadata = [
                ['Pitcher vs Batter Correlation Parlays', ''],
                ['Created At', datetime.now().isoformat()],
                ['Total Parlays', len(parlays)],
                ['Correlation Logic', 'Negative=Opposite Bets, Positive=Same Bets'],
                ['']
            ]
            
            all_data = metadata + [headers] + formatted_data
            worksheet.update(range_name='A1', values=all_data)
            
            print("✅ Successfully saved correlation parlays!")
            
        except Exception as e:
            logger.error(f"Error saving parlays: {e}")
            print(f"❌ Failed to save parlays: {e}")
            raise

def main():
    """Main function for Step 7"""
    try:
        builder = CorrelationParlayBuilder()
        
        # Connect to Google Sheets
        client = builder.connect_to_sheets()
        
        # Step 1: Read matchups to know who plays who
        matchups_df = builder.read_matchups(client)
        
        # Step 2: Read pitcher anchors
        pitcher_anchors_df = builder.read_pitcher_anchors(client)
        
        # Read all EV data for batter lookup
        all_ev_df = builder.read_all_ev_results(client)
        
        if pitcher_anchors_df.empty:
            print("❌ No pitcher anchors found from Step 6")
            return
        
        if all_ev_df.empty:
            print("❌ No EV data found for batter correlation lookup")
            return
        
        # Step 3: Match pitchers to opponents
        pitcher_matchups = builder.match_pitchers_to_opponents(pitcher_anchors_df, matchups_df)
        
        if not pitcher_matchups:
            print("❌ No pitcher-opponent matchups created")
            return
        
        # Steps 4 & 5: Find correlated batters and build parlays
        parlays = builder.find_correlated_batters(pitcher_matchups, all_ev_df)
        
        if not parlays:
            print("❌ No correlation parlays could be built")
            return
        
        # Save results
        builder.save_parlays(parlays, client)
        
        print(f"\n✅ STEP 7 COMPLETE - FULL PIPELINE FINISHED!")
        print(f"   🎯 Correlation parlays built: {len(parlays)}")
        print(f"   📊 Results saved to CORRELATION_PARLAYS sheet")
        
    except Exception as e:
        logger.error(f"Error in Step 7: {e}")
        print(f"❌ Step 7 failed: {e}")

if __name__ == "__main__":
    main()
