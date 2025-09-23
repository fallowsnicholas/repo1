# correlation_analyzer.py - Debug Version
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from itertools import combinations
import json

logger = logging.getLogger(__name__)

class CorrelationAnalyzer:
    """
    Simplified correlation analyzer focused on basic MLB prop relationships - DEBUG VERSION
    """
    
    def __init__(self):
        # Define simple, logical correlations based on baseball knowledge
        self.positive_correlations = {
            # Same player correlations (strong positive)
            'same_player_hitting': {
                ('hits', 'total_bases'): 0.8,
                ('hits', 'runs'): 0.6,
                ('hits', 'RBIs'): 0.5,
                ('total_bases', 'RBIs'): 0.6,
                ('hits', 'batter_singles'): 0.7,
                ('hits', 'singles'): 0.7,  # Alternative market name
            },
            # Same player pitcher correlations
            'same_player_pitching': {
                ('strikeouts', 'total_outs'): 0.7,
            }
        }
        
        self.negative_correlations = {
            # Same player pitcher correlations (negative)
            'pitcher_performance': {
                ('strikeouts', 'earned_runs'): -0.6,
                ('strikeouts', 'hits_allowed'): -0.5,
                ('total_outs', 'earned_runs'): -0.4,
                ('hits_allowed', 'strikeouts'): -0.5,
            }
        }
        
        # LOWERED THRESHOLDS for debugging
        self.min_individual_ev = 0.01  # Lowered from 0.02 to 0.01 (1%)
        self.min_parlay_correlation = 0.2  # Lowered from 0.4 to 0.2
    
    def get_matchup_data(self, ev_df):
        """Extract matchup information from EV results - simplified version"""
        if ev_df.empty:
            return pd.DataFrame()
        
        # Just return the original dataframe with some basic grouping
        ev_df_copy = ev_df.copy()
        
        # Simple game grouping - group by similar timing (this is a placeholder)
        ev_df_copy['game_group'] = ev_df_copy.index // 10  # Group every 10 props as same "game"
        
        return ev_df_copy
    
    def identify_correlated_props(self, ev_df, min_correlation=0.2, max_parlay_size=3):  # Lowered min_correlation
        """
        Identify sets of props that are positively correlated for parlay construction
        """
        if ev_df.empty:
            logger.warning("No EV data provided for correlation analysis")
            return []
        
        print(f"\n🔍 DEBUGGING: Analyzing {len(ev_df)} EV opportunities for parlay combinations...")
        
        # Show EV distribution
        print(f"EV Distribution:")
        print(f"  Min EV: {ev_df['Splash_EV_Percentage'].min():.4f}")
        print(f"  Max EV: {ev_df['Splash_EV_Percentage'].max():.4f}")
        print(f"  Mean EV: {ev_df['Splash_EV_Percentage'].mean():.4f}")
        print(f"  Props above {self.min_individual_ev}: {(ev_df['Splash_EV_Percentage'] >= self.min_individual_ev).sum()}")
        
        # Filter to only positive EV opportunities above threshold
        positive_ev = ev_df[ev_df['Splash_EV_Percentage'] >= self.min_individual_ev].copy()
        
        if len(positive_ev) < 2:
            print(f"❌ Not enough positive EV opportunities for parlays (need 2+, found {len(positive_ev)})")
            return []
        
        print(f"✅ Found {len(positive_ev)} positive EV opportunities to analyze")
        
        # Show player breakdown
        player_counts = positive_ev['Player'].value_counts()
        print(f"Player breakdown (top 10):")
        for player, count in player_counts.head(10).items():
            print(f"  {player}: {count} props")
        
        # Show market breakdown
        market_counts = positive_ev['Market'].value_counts()
        print(f"Market breakdown:")
        for market, count in market_counts.items():
            print(f"  {market}: {count} props")
        
        # SMARTER SELECTION: Prioritize players with multiple props for same-player correlations
        analysis_props = []
        
        # First, add all props from players who have multiple props (for same-player correlations)
        players_with_multiple = player_counts[player_counts >= 2].index
        for player in players_with_multiple:
            player_props = positive_ev[positive_ev['Player'] == player]
            analysis_props.extend(player_props.to_dict('records'))
            print(f"🎯 Added {len(player_props)} props for {player} (same-player correlations possible)")
        
        # Then fill remaining slots with highest EV single-player props
        remaining_slots = max(0, 20 - len(analysis_props))
        if remaining_slots > 0:
            single_player_props = positive_ev[~positive_ev['Player'].isin(players_with_multiple)]
            if not single_player_props.empty:
                top_singles = single_player_props.head(remaining_slots)
                analysis_props.extend(top_singles.to_dict('records'))
                print(f"📈 Added {len(top_singles)} high-EV single props")
        
        print(f"📊 Total props for analysis: {len(analysis_props)}")
        
        parlay_opportunities = []
        total_combinations_checked = 0
        max_total_combinations = 200  # Increased since we're being smarter about selection
        valid_combinations = 0
        
        # Convert back to DataFrame for easier processing
        analysis_df = pd.DataFrame(analysis_props)
        
        # Generate combinations starting with size 2, then 3
        for size in range(2, min(max_parlay_size + 1, min(len(analysis_df) + 1, 4))):
            combo_count = 0
            max_combos_this_size = 100  # Increased limit
            
            print(f"\n🔍 Checking {size}-prop combinations...")
            
            for combo_indices in combinations(range(len(analysis_df)), size):
                if total_combinations_checked >= max_total_combinations:
                    print(f"⚠️ Reached maximum combination limit ({max_total_combinations}), stopping analysis")
                    break
                    
                combo_props = analysis_df.iloc[list(combo_indices)]
                props_list = combo_props.to_dict('records')
                
                # Debug: Show what combination we're checking (first 10 now)
                if total_combinations_checked < 10:
                    print(f"  Checking combination {total_combinations_checked + 1}:")
                    for prop in props_list:
                        print(f"    - {prop['Player']} {prop['Market']} {prop['Line']} (EV: {prop['Splash_EV_Percentage']:.3f})")
                
                # Check if this is a valid parlay combination
                if not self._is_valid_parlay(props_list):
                    if total_combinations_checked < 10:
                        print(f"    ❌ Invalid parlay (duplicate player/market or conflicting)")
                    total_combinations_checked += 1
                    continue
                
                valid_combinations += 1
                if total_combinations_checked < 10:
                    print(f"    ✅ Valid combination")
                
                # Calculate correlation
                correlation_score = self._calculate_correlation_score(props_list)
                if total_combinations_checked < 10:
                    print(f"    📊 Correlation score: {correlation_score:.3f} (need ≥{min_correlation})")
                
                if correlation_score >= min_correlation:
                    parlay_info = self._analyze_combination(props_list)
                    if parlay_info:
                        parlay_opportunities.append(parlay_info)
                        combo_count += 1
                        if total_combinations_checked < 10:
                            print(f"    🎯 Added to parlay opportunities!")
                else:
                    if total_combinations_checked < 10:
                        print(f"    ❌ Correlation too low")
                
                total_combinations_checked += 1
                
                # Limit combinations per size to prevent excessive processing
                if combo_count >= max_combos_this_size:
                    print(f"  📈 Reached max combinations for size {size}, moving to next size")
                    break
                    
            if total_combinations_checked >= max_total_combinations:
                break
        
        print(f"\n📊 SUMMARY:")
        print(f"  Total combinations checked: {total_combinations_checked}")
        print(f"  Valid combinations: {valid_combinations}")
        print(f"  Correlation threshold: {min_correlation}")
        print(f"  Parlays found: {len(parlay_opportunities)}")
        
        # Sort by estimated parlay value
        parlay_opportunities.sort(key=lambda x: x['parlay_ev_estimate'], reverse=True)
        
        print(f"✅ Found {len(parlay_opportunities)} potential parlay opportunities")
        return parlay_opportunities[:10]
    
    def _is_valid_parlay(self, props_list):
        """
        Check if a combination is valid for parlaying
        """
        # Can't parlay same market for same player
        player_markets = [(prop['Player'], prop['Market']) for prop in props_list]
        if len(set(player_markets)) != len(player_markets):
            return False
        
        # Can't parlay contradictory props (e.g., over/under same line same player)
        for i, prop1 in enumerate(props_list):
            for prop2 in props_list[i+1:]:
                if (prop1['Player'] == prop2['Player'] and 
                    prop1['Market'] == prop2['Market'] and
                    prop1['Line'] == prop2['Line']):
                    return False
        
        return True
    
    def _calculate_correlation_score(self, props_list):
        """
        Calculate correlation score for the combination
        """
        if len(props_list) < 2:
            return 0
        
        total_correlation = 0
        pair_count = 0
        
        for i, prop1 in enumerate(props_list):
            for prop2 in props_list[i+1:]:
                correlation = self._get_pair_correlation(prop1, prop2)
                total_correlation += correlation
                pair_count += 1
        
        return total_correlation / pair_count if pair_count > 0 else 0
    
    def _get_pair_correlation(self, prop1, prop2):
        """
        Get correlation between two specific props
        """
        # Same player correlations
        if prop1['Player'] == prop2['Player']:
            corr = self._get_same_player_correlation(prop1['Market'], prop2['Market'])
            return corr
        
        # Different players - assume weak positive correlation
        return 0.1
    
    def _get_same_player_correlation(self, market1, market2):
        """
        Get correlation for same player, different markets
        """
        # Check positive correlations
        for category, correlations in self.positive_correlations.items():
            for (m1, m2), corr in correlations.items():
                if (m1 == market1 and m2 == market2) or (m1 == market2 and m2 == market1):
                    return corr
        
        # Check negative correlations  
        for category, correlations in self.negative_correlations.items():
            for (m1, m2), corr in correlations.items():
                if (m1 == market1 and m2 == market2) or (m1 == market2 and m2 == market1):
                    return corr
        
        # Default weak positive correlation for same player
        return 0.3  # Increased from 0.2 to 0.3
    
    def _analyze_combination(self, props_list):
        """
        Analyze a combination of props for parlay viability
        """
        # Basic validation
        if not self._is_valid_parlay(props_list):
            return None
        
        # Calculate correlation score
        correlation_score = self._calculate_correlation_score(props_list)
        
        if correlation_score < self.min_parlay_correlation:
            return None
        
        # Estimate parlay value
        individual_evs = [prop['Splash_EV_Percentage'] for prop in props_list]
        parlay_ev_estimate = self._estimate_parlay_value(individual_evs, correlation_score)
        
        # Determine risk level
        risk_level = self._assess_risk_level(props_list, correlation_score)
        confidence = self._calculate_confidence(props_list)
        
        return {
            'game_id': f"parlay_{hash(str(props_list)) % 10000}",  # Simple ID
            'props': props_list,
            'correlation_score': correlation_score,
            'individual_evs': individual_evs,
            'parlay_ev_estimate': parlay_ev_estimate,
            'confidence': confidence,
            'risk_level': risk_level,
            'correlation_type': self._identify_correlation_type(props_list),
            'reasoning': self._explain_correlation(props_list)
        }
    
    def _estimate_parlay_value(self, individual_evs, correlation_score):
        """
        Estimate the value of the parlay
        """
        # Simple estimation: sum of individual EVs adjusted by correlation
        base_value = sum(individual_evs)
        
        # Positive correlation bonus
        correlation_multiplier = 1 + (correlation_score * 0.3)  # Up to 30% bonus
        
        # Parlay difficulty penalty (more legs = harder)
        difficulty_penalty = 0.9 ** len(individual_evs)
        
        return base_value * correlation_multiplier * difficulty_penalty
    
    def _assess_risk_level(self, props_list, correlation_score):
        """
        Assess risk level of the parlay
        """
        num_props = len(props_list)
        avg_ev = np.mean([prop['Splash_EV_Percentage'] for prop in props_list])
        
        if num_props == 2 and avg_ev > 0.05 and correlation_score > 0.6:
            return 'Low'
        elif num_props <= 3 and avg_ev > 0.03 and correlation_score > 0.4:
            return 'Medium'
        else:
            return 'High'
    
    def _calculate_confidence(self, props_list):
        """
        Calculate confidence in the parlay
        """
        avg_books = np.mean([prop['Num_Books_Used'] for prop in props_list])
        avg_ev = np.mean([prop['Splash_EV_Percentage'] for prop in props_list])
        
        # More books and higher EV = higher confidence
        book_score = min(1.0, avg_books / 8)  # Normalize to 0-1
        ev_score = min(1.0, avg_ev / 0.10)    # Normalize to 0-1
        
        return (book_score + ev_score) / 2
    
    def _identify_correlation_type(self, props_list):
        """
        Identify the type of correlation
        """
        if len(set(prop['Player'] for prop in props_list)) == 1:
            return 'Same Player'
        else:
            return 'Multi-Player'
    
    def _explain_correlation(self, props_list):
        """
        Provide reasoning for why props are correlated
        """
        if len(set(prop['Player'] for prop in props_list)) == 1:
            player = props_list[0]['Player']
            markets = [prop['Market'] for prop in props_list]
            return f"Same player ({player}) correlations between {', '.join(markets)}"
        else:
            return "Multi-player correlation analysis"
    
    def generate_parlay_report(self, parlay_opportunities, top_n=10):
        """Generate a formatted report of top parlay opportunities"""
        if not parlay_opportunities:
            return "No parlay opportunities found."
        
        report = []
        report.append("🎯 TOP PARLAY OPPORTUNITIES")
        report.append("=" * 50)
        
        for i, parlay in enumerate(parlay_opportunities[:top_n], 1):
            report.append(f"\n#{i} PARLAY (Risk: {parlay['risk_level']}, Confidence: {parlay['confidence']:.2f})")
            report.append(f"Type: {parlay['correlation_type']}")
            report.append(f"Correlation Score: {parlay['correlation_score']:.3f}")
            report.append(f"Estimated Parlay EV: {parlay['parlay_ev_estimate']:.3f}")
            report.append(f"Reasoning: {parlay['reasoning']}")
            
            report.append("Props:")
            for j, prop in enumerate(parlay['props'], 1):
                report.append(f"  {j}. {prop['Player']} - {prop['Market']} {prop['Line']} ({prop['Bet_Type']})")
                report.append(f"     Individual EV: {prop['Splash_EV_Percentage']:.3f} | Prob: {prop.get('True_Prob', 0):.3f}")
            
            report.append("-" * 30)
        
        return "\n".join(report)

def main():
    """Example usage of the correlation analyzer"""
    try:
        # This would typically be called after running the EV calculator
        from ev_calculator import EVCalculator
        
        # Run EV analysis first
        calculator = EVCalculator()
        ev_results = calculator.run_full_analysis()
        
        if not ev_results.empty:
            # Analyze correlations and find parlay opportunities
            analyzer = CorrelationAnalyzer()
            parlays = analyzer.identify_correlated_props(ev_results)
            
            # Generate and print report
            report = analyzer.generate_parlay_report(parlays)
            print(report)
        else:
            print("No EV results available for correlation analysis")
            
    except Exception as e:
        print(f"Error in correlation analysis: {e}")

if __name__ == "__main__":
    main()
