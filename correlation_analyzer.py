# correlation_analyzer.py
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from itertools import combinations
import json

logger = logging.getLogger(__name__)

class CorrelationAnalyzer:
    """
    Analyzes correlations between player props to identify strong parlay opportunities
    """
    
    def __init__(self):
        # Define correlation categories and their expected relationships
        self.correlation_groups = {
            'pitcher_performance': {
                'markets': ['strikeouts', 'earned_runs', 'hits_allowed', 'total_outs'],
                'relationships': {
                    ('strikeouts', 'earned_runs'): 'negative',  # More Ks usually means fewer earned runs
                    ('strikeouts', 'hits_allowed'): 'negative',  # More Ks usually means fewer hits
                    ('earned_runs', 'hits_allowed'): 'positive',  # More hits often leads to more runs
                    ('strikeouts', 'total_outs'): 'positive',    # More Ks means pitcher goes deeper
                }
            },
            'batter_performance': {
                'markets': ['hits', 'runs', 'RBIs', 'total_bases', 'batter_singles'],
                'relationships': {
                    ('hits', 'total_bases'): 'positive',        # More hits usually means more bases
                    ('hits', 'runs'): 'positive',               # More hits can lead to more runs
                    ('hits', 'RBIs'): 'positive',               # More hits can lead to more RBIs
                    ('total_bases', 'RBIs'): 'positive',        # Extra base hits often drive in runs
                    ('runs', 'hits'): 'positive',               # Getting on base to score
                }
            },
            'pitcher_vs_batter': {
                'description': 'Cross-correlations between pitcher and opposing batters',
                'relationships': {
                    ('pitcher_strikeouts', 'batter_hits'): 'negative',     # Good pitcher vs batter performance
                    ('pitcher_earned_runs', 'batter_runs'): 'positive',    # Pitcher struggles = batter success
                    ('pitcher_hits_allowed', 'batter_hits'): 'positive',   # Pitcher allows hits = batters get hits
                }
            },
            'team_correlations': {
                'description': 'Same team player correlations',
                'relationships': {
                    ('batter1_runs', 'batter2_RBIs'): 'positive',          # Teammate scoring and driving in runs
                    ('batter1_hits', 'batter2_runs'): 'positive',          # Setting up teammates to score
                }
            }
        }
    
    def get_matchup_data(self, ev_df):
        """Extract matchup information from EV results"""
        if ev_df.empty:
            return pd.DataFrame()
        
        # Add game identification logic
        ev_df_copy = ev_df.copy()
        
        # Extract team information if available in player names or add game_id field
        # This would need to be enhanced based on your actual data structure
        ev_df_copy['game_id'] = ev_df_copy.apply(self._extract_game_id, axis=1)
        ev_df_copy['player_position'] = ev_df_copy.apply(self._determine_position, axis=1)
        
        return ev_df_copy
    
    def _extract_game_id(self, row):
        """Extract game identifier from player/market data"""
        # This is a placeholder - you'd implement based on your data structure
        # Could be based on date + teams, or if you have explicit game IDs
        return f"game_{hash(row['Player']) % 1000}"  # Simplified example
    
    def _determine_position(self, row):
        """Determine if player is pitcher or batter based on market"""
        pitcher_markets = ['strikeouts', 'earned_runs', 'hits_allowed', 'total_outs']
        if row['Market'] in pitcher_markets:
            return 'pitcher'
        else:
            return 'batter'
    
    def calculate_historical_correlations(self, historical_data_df):
        """
        Calculate historical correlations between different prop types
        This would use historical game data to establish correlation coefficients
        """
        correlations = {}
        
        if historical_data_df.empty:
            logger.warning("No historical data provided for correlation analysis")
            return correlations
        
        # Group by game to analyze within-game correlations
        for game_id, game_data in historical_data_df.groupby('game_id'):
            if len(game_data) < 2:
                continue
                
            # Calculate correlations between different props in the same game
            for (idx1, row1), (idx2, row2) in combinations(game_data.iterrows(), 2):
                prop_pair = tuple(sorted([
                    f"{row1['player_position']}_{row1['Market']}", 
                    f"{row2['player_position']}_{row2['Market']}"
                ]))
                
                if prop_pair not in correlations:
                    correlations[prop_pair] = {'outcomes': [], 'count': 0}
                
                # You'd implement actual outcome correlation logic here
                # This is simplified for demonstration
                correlations[prop_pair]['count'] += 1
        
        return correlations
    
    def identify_correlated_props(self, ev_df, min_correlation=0.3, max_parlay_size=4):
        """
        Identify sets of props that are positively correlated for parlay construction
        """
        if ev_df.empty:
            logger.warning("No EV data provided for correlation analysis")
            return []
        
        matchup_df = self.get_matchup_data(ev_df)
        parlay_opportunities = []
        
        # Group by game to find within-game correlations
        for game_id, game_props in matchup_df.groupby('game_id'):
            if len(game_props) < 2:
                continue
            
            # Find correlated prop combinations
            prop_combinations = self._find_prop_combinations(game_props, max_parlay_size)
            
            for combo in prop_combinations:
                correlation_score = self._calculate_combo_correlation(combo)
                
                if correlation_score >= min_correlation:
                    parlay_ev = self._calculate_parlay_ev(combo)
                    
                    parlay_opportunities.append({
                        'game_id': game_id,
                        'props': combo,
                        'correlation_score': correlation_score,
                        'individual_evs': [prop['Splash_EV_Percentage'] for prop in combo],
                        'parlay_ev_estimate': parlay_ev,
                        'confidence': self._calculate_confidence(combo),
                        'risk_level': self._assess_risk_level(combo)
                    })
        
        # Sort by parlay EV estimate
        parlay_opportunities.sort(key=lambda x: x['parlay_ev_estimate'], reverse=True)
        
        logger.info(f"Found {len(parlay_opportunities)} potential parlay opportunities")
        return parlay_opportunities
    
    def _find_prop_combinations(self, game_props, max_size):
        """Find all valid combinations of props within a game"""
        combinations_list = []
        props_list = game_props.to_dict('records')
        
        # Generate combinations of different sizes
        for size in range(2, min(max_size + 1, len(props_list) + 1)):
            for combo in combinations(props_list, size):
                if self._is_valid_combination(combo):
                    combinations_list.append(list(combo))
        
        return combinations_list
    
    def _is_valid_combination(self, prop_combo):
        """Check if a combination of props is valid for parlaying"""
        # Avoid same player, same market combinations
        player_markets = [(prop['Player'], prop['Market']) for prop in prop_combo]
        if len(set(player_markets)) != len(player_markets):
            return False
        
        # Add other validation logic (e.g., avoid conflicting props)
        return True
    
    def _calculate_combo_correlation(self, prop_combo):
        """Calculate correlation score for a combination of props"""
        if len(prop_combo) < 2:
            return 0
        
        total_correlation = 0
        pair_count = 0
        
        # Analyze each pair in the combination
        for prop1, prop2 in combinations(prop_combo, 2):
            correlation = self._get_prop_pair_correlation(prop1, prop2)
            total_correlation += correlation
            pair_count += 1
        
        return total_correlation / pair_count if pair_count > 0 else 0
    
    def _get_prop_pair_correlation(self, prop1, prop2):
        """Get correlation between two specific props"""
        # Create prop pair identifier
        market1 = f"{prop1.get('player_position', 'unknown')}_{prop1['Market']}"
        market2 = f"{prop2.get('player_position', 'unknown')}_{prop2['Market']}"
        
        # Check predefined correlations
        for group_name, group_data in self.correlation_groups.items():
            if 'relationships' in group_data:
                relationships = group_data['relationships']
                
                # Check both orderings of the pair
                for (m1, m2), relationship in relationships.items():
                    if (m1 == market1 and m2 == market2) or (m1 == market2 and m2 == market1):
                        if relationship == 'positive':
                            return 0.6  # Strong positive correlation
                        elif relationship == 'negative':
                            return -0.6  # Strong negative correlation (avoid in parlays)
        
        # Check same player correlations
        if prop1['Player'] == prop2['Player']:
            return self._get_same_player_correlation(prop1['Market'], prop2['Market'])
        
        # Check opposing pitcher-batter correlations
        if (prop1.get('player_position') == 'pitcher' and prop2.get('player_position') == 'batter') or \
           (prop1.get('player_position') == 'batter' and prop2.get('player_position') == 'pitcher'):
            return self._get_pitcher_batter_correlation(prop1, prop2)
        
        return 0.1  # Default weak correlation
    
    def _get_same_player_correlation(self, market1, market2):
        """Get correlation for same player, different markets"""
        same_player_correlations = {
            ('hits', 'total_bases'): 0.7,
            ('hits', 'runs'): 0.5,
            ('hits', 'RBIs'): 0.4,
            ('strikeouts', 'earned_runs'): -0.6,
            ('strikeouts', 'hits_allowed'): -0.5,
        }
        
        pair = tuple(sorted([market1, market2]))
        return same_player_correlations.get(pair, 0.2)
    
    def _get_pitcher_batter_correlation(self, pitcher_prop, batter_prop):
        """Get correlation between pitcher and opposing batter performance"""
        # Generally negative correlations (pitcher success vs batter success)
        return -0.4
    
    def _calculate_parlay_ev(self, prop_combo):
        """Estimate parlay EV considering correlations"""
        individual_evs = [prop['Splash_EV_Percentage'] for prop in prop_combo]
        individual_probs = [prop['True_Prob'] for prop in prop_combo]
        
        # Simple multiplicative model adjusted for correlation
        base_parlay_prob = np.prod(individual_probs)
        correlation_adjustment = 1.0  # Would be more sophisticated with real correlation data
        
        adjusted_prob = base_parlay_prob * correlation_adjustment
        parlay_multiplier = len(prop_combo) * 1.5  # Bonus for successful parlays
        
        return sum(individual_evs) * parlay_multiplier * adjusted_prob
    
    def _calculate_confidence(self, prop_combo):
        """Calculate confidence level for the parlay"""
        # Based on number of books, EV consistency, etc.
        avg_books = np.mean([prop['Num_Books_Used'] for prop in prop_combo])
        ev_consistency = 1 - np.std([prop['Splash_EV_Percentage'] for prop in prop_combo])
        
        return min(1.0, (avg_books / 10) * ev_consistency)
    
    def _assess_risk_level(self, prop_combo):
        """Assess risk level of the parlay"""
        avg_prob = np.mean([prop['True_Prob'] for prop in prop_combo])
        combo_size = len(prop_combo)
        
        if avg_prob > 0.7 and combo_size <= 2:
            return 'Low'
        elif avg_prob > 0.6 and combo_size <= 3:
            return 'Medium'
        else:
            return 'High'
    
    def generate_parlay_report(self, parlay_opportunities, top_n=10):
        """Generate a formatted report of top parlay opportunities"""
        if not parlay_opportunities:
            return "No parlay opportunities found."
        
        report = []
        report.append("🎯 TOP PARLAY OPPORTUNITIES")
        report.append("=" * 50)
        
        for i, parlay in enumerate(parlay_opportunities[:top_n], 1):
            report.append(f"\n#{i} PARLAY (Risk: {parlay['risk_level']}, Confidence: {parlay['confidence']:.2f})")
            report.append(f"Correlation Score: {parlay['correlation_score']:.3f}")
            report.append(f"Estimated Parlay EV: {parlay['parlay_ev_estimate']:.3f}")
            
            report.append("Props:")
            for j, prop in enumerate(parlay['props'], 1):
                report.append(f"  {j}. {prop['Player']} - {prop['Market']} {prop['Line']} ({prop['Bet_Type']})")
                report.append(f"     Individual EV: {prop['Splash_EV_Percentage']:.3f} | Prob: {prop['True_Prob']:.3f}")
            
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
