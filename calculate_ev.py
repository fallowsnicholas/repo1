# calculate_ev.py - Step 5: Calculate Expected Value from matched lines (Multi-Sport Version)
import pandas as pd
import numpy as np
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

class EVCalculator:
    """Step 5: Calculate Expected Value for matched Splash/Odds lines with team data preservation"""
    
    def __init__(self, sport='MLB'):
        self.sport = sport.upper()
        self.ev_results = []
        
        # Load sport-specific configuration
        config = get_sport_config(self.sport)
        self.spreadsheet_name = config['spreadsheet_name']
        self.ev_params = config['ev_params']
        
        print(f"🏈 Initialized {self.sport} EV Calculator")
        print(f"   Spreadsheet: {self.spreadsheet_name}")
        print(f"   EV Parameters:")
        print(f"      Min books: {self.ev_params['min_books']}")
        print(f"      Min true prob: {self.ev_params['min_true_prob']:.1%}")
        print(f"      EV threshold: {self.ev_params['ev_threshold']:.1%}")
    
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
    
    def read_matched_lines(self, client):
        """Read matched lines from Step 4 with robust metadata handling"""
        try:
            print(f"📋 Reading matched lines from Step 4...")
            spreadsheet = client.open(self.spreadsheet_name)
            matched_worksheet = spreadsheet.worksheet("MATCHED_LINES")
            
            # Use robust reading to handle metadata
            all_data = matched_worksheet.get_all_values()
            
            # Find where the actual data starts (after metadata)
            data_start_row = 0
            for i, row in enumerate(all_data):
                if row and any(col in row for col in ['Name', 'Player', 'Market']):  # Look for header row
                    data_start_row = i
                    break
            
            if data_start_row == 0:
                # Fallback: assume data starts after row 5
                data_start_row = 5
            
            # Extract headers and data
            headers = all_data[data_start_row]
            data_rows = all_data[data_start_row + 1:]
            
            # Create DataFrame
            matched_df = pd.DataFrame(data_rows, columns=headers)
            
            # Remove empty rows and empty columns
            matched_df = matched_df[matched_df['Name'].notna() & (matched_df['Name'] != '')]
            matched_df = matched_df.loc[:, matched_df.columns != '']
            
            print(f"✅ Successfully read {len(matched_df)} matched lines")
            
            if matched_df.empty:
                print("❌ No matched lines data found")
                return pd.DataFrame()
            
            # Check for team columns
            team_columns = ['Team', 'Home_Team', 'Away_Team']
            available_team_columns = [col for col in team_columns if col in matched_df.columns]
            print(f"🏟️ Team columns found: {available_team_columns}")
            
            # Show sample of data
            print(f"📊 Sample matched lines:")
            for i, row in matched_df.head(3).iterrows():
                team_info = f" [{row.get('Team', 'N/A')}]" if 'Team' in matched_df.columns else ""
                print(f"   • {row['Name']}{team_info} {row['Market']} {row['Line']} @ {row['Book']}: {row['Odds']}")
            
            return matched_df
            
        except Exception as e:
            logger.error(f"Error reading matched lines: {e}")
            print(f"❌ Failed to read matched lines: {e}")
            return pd.DataFrame()
    
    def american_to_implied_prob(self, odds):
        """Convert American odds to implied probability"""
        try:
            odds = float(odds)
            if odds > 0:
                return 100 / (odds + 100)
            else:
                return abs(odds) / (abs(odds) + 100)
        except (ValueError, TypeError):
            return None
    
    def calculate_expected_values(self, matched_df):
        """Calculate Expected Value for each prop with sufficient book coverage"""
        print(f"⚾ STEP 5: CALCULATING {self.sport} EXPECTED VALUES")
        print("=" * 60)
        
        if matched_df.empty:
            print("❌ No matched data for EV calculation")
            return pd.DataFrame()
        
        # Get EV parameters from config
        min_books = self.ev_params['min_books']
        min_true_prob = self.ev_params['min_true_prob']
        ev_threshold = self.ev_params['ev_threshold']
        
        print(f"🎯 Calculating EVs with parameters:")
        print(f"   Minimum books required: {min_books}")
        print(f"   Minimum true probability: {min_true_prob:.1%}")
        print(f"   EV threshold: {ev_threshold:.1%}")
        
        # Data cleaning and preparation
        matched_df = matched_df.copy()
        
        # Clean odds column - remove '+' signs and convert to numeric
        matched_df['Odds'] = matched_df['Odds'].astype(str).str.replace('+', '')
        matched_df['Odds'] = pd.to_numeric(matched_df['Odds'], errors='coerce')
        
        # Filter out unrealistic odds and missing data
        initial_count = len(matched_df)
        matched_df = matched_df[
            (matched_df['Odds'].notna()) & 
            (matched_df['Odds'] >= -2000) & 
            (matched_df['Odds'] <= 2000)
        ]
        filtered_count = len(matched_df)
        
        if initial_count != filtered_count:
            print(f"🧹 Filtered out {initial_count - filtered_count} rows with invalid odds")
        
        # Remove duplicates
        duplicate_count = len(matched_df)
        matched_df = matched_df.drop_duplicates(
            subset=['Name', 'Market', 'Line', 'Book', 'bet_type'], 
            keep='first'
        )
        dedup_count = len(matched_df)
        
        if duplicate_count != dedup_count:
            print(f"🧹 Removed {duplicate_count - dedup_count} duplicate entries")
        
        # Calculate implied probabilities
        matched_df['Implied_Prob'] = matched_df['Odds'].apply(self.american_to_implied_prob)
        matched_df = matched_df[matched_df['Implied_Prob'].notna()]
        
        print(f"📊 Processing {len(matched_df)} clean odds entries...")
        
        # Group by prop and calculate EV for each
        results = []
        grouped = matched_df.groupby(['Name', 'Market', 'Line', 'bet_type'])
        
        total_groups = len(grouped)
        processed_groups = 0
        
        for (player, market, line, bet_type), group in grouped:
            processed_groups += 1
            
            if len(group) < min_books:
                continue
            
            # Calculate true probability (market consensus minus vig)
            avg_implied_prob = group['Implied_Prob'].mean()
            true_prob = avg_implied_prob * 0.95  # Remove 5% vig assumption
            true_prob = max(0.01, min(0.99, true_prob))  # Bound between 1% and 99%
            
            if true_prob < min_true_prob:
                continue
            
            # Calculate Splash Sports EV (based on their payout structure)
            splash_ev_dollars = 100 * (true_prob - 0.50)
            splash_ev_percentage = splash_ev_dollars / 100
            
            if splash_ev_percentage > ev_threshold:
                # Find best sportsbook odds for this prop
                if any(group['Odds'] > 0):
                    best_book_row = group.loc[group['Odds'].idxmax()]
                    best_odds = group['Odds'].max()
                else:
                    best_book_row = group.loc[group['Odds'].idxmin()]  # Closest to 0 for negative odds
                    best_odds = group['Odds'].min()
                
                # Preserve team information from the matched data
                result_dict = {
                    'Player': player,
                    'Market': market,
                    'Line': line,
                    'Bet_Type': bet_type,
                    'True_Prob': true_prob,
                    'Splash_EV_Percentage': splash_ev_percentage,
                    'Splash_EV_Dollars_Per_100': splash_ev_dollars,
                    'Num_Books_Used': len(group),
                    'Best_Sportsbook': best_book_row['Book'],
                    'Best_Odds': best_odds,
                    'Avg_Implied_Prob': avg_implied_prob,
                    'Calculation_Time': datetime.now().isoformat()
                }
                
                # Add team columns if they exist in the data
                team_columns = ['Team', 'Home_Team', 'Away_Team']
                for team_col in team_columns:
                    if team_col in best_book_row:
                        result_dict[team_col] = best_book_row[team_col]
                        
                results.append(result_dict)
        
        print(f"⚡ Processed {processed_groups} prop groups")
        
        if results:
            ev_df = pd.DataFrame(results)
            ev_df = ev_df.sort_values('Splash_EV_Percentage', ascending=False)
            
            print(f"✅ Calculated EVs for {len(ev_df)} profitable opportunities!")
            
            # Check if team data was preserved
            team_columns = ['Team', 'Home_Team', 'Away_Team']
            preserved_team_cols = [col for col in team_columns if col in ev_df.columns]
            if preserved_team_cols:
                print(f"🏟️ Team data preserved: {preserved_team_cols}")
            else:
                print(f"⚠️ No team data found in results")
            
            # Show summary statistics
            print(f"\n📈 EV SUMMARY:")
            print(f"   Best EV: {ev_df['Splash_EV_Percentage'].max():.3f} ({ev_df['Splash_EV_Percentage'].max():.1%})")
            print(f"   Average EV: {ev_df['Splash_EV_Percentage'].mean():.3f} ({ev_df['Splash_EV_Percentage'].mean():.1%})")
            print(f"   Average books per prop: {ev_df['Num_Books_Used'].mean():.1f}")
            
            # Show top EVs with team info
            print(f"\n🏆 Top 5 EV Opportunities:")
            for i, row in ev_df.head(5).iterrows():
                team_info = f" ({row.get('Team', 'N/A')})" if 'Team' in row else ""
                print(f"   {i+1}. {row['Player']}{team_info} - {row['Market']} {row['Line']} ({row['Bet_Type']})")
                print(f"      EV: {row['Splash_EV_Percentage']:.3f} ({row['Splash_EV_Percentage']:.1%}) | Books: {row['Num_Books_Used']} | Best: {row['Best_Odds']:+.0f}")
            
            # Show market breakdown
            market_counts = ev_df['Market'].value_counts()
            print(f"\n📊 EVs by Market:")
            for market, count in market_counts.items():
                print(f"   • {market}: {count} opportunities")
            
            return ev_df
            
        else:
            print("❌ No EV opportunities found with current criteria")
            return pd.DataFrame()
    
    def save_ev_results(self, ev_df, client):
        """Save EV results to Google Sheets for Steps 6-7"""
        try:
            if ev_df.empty:
                print("❌ No EV results to save")
                return
            
            print(f"💾 Saving {len(ev_df)} EV results to Google Sheets...")
            
            spreadsheet = client.open(self.spreadsheet_name)
            
            # Get or create EV_RESULTS worksheet
            try:
                worksheet = spreadsheet.worksheet("EV_RESULTS")
            except:
                worksheet = spreadsheet.add_worksheet(title="EV_RESULTS", rows=1000, cols=20)
            
            # Clear existing data
            worksheet.clear()
            
            # Add metadata including team info status
            team_columns = ['Team', 'Home_Team', 'Away_Team']
            preserved_team_cols = [col for col in team_columns if col in ev_df.columns]
            
            metadata = [
                [f'{self.sport} Expected Value Results', ''],
                ['Calculated At', datetime.now().isoformat()],
                ['Total Opportunities', len(ev_df)],
                ['Best EV', f"{ev_df['Splash_EV_Percentage'].max():.1%}"],
                ['Average EV', f"{ev_df['Splash_EV_Percentage'].mean():.1%}"],
                ['Team Data Preserved', ', '.join(preserved_team_cols) if preserved_team_cols else 'None'],
                ['']  # Empty row for spacing
            ]
            
            # Combine metadata and data
            all_data = metadata + [ev_df.columns.tolist()] + ev_df.values.tolist()
            
            # Write to sheet
            worksheet.update(range_name='A1', values=all_data)
            
            print("✅ Successfully saved EV results to EV_RESULTS sheet")
            if preserved_team_cols:
                print(f"🏟️ Team data included: {preserved_team_cols}")
            
        except Exception as e:
            logger.error(f"Error saving EV results: {e}")
            print(f"❌ Failed to save EV results: {e}")
            raise

