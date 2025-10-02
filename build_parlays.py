# build_parlays.py - Step 7: Build pitcher vs opposing batter correlation parlays (Simplified with Team Data)
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
    """Step 7: Build pitcher vs opposing batter correlation parlays using team data from Step 2"""
    
    def __init__(self):
        # Correlation mappings with proper bet direction logic
        self.CORRELATIONS = {
            'pitcher_strikeouts': {
                'opposing_market': 'batter_hits',
                'correlation': 'negative',  # More strikeouts = fewer hits
                'strength': -0.70,
                'bet_logic': 'opposite'  # Pitcher OVER → Batter UNDER
            },
            'pitcher_earned_runs': {
                'opposing_market': 'batter_runs_scored', 
                'correlation': 'positive',  # More earned runs = more runs scored
                'strength': 0.70,
                'bet_logic': 'same'  # Pitcher OVER → Batter OVER
            },
            'pitcher_hits_allowed': {
                'opposing_market': 'batter_hits',
                'correlation': 'positive',  # More hits allowed = more hits
                'strength': 0.75,
                'bet_logic': 'same'  # Pitcher OVER → Batter OVER
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
    
    def read_pitcher_anchors(self, client):
        """Step 1: Read pitcher anchors from Step 6"""
        try:
            print("📋 Step 1: Reading pitcher anchors from Step 6...")
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
    
    def read_all_ev_results_with_teams(self, client):
        """Step 2: Read all EV results with team information from Step 2"""
        try:
            print("📋 Step 2: Reading all EV results with team data...")
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
            
            # Check if we have team data
            team_columns = ['Team', 'Home_Team', 'Away_Team']
            missing_columns = [col for col in team_columns if col not in ev_df.columns]
            
            if missing_columns:
                print(f"⚠️ Missing team columns: {missing_columns}")
                print("   Step 2 (fetch_odds_data.py) may need to be re-run with team data")
                return pd.DataFrame()
            
            # Show team breakdown
            if 'Team' in ev_df.columns:
                team_counts = ev_df['Team'].value_counts()
                print(f"📊 EV opportunities by team: {dict(team_counts.head())}")
            
            return ev_df
            
        except Exception as e:
            logger.error(f"Error reading EV results: {e}")
            print(f"❌ Failed to read EV results: {e}")
            return pd.DataFrame()
    
    def build_correlation_parlays(self, pitcher_anchors_df, all_ev_df):
        """Step 3: Build correlation parlays using team data"""
        print("⚾ STEP 7: BUILDING PITCHER-BATTER CORRELATION PARLAYS")
        print("=" * 60)
        
        if pitcher_anchors_df.empty or all_ev_df.empty:
            print("❌ Missing pitcher anchors or EV data")
            return []
        
        print(f"🎯 Building parlays with team-based opponent matching:")
        print(f"📊 Correlation logic:")
        print(f"   • Strikeouts ↔ Batter Hits (NEGATIVE - opposite bets)")
        print(f"   • Earned Runs ↔ Batter Runs (POSITIVE - same bets)")
        print(f"   • Hits Allowed ↔ Batter Hits (POSITIVE - same bets)")
        
        all_parlays = []
        
        for _, pitcher in pitcher_anchors_df.iterrows():
            pitcher_name = pitcher['Player_Name']
            pitcher_market = pitcher['Market']
            pitcher_bet_type = pitcher.get('Bet_Type', '').lower()
            pitcher_ev = pitcher.get('EV', 0)
            pitcher_anchor_id = pitcher['Anchor_ID']
            
            # Get correlation info
            correlation_info = self.CORRELATIONS.get(pitcher_market)
            if not correlation_info:
                print(f"   ⏭️ {pitcher_name}: No correlation mapping for {pitcher_market}")
                continue
            
            print(f"\n🎯 Building parlay for: {pitcher_name} ({pitcher_market})")
            
            # Find this pitcher in the EV data to get their team info
            pitcher_ev_rows = all_ev_df[
                (all_ev_df['Player'].str.lower() == pitcher_name.lower()) &
                (all_ev_df['Market'] == pitcher_market)
            ]
            
            if pitcher_ev_rows.empty:
                print(f"   ❌ Could not find {pitcher_name} in EV data with team info")
                continue
            
            # Get pitcher's team and game info from EV data
            pitcher_row = pitcher_ev_rows.iloc[0]
            pitcher_team = pitcher_row.get('Team', '')
            home_team = pitcher_row.get('Home_Team', '')
            away_team = pitcher_row.get('Away_Team', '')
            
            if not pitcher_team or not home_team or not away_team:
                print(f"   ❌ Missing team data for {pitcher_name}")
                continue
            
            # Determine opposing team
            opposing_team = away_team if pitcher_team == home_team else home_team
            print(f"   🏟️ {pitcher_name} ({pitcher_team}) vs {opposing_team}")
            
            # Find correlated batter opportunities from opposing team
            target_market = correlation_info['opposing_market']
            bet_logic = correlation_info['bet_logic']
            
            # Determine target bet type based on correlation
            if bet_logic == 'opposite':
                target_bet_type = 'under' if pitcher_bet_type == 'over' else 'over'
            else:  # same
                target_bet_type = pitcher_bet_type
            
            print(f"   📊 Pitcher: {pitcher_bet_type} {pitcher_market}")
            print(f"   📊 Looking for: {target_bet_type} {target_market} from {opposing_team}")
            
            # Find matching batter opportunities from opposing team
            batter_opportunities = all_ev_df[
                (all_ev_df['Team'] == opposing_team) &
                (all_ev_df['Market'] == target_market) &
                (all_ev_df['Bet_Type'].str.lower() == target_bet_type) &
                (all_ev_df['Splash_EV_Percentage'] >= self.MIN_BATTER_EV)
            ].copy()
            
            if batter_opportunities.empty:
                print(f"   ❌ No {target_bet_type} {target_market} opportunities from {opposing_team}")
                continue
            
            # Sort by EV and take top batters
            batter_opportunities = batter_opportunities.sort_values('Splash_EV_Percentage', ascending=False)
            selected_batters = batter_opportunities.head(self.MAX_BATTERS_PER_PARLAY)
            
            if len(selected_batters) > 0:
                parlay = self._create_parlay(pitcher, selected_batters, correlation_info, opposing_team)
                all_parlays.append(parlay)
                
                print(f"   ✅ Created parlay with {len(selected_batters)} opposing batters:")
                for _, batter in selected_batters.iterrows():
                    print(f"      • {batter['Player']} ({opposing_team}) {target_market} {batter.get('Line', 'N/A')} ({target_bet_type}) - EV: {batter['Splash_EV_Percentage']:.3f}")
        
        # Sort parlays by estimated value
        if all_parlays:
            all_parlays.sort(key=lambda x: x['estimated_parlay_ev'], reverse=True)
            
            print(f"\n🎉 Built {len(all_parlays)} correlation parlays!")
            print(f"📈 Best parlay EV estimate: {all_parlays[0]['estimated_parlay_ev']:.3f}")
            print(f"📊 Average correlation strength: {np.mean([p['avg_correlation_strength'] for p in all_parlays]):.3f}")
        else:
            print(f"\n❌ No correlation parlays could be built")
        
        return all_parlays
    
    def _create_parlay(self, pitcher, selected_batters, correlation_info, opposing_team):
        """Create a complete parlay object"""
        pitcher_ev = pitcher.get('EV', 0)
        batter_evs = selected_batters['Splash_EV_Percentage'].tolist()
        
        # Calculate estimated parlay EV (simplified)
        total_individual_ev = pitcher_ev + sum(batter_evs)
        correlation_strength = abs(correlation_info['strength'])
        correlation_bonus = correlation_strength * 0.2  # Up to 20% bonus for strong correlations
        estimated_parlay_ev = total_individual_ev * (1 + correlation_bonus)
        
        return {
            'parlay_id': f"PARLAY_{pitcher['Anchor_ID']}_{len(selected_batters)}",
            'pitcher_anchor_id': pitcher['Anchor_ID'],
            'pitcher_name': pitcher['Player_Name'],
            'pitcher_team': selected_batters.iloc[0].get('Home_Team', '') if pitcher.get('Team') == selected_batters.iloc[0].get('Home_Team', '') else selected_batters.iloc[0].get('Away_Team', ''),
            'pitcher_market': pitcher['Market'],
            'pitcher_line': pitcher.get('Line', ''),
            'pitcher_bet_type': pitcher.get('Bet_Type', ''),
            'pitcher_ev': pitcher_ev,
            'opposing_team': opposing_team,
            'num_batters': len(selected_batters),
            'batter_props': selected_batters.to_dict('records'),
            'correlation_type': correlation_info['correlation'],
            'correlation_strength': correlation_info['strength'],
            'avg_correlation_strength': correlation_strength,
            'bet_logic': correlation_info['bet_logic'],
            'estimated_parlay_ev': estimated_parlay_ev,
            'total_legs': 1 + len(selected_batters),
            'created_at': datetime.now().isoformat()
        }
    
    def save_parlays_compressed(self, parlays, client):
        """Save all parlay data with each batter compressed into a single cell"""
        try:
            if not parlays:
                print("❌ No parlays to save")
                return
            
            print(f"💾 Saving {len(parlays)} correlation parlays with compressed batter format...")
            
            spreadsheet = client.open("MLB_Splash_Data")
            
            try:
                worksheet = spreadsheet.worksheet("CORRELATION_PARLAYS")
            except:
                worksheet = spreadsheet.add_worksheet(title="CORRELATION_PARLAYS", rows=1000, cols=25)
            
            worksheet.clear()
            
            # Find maximum number of batters across all parlays
            max_batters = max(len(parlay['batter_props']) for parlay in parlays) if parlays else 0
            print(f"📊 Maximum batters per parlay: {max_batters}")
            
            # Build headers with compressed batter format
            base_headers = [
                'Parlay_ID', 'Pitcher_Name', 'Pitcher_Team', 'Pitcher_Market', 'Pitcher_Line', 
                'Pitcher_Bet_Type', 'Pitcher_EV', 'Opposing_Team', 'Num_Batters', 
                'Correlation_Type', 'Correlation_Strength', 'Bet_Logic', 
                'Estimated_Parlay_EV', 'Total_Legs', 'Created_At'
            ]
            
            # Add compressed batter columns
            batter_headers = [f'Batter_{i}' for i in range(1, max_batters + 1)]
            all_headers = base_headers + batter_headers
            
            # Format parlay data with compressed batter cells
            formatted_data = []
            for parlay in parlays:
                # Base parlay information
                row_data = [
                    parlay['parlay_id'],
                    parlay['pitcher_name'],
                    parlay['pitcher_team'],
                    parlay['pitcher_market'],
                    parlay['pitcher_line'],
                    parlay['pitcher_bet_type'],
                    parlay['pitcher_ev'],
                    parlay['opposing_team'],
                    parlay['num_batters'],
                    parlay['correlation_type'],
                    parlay['correlation_strength'],
                    parlay['bet_logic'],
                    parlay['estimated_parlay_ev'],
                    parlay['total_legs'],
                    parlay['created_at']
                ]
                
                # Add compressed batter data for each batter slot
                for i in range(max_batters):
                    if i < len(parlay['batter_props']):
                        # Batter exists - compress all data into single cell
                        batter = parlay['batter_props'][i]
                        
                        # Format: "Name, Market, Line, Bet_Type, EV, Best_Odds"
                        compressed_batter = f"{batter['Player']}, {batter['Market']}, {batter.get('Line', 'N/A')}, {batter.get('Bet_Type', 'N/A')}, {batter['Splash_EV_Percentage']:.3f}, {batter.get('Best_Odds', 'N/A')}"
                        
                        row_data.append(compressed_batter)
                    else:
                        # No batter for this slot - add empty value
                        row_data.append('')
                
                formatted_data.append(row_data)
            
            # Add metadata with format explanation
            metadata = [
                ['Pitcher vs Batter Correlation Parlays (Compressed Format)', ''],
                ['Created At', datetime.now().isoformat()],
                ['Total Parlays', len(parlays)],
                ['Max Batters Per Parlay', max_batters],
                ['Batter Format', 'Name, Market, Line, Bet_Type, EV, Best_Odds'],
                ['Example', 'Jose Altuve, Hits, 1.5, Under, 0.031, +125'],
                ['Correlation Logic', 'Negative=Opposite Bets, Positive=Same Bets'],
                ['']
            ]
            
            all_data = metadata + [all_headers] + formatted_data
            worksheet.update(range_name='A1', values=all_data)
            
            print("✅ Successfully saved compressed parlays to CORRELATION_PARLAYS sheet!")
            print(f"📊 Format: {max_batters} batter columns with compressed data")
            print(f"🔧 Batter format: Name, Market, Line, Bet_Type, EV, Best_Odds")
            
        except Exception as e:
            logger.error(f"Error saving compressed parlays: {e}")
            print(f"❌ Failed to save parlays: {e}")
            raise

def main():
    """Main function for simplified Step 7"""
    try:
        builder = CorrelationParlayBuilder()
        
        # Connect to Google Sheets
        client = builder.connect_to_sheets()
        
        # Step 1: Read pitcher anchors
        pitcher_anchors_df = builder.read_pitcher_anchors(client)
        
        if pitcher_anchors_df.empty:
            print("❌ No pitcher anchors found from Step 6")
            return
        
        # Step 2: Read all EV data with team information
        all_ev_df = builder.read_all_ev_results_with_teams(client)
        
        if all_ev_df.empty:
            print("❌ No EV data with team info found")
            print("   💡 Make sure Step 2 (fetch_odds_data.py) includes team data")
            return
        
        # Step 3: Build correlation parlays using team data
        parlays = builder.build_correlation_parlays(pitcher_anchors_df, all_ev_df)
        
        if not parlays:
            print("❌ No correlation parlays could be built")
            return
        
        # Save results
        builder.save_parlays(parlays, client)
        
        print(f"\n✅ STEP 7 COMPLETE - SIMPLIFIED PIPELINE!")
        print(f"   🎯 Correlation parlays built: {len(parlays)}")
        print(f"   🏟️ Team-based opponent matching successful")
        print(f"   📊 Results saved to CORRELATION_PARLAYS sheet")
        
    except Exception as e:
        logger.error(f"Error in Step 7: {e}")
        print(f"❌ Step 7 failed: {e}")

if __name__ == "__main__":
    main()
