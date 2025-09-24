# find_pitcher_anchors.py - Step 6: Find pitchers with positive EV to use as parlay anchors
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json
import os
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PitcherAnchorFinder:
    """Step 6: Identify pitchers with positive EV to use as parlay anchors"""
    
    def __init__(self):
        # Target pitcher markets for correlation parlays
        self.PITCHER_MARKETS = [
            'pitcher_strikeouts',
            'pitcher_earned_runs', 
            'pitcher_hits_allowed',
            'pitcher_outs'
        ]
        
        # Minimum EV threshold for pitcher anchors
        self.MIN_PITCHER_EV = 0.02  # 2% minimum EV
        
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
    
    def read_ev_results(self, client):
        """Read EV results from Step 5"""
        try:
            print("📋 Reading EV results from Step 5...")
            spreadsheet = client.open("MLB_Splash_Data")
            ev_worksheet = spreadsheet.worksheet("EV_RESULTS")
            
            # Get all data and skip metadata rows
            all_data = ev_worksheet.get_all_values()
            
            # Find where the actual data starts (after metadata)
            data_start_row = 0
            for i, row in enumerate(all_data):
                if row and row[0] in ['Player', 'Name']:  # Look for header row
                    data_start_row = i
                    break
            
            if data_start_row == 0:
                # Fallback: assume data starts after row 6
                data_start_row = 6
            
            # Extract headers and data
            headers = all_data[data_start_row]
            data_rows = all_data[data_start_row + 1:]
            
            # Create DataFrame
            ev_df = pd.DataFrame(data_rows, columns=headers)
            
            # Remove empty rows
            ev_df = ev_df[ev_df['Player'].notna() & (ev_df['Player'] != '')]
            
            # Convert numeric columns
            numeric_columns = ['Splash_EV_Percentage', 'Num_Books_Used', 'Best_Odds', 'True_Prob']
            for col in numeric_columns:
                if col in ev_df.columns:
                    ev_df[col] = pd.to_numeric(ev_df[col], errors='coerce')
            
            print(f"✅ Successfully read {len(ev_df)} EV opportunities")
            return ev_df
            
        except Exception as e:
            logger.error(f"Error reading EV results: {e}")
            print(f"❌ Failed to read EV results: {e}")
            return pd.DataFrame()
    
    def read_pitcher_matchups(self, client):
        """Read pitcher matchups from Step 1"""
        try:
            print("📋 Reading pitcher matchup data from Step 1...")
            spreadsheet = client.open("MLB_Splash_Data")
            matchups_worksheet = spreadsheet.worksheet("PITCHER_MATCHUPS")
            matchups_data = matchups_worksheet.get_all_records()
            matchups_df = pd.DataFrame(matchups_data)
            
            print(f"✅ Successfully read {len(matchups_df)} pitcher matchups")
            return matchups_df
            
        except Exception as e:
            logger.error(f"Error reading pitcher matchups: {e}")
            print(f"❌ Failed to read pitcher matchups: {e}")
            return pd.DataFrame()
    
    def find_pitcher_anchors(self, ev_df):
        """Find pitchers with positive EV in target markets"""
        print("⚾ STEP 6: FINDING PITCHER ANCHORS")
        print("=" * 60)
        
        if ev_df.empty:
            print("❌ No EV data available")
            return pd.DataFrame()
        
        print(f"🎯 Looking for pitcher EVs in markets: {self.PITCHER_MARKETS}")
        print(f"📈 Minimum EV threshold: {self.MIN_PITCHER_EV:.1%}")
        
        # Filter for pitcher markets with sufficient EV
        pitcher_evs = ev_df[
            (ev_df['Market'].isin(self.PITCHER_MARKETS)) & 
            (ev_df['Splash_EV_Percentage'] >= self.MIN_PITCHER_EV)
        ].copy()
        
        if pitcher_evs.empty:
            print("❌ No pitcher EVs found above threshold")
            return pd.DataFrame()
        
        print(f"✅ Found {len(pitcher_evs)} pitcher EV opportunities")
        
        # Show breakdown by market
        market_breakdown = pitcher_evs['Market'].value_counts()
        print(f"📊 Pitcher EVs by market:")
        for market, count in market_breakdown.items():
            print(f"   • {market}: {count} opportunities")
        
        # Show top pitcher opportunities
        print(f"\n🏆 Top pitcher anchor opportunities:")
        top_pitchers = pitcher_evs.nlargest(5, 'Splash_EV_Percentage')
        for i, (_, row) in enumerate(top_pitchers.iterrows(), 1):
            print(f"   {i}. {row['Player']} - {row['Market']} {row['Line']} ({row['Bet_Type']})")
            print(f"      EV: {row['Splash_EV_Percentage']:.3f} ({row['Splash_EV_Percentage']:.1%}) | Books: {row['Num_Books_Used']}")
        
        return pitcher_evs
    
    def match_pitchers_to_opponents(self, pitcher_evs, matchups_df):
        """Match pitcher anchors to their opposing batters"""
        if pitcher_evs.empty or matchups_df.empty:
            print("❌ Missing pitcher EVs or matchup data")
            return []
        
        print(f"🔗 Matching {len(pitcher_evs)} pitcher anchors to opposing batters...")
        
        pitcher_anchor_matchups = []
        
        for _, pitcher_ev in pitcher_evs.iterrows():
            pitcher_name = pitcher_ev['Player']
            
            # Find matchups for this pitcher
            pitcher_matchups = matchups_df[matchups_df['Pitcher_Name'] == pitcher_name]
            
            for _, matchup in pitcher_matchups.iterrows():
                # Parse opposing batter names
                opposing_batters = []
                if matchup['Batter_Names'] and matchup['Batter_Names'] != '':
                    batter_names = str(matchup['Batter_Names']).split('; ')
                    for i, name in enumerate(batter_names[:5], 1):  # Top 5 batters
                        opposing_batters.append({
                            'name': name.strip(),
                            'position': i
                        })
                
                if opposing_batters:
                    pitcher_anchor_matchups.append({
                        'pitcher_anchor': pitcher_ev.to_dict(),
                        'game_id': matchup['Game_ID'],
                        'pitcher_team': matchup['Pitcher_Team'],
                        'opposing_team': matchup['Opposing_Team'],
                        'opposing_batters': opposing_batters,
                        'matchup_type': matchup['Matchup_Type']
                    })
        
        print(f"⚾ Created {len(pitcher_anchor_matchups)} pitcher anchor vs opposing batter matchups")
        
        if pitcher_anchor_matchups:
            # Show sample matchups
            print(f"\n🎯 Sample pitcher anchor matchups:")
            for i, matchup in enumerate(pitcher_anchor_matchups[:3], 1):
                anchor = matchup['pitcher_anchor']
                batters_count = len(matchup['opposing_batters'])
                print(f"   {i}. {anchor['Player']} ({matchup['pitcher_team']}) vs {batters_count} opposing batters ({matchup['opposing_team']})")
                print(f"      Anchor EV: {anchor['Splash_EV_Percentage']:.3f} | Market: {anchor['Market']} {anchor['Line']} ({anchor['Bet_Type']})")
        
        return pitcher_anchor_matchups
    
    def save_pitcher_anchors(self, pitcher_anchor_matchups, client):
        """Save pitcher anchor matchups for Step 7"""
        try:
            if not pitcher_anchor_matchups:
                print("❌ No pitcher anchor matchups to save")
                return
            
            print(f"💾 Saving {len(pitcher_anchor_matchups)} pitcher anchor matchups...")
            
            spreadsheet = client.open("MLB_Splash_Data")
            
            # Get or create PITCHER_ANCHORS worksheet
            try:
                worksheet = spreadsheet.worksheet("PITCHER_ANCHORS")
            except:
                worksheet = spreadsheet.add_worksheet(title="PITCHER_ANCHORS", rows=1000, cols=20)
            
            # Clear existing data
            worksheet.clear()
            
            # Format data for sheet
            formatted_data = []
            for i, matchup in enumerate(pitcher_anchor_matchups, 1):
                anchor = matchup['pitcher_anchor']
                opposing_batters = matchup['opposing_batters']
                
                # Create summary of opposing batters
                batter_names = [b['name'] for b in opposing_batters]
                batter_summary = '; '.join(batter_names)
                
                formatted_data.append([
                    f"ANCHOR_{i:03d}",
                    matchup['game_id'],
                    anchor['Player'],
                    anchor['Market'],
                    anchor['Line'],
                    anchor['Bet_Type'],
                    anchor['Splash_EV_Percentage'],
                    anchor['Num_Books_Used'],
                    anchor['Best_Odds'],
                    matchup['pitcher_team'],
                    matchup['opposing_team'],
                    len(opposing_batters),
                    batter_summary,
                    matchup['matchup_type'],
                    datetime.now().isoformat()
                ])
            
            # Add headers and metadata
            headers = [
                'Anchor_ID', 'Game_ID', 'Pitcher_Name', 'Market', 'Line', 'Bet_Type',
                'Pitcher_EV', 'Num_Books', 'Best_Odds', 'Pitcher_Team', 'Opposing_Team',
                'Num_Opposing_Batters', 'Opposing_Batter_Names', 'Matchup_Type', 'Created_At'
            ]
            
            metadata = [
                ['Pitcher Anchor Data', ''],
                ['Created At', datetime.now().isoformat()],
                ['Total Anchors', len(pitcher_anchor_matchups)],
                ['']
            ]
            
            all_data = metadata + [headers] + formatted_data
            
            # Write to sheet
            worksheet.update(range_name='A1', values=all_data)
            
            print("✅ Successfully saved pitcher anchors to PITCHER_ANCHORS sheet")
            
        except Exception as e:
            logger.error(f"Error saving pitcher anchors: {e}")
            print(f"❌ Failed to save pitcher anchors: {e}")
            raise