def main():
    """Main function for Step 5"""
    parser = argparse.ArgumentParser(description='Calculate EV for MLB or NFL')
    parser.add_argument('--sport', default='MLB', choices=['MLB', 'NFL'],
                       help='Sport to calculate EV for (default: MLB)')
    args = parser.parse_args()
    
    try:
        calculator = EVCalculator(sport=args.sport)
        
        # Connect to Google Sheets
        client = calculator.connect_to_sheets()
        
        # Read matched lines from Step 4
        matched_df = calculator.read_matched_lines(client)
        
        if matched_df.empty:
            print("❌ No matched lines found from Step 4")
            return
        
        # Calculate Expected Values
        ev_df = calculator.calculate_expected_values(matched_df)
        
        if ev_df.empty:
            print("❌ No positive EV opportunities found")
            return
        
        # Save EV results for Steps 6-7
        calculator.save_ev_results(ev_df, client)
        
        print(f"\n✅ STEP 5 COMPLETE:")
        print(f"   EV opportunities found: {len(ev_df)}")
        print(f"   Ready for Steps 6-7 (Correlation Parlays)")
        
    except Exception as e:
        logger.error(f"Error in Step 5: {e}")
        print(f"❌ Step 5 failed: {e}")

if __name__ == "__main__":
    main()
