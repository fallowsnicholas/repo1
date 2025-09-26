# process_splash_data.py - Step 3B: Process raw JSON and save to Google Sheets
import json
import pandas as pd
import gspread
from gspread_dataframe import set_with_dataframe
from google.oauth2.service_account import Credentials
import os
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SplashDataProcessor:
    """Process raw JSON data and save to Google Sheets"""
    
    def __init__(self):
        self.input_file = "splash_raw_data.json"
        self.processed_data = []
        
    def load_raw_json(self):
        """Load raw JSON data from fetch script"""
        try:
            print("📂 Loading raw JSON data...")
            
            if not os.path.exists(self.input_file):
                print(f"❌ Raw data file not found: {self.input_file}")
                print("💡 Make sure to run fetch_splash_json.py first")
                return None
            
            with open(self.input_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Validate data structure
            if 'fetch_metadata' not in data or 'raw_batches' not in data:
                print("❌ Invalid JSON structure in raw data file")
                return None
            
            metadata = data['fetch_metadata']
            batches = data['raw_batches']
            
            print("✅ Raw JSON loaded successfully")
            print(f"📊 Fetch Summary:")
            print(f"   • Fetch time: {metadata['fetch_timestamp']}")
            print(f"   • Total requests: {metadata['total_requests_made']}")
            print(f"   • Total props: {metadata['total_props_collected']}")
            print(f"   • Services used: {list(metadata['services_used'].keys())}")
            print(f"   • Batches to process: {len(batches)}")
            
            return data
            
        except Exception as e:
            print(f"❌ Failed to load raw JSON: {e}")
            return None
    
    def process_raw_data(self, raw_data):
        """Process raw JSON into structured DataFrame"""
        print("\n🔄 STEP 3B: PROCESSING RAW SPLASH DATA")
        print("=" * 60)
        
        batches = raw_data['raw_batches']
        all_props = []
        
        # Extract all props from all batches
        for batch_info in batches:
            batch_props = batch_info['raw_data']
            batch_num = batch_info['request_number']
            
            print(f"   Processing batch {batch_num}: {len(batch_props)} props")
            all_props.extend(batch_props)
        
        print(f"📊 Total raw props: {len(all_props)}")
        
        # Filter for MLB only
        mlb_props = [prop for prop in all_props if prop.get('league') == 'mlb']
        print(f"⚾ MLB props: {len(mlb_props)}")
        
        if not mlb_props:
            print("❌ No MLB props found in raw data")
            return pd.DataFrame()
        
        # Process into structured format
        processed_props = []
        
        for prop in mlb_props:
            try:
                # Extract relevant fields
                processed_prop = {
                    'Name': prop.get('entity_name', '').strip(),
                    'Market': prop.get('type', '').strip(),
                    'Line': prop.get('line', ''),
                    'Entity_ID': prop.get('entity_id', ''),
                    'Prop_ID': prop.get('id', ''),
                    'League': prop.get('league', ''),
                    'Sport': prop.get('sport', ''),
                    'Status': prop.get('status', ''),
                    'Created_At': prop.get('created_at', ''),
                    'Updated_At': prop.get('updated_at', ''),
                    'Raw_Data': json.dumps(prop)  # Keep full raw data for debugging
                }
                
                # Only include props with essential data
                if processed_prop['Name'] and processed_prop['Market']:
                    processed_props.append(processed_prop)
                    
            except Exception as e:
                logger.warning(f"Failed to process prop: {e}")
                continue
        
        print(f"✅ Processed props: {len(processed_props)}")
        
        # Create DataFrame
        df = pd.DataFrame(processed_props)
        
        if df.empty:
            print("❌ No valid props after processing")
            return df
        
        # Data quality checks
        print(f"📋 Data Quality Summary:")
        print(f"   • Unique players: {df['Name'].nunique()}")
        print(f"   • Unique markets: {df['Market'].nunique()}")
        print(f"   • Missing names: {df['Name'].isna().sum()}")
        print(f"   • Missing markets: {df['Market'].isna().sum()}")
        
        # Show market breakdown
        market_counts = df['Market'].value_counts()
        print(f"📊 Top markets:")
        for market, count in market_counts.head(10).items():
            print(f"   • {market}: {count}")
        
        return df
    
    def save_to_google_sheets(self, df, raw_metadata):
        """Save processed data to Google Sheets"""
        if df.empty:
            print("❌ No data to save to Google Sheets")
            return False
        
        print(f"\n💾 SAVING TO GOOGLE SHEETS")
        print("=" * 40)
        
        try:
            # Connect to Google Sheets
            scopes = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
            
            service_account_info = json.loads(os.environ['GOOGLE_SERVICE_ACCOUNT_CREDENTIALS'])
            credentials = Credentials.from_service_account_info(service_account_info, scopes=scopes)
            client = gspread.authorize(credentials)
            
            spreadsheet = client.open("MLB_Splash_Data")
            
            # Get or create SPLASH_MLB worksheet
            try:
                worksheet = spreadsheet.worksheet("SPLASH_MLB")
                print("📋 Using existing SPLASH_MLB worksheet")
            except:
                worksheet = spreadsheet.add_worksheet(title="SPLASH_MLB", rows=5000, cols=15)
                print("📋 Created new SPLASH_MLB worksheet")
            
            # Clear existing data
            print("🧹 Clearing existing data...")
            worksheet.clear()
            
            # Prepare data with metadata header
            metadata = raw_metadata['fetch_metadata']
            
            header_info = [
                ['Splash Sports MLB Data', ''],
                ['Processed At', datetime.now().isoformat()],
                ['Original Fetch', metadata['fetch_timestamp']],
                ['Total Props', len(df)],
                ['Unique Players', df['Name'].nunique()],
                ['Services Used', ', '.join(metadata['services_used'].keys())],
                ['API Requests Made', metadata['total_requests_made']],
                ['']  # Empty row for spacing
            ]
            
            # Sort data by market then by player name
            df_sorted = df.sort_values(['Market', 'Name']).reset_index(drop=True)
            
            # Combine header info, column names, and data
            all_data = header_info + [df_sorted.columns.tolist()] + df_sorted.values.tolist()
            
            # Write to sheet
            print("✍️ Writing data to sheet...")
            worksheet.update(range_name='A1', values=all_data)
            
            print("✅ Successfully saved to Google Sheets!")
            print(f"📊 Saved {len(df)} props to SPLASH_MLB worksheet")
            
            # Show final summary
            print(f"\n📈 FINAL SUMMARY:")
            print(f"   • Sheet: MLB_Splash_Data → SPLASH_MLB")
            print(f"   • Total rows: {len(df)}")
            print(f"   • Players: {df['Name'].nunique()}")
            print(f"   • Markets: {df['Market'].nunique()}")
            print(f"   • Data source: {list(metadata['services_used'].keys())}")
            
            return True
            
        except Exception as e:
            logger.error(f"Google Sheets error: {e}")
            print(f"❌ Failed to save to Google Sheets: {e}")
            return False
    
    def cleanup_files(self):
        """Clean up temporary files"""
        try:
            if os.path.exists(self.input_file):
                os.remove(self.input_file)
                print(f"🗑️ Cleaned up temporary file: {self.input_file}")
        except Exception as e:
            print(f"⚠️ Could not clean up {self.input_file}: {e}")

def main():
    """Main processing execution"""
    print(f"⚙️ Starting data processing at: {datetime.now()}")
    
    processor = SplashDataProcessor()
    
    try:
        # Load raw JSON data
        raw_data = processor.load_raw_json()
        if not raw_data:
            print("❌ Cannot proceed without raw data")
            exit(1)
        
        # Process raw data
        df = processor.process_raw_data(raw_data)
        if df.empty:
            print("❌ No valid data after processing")
            exit(1)
        
        # Save to Google Sheets
        success = processor.save_to_google_sheets(df, raw_data)
        if not success:
            print("❌ Failed to save to Google Sheets")
            exit(1)
        
        # Cleanup temporary files
        processor.cleanup_files()
        
        print(f"\n🎉 PROCESSING COMPLETE!")
        print(f"✅ Data successfully processed and saved to Google Sheets")
        print(f"🔄 Ready for Step 4: match_lines.py")
        
    except Exception as e:
        logger.error(f"Processing failed: {e}")
        print(f"❌ Processing failed: {e}")
        exit(1)

if __name__ == "__main__":
    main()
