# find_pitcher_anchors.py - Step 6: Find pitcher anchors in target correlation markets
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
    """Step 6: Find pitcher props with positive EV in target correlation markets"""
    
    def __init__(self):
        # Target pitcher markets for correlation parlays
        self.TARGET_PITCHER_MARKETS = [
            'pitcher_strikeouts',    # Correlates with opposing batter hits (negative)
            'pitcher_earned_runs',   # Correlates with opposing batter runs (positive)  
            'pitcher_hits_allowed'   # Correlates with opposing batter hits (positive)
        ]
        
        # Minimum EV threshold for pitcher anchors
        self.MIN_PITCHER_EV = 0.01  # 1% minimum EV
        
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
    
    def find_pitcher_anchors(self, ev_df):
        """Find pitcher anchors in target correlation markets"""
        print("⚾ STEP 6: FINDING PITCHER ANCHORS FOR CORRELATION PARLAYS")
        print("=" * 60)
        
        if ev_df.empty:
            print("❌ No EV data available")
            return pd.DataFrame()
        
        print(f"🎯 Target pitcher markets for correlations:")
        print(f"   • pitcher_strikeouts ↔ opposing batter hits (negative correlation)")
        print(f"   • pitcher_earned_runs ↔ opposing batter runs (positive correlation)")
        print(f"   • pitcher_hits_allowed ↔ opposing batter hits (positive correlation)")
        print(f"📈 Minimum EV threshold: {self.MIN_PITCHER_EV:.1%}")
        
        # Filter for pitcher markets with sufficient EV
        pitcher_anchors = ev_df[
            (ev_df['Market'].isin(self.TARGET_PITCHER_MARKETS)) & 
            (ev_df['Splash_EV_Percentage'] >= self.MIN_PITCHER_EV)
        ].copy()
        
        if pitcher_anchors.empty:
            print("❌ No pitcher anchors found above EV threshold")
            print("💡 Try lowering MIN_PITCHER_EV or check if pitcher markets exist in EV data")
            
            # Show what markets we do have
            if 'Market' in ev_df.columns:
                available_markets = ev_df['Market'].value_counts()
                print(f"📊 Available markets in EV data:")
                for market, count in available_markets.head(10).items():
                    print(f"   • {market}: {count} opportunities")
            
            return pd.DataFrame()
        
        print(f"✅ Found {len(pitcher_anchors)} pitcher anchor opportunities")
        
        # Show breakdown by market
        market_breakdown = pitcher_anchors['Market'].value_counts()
        print(f"📊 Pitcher anchors by market:")
        for market, count in market_breakdown.items():
            print(f"   • {market}: {count} opportunities")
        
        # Show top pitcher opportunities
        print(f"\n🏆 Top pitcher anchor opportunities:")
        top_pitchers = pitcher_anchors.nlargest(10, 'Splash_EV_Percentage')
        for i, (_, row) in enumerate(top_pitchers.iterrows(), 1):
            player = row['Player']
            market = row['Market']
            line = row.get('Line', 'N/A')
            bet_type = row.get('Bet_Type', 'N/A')
            ev = row['Splash_EV_Percentage']
            books = row.get('Num_Books_Used', 0)
            
            # Determine correlation type
            correlation_type = "negative" if market == 'pitcher_strikeouts' else "positive"
            
            print(f"   {i:2d}. {player} - {market} {line} ({bet_type})")
            print(f"       EV: {ev:.3f} ({ev:.1%}) | Books: {books} | Correlation: {correlation_type}")
        
        return pitcher_anchors
    
    def add_correlation_info(self, pitcher_anchors):
        """Add correlation information to pitcher anchors"""
        if pitcher_anchors.empty:
            return pitcher_anchors
            
        print(f"🔗 Adding correlation information to pitcher anchors...")
        
        # Define correlations for each pitcher market
        correlation_mappings = {
            'pitcher_strikeouts': {
                'opposing_market': 'batter_hits',
                'correlation_strength': -0.70,
                'correlation_type': 'negative',
                'logic': 'More strikeouts = fewer hits for opposing batters'
            },
            'pitcher_earned_runs': {
                'opposing_market': 'batter_runs_scored', 
                'correlation_strength': 0.70,
                'correlation_type': 'positive',
                'logic': 'Pitcher struggles = opposing batters score more runs'
            },
            'pitcher_hits_allowed': {
                'opposing_market': 'batter_hits',
                'correlation_strength': 0.75,
                'correlation_type': 'positive', 
                'logic': 'Pitcher allows hits = batters get hits'
            }
        }
        
        # Add correlation info to each pitcher anchor
        pitcher_anchors = pitcher_anchors.copy()
        
        for market, corr_info in correlation_mappings.items():
            mask = pitcher_anchors['Market'] == market
            pitcher_anchors.loc[mask, 'Opposing_Market'] = corr_info['opposing_market']
            pitcher_anchors.loc[mask, 'Correlation_Strength'] = corr_info['correlation_strength']
            pitcher_anchors.loc[mask, 'Correlation_Type'] = corr_info['correlation_type']
            pitcher_anchors.loc[mask, 'Correlation_Logic'] = corr_info['logic']
        
        print(f"✅ Added correlation info to {len(pitcher_anchors)} pitcher anchors")
        return pitcher_anchors
    
    def save_pitcher_anchors(self, pitcher_anchors, client):
        """Save pitcher anchors for Step 7"""
        try:
            if pitcher_anchors.empty:
                print("❌ No pitcher anchors to save")
                return
            
            print(f"💾 Saving {len(pitcher_anchors)} pitcher anchors to Google Sheets...")
            
            spreadsheet = client.open("MLB_Splash_Data")
            
            # Get or create PITCHER_ANCHORS worksheet
            try:
                worksheet = spreadsheet.worksheet("PITCHER_ANCHORS")
            except:
                worksheet = spreadsheet.add_worksheet(title="PITCHER_ANCHORS", rows=1000, cols=20)
            
            # Clear existing data
            worksheet.clear()
            
            # Prepare data for saving
            save_data = []
            for i, (_, row) in enumerate(pitcher_anchors.iterrows(), 1):
                save_data.append([
                    f"ANCHOR_{i:03d}",  # Anchor_ID
                    row['Player'],      # Player_Name
                    row['Market'],      # Market
                    row.get('Line', ''), # Line
                    row.get('Bet_Type', ''), # Bet_Type
                    row['Splash_EV_Percentage'], # EV
                    row.get('Num_Books_Used', 0), # Num_Books
                    row.get('Best_Odds', 0), # Best_Odds
                    row.get('Best_Sportsbook', ''), # Best_Book
                    row.get('Opposing_Market', ''), # Opposing_Market
                    row.get('Correlation_Strength', 0), # Correlation_Strength
                    row.get('Correlation_Type', ''), # Correlation_Type
                    row.get('Correlation_Logic', ''), # Correlation_Logic
                    datetime.now().isoformat() # Created_At
                ])
            
            # Headers
            headers = [
                'Anchor_ID', 'Player_Name', 'Market', 'Line', 'Bet_Type', 'EV',
                'Num_Books', 'Best_Odds', 'Best_Book', 'Opposing_Market', 
                'Correlation_Strength', 'Correlation_Type', 'Correlation_Logic', 'Created_At'
            ]
            
            # Add metadata
            metadata = [
                ['Pitcher Anchor Data for Correlation Parlays', ''],
                ['Created At', datetime.now().isoformat()],
                ['Total Anchors', len(pitcher_anchors)],
                ['Target Markets', ', '.join(self.TARGET_PITCHER_MARKETS)],
                ['Min EV Threshold', f"{self.MIN_PITCHER_EV:.1%}"],
                ['']
            ]
            
            all_data = metadata + [headers] + save_data
            
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
        
        # Find pitcher anchors in target markets
        pitcher_anchors = finder.find_pitcher_anchors(ev_df)
        
        if pitcher_anchors.empty:
            print("❌ No pitcher anchors found")
            return
        
        # Add correlation information
        pitcher_anchors = finder.add_correlation_info(pitcher_anchors)
        
        # Save for Step 7
        finder.save_pitcher_anchors(pitcher_anchors, client)
        
        print(f"\n✅ STEP 6 COMPLETE:")
        print(f"   🎯 Pitcher anchors found: {len(pitcher_anchors)}")
        print(f"   📊 Target correlation markets:")
        print(f"      • Strikeouts → Opposing Hits (negative)")
        print(f"      • Earned Runs → Opposing Runs (positive)")  
        print(f"      • Hits Allowed → Opposing Hits (positive)")
        print(f"   📋 Data ready for Step 7 (Build Parlays)")
        
    except Exception as e:
        logger.error(f"Error in Step 6: {e}")
        print(f"❌ Step 6 failed: {e}")

if __name__ == "__main__":
    main()
