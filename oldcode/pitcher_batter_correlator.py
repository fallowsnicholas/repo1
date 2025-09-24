# pitcher_batter_correlator.py
import pandas as pd
import numpy as np
from datetime import datetime
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class PitcherBatterCorrelator:
    """
    Core logic for creating pitcher vs opposing batter parlay correlations
    """
    
    def __init__(self):
        # Research-based correlation strengths
        self.correlations = {
            # Negative correlations (opposing directions)
            'pitcher_strikeouts_vs_batter_hits': {
                'strength': -0.70,
                'pitcher_market': 'pitcher_strikeouts',
                'batter_market': 'batter_hits',
                'logic': 'More strikeouts = fewer hits for opposing batters'
            },
            'pitcher_strikeouts_vs_batter_total_bases': {
                'strength': -0.60,
                'pitcher_market': 'pitcher_strikeouts', 
                'batter_market': 'batter_total_bases',
                'logic': 'Strikeouts prevent extra-base hits'
            },
            'pitcher_strikeouts_vs_batter_runs_scored': {
                'strength': -0.75,
                'pitcher_market': 'pitcher_strikeouts',
                'batter_market': 'batter_runs_scored', 
                'logic': 'Dominant pitching prevents runs'
            },
            
            # Positive correlations (same directions)
            'pitcher_earned_runs_vs_batter_runs_scored': {
                'strength': 0.70,
                'pitcher_market': 'pitcher_earned_runs',
                'batter_market': 'batter_runs_scored',
                'logic': 'Pitcher struggles = opposing batters score more'
            },
            'pitcher_hits_allowed_vs_batter_hits': {
                'strength': 0.75,
                'pitcher_market': 'pitcher_hits_allowed',
                'batter_market': 'batter_hits',
                'logic': 'Pitcher allows hits = batters get hits'
            },
            'pitcher_hits_allowed_vs_batter_total_bases': {
                'strength': 0.65,
                'pitcher_market': 'pitcher_hits_allowed',
                'batter_market': 'batter_total_bases',
                'logic': 'Hits allowed often include extra-base hits'
            }
        }
        
        # Minimum thresholds
        self.min_pitcher_ev = 0.02  # 2% minimum EV for pitcher (anchor)
        self.min_batter_ev = 0.01   # 1% minimum EV for batters
        self.min_correlation_strength = 0.50  # Only use strong correlations
        
    def find_pitcher_anchors(self, ev_df: pd.DataFrame) -> List[Dict]:
        """Find pitchers with positive EV to use as parlay anchors"""
        print("🎯 Finding pitcher anchors with positive EV...")
        
        # Filter for pitcher markets with sufficient EV
        pitcher_markets = ['pitcher_strikeouts', 'pitcher_earned_runs', 'pitcher_hits_allowed', 'pitcher_outs']
        pitcher_evs = ev_df[
            (ev_df['Market'].isin(pitcher_markets)) & 
            (ev_df['Splash_EV_Percentage'] >= self.min_pitcher_ev)
        ].copy()
        
        if pitcher_evs.empty:
            print("❌ No pitcher EVs found above threshold")
            return []
        
        print(f"📈 Found {len(pitcher_evs)} pitcher EV opportunities")
        
        # Group by pitcher
        pitcher_anchors = []
        for pitcher, pitcher_props in pitcher_evs.groupby('Player'):
            for _, prop in pitcher_props.iterrows():
                pitcher_anchors.append({
                    'pitcher_name': pitcher,
                    'market': prop['Market'],
                    'line': prop['Line'],
                    'bet_type': prop['Bet_Type'],
                    'ev': prop['Splash_EV_Percentage'],
                    'books_used': prop['Num_Books_Used'],
                    'true_prob': prop.get('True_Prob', 0),
                    'prop_data': prop.to_dict()
                })
        
        # Sort by EV (highest first)
        pitcher_anchors.sort(key=lambda x: x['ev'], reverse=True)
        
        print(f"⚾ Found {len(pitcher_anchors)} pitcher anchor opportunities")
        return pitcher_anchors
    
    def find_correlated_batters(self, pitcher_anchor: Dict, ev_df: pd.DataFrame, 
                              opposing_batters: List[Dict]) -> List[Dict]:
        """Find opposing batters with correlated markets and positive EV"""
        pitcher_market = pitcher_anchor['market']
        pitcher_bet_type = pitcher_anchor['bet_type']
        
        # Find applicable correlations
        applicable_correlations = []
        for corr_key, corr_data in self.correlations.items():
            if corr_data['pitcher_market'] == pitcher_market and abs(corr_data['strength']) >= self.min_correlation_strength:
                applicable_correlations.append((corr_key, corr_data))
        
        if not applicable_correlations:
            return []
        
        print(f"🔗 Found {len(applicable_correlations)} applicable correlations for {pitcher_market}")
        
        correlated_batters = []
        
        for corr_key, corr_data in applicable_correlations:
            batter_market = corr_data['batter_market']
            correlation_strength = corr_data['strength']
            
            # Determine directional alignment
            if correlation_strength < 0:  # Negative correlation
                # Opposite directions: pitcher OVER → batter UNDER, pitcher UNDER → batter OVER
                target_batter_bet_type = 'under' if pitcher_bet_type == 'over' else 'over'
            else:  # Positive correlation
                # Same directions: pitcher OVER → batter OVER, pitcher UNDER → batter UNDER
                target_batter_bet_type = pitcher_bet_type
            
            # Find batters with this market and bet type
            for batter_info in opposing_batters:
                batter_name = batter_info.get('name', 'Unknown')
                
                # Find EV opportunities for this batter in this market
                batter_evs = ev_df[
                    (ev_df['Player'] == batter_name) &
                    (ev_df['Market'] == batter_market) &
                    (ev_df['Bet_Type'] == target_batter_bet_type) &
                    (ev_df['Splash_EV_Percentage'] >= self.min_batter_ev)
                ]
                
                for _, batter_prop in batter_evs.iterrows():
                    correlated_batters.append({
                        'batter_name': batter_name,
                        'batter_position': batter_info.get('position', 0),
                        'market': batter_market,
                        'line': batter_prop['Line'],
                        'bet_type': batter_prop['Bet_Type'],
                        'ev': batter_prop['Splash_EV_Percentage'],
                        'books_used': batter_prop['Num_Books_Used'],
                        'true_prob': batter_prop.get('True_Prob', 0),
                        'correlation_key': corr_key,
                        'correlation_strength': abs(correlation_strength),
                        'correlation_logic': corr_data['logic'],
                        'prop_data': batter_prop.to_dict()
                    })
        
        # Sort by correlation strength * EV (prioritize strong correlations with good EV)
        correlated_batters.sort(key=lambda x: x['correlation_strength'] * x['ev'], reverse=True)
        
        return correlated_batters
    
    def build_pitcher_parlay(self, pitcher_anchor: Dict, correlated_batters: List[Dict], 
                           max_batters: int = 5) -> Dict[str, Any]:
        """Build a complete parlay with pitcher anchor + correlated batters"""
        if not correlated_batters:
            return None
        
        # Select top correlated batters (up to max_batters)
        selected_batters = correlated_batters[:max_batters]
        
        # Calculate parlay metrics
        all_props = [pitcher_anchor] + selected_batters
        individual_evs = [prop['ev'] for prop in all_props]
        avg_correlation = np.mean([batter['correlation_strength'] for batter in selected_batters])
        
        # Estimate parlay EV with correlation bonus
        base_ev = sum(individual_evs)
        correlation_bonus = avg_correlation * 0.3  # Up to 30% bonus for strong correlations
        parlay_ev_estimate = base_ev * (1 + correlation_bonus)
        
        # Calculate confidence
        avg_books = np.mean([prop['books_used'] for prop in all_props])
        confidence = min(1.0, (avg_books / 8) * 0.6 + avg_correlation * 0.4)
        
        # Assess risk level
        if avg_correlation >= 0.70 and np.mean(individual_evs) >= 0.03:
            risk_level = "Low"
            quality = "Excellent"
        elif avg_correlation >= 0.60 and np.mean(individual_evs) >= 0.025:
            risk_level = "Medium"
            quality = "Good"
        else:
            risk_level = "High"
            quality = "Speculative"
        
        return {
            'parlay_id': f"pitcher_parlay_{hash(str(all_props)) % 10000}",
            'pitcher_anchor': pitcher_anchor,
            'correlated_batters': selected_batters,
            'total_legs': len(all_props),
            'individual_evs': individual_evs,
            'parlay_ev_estimate': parlay_ev_estimate,
            'avg_correlation_strength': avg_correlation,
            'confidence': confidence,
            'risk_level': risk_level,
            'quality_tier': quality,
            'parlay_logic': self._explain_parlay_logic(pitcher_anchor, selected_batters),
            'created_at': datetime.now().isoformat()
        }
    
    def _explain_parlay_logic(self, pitcher_anchor: Dict, selected_batters: List[Dict]) -> str:
        """Generate human-readable explanation of parlay logic"""
        pitcher_desc = f"{pitcher_anchor['pitcher_name']} {pitcher_anchor['market']} {pitcher_anchor['bet_type']}"
        
        explanations = []
        for batter in selected_batters:
            batter_desc = f"{batter['batter_name']} {batter['market']} {batter['bet_type']}"
            logic = batter['correlation_logic']
            explanations.append(f"{batter_desc} ({logic})")
        
        return f"Anchor: {pitcher_desc} → Correlated: {'; '.join(explanations)}"
    
    def create_all_pitcher_parlays(self, ev_df: pd.DataFrame, pitcher_matchups: List[Dict]) -> List[Dict]:
        """Create all possible pitcher-based parlays from matchup data"""
        print("\n🏗️ Building pitcher-based correlation parlays...")
        
        # Find pitcher anchors
        pitcher_anchors = self.find_pitcher_anchors(ev_df)
        
        if not pitcher_anchors:
            print("❌ No pitcher anchors found")
            return []
        
        all_parlays = []
        
        for matchup in pitcher_matchups:
            matchup_pitcher = matchup.get('pitcher', {}).get('name', 'Unknown')
            opposing_batters = matchup.get('opposing_batters', [])
            
            if not opposing_batters:
                continue
            
            # Find anchors for this pitcher
            pitcher_anchors_for_game = [
                anchor for anchor in pitcher_anchors 
                if anchor['pitcher_name'] == matchup_pitcher
            ]
            
            for pitcher_anchor in pitcher_anchors_for_game:
                # Find correlated batters for this pitcher
                correlated_batters = self.find_correlated_batters(
                    pitcher_anchor, ev_df, opposing_batters
                )
                
                if correlated_batters:
                    # Build parlay
                    parlay = self.build_pitcher_parlay(
                        pitcher_anchor, correlated_batters, max_batters=5
                    )
                    
                    if parlay:
                        # Add matchup context
                        parlay['game_context'] = {
                            'game_id': matchup['game_id'],
                            'pitcher_team': matchup['pitcher_team'],
                            'opposing_team': matchup['opposing_team'],
                            'matchup_type': matchup['matchup_type']
                        }
                        all_parlays.append(parlay)
                        
                        print(f"  ✅ Created parlay: {pitcher_anchor['pitcher_name']} vs {len(correlated_batters)} opposing batters")
        
        # Sort by parlay EV estimate
        all_parlays.sort(key=lambda x: x['parlay_ev_estimate'], reverse=True)
        
        print(f"\n🎯 TOTAL PARLAYS CREATED: {len(all_parlays)}")
        return all_parlays
    
    def generate_parlay_report(self, parlays: List[Dict], top_n: int = 10) -> str:
        """Generate detailed report of pitcher-based parlays"""
        if not parlays:
            return "No pitcher-based parlays found."
        
        report = []
        report.append("⚾ PITCHER VS OPPOSING BATTERS PARLAY OPPORTUNITIES")
        report.append("=" * 70)
        report.append(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Total Parlays Found: {len(parlays)}")
        report.append("")
        
        for i, parlay in enumerate(parlays[:top_n], 1):
            anchor = parlay['pitcher_anchor']
            batters = parlay['correlated_batters']
            
            report.append(f"#{i} - {parlay['quality_tier']} Quality ({parlay['risk_level']} Risk)")
            report.append(f"Game: {parlay['game_context']['pitcher_team']} vs {parlay['game_context']['opposing_team']}")
            report.append(f"Parlay EV: {parlay['parlay_ev_estimate']:.3f} | Confidence: {parlay['confidence']:.2f}")
            report.append(f"Avg Correlation: {parlay['avg_correlation_strength']:.3f}")
            report.append("")
            
            # Pitcher anchor
            report.append(f"📍 ANCHOR: {anchor['pitcher_name']} - {anchor['market']} {anchor['line']} ({anchor['bet_type']})")
            report.append(f"    EV: {anchor['ev']:.3f} | Books: {anchor['books_used']}")
            report.append("")
            
            # Correlated batters
            report.append("🎯 CORRELATED BATTERS:")
            for j, batter in enumerate(batters, 1):
                report.append(f"  {j}. {batter['batter_name']} (#{batter['batter_position']}) - {batter['market']} {batter['line']} ({batter['bet_type']})")
                report.append(f"     EV: {batter['ev']:.3f} | Correlation: {batter['correlation_strength']:.3f} | Logic: {batter['correlation_logic']}")
            
            report.append("")
            report.append(f"📝 Full Logic: {parlay['parlay_logic']}")
            report.append("-" * 60)
        
        return "\n".join(report)

def main():
    """Test pitcher-batter correlator"""
    print("Testing Pitcher-Batter Correlator...")
    
    # This would be called with real EV data and matchups
    correlator = PitcherBatterCorrelator()
    
    # Show available correlations
    print("Available Correlations:")
    for key, data in correlator.correlations.items():
        print(f"  • {key}: {data['strength']:.2f} - {data['logic']}")

if __name__ == "__main__":
    main()
