# simplified_correlation_analyzer.py
import pandas as pd
import numpy as np
from datetime import datetime
import logging
from itertools import combinations

logger = logging.getLogger(__name__)

class SimplifiedCorrelationAnalyzer:
    """
    Simple, testable correlation analyzer focused on basic MLB prop relationships
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
            },
            # Same player pitcher correlations
            'same_player_pitching': {
                ('strikeouts', 'total_outs'): 0.7,  # More Ks = pitches deeper
            }
        }
        
        self.negative_correlations = {
            # Same player pitcher correlations (negative)
            'pitcher_performance': {
                ('strikeouts', 'earned_runs'): -0.6,
                ('strikeouts', 'hits_allowed'): -0.5,
                ('total_outs', 'earned_runs'): -0.4,
            }
        }
        
        # Minimum EV threshold for parlay consideration
        self.min_individual_ev = 0.02  # 2%
        self.min_parlay_correlation = 0.4
    
    def identify_simple_parlays(self, ev_df, max_parlay_size=3):
        """
        Find simple, logical parlay opportunities based on basic correlations
        """
        if ev_df.empty:
            logger.warning("No EV data provided")
            return []
        
        print(f"\nAnalyzing {len(ev_df)} EV opportunities for parlay combinations...")
        
        # Filter to only positive EV opportunities
        positive_ev = ev_df[ev_df['Splash_EV_Percentage'] >= self.min_individual_ev].copy()
        
        if len(positive_ev) < 2:
            print("Not enough positive EV opportunities for parlays")
            return []
        
        print(f"Found {len(positive_ev)} positive EV opportunities to analyze")
        
        parlay_opportunities = []
        
        # Generate all combinations of 2-3 props
        for size in range(2, min(max_parlay_size + 1, len(positive_ev) + 1)):
            for combo_indices in combinations(range(len(positive_ev)), size):
                combo_props = positive_ev.iloc[list(combo_indices)]
                
                # Check if this is a valid parlay combination
                parlay_info = self._analyze_combination(combo_props)
                
                if parlay_info and parlay_info['correlation_score'] >= self.min_parlay_correlation:
                    parlay_opportunities.append(parlay_info)
        
        # Sort by estimated parlay value
        parlay_opportunities.sort(key=lambda x: x['estimated_value'], reverse=True)
        
        print(f"Found {len(parlay_opportunities)} potential parlay opportunities")
        return parlay_opportunities[:20]  # Return top 20
    
    def _analyze_combination(self, combo_props):
        """
        Analyze a combination of props for parlay viability
        """
        props_list = combo_props.to_dict('records')
        
        # Basic validation
        if not self._is_valid_parlay(props_list):
            return None
        
        # Calculate correlation score
        correlation_score = self._calculate_correlation_score(props_list)
        
        if correlation_score < self.min_parlay_correlation:
            return None
        
        # Estimate parlay value
        individual_evs = [prop['Splash_EV_Percentage'] for prop in props_list]
        estimated_value = self._estimate_parlay_value(individual_evs, correlation_score)
        
        # Determine risk level
        risk_level = self._assess_risk(props_list, correlation_score)
        
        return {
            'props': props_list,
            'num_props': len(props_list),
            'correlation_score': correlation_score,
            'correlation_type': self._identify_correlation_type(props_list),
            'individual_evs': individual_evs,
            'estimated_value': estimated_value,
            'avg_individual_ev': np.mean(individual_evs),
            'risk_level': risk_level,
            'confidence': self._calculate_confidence(props_list),
            'reasoning': self._explain_correlation(props_list)
        }
    
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
            return self._get_same_player_correlation(prop1['Market'], prop2['Market'])
        
        # Different players - assume weak positive correlation for now
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
        return 0.2
    
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
    
    def _assess_risk(self, props_list, correlation_score):
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
        """
        Generate a readable report of parlay opportunities
        """
        if not parlay_opportunities:
            return "No parlay opportunities found with current criteria."
        
        report = []
        report.append("🎯 SIMPLIFIED PARLAY OPPORTUNITIES")
        report.append("=" * 60)
        report.append(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Total Opportunities Found: {len(parlay_opportunities)}")
        report.append("")
        
        for i, parlay in enumerate(parlay_opportunities[:top_n], 1):
            report.append(f"#{i} - {parlay['correlation_type']} Parlay ({parlay['risk_level']} Risk)")
            report.append(f"Correlation Score: {parlay['correlation_score']:.3f}")
            report.append(f"Estimated Value: {parlay['estimated_value']:.4f}")
            report.append(f"Confidence: {parlay['confidence']:.2f}")
            report.append(f"Reasoning: {parlay['reasoning']}")
            report.append("")
            
            for j, prop in enumerate(parlay['props'], 1):
                report.append(f"  {j}. {prop['Player']}")
                report.append(f"     {prop['Market']} - {prop['Bet_Type']} {prop['Line']}")
                report.append(f"     EV: {prop['Splash_EV_Percentage']:.3f} | Books: {prop['Num_Books_Used']}")
            
            report.append("-" * 40)
        
        return "\n".join(report)

def test_correlation_analyzer():
    """
    Test function to verify the analyzer works
    """
    print("Testing Simplified Correlation Analyzer...")
    
    # Create sample EV data for testing
    sample_data = [
        {'Player': 'Mike Trout', 'Market': 'hits', 'Line': '1.5', 'Bet_Type': 'over', 
         'Splash_EV_Percentage': 0.045, 'Num_Books_Used': 6},
        {'Player': 'Mike Trout', 'Market': 'total_bases', 'Line': '2.5', 'Bet_Type': 'over', 
         'Splash_EV_Percentage': 0.038, 'Num_Books_Used': 7},
        {'Player': 'Shohei Ohtani', 'Market': 'strikeouts', 'Line': '6.5', 'Bet_Type': 'over', 
         'Splash_EV_Percentage': 0.052, 'Num_Books_Used': 8},
        {'Player': 'Shohei Ohtani', 'Market': 'earned_runs', 'Line': '2.5', 'Bet_Type': 'under', 
         'Splash_EV_Percentage': 0.041, 'Num_Books_Used': 5},
    ]
    
    test_df = pd.DataFrame(sample_data)
    
    analyzer = SimplifiedCorrelationAnalyzer()
    parlays = analyzer.identify_simple_parlays(test_df)
    
    report = analyzer.generate_parlay_report(parlays)
    print(report)
    
    return parlays

if __name__ == "__main__":
    test_correlation_analyzer()
