# match_lines.py - Step 4: Match Splash props to Odds data (Multi-Sport Version)
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json
import os
from datetime import datetime
import logging
import argparse
from sports_config import get_sport_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LineMatching:
    """Step 4: Match Splash Sports props to Odds API data (both read from Google Sheets)"""
    
    def __init__(self, sport='MLB'):
        self.sport = sport.upper()
        
        # Load sport-specific configuration
        config = get_sport_config(self.sport)
        self.spreadsheet_name = config['spreadsheet_name']
        self.market_mapping = config['market_mappings']
        
        # Determine worksheet names based on sport
        if self.sport == 'MLB':
            self.splash_worksheet_name = 'SPLASH_MLB'
        elif self.sport == 'NFL':
            self.splash_worksheet_name = 'SPLASH_NFL'
        else:
            self.splash_worksheet_name = f'SPLASH_{self.sport}'
        
        self.odds_worksheet_name = 'ODDS_API'
        self.output_worksheet_name = 'MATCHED_LINES'
        
        print(f"🏈 Initialized {self.sport} Line Matching")
        print(f"   Spreadsheet: {self.spreadsheet_name}")
        print(f"   Splash worksheet: {self.splash_worksheet_name}")
        print(f"   Odds worksheet: {self.odds_worksheet_name}")
        print(f"   Market mappings: {len(self.market_mapping)} markets")
    
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
    
    def read_sheet_with_metadata_skip(self, worksheet, sheet_name, expected_columns=None):
        """
        Robust function to read Google Sheets data while skipping metadata headers
        """
        try:
            print(f"📋 Reading {sheet_name} with metadata handling...")
            
            # Get all data from sheet
            all_data = worksheet.get_all_values()
            
            if not all_data:
                print(f"❌ {sheet_name} sheet is empty")
                return pd.DataFrame()
            
            print(f"📊 Total rows in {sheet_name}: {len(all_data)}")
            
            # Find the header row (contains actual column names)
            header_row_index = -1
            
            # Look for common header patterns
            header_indicators = ['Name', 'Player', 'Market', 'Line', 'Odds', 'Book', 'Team']
            
            for i, row in enumerate(all_data):
                # Check if this row contains header-like values
                if any(indicator in row for indicator in header_indicators):
                    print(f"✅ Found header row at index {i} in {sheet_name}: {row[:5]}...")
                    header_row_index = i
                    break
            
            # If no header found, assume it starts at row 0 (no metadata)
            if header_row_index == -1:
                print(f"📋 No metadata detected in {sheet_name}, using row 0 as headers")
                header_row_index = 0
            
            # Extract headers and data
            headers = all_data[header_row_index]
            data_rows = all_data[header_row_index + 1:]
            
            # Filter out empty rows
            data_rows = [row for row in data_rows if any(cell.strip() if cell else '' for cell in row)]
            
            print(f"📈 Data rows found in {sheet_name}: {len(data_rows)}")
            print(f"🏷️ Columns: {headers}")
            
            # Create DataFrame
            df = pd.DataFrame(data_rows, columns=headers)
            
            # Remove completely empty rows
            df = df.dropna(how='all')
            
            # Remove empty string columns that might cause issues
            df = df.loc[:, df.columns != '']
            
            print(f"✅ Successfully read {len(df)} rows from {sheet_name}")
            return df
            
        except Exception as e:
            print(f"❌ Error reading {sheet_name}: {e}")
            return pd.DataFrame()
    
    def read_splash_data(self, client):
        """Read Splash Sports data from sport-specific worksheet"""
        try:
            spreadsheet = client.open(self.spreadsheet_name)
            splash_worksheet = spreadsheet.worksheet(self.splash_worksheet_name)
            
            expected_columns = ['Name', 'Market', 'Line']
            splash_df = self.read_sheet_with_metadata_skip(splash_worksheet, self.splash_worksheet_name, expected_columns)
            
            if splash_df.empty:
                print(f"❌ No Splash data found - make sure {self.splash_worksheet_name} sheet is populated")
                return pd.DataFrame()
            
            # Show breakdown
            if not splash_df.empty and 'Market' in splash_df.columns:
                unique_players = splash_df['Name'].nunique() if 'Name' in splash_df.columns else 0
                market_counts = splash_df['Market'].value_counts()
                print(f"📊 Splash: {unique_players} players, {len(market_counts)} markets")
                print(f"   Top markets: {dict(market_counts.head(3))}")
            
            return splash_df
            
        except Exception as e:
            logger.error(f"Error reading Splash data: {e}")
            print(f"❌ Failed to read Splash data: {e}")
            return pd.DataFrame()
    
    def read_odds_data(self, client):
        """Read Odds API data from ODDS_API sheet"""
        try:
            spreadsheet = client.open(self.spreadsheet_name)
            odds_worksheet = spreadsheet.worksheet(self.odds_worksheet_name)
            
            expected_columns = ['Name', 'Market', 'Line', 'Odds', 'Book']
            odds_df = self.read_sheet_with_metadata_skip(odds_worksheet, self.odds_worksheet_name, expected_columns)
            
            if odds_df.empty:
                print(f"❌ No Odds data found - make sure {self.odds_worksheet_name} sheet is populated")
                print(f"   💡 Run Step 2 (fetch_odds_data.py --sport {self.sport}) first to populate this sheet")
                return pd.DataFrame()
            
            # Show breakdown
            if not odds_df.empty:
                unique_players = odds_df['Name'].nunique() if 'Name' in odds_df.columns else 0
                unique_books = odds_df['Book'].nunique() if 'Book' in odds_df.columns else 0
                market_counts = odds_df['Market'].value_counts() if 'Market' in odds_df.columns else {}
                print(f"📊 Odds: {unique_players} players, {unique_books} books")
                print(f"   Top markets: {dict(market_counts.head(3))}")
            
            return odds_df
            
        except Exception as e:
            logger.error(f"Error reading odds data: {e}")
            print(f"❌ Failed to read odds data: {e}")
            return pd.DataFrame()
    
    def preprocess_odds_data(self, odds_df):
        """Preprocess odds data to extract bet type and clean lines"""
        if odds_df.empty:
            return odds_df
        
        print("🔧 Preprocessing odds data for matching...")
        
        def extract_bet_info(line_str):
            line_str = str(line_str).strip()
            if line_str.lower().startswith('over '):
                return 'over', line_str.lower().replace('over ', '')
            elif line_str.lower().startswith('under '):
                return 'under', line_str.lower().replace('under ', '')
            else:
                return 'unknown', line_str

        odds_df = odds_df.copy()
        odds_df['bet_type'] = odds_df['Line'].apply(lambda x: extract_bet_info(x)[0])
        odds_df['line_value'] = odds_df['Line'].apply(lambda x: extract_bet_info(x)[1])
        
        # Map markets using the market mapping (reverse lookup)
        reverse_mapping = {v: k for k, v in self.market_mapping.items()}
        odds_df['mapped_market'] = odds_df['Market'].map(reverse_mapping)
        
        # Remove rows that couldn't be mapped
        unmapped_before = len(odds_df)
        odds_df = odds_df[odds_df['mapped_market'].notna()]
        unmapped_after = len(odds_df)
        
        if unmapped_before != unmapped_after:
            print(f"   ⚠️ Filtered out {unmapped_before - unmapped_after} unmappable market rows")
        
        print(f"   ✅ Preprocessed: {len(odds_df)} rows ready for matching")
        return odds_df
    
    def find_matching_lines(self, splash_df, odds_df):
        """Find matching lines between Splash and Odds data"""
        print(f"⚾ STEP 4: MATCHING {self.sport} SPLASH PROPS TO ODDS DATA")
        print("=" * 60)
        
        if splash_df.empty:
            print("❌ No Splash data - cannot proceed")
            return pd.DataFrame()
            
        if odds_df.empty:
            print("❌ No Odds data - cannot proceed")
            print(f"   💡 Make sure to populate {self.odds_worksheet_name} sheet first")
            return pd.DataFrame()
        
        # Prepare data for matching
        splash_df = splash_df.copy()
        splash_df['Line'] = splash_df['Line'].astype(str)
        
        print(f"🔍 Attempting to match:")
        print(f"   📊 Splash: {len(splash_df)} props")
        print(f"   📈 Odds: {len(odds_df)} odds entries")
        
        matching_rows = []
        matches_found = 0
        match_details = {}
        
        for _, splash_row in splash_df.iterrows():
            splash_name = splash_row['Name']
            splash_market = splash_row['Market'] 
            splash_line = splash_row['Line']
            
            # Find odds rows that match this splash prop
            matches = odds_df[
                (odds_df['Name'].str.lower() == splash_name.lower()) &
                (odds_df['mapped_market'] == splash_market) &
                (odds_df['line_value'] == splash_line)
            ]
            
            if not matches.empty:
                matches_found += len(matches)
                matching_rows.append(matches)
                
                # Track match details for reporting
                key = f"{splash_name}_{splash_market}_{splash_line}"
                match_details[key] = len(matches)
        
        if not matching_rows:
            print("❌ No matching lines found between Splash and Odds data")
            self._analyze_match_failures(splash_df, odds_df)
            return pd.DataFrame()
        
        # Combine all matches
        matched_df = pd.concat(matching_rows, ignore_index=True)
        matched_df = matched_df.drop(['mapped_market', 'line_value'], axis=1)  # Remove helper columns
        
        # Get unique prop count
        unique_props = len(matched_df.groupby(['Name', 'Market', 'Line']))
        
        print(f"✅ Successfully matched lines!")
        print(f"   📊 Total odds entries matched: {matches_found}")
        print(f"   🎯 Unique props with odds: {unique_props}")
        print(f"   📈 Average books per prop: {matches_found / unique_props:.1f}")
        
        # Show top matches by book count
        if not matched_df.empty:
            print(f"\n🔝 Top matched props by book count:")
            prop_book_counts = matched_df.groupby(['Name', 'Market', 'Line']).size().sort_values(ascending=False)
            for (player, market, line), count in prop_book_counts.head(5).items():
                print(f"   • {player} {market} {line}: {count} books")
        
        return matched_df
    
    def _analyze_match_failures(self, splash_df, odds_df):
        """Analyze why matches failed to help with debugging"""
        print("\n🔍 ANALYZING MATCH FAILURES:")
        
        # Check player name overlaps
        splash_players = set(splash_df['Name'].str.lower()) if 'Name' in splash_df.columns else set()
        odds_players = set(odds_df['Name'].str.lower()) if 'Name' in odds_df.columns else set()
        common_players = splash_players.intersection(odds_players)
        
        print(f"   👥 Players in Splash: {len(splash_players)}")
        print(f"   👥 Players in Odds: {len(odds_players)}")
        print(f"   🤝 Common players: {len(common_players)}")
        
        if len(common_players) < 5:
            print(f"   Sample Splash players: {list(splash_players)[:5]}")
            print(f"   Sample Odds players: {list(odds_players)[:5]}")
            if common_players:
                print(f"   Common players found: {list(common_players)[:5]}")
        
        # Check market overlaps
        splash_markets = set(splash_df['Market']) if 'Market' in splash_df.columns else set()
        odds_mapped_markets = set(odds_df['mapped_market'].dropna()) if 'mapped_market' in odds_df.columns else set()
        common_markets = splash_markets.intersection(odds_mapped_markets)
        
        print(f"   📊 Markets in Splash: {splash_markets}")
        print(f"   📊 Mapped markets in Odds: {odds_mapped_markets}")
        print(f"   🤝 Common markets: {common_markets}")
        
        # Sample line formats
        if 'Line' in splash_df.columns:
            sample_splash_lines = splash_df['Line'].head(3).tolist()
            print(f"   Sample Splash lines: {sample_splash_lines}")
        
        if 'line_value' in odds_df.columns:
            sample_odds_lines = odds_df['line_value'].head(3).tolist()
            print(f"   Sample Odds line values: {sample_odds_lines}")
    
    def save_matched_lines(self, matched_df, client):
        """Save matched lines to Google Sheets for Step 5"""
        try:
            if matched_df.empty:
                print("❌ No matched data to save")
                return
            
            print(f"💾 Saving {len(matched_df)} matched lines to Google Sheets...")
            
            spreadsheet = client.open(self.spreadsheet_name)
            
            # Get or create MATCHED_LINES worksheet
            try:
                worksheet = spreadsheet.worksheet(self.output_worksheet_name)
            except:
                worksheet = spreadsheet.add_worksheet(title=self.output_worksheet_name, rows=5000, cols=15)
            
            # Clear existing data
            worksheet.clear()
            
            # Add metadata
            metadata = [
                [f'{self.sport} Matched Lines Data', ''],
                ['Created At', datetime.now().isoformat()],
                ['Total Matched Lines', len(matched_df)],
                ['Unique Props', len(matched_df.groupby(['Name', 'Market', 'Line']))],
                ['Data Sources', f'{self.splash_worksheet_name} + {self.odds_worksheet_name} sheets'],
                ['']  # Empty row for spacing
            ]
            
            # Combine metadata and data
            all_data = metadata + [matched_df.columns.tolist()] + matched_df.values.tolist()
            
            # Write to sheet
            worksheet.update(range_name='A1', values=all_data)
            
            print(f"✅ Successfully saved matched lines to {self.output_worksheet_name} sheet")
            
        except Exception as e:
            logger.error(f"Error saving matched lines: {e}")
            print(f"❌ Failed to save matched lines: {e}")
            raise

