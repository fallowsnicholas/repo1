# enhanced_ev_calculator.py
import pandas as pd
import json
import gspread
from google.oauth2.service_account import Credentials
import os
from datetime import datetime
import logging
from matchup_fetcher import MLBMatchupFetcher
from pitcher_batter_correlator import PitcherBatterCorrelator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedEVCalculator:
    """
    Enhanced EV Calculator with pitcher vs batter correlation support
    """
    
    def __init__(self, google_creds_json=None):
        """Initialize with Google credentials"""
        self.google_creds = json.loads(google_creds_json) if google_creds_json else json.loads(os.environ.get('GOOGLE_SERVICE_ACCOUNT_CREDENTIALS', '{}'))
        
        # Market mapping for matching between Splash and Odds API
        self.market_mapping = {
            'strikeouts': 'pitcher_strikeouts',
            'earned_runs': 'pitcher_earned_runs',
            'hits': 'batter_hits',
            'hits_allowed': 'pitcher_hits_allowed',
            'hits_plus_runs_plus_RBIs': 'hits_plus_runs_plus_RBIs',
            'runs': 'batter_runs_scored',
            'batter_singles': 'batter_singles',
            'total_bases': 'batter_total_bases',
            'RBIs': 'batter_rbis',
            'total_outs': 'pitcher_outs',
            'singles': 'batter_singles'  # Additional mapping
        }
        
        # Initialize components
        self.matchup_fetcher = MLBMatchupFetcher()
        self.correlator = PitcherBatterCorrelator()
        
    def connect_to_sheets(self):
        """Establish connection to Google Sheets"""
        try:
            scopes = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
            
            credentials = Credentials.from_service_account_info(
                self.google_creds, scopes=scopes)
            client = gspread.authorize(credentials)
            return client
            
        except Exception as e:
            logger.error(f"Failed to connect to Google Sheets: {e}")
            raise
    
    def read_splash_data(self, client):
        """Read Splash Sports data from Google Sheets"""
        try:
            logger.info("Reading Splash data from Google Sheets...")
            spreadsheet = client.open("MLB_Splash_Data")
            splash_worksheet = spreadsheet.worksheet("SPLASH_MLB")
            splash_data = splash_worksheet.get_all_records()
            splash_df = pd.DataFrame(splash_data)
            
            logger.info(f"Successfully read {len(splash_df)} rows of Splash data")
            return splash_df
            
        except Exception as e:
            logger.error(f"Error reading Splash data: {e}")
            return pd.DataFrame()
    
    def read_odds_data(self, client):
        """Read Odds API data from Google Sheets"""
        try:
            logger.info("Reading Odds data from Google Sheets...")
            spreadsheet = client.open("MLB_Splash_Data")
            odds_worksheet = spreadsheet.worksheet("ODDS_API")
            odds_data = odds_worksheet.get_all_records()
            odds_df = pd.DataFrame(odds_data)
            
            logger.info(f"Successfully read {len(odds_df)} rows of Odds data")
            return odds_df
            
        except Exception as e:
            logger.error(f"Error reading Odds data: {e}")
            return pd.DataFrame()
    
    def preprocess_odds_data(self, odds_df):
        """Preprocess odds data to extract bet type and clean lines"""
        if odds_df.empty:
            return odds_df
        
        def extract_bet_info(line_str):
            line_str = str(line_str).strip()
            if line_str.lower().startswith('over '):
                return 'over', line_str.lower().replace('over ', '')
            elif line_str.lower().startswith('under '):
                return 'under', line_str.lower().replace('under ', '')
            else:
                return 'unknown', line_str

        odds_df['bet_type'] = odds_df['Line'].apply(lambda x: extract_bet_info(x)[0])
        odds_df['Line'] = odds_df['Line'].apply(lambda x: extract_bet_info(x)[1])
        
        # Map markets using the market mapping
        reverse_mapping = {v: k for k, v in self.market_mapping.items()}
        odds_df['mapped_market'] = odds_df['Market'].map(reverse_mapping)
        
        logger.info(f"Preprocessed odds data: {len(odds_df)} rows")
        return odds_df
    
    def find_matching_bets(self, splash_df, odds_df):
        """Find matching bets between Splash and Odds data"""
        if splash_df.empty or odds_df.empty:
            logger.warning("One or both datasets are empty")
            return pd.DataFrame()
        
        # Convert Line columns to string for consistent matching
        splash_df['Line'] = splash_df['Line'].astype(str)
        odds_df['Line'] = odds_df['Line'].astype(str)
        
        matching_rows = []
        matches_found = 0
        
        logger.info("Finding matching bets...")
        
        for _, splash_row in splash_df.iterrows():
            matches = odds_df[
                (odds_df['Name'] == splash_row['Name']) &
                (odds_df['mapped_market'] == splash_row['Market']) &
                (odds_df['Line'] == splash_row['Line'])
            ]
            
            if not matches.empty:
                matches_found += len(matches)
                matching_rows.append(matches)
        
        if not matching_rows:
            logger.warning("No matching bets found")
            return pd.DataFrame()
        
        matched_df = pd.concat(matching_rows, ignore_index=True)
        matched_df = matched_df.drop('mapped_market', axis=1)
        
        logger.info(f"Found {matches_found} matching bets across {len(matched_df.groupby(['Name', 'Market', 'Line']))} unique props")
        return matched_df
    
    def american_to_implied_prob(self, odds):
        """Convert American odds to implied probability"""
        if odds > 0:
            return 100 / (odds + 100)
        else:
            return abs(odds) / (abs(odds) + 100)
    
    def calculate_ev(self, matched_df, min_books=3, min_true_prob=0.50, ev_threshold=0.01):
        """Calculate Expected Value for matched bets"""
        if matched_df.empty:
            logger.warning("No matched data for EV calculation")
            return pd.DataFrame()
        
        logger.info("Calculating Expected Value...")
        
        # Data cleaning and preparation
        matched_df = matched_df.copy()
        matched_df['Odds'] = pd.to_numeric(matched_df['Odds'], errors='coerce')
        
        # Filter out unrealistic odds
        matched_df = matched_df[(matched_df['Odds'] >= -2000) & (matched_df['Odds'] <= 2000)]
        
        # Remove duplicates
        matched_df = matched_df.drop_duplicates(
            subset=['Name', 'Market', 'Line', 'Book', 'bet_type'], 
            keep='first'
        )
        
        # Calculate implied probabilities
        matched_df['Implied_Prob'] = matched_df['Odds'].apply(self.american_to_implied_prob)
        
        results = []
        grouped = matched_df.groupby(['Name', 'Market', 'Line', 'bet_type'])
        
        for (player, market, line, bet_type), group in grouped:
            if len(group) < min_books:
                continue
            
            # Calculate true probability (market consensus minus vig)
            avg_implied_prob = group['Implied_Prob'].mean()
            true_prob = avg_implied_prob * 0.95  # Remove 5% vig
            true_prob = max(0.01, min(0.99, true_prob))  # Bound between 1% and 99%
            
            if true_prob < min_true_prob:
                continue
            
            # Calculate Splash Sports EV
            splash_ev_dollars = 100 * (true_prob - 0.50)
            splash_ev_percentage = splash_ev_dollars / 100
            
            if splash_ev_percentage > ev_threshold:
                # Find best sportsbook odds
                if any(group['Odds'] > 0):
                    best_book_row = group.loc[group['Odds'].idxmax()]
                    best_odds = group['Odds'].max()
                else:
                    best_book_row = group.loc[group['Odds'].idxmin()]
                    best_odds = group['Odds'].min()
                
                results.append({
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
                    'Calculation_Time': datetime.now().isoformat()
                })
        
        if results:
            ev_df = pd.DataFrame(results)
            ev_df = ev_df.sort_values('Splash_EV_Percentage', ascending=False)
            logger.info(f"Calculated EV for {len(ev_df)} opportunities")
            return ev_df
        else:
            logger.warning("No EV opportunities found")
            return pd.DataFrame()
    
    def save_results_to_sheets(self, ev_df, client, worksheet_name="EV_RESULTS"):
        """Save EV results back to Google Sheets"""
        try:
            if ev_df.empty:
                logger.warning("No results to save")
                return
            
            logger.info(f"Saving {len(ev_df)} results to Google Sheets...")
            
            spreadsheet = client.open("MLB_Splash_Data")
            
            # Try to get existing worksheet or create new one
            try:
                worksheet = spreadsheet.worksheet(worksheet_name)
            except gspread.WorksheetNotFound:
                worksheet = spreadsheet.add_worksheet(title=worksheet_name, rows=1000, cols=20)
            
            # Clear existing data
            worksheet.clear()
            
            # Add metadata
            metadata = [
                ['Last Updated', datetime.now().isoformat()],
                ['Total Opportunities', len(ev_df)],
                ['']  # Empty row for spacing
            ]
            
            # Combine metadata and data
            all_data = metadata + [ev_df.columns.tolist()] + ev_df.values.tolist()
            
            # Write to sheet
            worksheet.update(range_name='A1', values=all_data)
            
            logger.info(f"Successfully saved results to {worksheet_name}")
            
        except Exception as e:
            logger.error(f"Error saving results to sheets: {e}")
            raise
    
    def save_pitcher_parlays_to_sheets(self, parlays, client, worksheet_name="PITCHER_PARLAYS"):
        """Save pitcher-based parlays to Google Sheets"""
        try:
            if not parlays:
                logger.warning("No pitcher parlays to save")
                return
            
            logger.info(f"Saving {len(parlays)} pitcher parlays to Google Sheets...")
            
            spreadsheet = client.open("MLB_Splash_Data")
            
            # Try to get existing worksheet or create new one
            try:
                worksheet = spreadsheet.worksheet(worksheet_name)
            except gspread.WorksheetNotFound:
                worksheet = spreadsheet.add_worksheet(title=worksheet_name, rows=1000, cols=25)
            
            # Clear existing data
            worksheet.clear()
            
            # Format parlay data for sheets
            formatted_data = []
            for i, parlay in enumerate(parlays, 1):
                anchor = parlay['pitcher_anchor']
                batters = parlay['correlated_batters']
                
                # Create summary row
                batter_summary = " | ".join([
                    f"{b['batter_name']} {b['market']} {b['line']} ({b['bet_type']})"
                    for b in batters
                ])
                
                formatted_data.append([
                    f"PARLAY_{i:03d}",
                    parlay['game_context']['pitcher_team'],
                    parlay['game_context']['opposing_team'],
                    f"{anchor['pitcher_name']} {anchor['market']} {anchor['line']} ({anchor['bet_type']})",
                    anchor['ev'],
                    len(batters),
                    batter_summary,
                    parlay['parlay_ev_estimate'],
                    parlay['avg_correlation_strength'],
                    parlay['confidence'],
                    parlay['risk_level'],
                    parlay['quality_tier'],
                    parlay['parlay_logic'],
                    parlay['created_at']
                ])
            
            # Add headers and metadata
            headers = [
                'Parlay_ID', 'Pitcher_Team', 'Opposing_Team', 'Pitcher_Anchor', 
                'Pitcher_EV', 'Num_Batters', 'Batter_Props', 'Parlay_EV_Estimate',
                'Avg_Correlation', 'Confidence', 'Risk_Level', 'Quality_Tier',
                'Parlay_Logic', 'Created_At'
            ]
            
            metadata = [
                ['Pitcher-Based Parlay Analysis', ''],
                ['Last Updated', datetime.now().isoformat()],
                ['Total Parlays', len(parlays)],
                ['']
            ]
            
            all_data = metadata + [headers] + formatted_data
            
            # Write to sheet
            worksheet.update(range_name='A1', values=all_data)
            
            logger.info(f"Successfully saved pitcher parlays to {worksheet_name}")
            
        except Exception as e:
            logger.error(f"Error saving pitcher parlays to sheets: {e}")
            raise
    
    def run_enhanced_analysis(self, save_to_sheets=True):
        """Run the complete enhanced analysis pipeline with pitcher correlations"""
        try:
            logger.info("Starting enhanced pitcher-based analysis...")
            start_time = datetime.now()
            
            # Step 1: Get game matchups
            logger.info("Step 1: Fetching game matchups and lineups...")
            matchup_data = self.matchup_fetcher.run_matchup_fetch()
            
            if not matchup_data or not matchup_data['pitcher_matchups']:
                logger.warning("No matchup data found - falling back to individual EV only")
                matchup_data = {'pitcher_matchups': []}
            
            # Step 2: Connect to Google Sheets and get data
            logger.info("Step 2: Reading EV calculation data...")
            client = self.connect_to_sheets()
            
            splash_df = self.read_splash_data(client)
            odds_df = self.read_odds_data(client)
            
            if splash_df.empty or odds_df.empty:
                logger.error("Missing required data - cannot proceed with analysis")
                return {
                    'ev_results': pd.DataFrame(),
                    'pitcher_parlays': [],
                    'matchup_data': matchup_data
                }
            
            # Step 3: Calculate individual EVs
            logger.info("Step 3: Calculating individual EVs...")
            odds_df = self.preprocess_odds_data(odds_df)
            matched_df = self.find_matching_bets(splash_df, odds_df)
            
            if matched_df.empty:
                logger.warning("No matches found between datasets")
                return {
                    'ev_results': pd.DataFrame(),
                    'pitcher_parlays': [],
                    'matchup_data': matchup_data
                }
            
            ev_df = self.calculate_ev(matched_df)
            
            # Step 4: Create pitcher-based parlays
            pitcher_parlays = []
            if not ev_df.empty and matchup_data['pitcher_matchups']:
                logger.info("Step 4: Creating pitcher vs batter correlation parlays...")
                pitcher_parlays = self.correlator.create_all_pitcher_parlays(
                    ev_df, matchup_data['pitcher_matchups']
                )
            else:
                logger.warning("Skipping pitcher parlays - insufficient data")
            
            # Step 5: Save results
            if save_to_sheets:
                logger.info("Step 5: Saving results to Google Sheets...")
                if not ev_df.empty:
                    self.save_results_to_sheets(ev_df, client, "EV_RESULTS")
                
                if pitcher_parlays:
                    self.save_pitcher_parlays_to_sheets(pitcher_parlays, client, "PITCHER_PARLAYS")
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            logger.info(f"Enhanced analysis completed in {duration:.2f} seconds")
            logger.info(f"Found {len(ev_df)} individual EV opportunities")
            logger.info(f"Found {len(pitcher_parlays)} pitcher-based parlay opportunities")
            
            return {
                'ev_results': ev_df,
                'pitcher_parlays': pitcher_parlays,
                'matchup_data': matchup_data,
                'analysis_duration': duration
            }
            
        except Exception as e:
            logger.error(f"Error in enhanced analysis: {e}")
            raise

def main():
    """Main function for standalone execution"""
    try:
        calculator = EnhancedEVCalculator()
        results = calculator.run_enhanced_analysis(save_to_sheets=True)
        
        print(f"\n✅ ENHANCED ANALYSIS COMPLETE:")
        print(f"   Individual EV Opportunities: {len(results['ev_results'])}")
        print(f"   Pitcher-Based Parlays: {len(results['pitcher_parlays'])}")
        
        if results['pitcher_parlays']:
            print(f"\nTop 3 Pitcher Parlays:")
            for i, parlay in enumerate(results['pitcher_parlays'][:3], 1):
                anchor = parlay['pitcher_anchor']
                batters_count = len(parlay['correlated_batters'])
                print(f"  {i}. {anchor['pitcher_name']} + {batters_count} opposing batters")
                print(f"     EV: {parlay['parlay_ev_estimate']:.3f} | Quality: {parlay['quality_tier']}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