def main():
    """Main function for Step 6"""
    try:
        finder = PitcherAnchorFinder()
        
        # Connect to Google Sheets
        client = finder.connect_to_sheets()
        
        # Read EV results from Step 5
        ev_df = finder.read_ev_results(client)
        
        if ev_df.empty:
            print("❌ No EV results found from Step 5")
            return
        
        # Read pitcher matchups from Step 1
        matchups_df = finder.read_pitcher_matchups(client)
        
        if matchups_df.empty:
            print("❌ No pitcher matchup data found from Step 1")
            return
        
        # Find pitcher anchors
        pitcher_evs = finder.find_pitcher_anchors(ev_df)
        
        if pitcher_evs.empty:
            print("❌ No pitcher anchors found with sufficient EV")
            return
        
        # Match pitchers to opposing batters
        pitcher_anchor_matchups = finder.match_pitchers_to_opponents(pitcher_evs, matchups_df)
        
        if not pitcher_anchor_matchups:
            print("❌ No pitcher anchor matchups created")
            return
        
        # Save for Step 7
        finder.save_pitcher_anchors(pitcher_anchor_matchups, client)
        
        print(f"\n✅ STEP 6 COMPLETE:")
        print(f"   Pitcher anchors found: {len(pitcher_evs)}")
        print(f"   Anchor-opponent matchups: {len(pitcher_anchor_matchups)}")
        print(f"   Ready for Step 7 (Build Parlays)")
        
    except Exception as e:
        logger.error(f"Error in Step 6: {e}")
        print(f"❌ Step 6 failed: {e}")

if __name__ == "__main__":
    main()
