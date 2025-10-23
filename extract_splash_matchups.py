# extract_splash_matchups.py - Generate matchups FROM Splash props (replaces Step 1)
"""
This script extracts unique matchups from Splash Sports props data.
Instead of fetching scheduled games from ESPN (which limits to today's games),
we derive matchups from whatever props currently exist in Splash.

This approach ensures:
1. We see ALL props in Splash (regardless of game date)
2. We only fetch Odds API data for games that have Splash props
3. No outdated data issues
"""
import gspread
from google.oauth2.service_account import Credentials
import json
import os
import pandas as pd
from datetime import datetime
import logging
import argparse
from sports_config import get_sport_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SplashMatchupExtractor:
    def __init__(self, sport='MLB'):
        self.sport = sport.upper()

        # Load sport-specific configuration
        config = get_sport_config(self.sport)
        self.spreadsheet_name = config['spreadsheet_name']

        # Determine worksheet names based on sport
        if self.sport == 'MLB':
            self.splash_worksheet_name = 'SPLASH_MLB'
        elif self.sport == 'NFL':
            self.splash_worksheet_name = 'SPLASH_NFL'
        elif self.sport == 'WNBA':
            self.splash_worksheet_name = 'SPLASH_WNBA'
        else:
            self.splash_worksheet_name = f'SPLASH_{self.sport}'

        self.matchups_worksheet_name = 'MATCHUPS'

        print(f"🏈 Initialized {self.sport} Matchup Extractor (from Splash)")
        print(f"   Spreadsheet: {self.spreadsheet_name}")
        print(f"   Source: {self.splash_worksheet_name}")
        print(f"   Output: {self.matchups_worksheet_name}")

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

    def read_splash_data(self, client):
        """Read Splash Sports data with metadata handling"""
        try:
            print(f"📋 Reading Splash props from {self.splash_worksheet_name}...")

            spreadsheet = client.open(self.spreadsheet_name)
            splash_worksheet = spreadsheet.worksheet(self.splash_worksheet_name)

            # Get all data
            all_data = splash_worksheet.get_all_values()

            if not all_data:
                print(f"❌ {self.splash_worksheet_name} sheet is empty")
                return pd.DataFrame()

            # Find header row (skip metadata)
            header_row_index = -1
            header_indicators = ['Name', 'Player', 'Market', 'Entity_ID', 'Prop_ID']

            for i, row in enumerate(all_data):
                if any(indicator in row for indicator in header_indicators):
                    print(f"✅ Found header row at index {i}")
                    header_row_index = i
                    break

            if header_row_index == -1:
                print(f"❌ Could not find header row in {self.splash_worksheet_name}")
                return pd.DataFrame()

            # Extract headers and data
            headers = all_data[header_row_index]
            data_rows = all_data[header_row_index + 1:]

            # Filter out empty rows
            data_rows = [row for row in data_rows if any(cell.strip() if cell else '' for cell in row)]

            # Create DataFrame
            df = pd.DataFrame(data_rows, columns=headers)
            df = df.dropna(how='all')
            df = df.loc[:, df.columns != '']

            print(f"✅ Read {len(df)} Splash props")
            return df

        except Exception as e:
            logger.error(f"Error reading Splash data: {e}")
            print(f"❌ Failed to read Splash data: {e}")
            return pd.DataFrame()

    def extract_matchups_from_props(self, splash_df):
        """
        Extract unique matchups/entities from Splash props.
        For team sports (MLB, NFL), extract team matchups.
        For WNBA or other sports, extract entity IDs.
        """
        print(f"\n🔍 EXTRACTING MATCHUPS FROM {self.sport} SPLASH PROPS")
        print("=" * 60)

        if splash_df.empty:
            print("❌ No Splash data to extract matchups from")
            return []

        # Extract unique entity IDs (these represent teams/players that have props)
        entity_ids = splash_df['Entity_ID'].unique() if 'Entity_ID' in splash_df.columns else []

        print(f"📊 Found {len(entity_ids)} unique entities with props in Splash")

        # For now, we'll create a simple matchup structure
        # The key insight: we don't need ESPN matchups at all
        # We just need to know which entities have props
        matchups = []

        for entity_id in entity_ids:
            if pd.notna(entity_id) and str(entity_id).strip():
                # Get all props for this entity to extract metadata
                entity_props = splash_df[splash_df['Entity_ID'] == entity_id]

                if not entity_props.empty:
                    first_prop = entity_props.iloc[0]

                    matchup = {
                        'entity_id': entity_id,
                        'entity_name': first_prop.get('Name', ''),
                        'prop_count': len(entity_props),
                        'markets': entity_props['Market'].unique().tolist() if 'Market' in entity_props.columns else [],
                        'created_at': first_prop.get('Created_At', ''),
                        'updated_at': first_prop.get('Updated_At', '')
                    }

                    matchups.append(matchup)

        print(f"✅ Extracted {len(matchups)} unique matchups/entities")

        # Show summary
        total_props = sum(m['prop_count'] for m in matchups)
        avg_props = total_props / len(matchups) if matchups else 0
        print(f"📈 Total props across all entities: {total_props}")
        print(f"📊 Average props per entity: {avg_props:.1f}")

        # Show top entities by prop count
        if matchups:
            print(f"\n🔝 Top entities by prop count:")
            sorted_matchups = sorted(matchups, key=lambda x: x['prop_count'], reverse=True)
            for i, matchup in enumerate(sorted_matchups[:5], 1):
                name = matchup['entity_name']
                count = matchup['prop_count']
                markets = len(matchup['markets'])
                print(f"   {i}. {name}: {count} props ({markets} markets)")

        return matchups

    def save_matchups_to_sheets(self, matchups, client):
        """Save extracted matchups to MATCHUPS sheet"""
        try:
            if not matchups:
                print("❌ No matchups to save")
                return False

            print(f"\n💾 Saving {len(matchups)} matchups to Google Sheets...")

            spreadsheet = client.open(self.spreadsheet_name)

            # Get or create MATCHUPS worksheet
            try:
                worksheet = spreadsheet.worksheet(self.matchups_worksheet_name)
            except:
                worksheet = spreadsheet.add_worksheet(title=self.matchups_worksheet_name, rows=1000, cols=10)

            # Clear existing data
            worksheet.clear()

            # Add metadata
            metadata = [
                [f'{self.sport} Matchups (Extracted from Splash Props)', ''],
                ['Source', f'{self.splash_worksheet_name} worksheet'],
                ['Extraction Method', 'Entity-based (from Splash props, not ESPN schedule)'],
                ['Total Entities', len(matchups)],
                ['Total Props Represented', sum(m['prop_count'] for m in matchups)],
                ['Extracted At', datetime.now().isoformat()],
                ['Note', 'These matchups are derived from current Splash props, not limited to today\'s games'],
                ['']  # Empty row
            ]

            # Create headers
            headers = ['Entity_ID', 'Entity_Name', 'Prop_Count', 'Markets', 'Created_At', 'Updated_At']

            # Flatten matchups data
            flattened = []
            for matchup in matchups:
                flattened.append([
                    matchup['entity_id'],
                    matchup['entity_name'],
                    matchup['prop_count'],
                    ', '.join(matchup['markets'][:5]),  # First 5 markets
                    matchup.get('created_at', ''),
                    matchup.get('updated_at', '')
                ])

            # Combine all data
            all_data = metadata + [headers] + flattened

            # Write to sheet
            worksheet.update(range_name='A1', values=all_data)

            print(f"✅ Successfully saved matchups to {self.matchups_worksheet_name} sheet")
            return True

        except Exception as e:
            logger.error(f"Error saving matchups: {e}")
            print(f"❌ Failed to save matchups: {e}")
            return False