def main():
    """Main function for Step 4 - matching data from Google Sheets"""
    parser = argparse.ArgumentParser(description='Match Splash to Odds data for MLB or NFL')
    parser.add_argument('--sport', default='MLB', choices=['MLB', 'NFL'],
                       help='Sport to match data for (default: MLB)')
    args = parser.parse_args()
    
    try:
        matcher = LineMatching(sport=args.sport)
        
        # Connect to Google Sheets
        client = matcher.connect_to_sheets()
        
        # Read data from both sheets using robust reading
        splash_df = matcher.read_splash_data(client)
        odds_df = matcher.read_odds_data(client)
        
        if splash_df.empty:
            print(f"❌ Missing Splash data from {matcher.splash_worksheet_name} sheet")
            print(f"   💡 Make sure Step 3 completed successfully")
            return
            
        if odds_df.empty:
            print(f"❌ Missing Odds data from {matcher.odds_worksheet_name} sheet") 
            print(f"   💡 Make sure Step 2 completed successfully")
            return
        
        # Preprocess odds data for matching
        odds_df = matcher.preprocess_odds_data(odds_df)
        
        if odds_df.empty:
            print("❌ No processable odds data after preprocessing")
            return
        
        # Find matching lines
        matched_df = matcher.find_matching_lines(splash_df, odds_df)
        
        if matched_df.empty:
            print("❌ No matches found - cannot proceed to Step 5")
            return
        
        # Save matched lines for Step 5
        matcher.save_matched_lines(matched_df, client)
        
        print(f"\n✅ STEP 4 COMPLETE:")
        print(f"   Matched lines: {len(matched_df)}")
        print(f"   Unique props: {len(matched_df.groupby(['Name', 'Market', 'Line']))}")
        print(f"   Ready for Step 5: calculate_ev.py --sport {args.sport}")
        
    except Exception as e:
        logger.error(f"Error in Step 4: {e}")
        print(f"❌ Step 4 failed: {e}")

if __name__ == "__main__":
    main()
