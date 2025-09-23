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
    Baseball correlation analyzer using well-established statistical relationships
    Based on actual Splash Sports markets: batter_total_bases, batter_hits, pitcher_hits_allowed,
    pitcher_strikeouts, batter_runs_scored, pitcher_earned_runs, pitcher_outs
    """
    
    def __init__(self):
        # Well-documented baseball correlations based on actual Splash markets
        self.correlations = {
            # STRONG POSITIVE CORRELATIONS (0.7-0.9)
            'strong_positive': {
                # Same batter: hits lead to bases, runs, opportunities
                ('batter_hits', 'batter_total_bases'): 0.85,  # More hits = more total bases
                ('batter_hits', 'batter_runs_scored'): 0.75,  # Getting on base to score
                ('batter_total_bases', 'batter_runs_scored'): 0.80,  # Extra bases = better scoring position
                
                # Same pitcher: efficiency metrics
                ('pitcher_strikeouts', 'pitcher_outs'): 0.80,  # More Ks = pitching deeper
            },
            
            # MODERATE POSITIVE CORRELATIONS (0.5-0.7)
            'moderate_positive': {
                # Cross-team same game (high-scoring games benefit both)
                ('batter_runs_scored', 'batter_total_bases'): 0.60,  # Different teams in high-scoring game
                ('batter_hits', 'pitcher_hits_allowed'): 0.55,  # Overall offensive game
            },
            
            # STRONG NEGATIVE CORRELATIONS (pitcher vs opposing offense)
            'strong_negative': {
                # Pitcher dominance vs opposing offense
                ('pitcher_strikeouts', 'batter_hits'): -0.70,  # Dominant pitcher vs opposing batter
                ('pitcher_strikeouts', 'batter_total_bases'): -0.65,  # Ks prevent extra bases
                ('pitcher_strikeouts', 'batter_runs_scored'): -0.75,  # Dominant pitching prevents runs
                
                # Pitcher control vs run prevention
                ('pitcher_strikeouts', 'pitcher_earned_runs'): -0.80,  # More Ks = fewer runs allowed
                ('pitcher_strikeouts', 'pitcher_hits_allowed'): -0.70,  # Strike out batters = fewer hits
                ('pitcher_outs', 'pitcher_earned_runs'): -0.65,  # Pitching deeper with control
            },
            
            # MODERATE NEGATIVE CORRELATIONS
            'moderate_negative': {
                # Opposing performance relationships
                ('pitcher_hits_allowed', 'batter_runs_scored'): -0.50,  # Opposing team relationship
                ('pitcher_earned_runs', 'batter_total_bases'): -0.55,  # Pitcher struggles = batter success
            }
        }
        
        # Minimum thresholds - more realistic
        self.min_individual_ev = 0.015  # 1.5% minimum EV
        self.min_strong_correlation = 0.60  # Strong relationships only
        self.min_moderate_correlation = 0.45  # Moderate relationships
    
    def identify_correlated_props(self, ev_df, min_correlation=0.45, max_parlay_size=3):
        """
        Find parlay opportunities using established baseball correlations
        """
        if ev_df.empty:
            logger.warning("No EV data provided for correlation analysis")
            return []
        
        print(f"\n🏈 Analyzing {len(ev_df)} EV opportunities using baseball correlations...")
        
        # Filter for meaningful EV opportunities
        quality_ev = ev_df[ev_df['Splash_EV_Percentage'] >= self.min_individual_ev].copy()
        
        if len(quality_ev) < 2:
            print(f"❌ Not enough quality EV opportunities (need ≥{self.min_individual_ev:.1%})")
            return []
        
        print(f"📊 Found {len(quality_ev)} quality EV opportunities (≥{self.min_individual_ev:.1%})")
        
        # Show breakdown
        market_breakdown = quality_ev['Market'].value_counts()
        print("Available markets for correlation analysis:")
        for market, count in market_breakdown.items():
            print(f"  • {market}: {count} props")
        
        # Smart prop selection: prioritize same-player and opposing relationships
        analysis_props = self._select_correlated_props(quality_ev)
        
        if len(analysis_props) < 2:
            print("❌ No correlated prop relationships found")
            return []
        
        print(f"🎯 Selected {len(analysis_props)} props with potential correlations")
        
        # Find parlay combinations
        parlay_opportunities = []
        combinations_checked = 0
        max_combinations = 300
        
        # Convert to DataFrame for easier processing
        analysis_df = pd.DataFrame(analysis_props)
        
        # Check 2-prop and 3-prop combinations
        for size in [2, 3]:
            if len(analysis_df) < size:
                continue
                
            print(f"\n🔍 Checking {size}-prop combinations...")
            size_count = 0
            
            for combo_indices in combinations(range(len(analysis_df)), size):
                if combinations_checked >= max_combinations:
                    print(f"⚠️ Reached combination limit ({max_combinations})")
                    break
                
                combo_props = analysis_df.iloc[list(combo_indices)].to_dict('records')
                
                # Validate and score combination
                if not self._is_valid_parlay(combo_props):
                    combinations_checked += 1
                    continue
                
                correlation_score = self._calculate_baseball_correlation(combo_props)
                
                if correlation_score >= min_correlation:
                    parlay_info = self._create_parlay_opportunity(combo_props, correlation_score)
                    if parlay_info:
                        parlay_opportunities.append(parlay_info)
                        size_count += 1
                        
                        # Show promising combinations
                        if size_count <= 3:
                            print(f"  ✅ Found {correlation_score:.2f} correlation: {self._describe_combo(combo_props)}")
                
                combinations_checked += 1
                
                if size_count >= 20:  # Limit per size
                    break
            
            print(f"  📈 Found {size_count} viable {size}-prop parlays")
        
        # Sort by strength
        parlay_opportunities.sort(key=lambda x: x['strength_score'], reverse=True)
        
        print(f"\n🎯 Final Result: {len(parlay_opportunities)} parlay opportunities found")
        return parlay_opportunities[:15]  # Return top 15
    
    def _select_correlated_props(self, quality_ev):
        """
        Select props that have potential correlations based on baseball knowledge
        """
        selected_props = []
        
        # Group by player to find same-player opportunities
        by_player = quality_ev.groupby('Player')
        
        for player, player_props in by_player:
            if len(player_props) >= 2:
                # Add all props for players with multiple markets
                selected_props.extend(player_props.to_dict('records'))
                print(f"  👤 {player}: {len(player_props)} props (same-player correlations)")
        
        # Add high-EV single props for cross-player correlations
        remaining_props = quality_ev[~quality_ev['Player'].isin(by_player.groups.keys())]
        if not remaining_props.empty:
            # Take top single props by EV
            top_singles = remaining_props.nlargest(10, 'Splash_EV_Percentage')
            selected_props.extend(top_singles.to_dict('records'))
            print(f"  ⭐ Added {len(top_singles)} high-EV props for cross-correlations")
        
        return selected_props
    
    def _calculate_baseball_correlation(self, combo_props):
        """
        Calculate correlation based on established baseball relationships
        """
        if len(combo_props) < 2:
            return 0
        
        total_correlation = 0
        pair_count = 0
        
        for i, prop1 in enumerate(combo_props):
            for prop2 in combo_props[i+1:]:
                correlation = self._get_baseball_correlation(prop1, prop2)
                total_correlation += abs(correlation)  # Use absolute value for parlay strength
                pair_count += 1
        
        return total_correlation / pair_count if pair_count > 0 else 0
    
    def _get_baseball_correlation(self, prop1, prop2):
        """
        Get correlation between two props using baseball knowledge
        """
        market1, market2 = prop1['Market'], prop2['Market']
        player1, player2 = prop1['Player'], prop2['Player']
        
        # Create market pair (order doesn't matter)
        market_pair = tuple(sorted([market1, market2]))
        
        # Check all correlation categories
        for category, correlations in self.correlations.items():
            if market_pair in correlations:
                base_correlation = correlations[market_pair]
                
                # Same player gets full correlation strength
                if player1 == player2:
                    return base_correlation
                
                # Different players get reduced correlation for opposing relationships
                if 'negative' in category:
                    # This could be pitcher vs opposing batter
                    return base_correlation * 0.8  # Slightly reduced for uncertainty
                else:
                    # Different players, positive correlation (same game effects)
                    return base_correlation * 0.6
        
        # Default correlation for same player (general positive relationship)
        if player1 == player2:
            return 0.40
        
        # Very weak correlation for unrelated different players
        return 0.05
    
    def _is_valid_parlay(self, combo_props):
        """
        Validate parlay combination using baseball logic
        """
        # No duplicate player-market combinations
        player_markets = [(prop['Player'], prop['Market']) for prop in combo_props]
        if len(set(player_markets)) != len(player_markets):
            return False
        
        # No contradictory same-player bets (over/under same line)
        for i, prop1 in enumerate(combo_props):
            for prop2 in combo_props[i+1:]:
                if (prop1['Player'] == prop2['Player'] and 
                    prop1['Market'] == prop2['Market'] and
                    prop1['Line'] == prop2['Line']):
                    return False
        
        return True
    
    def _create_parlay_opportunity(self, combo_props, correlation_score):
        """
        Create structured parlay opportunity
        """
        individual_evs = [prop['Splash_EV_Percentage'] for prop in combo_props]
        avg_ev = np.mean(individual_evs)
        
        # Calculate strength score (combination of correlation and EV)
        strength_score = correlation_score * (1 + avg_ev * 5)  # Boost for higher EV
        
        # Determine quality tier
        if correlation_score >= 0.70 and avg_ev >= 0.04:
            quality = "Excellent"
            risk_level = "Low"
        elif correlation_score >= 0.60 and avg_ev >= 0.03:
            quality = "Good"
            risk_level = "Medium"
        elif correlation_score >= 0.50 and avg_ev >= 0.02:
            quality = "Fair"
            risk_level = "Medium"
        else:
            quality = "Speculative" 
            risk_level = "High"
        
        # Calculate confidence based on book coverage and EV consistency
        books_used = [prop['Num_Books_Used'] for prop in combo_props]
        avg_books = np.mean(books_used)
        ev_consistency = 1 - (np.std(individual_evs) / np.mean(individual_evs)) if np.mean(individual_evs) > 0 else 0
        confidence = min(1.0, (avg_books / 8) * 0.7 + ev_consistency * 0.3)
        
        return {
            'game_id': f"parlay_{hash(str(combo_props)) % 10000}",
            'props': combo_props,
            'correlation_score': correlation_score,
            'individual_evs': individual_evs,
            'parlay_ev_estimate': sum(individual_evs) * (1 + correlation_score * 0.2),  # Correlation bonus
            'strength_score': strength_score,
            'confidence': confidence,
            'risk_level': risk_level,
            'quality_tier': quality,
            'correlation_type': self._identify_correlation_type(combo_props),
            'reasoning': self._explain_baseball_correlation(combo_props)
        }
    
    def _identify_correlation_type(self, combo_props):
        """
        Identify the type of correlation for this combination
        """
        players = set(prop['Player'] for prop in combo_props)
        
        if len(players) == 1:
            return 'Same Player'
        else:
            # Check if it's pitcher vs batter
            markets = [prop['Market'] for prop in combo_props]
            pitcher_markets = any('pitcher_' in market for market in markets)
            batter_markets = any('batter_' in market for market in markets)
            
            if pitcher_markets and batter_markets:
                return 'Pitcher vs Batter'
            else:
                return 'Multi-Player'
    
    def _explain_baseball_correlation(self, combo_props):
        """
        Explain why these props are correlated using baseball logic
        """
        if len(combo_props) != 2:
            return "Multi-prop correlation analysis"
        
        prop1, prop2 = combo_props
        market1, market2 = prop1['Market'], prop2['Market']
        
        # Same player explanations
        if prop1['Player'] == prop2['Player']:
            explanations = {
                ('batter_hits', 'batter_total_bases'): "More hits typically lead to more total bases",
                ('batter_hits', 'batter_runs_scored'): "Getting on base creates scoring opportunities", 
                ('batter_total_bases', 'batter_runs_scored'): "Extra base hits improve scoring position",
                ('pitcher_strikeouts', 'pitcher_outs'): "More strikeouts indicate pitcher going deeper",
                ('pitcher_strikeouts', 'pitcher_earned_runs'): "Dominant strikeout pitchers allow fewer runs",
                ('pitcher_strikeouts', 'pitcher_hits_allowed'): "High strikeout rate limits hits allowed"
            }
            
            market_pair = tuple(sorted([market1, market2]))
            return explanations.get(market_pair, f"Same player correlation: {market1} ↔ {market2}")
        
        # Cross-player explanations
        cross_explanations = {
            ('pitcher_strikeouts', 'batter_hits'): "Dominant pitcher vs opposing batter performance",
            ('pitcher_strikeouts', 'batter_runs_scored'): "Strong pitching limits opposing team scoring",
            ('pitcher_earned_runs', 'batter_total_bases'): "Pitcher struggles often benefit opposing offense"
        }
        
        market_pair = tuple(sorted([market1, market2]))
        return cross_explanations.get(market_pair, "Cross-player game flow correlation")
    
    def _describe_combo(self, combo_props):
        """
        Short description of prop combination
        """
        if len(combo_props) == 2:
            p1, p2 = combo_props
            return f"{p1['Player']} {p1['Market']} + {p2['Player']} {p2['Market']}"
        else:
            players = len(set(prop['Player'] for prop in combo_props))
            return f"{len(combo_props)} props across {players} player(s)"
    
    def generate_parlay_report(self, parlay_opportunities, top_n=10):
        """Generate comprehensive parlay report"""
        if not parlay_opportunities:
            return "No parlay opportunities found with current criteria."
        
        report = []
        report.append("⚾ BASEBALL CORRELATION PARLAY OPPORTUNITIES")
        report.append("=" * 60)
        report.append(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Total Opportunities: {len(parlay_opportunities)}")
        report.append("")
        
        for i, parlay in enumerate(parlay_opportunities[:top_n], 1):
            report.append(f"#{i} - {parlay['quality_tier']} Quality ({parlay['risk_level']} Risk)")
            report.append(f"Correlation: {parlay['correlation_score']:.3f} | Type: {parlay['correlation_type']}")
            report.append(f"Est. Parlay EV: {parlay['parlay_ev_estimate']:.3f} | Confidence: {parlay['confidence']:.2f}")
            report.append(f"Logic: {parlay['reasoning']}")
            report.append("")
            
            for j, prop in enumerate(parlay['props'], 1):
                report.append(f"  {j}. {prop['Player']} - {prop['Market']} {prop['Line']} ({prop['Bet_Type']})")
                report.append(f"     EV: {prop['Splash_EV_Percentage']:.3f} | Books: {prop['Num_Books_Used']}")
            
            report.append("-" * 40)
        
        return "\n".join(report)

# Keep existing main() and other methods for compatibility
def main():
    """Example usage of the correlation analyzer"""
    try:
        from ev_calculator import EVCalculator
        
        calculator = EVCalculator()
        ev_results = calculator.run_full_analysis()
        
        if not ev_results.empty:
            analyzer = CorrelationAnalyzer()
            parlays = analyzer.identify_correlated_props(ev_results)
            
            report = analyzer.generate_parlay_report(parlays)
            print(report)
        else:
            print("No EV results available for correlation analysis")
            
    except Exception as e:
        print(f"Error in correlation analysis: {e}")

if __name__ == "__main__":
    main()