def main():
    """Main execution - extract matchups from Splash props"""
    parser = argparse.ArgumentParser(description='Extract matchups from Splash props for MLB, NFL, or WNBA')
    parser.add_argument('--sport', default='MLB', choices=['MLB', 'NFL', 'WNBA'],
                       help='Sport to extract matchups for (default: MLB)')
    args = parser.parse_args()

    try:
        print(f"🚀 Extracting {args.sport} matchups from Splash props...")
        print("📝 This replaces ESPN schedule fetching (Step 1)")
        print()

        extractor = SplashMatchupExtractor(sport=args.sport)

        # Connect to Google Sheets
        client = extractor.connect_to_sheets()

        # Read Splash data
        splash_df = extractor.read_splash_data(client)

        if splash_df.empty:
            print(f"❌ No Splash data found in {extractor.splash_worksheet_name}")
            print(f"   💡 Make sure Step 3 (fetch_splash_json.py + process_splash_data.py) ran successfully")
            exit(1)

        # Extract matchups from Splash props
        matchups = extractor.extract_matchups_from_props(splash_df)

        if not matchups:
            print("❌ No matchups could be extracted")
            exit(1)

        # Save matchups
        success = extractor.save_matchups_to_sheets(matchups, client)

        if not success:
            print("❌ Failed to save matchups")
            exit(1)

        print(f"\n✅ MATCHUP EXTRACTION COMPLETE!")
        print(f"   📊 Extracted {len(matchups)} entities/matchups from Splash props")
        print(f"   💾 Saved to {extractor.matchups_worksheet_name} sheet")
        print(f"   🔄 Ready for Step 2: fetch_odds_data.py --sport {args.sport}")
        print()
        print(f"💡 KEY INSIGHT: We now fetch odds for ALL games with Splash props,")
        print(f"   not just today's scheduled games!")

    except Exception as e:
        logger.error(f"Error in matchup extraction: {e}")
        print(f"❌ Matchup extraction failed: {e}")
        exit(1)

if __name__ == "__main__":
    main()
