# process_splash_data_robust.py - More flexible version that can handle different JSON structures
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

class RobustSplashDataProcessor:
    """More flexible processor that can handle various JSON structures"""
    
    def __init__(self):
        self.input_file = "splash_raw_data.json"
        self.processed_data = []
        
    def load_and_analyze_json(self):
        """Load JSON and figure out its structure dynamically"""
        try:
            print("📂 Loading and analyzing JSON structure...")
            
            if not os.path.exists(self.input_file):
                print(f"❌ Raw data file not found: {self.input_file}")
                return None
            
            # Show file info
            file_size = os.path.getsize(self.input_file) / 1024
            print(f"📦 File size: {file_size:.1f} KB")
            
            with open(self.input_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            print("✅ JSON loaded successfully")
            
            # Analyze structure
            print(f"🔍 Structure Analysis:")
            print(f"   • Root type: {type(data).__name__}")
            
            if isinstance(data, dict):
                print(f"   • Top-level keys: {list(data.keys())}")
                return self._process_dict_structure(data)
            elif isinstance(data, list):
                print(f"   • List length: {len(data)}")
                return self._process_list_structure(data)
            else:
                print(f"❌ Unexpected root type: {type(data)}")
                return None
                
        except Exception as e:
            print(f"❌ Failed to load JSON: {e}")
            return None
    
    def _process_dict_structure(self, data):
        """Handle dictionary-based JSON structures"""
        print("📊 Processing dictionary structure...")
        
        # Look for different possible structures
        if 'fetch_metadata' in data and 'raw_api_responses' in data:
            print("✅ Found structure: fetch_metadata + raw_api_responses")
            return self._extract_from_responses(data['raw_api_responses'], data['fetch_metadata'])
        
        elif 'fetch_metadata' in data and 'raw_batches' in data:
            print("✅ Found structure: fetch_metadata + raw_batches")
            return self._extract_from_batches(data['raw_batches'], data['fetch_metadata'])
        
        elif 'data' in data:
            print("✅ Found direct data structure")
            return self._extract_from_direct_data(data['data'], {})
        
        else:
            print("🔍 Unknown structure, attempting automatic detection...")
            # Try to find data automatically
            for key, value in data.items():
                if isinstance(value, list) and value:
                    # Check if this looks like props data
                    first_item = value[0]
                    if isinstance(first_item, dict) and any(field in first_item for field in ['entity_name', 'type', 'league']):
                        print(f"✅ Found props data in key: '{key}'")
                        return self._extract_from_direct_data(value, {})
            
            print("❌ Could not identify data structure")
            return None
    
    def _process_list_structure(self, data):
        """Handle list-based JSON structures"""
        print("📊 Processing list structure...")
        
        if data and isinstance(data[0], dict):
            # Check if this looks like props data
            first_item = data[0]
            if any(field in first_item for field in ['entity_name', 'type', 'league']):
                print("✅ Direct props list detected")
                return self._extract_from_direct_data(data, {})
        
        print("❌ Could not process list structure")
        return None
    
    def _extract_from_responses(self, responses, metadata):
        """Extract props from raw_api_responses structure"""
        print(f"📤 Extracting from {len(responses)} API responses...")
        
        all_props = []
        for i, response_info in enumerate(responses):
            print(f"   Processing response {i+1}...")
            
            # Handle different response structures
            if 'complete_raw_response' in response_info:
                raw_response = response_info['complete_raw_response']
            elif 'raw_data' in response_info:
                raw_response = {'data': response_info['raw_data']}
            else:
                print(f"   ⚠️ Unknown response structure in item {i+1}")
                continue
            
            # Extract data from response
            if isinstance(raw_response, dict) and 'data' in raw_response:
                props_batch = raw_response['data']
                print(f"      Found {len(props_batch)} props")
                all_props.extend(props_batch)
            else:
                print(f"      No 'data' field found in response {i+1}")
        
        return self._process_props_data(all_props, metadata)
    
    def _extract_from_batches(self, batches, metadata):
        """Extract props from raw_batches structure (old format)"""
        print(f"📤 Extracting from {len(batches)} batches...")
        
        all_props = []
        for batch_info in batches:
            if 'raw_data' in batch_info:
                props_batch = batch_info['raw_data']
                all_props.extend(props_batch)
        
        return self._process_props_data(all_props, metadata)
    
    def _extract_from_direct_data(self, props_data, metadata):
        """Extract props from direct data structure"""
        print(f"📤 Processing direct data: {len(props_data)} items")
        return self._process_props_data(props_data, metadata)
    
    def _process_props_data(self, all_props, metadata):
        """Process the actual props data"""
        print(f"\n🔄 PROCESSING PROPS DATA")
        print(f"📊 Total raw items: {len(all_props)}")
        
        if not all_props:
            print("❌ No props data to process")
            return pd.DataFrame()
        
        # Show sample of first item for debugging
        if all_props:
            print(f"🔍 Sample item structure:")
            sample = all_props[0]
            if isinstance(sample, dict):
                print(f"   Keys: {list(sample.keys())}")
            else:
                print(f"   Type: {type(sample)}")
        
        # Filter for MLB only
        mlb_props = []
        for prop in all_props:
            if isinstance(prop, dict) and prop.get('league', '').lower() == 'mlb':
                mlb_props.append(prop)
        
        print(f"⚾ MLB props: {len(mlb_props)}")
        
        if not mlb_props:
            print("❌ No MLB props found")
            return pd.DataFrame()
        
        # Process into structured format
        processed_props = []
        for prop in mlb_props:
            try:
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
        
        if not df.empty:
            print(f"📋 Data Quality Summary:")
            print(f"   • Unique players: {df['Name'].nunique()}")
            print(f"   • Unique markets: {df['Market'].nunique()}")
            
            # Show market breakdown
            market_counts = df['Market'].value_counts()
            print(f"📊 Top markets:")
            for market, count in market_counts.head(5).items():
                print(f"   • {market}: {count}")
        
        return df
    
    def save_to_google_sheets(self, df):
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
            header_info = [
                ['Splash Sports MLB Data (Robust Processing)', ''],
                ['Processed At', datetime.now().isoformat()],
                ['Total Props', len(df)],
                ['Unique Players', df['Name'].nunique()],
                ['Processing Method', 'Robust structure detection'],
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
    """Main processing execution with robust handling"""
    print(f"⚙️ Starting ROBUST data processing at: {datetime.now()}")
    
    processor = RobustSplashDataProcessor()
    
    try:
        # Load and analyze JSON
        df = processor.load_and_analyze_json()
        if df is None or df.empty:
            print("❌ No valid data after processing")
            exit(1)
        
        # Save to Google Sheets
        success = processor.save_to_google_sheets(df)
        if not success:
            print("❌ Failed to save to Google Sheets")
            exit(1)
        
        # Cleanup temporary files
        processor.cleanup_files()
        
        print(f"\n🎉 ROBUST PROCESSING COMPLETE!")
        print(f"✅ Data successfully processed and saved to Google Sheets")
        print(f"🔄 Ready for Step 4: match_lines.py")
        
    except Exception as e:
        logger.error(f"Processing failed: {e}")
        print(f"❌ Processing failed: {e}")
        exit(1)

if __name__ == "__main__":
    main()
