# build_parlays.py - Step 7: Build correlated parlays using pitcher anchors vs opposing batters
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

class ParlayBuilder:
    """Step 7: Build pitcher vs opposing batter correlation parlays"""
    
    def __init__(self):
        # Research-based correlation strengths for pitcher vs opposing batters
        self.CORRELATIONS = {
            # Negative correlations (opposing directions)
            ('pitcher_strikeouts', 'batter_hits'): {
                'strength': -0.70,
                'logic': 'More strikeouts = fewer hits for opposing batters'
            },
            ('pitcher_strikeouts', 'batter_total_bases'): {
                'strength': -0.60,
                'logic': 'Strikeouts prevent extra-base hits'
            },
            ('pitcher_strikeouts', 'batter_runs_scored'): {
                'strength': -0.75,
                'logic': 'Dominant pitching prevents runs'
            },
            
            # Positive correlations (same directions)
            ('pitcher_earned_runs', 'batter_runs_scored'): {
                'strength': 0.70,
                'logic': 'Pitcher struggles = opposing batters score more'
            },
            ('pitcher_hits_allowed', 'batter_hits'): {
                'strength': 0.75,
                'logic': 'Pitcher allows hits = batters get hits'
            },
            ('pitcher_hits_allowed', 'batter_total_bases'): {
                'strength': 0.65,
                'logic': 'Hits allowed often include extra-base hits'
            }
        }
        
        # Minimum thresholds
        self.MIN_BATTER_EV = 0.01  # 1% minimum EV for batters
        self.MIN_CORRELATION_STRENGTH = 0.50  # Only use strong correlations
        self.MAX_BATTERS_PER_PARLAY = 5  # Up to 5 batters per pitcher
    
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
        """Read pitcher anchor data from Step 6"""
        try:
            print("📋 Reading pitcher anchor data from Step 6...")
            spreadsheet = client.open("MLB_Splash_Data")
            anchors_worksheet = spreadsheet.worksheet("PITCHER_ANCHORS")
            
            # Get all data and skip metadata rows
            all_data = anchors_worksheet.get_all_values()
            
            # Find where the actual data starts
            data_start_row = 0
            for i, row in enumerate(all_data):
                if row and row[0] == 'Anchor_ID':
                    data_start_row = i
                    break
            
            if data_start_row == 0:
                data_start_row = 4  # Fallback
            
            # Extract headers and data
            headers = all_data[data_start_row]
            data_rows = all_data[data_start_row + 1:]
            
            # Create DataFrame
            anchors_df = pd.DataFrame(data_rows, columns=headers)
            anchors_df = anchors_df[anchors_df['Anchor_ID'].notna() & (anchors_df['Anchor_ID'] != '')]
            
            # Convert numeric columns
            numeric_columns = ['Pitcher_EV', 'Num_Books', 'Best_Odds', 'Num_Opposing_Batters']
            for col in numeric_columns:
                if col in anchors_df.columns:
                    anchors_df[col] = pd.to_numeric(anchors_df[col], errors='coerce')
            
            print(f"✅ Successfully read {len(anchors_df)} pitcher anchors")
            return anchors_df
            
        except Exception as e:
            logger.error(f"Error reading pitcher anchors: {e}")
            print(f"❌ Failed to read pitcher anchors: {e}")
            return pd.DataFrame()
    
    def read_all_ev_results(self, client):
        """Read all EV results to find correlated batter opportunities"""
        try:
            print("📋 Reading all EV results for batter correlation lookup...")
            spreadsheet = client.open("MLB_Splash_Data")
            ev_worksheet = spreadsheet.worksheet("EV_RESULTS")
            
            # Get all data and skip metadata rows
            all_data = ev_worksheet.get_all_values()
            
            # Find where the actual data starts
            data_start_row = 0
            for i, row in enumerate(all_data):
                if row and row[0] in ['Player', 'Name']:
                    data_start_row = i
                    break
            
            if data_start_row == 0:
                data_start_row = 6  # Fallback
            
            # Extract headers and data
            headers = all_data[data_start_row]
            data_rows = all_data[data_start_row + 1:]
            
            # Create DataFrame
            ev_df = pd.DataFrame(data_rows, columns=headers)
            ev_df = ev_df[ev_df['Player'].notna() & (ev_df['Player'] != '')]
            
            # Convert numeric columns
            numeric_columns = ['Splash_EV_Percentage', 'Num_Books_Used', 'Best_Odds', 'True_Prob']
            for col in numeric_columns:
                if col in ev_df.columns:
                    ev_df[col] = pd.to_numeric(ev_df[col], errors='coerce')
            
            print(f"✅ Successfully read {len(ev_df)} total EV opportunities")
            return ev_df
            
        except Exception as e:
            logger.error(f"Error reading EV results: {e}")
            print(f"❌ Failed to read EV results: {e}")
            return pd.DataFrame()
    
    def build_pitcher_parlays(self, pitcher_anchors_df, all_evs_df):
        """Build correlated parlays for each pitcher anchor"""
        print("⚾ STEP 7: BUILDING PITCHER-BATTER CORRELATION PARLAYS")
        print("=" * 60)
        
        if pitcher_anchors_df.empty or all_evs_df.empty:
            print("❌ Missing pitcher anchors or EV data")
            return []
        
        print(f"🎯 Building parlays for {len(pitcher_anchors_df)} pitcher anchors")
        print(f"📊 Available correlations: {len(self.CORRELATIONS)}")
        
        all_parlays = []
        
        for _, anchor_row in pitcher_anchors_df.iterrows():
            parlay = self._build_single_pitcher_parlay(anchor_row, all_evs_df)
            if parlay:
                all_parlays.append(parlay)
        
        # Sort parlays by estimated value
        all_parlays.sort(key=lambda x: x['parlay_ev_estimate'], reverse=True)
        
        print(f"✅ Built {len(all_parlays)} correlation parlays!")
        
        if all_parlays:
            # Show summary
            print(f"\n📈 PARLAY SUMMARY:")
            print(f"   Best parlay EV: {all_parlays[0]['parlay_ev_estimate']:.3f}")
            print(f"   Average correlation: {np.mean([p['avg_correlation_strength'] for p in all_parlays]):.3f}")
            
            # Show top parlays
            print(f"\n🏆 Top 3 parlays:")
            for i, parlay in enumerate(all_parlays[:3], 1):
                anchor = parlay['pitcher_anchor']
                batter_count = len(parlay['correlated_batters'])
                print(f"   {i}. {anchor['Pitcher_Name']} + {batter_count} opposing batters")
                print(f"      EV: {parlay['parlay_ev_estimate']:.3f} | Correlation: {parlay['avg_correlation_strength']:.3f}")
        
        return all_parlays
    
    def _build_single_pitcher_parlay(self, anchor_row, all_evs_df):
        """Build a parlay for a single pitcher anchor"""
        pitcher_name = anchor_row['Pitcher_Name']
        pitcher_market = anchor_row['Market']
        pitcher_bet_type = anchor_row['Bet_Type']
        
        # Parse opposing batter names
        opposing_batter_names = []
        if anchor_row['Opposing_Batter_Names']:
            batter_names = str(anchor_row['Opposing_Batter_Names']).split('; ')
            opposing_batter_names = [name.strip() for name in batter_names if name.strip()]
        
        if not opposing_batter_names:
            return None
        
        # Find correlations for this pitcher market
        applicable_correlations = []
        for (p_market, b_market), corr_info in self.CORRELATIONS.items():
            if p_market == pitcher_market and abs(corr_info['strength']) >= self.MIN_CORRELATION_STRENGTH:
                applicable_correlations.append((b_market, corr_info))
        
        if not applicable_correlations:
            return None
        
        # Find correlated batter opportunities
        correlated_batters = []
        for batter_name in opposing_batter_names:
            for batter_market, corr_info in applicable_correlations:
                batter_opportunities = self._find_batter_opportunities(
                    batter_name, batter_market, pitcher_bet_type, corr_info, all_evs_df
                )
                correlated_batters.extend(batter_opportunities)
        
        if not correlated_batters:
            return None
        
        # Sort by correlation strength * EV and take top batters
        correlated_batters.sort(key=lambda x: x['correlation_strength'] * x['ev'], reverse=True)
        selected_batters = correlated_batters[:self.MAX_BATTERS_PER_PARLAY]
        
        # Build the parlay
        return self._create_parlay_object(anchor_row, selected_batters)
    
    def _find_batter_opportunities(self, batter_name, batter_market, pitcher_bet_type, corr_info, all_evs_df):
        """Find EV opportunities for a specific batter in the correlated market"""
        correlation_strength = abs(corr_info['strength'])
        
        # Determine target bet type based on correlation
        if corr_info['strength'] < 0:  # Negative correlation
            target_bet_type = 'under' if pitcher_bet_type == 'over' else 'over'
        else:  # Positive correlation
            target_bet_type = pitcher_bet_type
        
        # Find matching batter EVs
        batter_evs = all_evs_df[
            (all_evs_df['Player'] == batter_name) &
            (all_evs_df['Market'] == batter_market) &
            (all_evs_df['Bet_Type'] == target_bet_type) &
            (all_evs_df['Splash_EV_Percentage'] >= self.MIN_BATTER_EV)
        ]
        
        opportunities = []
        for _, batter_ev in batter_evs.iterrows():
            opportunities.append({
                'player': batter_name,
                'market': batter_market,
                'line': batter_ev['Line'],
                'bet_type': batter_ev['Bet_Type'],
                'ev': batter_ev['Splash_EV_Percentage'],
                'books_used': batter_ev['Num_Books_Used'],
                'best_odds': batter_ev['Best_Odds'],
                'correlation_strength': correlation_strength,
                'correlation_logic': corr_info['logic'],
                'true_prob': batter_ev.get('True_Prob', 0)
            })
        
        return opportunities
    
    def _create_parlay_object(self, anchor_row, selected_batters):
        """Create a complete parlay object"""
        # Extract pitcher anchor info
        pitcher_anchor = {
            'player': anchor_row['Pitcher_Name'],
            'market': anchor_row['Market'],
            'line': anchor_row['Line'],
            'bet_type': anchor_row['Bet_Type'],
            'ev': anchor_row['Pitcher_EV'],
            'books_used': anchor_row['Num_Books'],
            'best_odds': anchor_row['Best_Odds']
        }
        
        # Calculate parlay metrics
        all_evs = [pitcher_anchor['ev']] + [b['ev'] for b in selected_batters]
        avg_correlation = np.mean([b['correlation_strength'] for b in selected_batters])
        
        # Estimate parlay EV with correlation bonus
        base_ev = sum(all_evs)
        correlation_bonus = avg_correlation * 0.3  # Up to 30% bonus
        parlay_ev_estimate = base_ev * (1 + correlation_bonus)
        
        # Calculate confidence
        all_books = [pitcher_anchor['books_used']] + [b['books_used'] for b in selected_batters]
        avg_books = np.mean(all_books)
        confidence = min(1.0, (avg_books / 8) * 0.6 + avg_correlation * 0.4)
        
        # Assess risk and quality
        risk_level, quality = self._assess_parlay_quality(all_evs, avg_correlation, len(selected_batters))
        
        return {
            'parlay_id': f"parlay_{hash(str(anchor_row['Anchor_ID']) + str(selected_batters)) % 10000}",
            'game_id': anchor_row['Game_ID'],
            'pitcher_anchor': pitcher_anchor,
            'correlated_batters': selected_batters,
            'total_legs': 1 + len(selected_batters),
            'individual_evs': all_evs,
            'parlay_ev_estimate': parlay_ev_estimate,
            'avg_correlation_strength': avg_correlation,
            'confidence': confidence,
            'risk_level': risk_level,
            'quality_tier': quality,
            'game_context': {
                'pitcher_team': anchor_row['Pitcher_Team'],
                'opposing_team': anchor_row['Opposing_Team'],
                'matchup_type': anchor_row['Matchup_Type']
            },
            'parlay_logic': self._explain_parlay_logic(pitcher_anchor, selected_batters),
            'created_at': datetime.now().isoformat()
        }
    
    def _assess_parlay_quality(self, all_evs, avg_correlation, num_batters):
        """Assess parlay risk level and quality tier"""
        avg_ev = np.mean(all_evs)
        
        if avg_correlation >= 0.70 and avg_ev >= 0.035 and num_batters <= 3:
            return "Low", "Excellent"
        elif avg_correlation >= 0.60 and avg_ev >= 0.025 and num_batters <= 4:
            return "Medium", "Good"
        elif avg_correlation >= 0.50 and avg_ev >= 0.02:
            return "Medium", "Fair"
        else:
            return "High", "Speculative"
    
    def _explain_parlay_logic(self, pitcher_anchor, selected_batters):
        """Generate human-readable parlay logic"""
        pitcher_desc = f"{pitcher_anchor['player']} {pitcher_anchor['market']} {pitcher_anchor['bet_type']}"
        
        batter_descriptions = []
        for batter in selected_batters:
            batter_desc = f"{batter['player']} {batter['market']} {batter['bet_type']}"
            logic = batter['correlation_logic']
            batter_descriptions.append(f"{batter_desc} ({logic})")
        
        return f"Anchor: {pitcher_desc} → Correlated: {'; '.join(batter_descriptions)}"
    
    def save_parlays(self, parlays, client):
        """Save final parlays to Google Sheets"""
        try:
            if not parlays:
                print("❌ No parlays to save")
                return
            
            print(f"💾 Saving {len(parlays)} correlation parlays...")
            
            spreadsheet = client.open("MLB_Splash_Data")
            
            # Get or create CORRELATION_PARLAYS worksheet
            try:
                worksheet = spreadsheet.worksheet("CORRELATION_PARLAYS")
            except:
                worksheet = spreadsheet.add_worksheet(title="CORRELATION_PARLAYS", rows=1000, cols=25)
            
            # Clear existing data
            worksheet.clear()
            
            # Format parlay data for sheet
            formatted_data = []
            for i, parlay in enumerate(parlays, 1):
                pitcher = parlay['pitcher_anchor']
                batters = parlay['correlated_batters']
                
                # Create batter summary
                batter_summary = " | ".join([
                    f"{b['player']} {b['market']} {b['line']} ({b['bet_type']})"
                    for b in batters
                ])
                
                formatted_data.append([
                    f"PARLAY_{i:03d}",
                    parlay['game_id'],
                    parlay['game_context']['pitcher_team'],
                    parlay['game_context']['opposing_team'],
                    f"{pitcher['player']} {pitcher['market']} {pitcher['line']} ({pitcher['bet_type']})",
                    pitcher['ev'],
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
            
            # Headers and metadata
            headers = [
                'Parlay_ID', 'Game_ID', 'Pitcher_Team', 'Opposing_Team', 'Pitcher_Anchor',
                'Pitcher_EV', 'Num_Batters', 'Batter_Props', 'Parlay_EV_Estimate',
                'Avg_Correlation', 'Confidence', 'Risk_Level', 'Quality_Tier',
                'Parlay_Logic', 'Created_At'
            ]
            
            metadata = [
                ['Pitcher vs Batter Correlation Parlays', ''],
                ['Created At', datetime.now().isoformat()],
                ['Total Parlays', len(parlays)],
                ['Best Parlay EV', f"{parlays[0]['parlay_ev_estimate']:.3f}" if parlays else 'N/A'],
                ['']
            ]
            
            all_data = metadata + [headers] + formatted_data
            
            # Write to sheet
            worksheet.update(range_name='A1', values=all_data)
            
            print("✅ Successfully saved correlation parlays to CORRELATION_PARLAYS sheet")
            
        except Exception as e:
            logger.error(f"Error saving parlays: {e}")
            print(f"❌ Failed to save parlays: {e}")
            raise

def main():
    """Main function for Step 7"""
    try:
        builder = ParlayBuilder()
        
        # Connect to Google Sheets
        client = builder.connect_to_sheets()
        
        # Read pitcher anchors from Step 6
        pitcher_anchors_df = builder.read_pitcher_anchors(client)
        
        if pitcher_anchors_df.empty:
            print("❌ No pitcher anchors found from Step 6")
            return
        
        # Read all EV results for batter lookup
        all_evs_df = builder.read_all_ev_results(client)
        
        if all_evs_df.empty:
            print("❌ No EV results found for batter correlation lookup")
            return
        
        # Build correlation parlays
        parlays = builder.build_pitcher_parlays(pitcher_anchors_df, all_evs_df)
        
        if not parlays:
            print("❌ No correlation parlays could be built")
            return
        
        # Save parlays
        builder.save_parlays(parlays, client)
        
        print(f"\n✅ STEP 7 COMPLETE - FULL PIPELINE FINISHED!")
        print(f"   Correlation parlays built: {len(parlays)}")
        print(f"   Best parlay EV: {parlays[0]['parlay_ev_estimate']:.3f}")
        print(f"   Average parlay correlation: {np.mean([p['avg_correlation_strength'] for p in parlays]):.3f}")
        print("   📊 Results saved to CORRELATION_PARLAYS sheet")
        
    except Exception as e:
        logger.error(f"Error in Step 7: {e}")
        print(f"❌ Step 7 failed: {e}")

if __name__ == "__main__":
    main()
