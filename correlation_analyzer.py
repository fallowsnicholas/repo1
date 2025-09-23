# correlation_analyzer.py - Data-Driven Version
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from itertools import combinations
import json
import os

logger = logging.getLogger(__name__)

class CorrelationAnalyzer:
    """
    Baseball correlation analyzer using REAL historical data correlations
    """
    
    def __init__(self, correlation_file="baseball_correlations.json"):
        # Load real correlations from extracted data
        self.real_correlations = self._load_real_correlations(correlation_file)
        
        # Enhanced correlations using real data + baseball knowledge
        self.correlations = {
            # REAL DATA CORRELATIONS (from 40,460 games)
            'real_data': {
                ('batter_hits', 'batter_total_bases'): 0.436,  # Real data: Moderate correlation
                ('batter_hits', 'batter_runs_scored'): 0.533,  # Real data: Moderate-Strong correlation
                ('batter_runs_scored', 'batter_total_bases'): 0.256,  # Real data: Weak correlation
            },
            
            # PITCHER CORRELATIONS (baseball knowledge - need pitcher data to verify)
            'pitcher_knowledge': {
                ('pitcher_strikeouts', 'pitcher_earned_runs'): -0.65,  # Dominant pitchers allow fewer runs
                ('pitcher_strikeouts', 'pitcher_hits_allowed'): -0.55,  # More Ks = fewer hits allowed
                ('pitcher_strikeouts', 'pitcher_outs'): 0.60,  # More Ks = pitching deeper
                ('pitcher_hits_allowed', 'pitcher_earned_runs'): 0.50,  # More hits = more runs
            },
            
            # OPPOSING CORRELATIONS (pitcher vs opposing batters)
            'opposing_performance': {
                ('pitcher_strikeouts', 'batter_hits'): -0.45,  # Good pitcher vs opposing batter
                ('pitcher_strikeouts', 'batter_runs_scored'): -0.50,  # Dominant pitching prevents runs
                ('pitcher_strikeouts', 'batter_total_bases'): -0.40,  # Ks prevent extra bases
                ('pitcher_earned_runs', 'batter_runs_scored'): -0.35,  # Pitcher struggles = batter success
            }
        }
        
        # Adjusted thresholds based on real data
        self.min_individual_ev = 0.015  # 1.5% minimum EV
        self.min_strong_correlation = 0.45  # Lowered from 0.60 based on real data
        self.min_moderate_correlation = 0.30  # Lowered from 0.45 based on real data
        
        print(f"📊 Loaded correlation analyzer with real baseball data")
        if self.real_correlations:
            print(f"   ✅ {len(self.real_correlations)} real correlations loaded")
        else:
            print(f"   ⚠️  Using theoretical correlations (no real data file found)")
    
    def _load_real_correlations(self, correlation_file):
        """Load real correlations from extracted data file"""
        try:
            if os.path.exists(correlation_file):
                with open(correlation_file, 'r') as f:
                    data = json.load(f)
                print(f"✅ Loaded real correlations from {correlation_file}")
                return data
            else:
                print(f"⚠️ Correlation file {correlation_file} not found, using theoretical values")
                return {}
        except Exception as e:
            print(f"❌ Error loading correlations: {e}")
            return {}
    
    def identify_correlated_props(self, ev_df, min_correlation=0.30, max_parlay_size=3):
        """
        Find parlay opportunities using real baseball correlations
        """
        if ev_df.empty:
            logger.warning("No EV data provided for correlation analysis")
            return []
        
        print(f"\n📊 Analyzing {len(ev_df)} EV opportunities using REAL baseball correlations...")
        print(f"🎯 Minimum correlation threshold: {min_correlation:.3f}")
        
        # Filter for meaningful EV opportunities
        quality_ev = ev_df[ev_df['Splash_EV_Percentage'] >= self.min_individual_ev].copy()
        
        if len(quality_ev) < 2:
            print(f"❌ Not enough quality EV opportunities (need ≥{self.min_individual_ev:.1%})")
            return []
        
        print(f"📈 Found {len(quality_ev)} quality EV opportunities (≥{self.min_individual_ev:.1%})")
        
        # Show what we're working with
        market_breakdown = quality_ev['Market'].value_counts()
        print("📋 Available markets:")
        for market, count in market_breakdown.items():
            print(f"   • {market}: {count} props")
        
        # Smart prop selection for correlations
        analysis_props = self._select_correlated_props_smart(quality_ev)
        
        if len(analysis_props) < 2:
            print("❌ No correlated prop relationships available")
            return []
        
        print(f"🎯 Selected {len(analysis_props)} props with correlation potential")
        
        # Find parlay combinations using real data
        parlay_opportunities = []
        combinations_checked = 0
        max_combinations = 400
        
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
                
                if not self._is_valid_parlay(combo_props):
                    combinations_checked += 1
                    continue
                
                # Calculate correlation using real data
                correlation_info = self._calculate_real_correlation(combo_props)
                correlation_score = correlation_info['score']
                
                if correlation_score >= min_correlation:
                    parlay_info = self._create_data_driven_parlay(combo_props, correlation_info)
                    if parlay_info:
                        parlay_opportunities.append(parlay_info)
                        size_count += 1
                        
                        # Show first few promising combinations
                        if size_count <= 3:
                            source = correlation_info['source']
                            print(f"   ✅ {correlation_score:.3f} correlation ({source}): {self._describe_combo(combo_props)}")
                
                combinations_checked += 1
                
                if size_count >= 25:  # Increased limit
                    break
            
            print(f"   📈 Found {size_count} viable {size}-prop parlays")
        
        # Sort by data-driven strength
        parlay_opportunities.sort(key=lambda x: x['data_strength_score'], reverse=True)
        
        print(f"\n🎯 Final Result: {len(parlay_opportunities)} data-driven parlay opportunities")
        return parlay_opportunities[:20]
    
    def _select_correlated_props_smart(self, quality_ev):
        """
        Smart selection prioritizing props that have real correlation data
        """
        selected_props = []
        
        # Group by player for same-player correlations (we have real data for these)
        by_player = quality_ev.groupby('Player')
        same_player_added = 0
        
        for player, player_props in by_player:
            if len(player_props) >= 2:
                # Check if this player has markets we have real correlations for
                player_markets = player_props['Market'].tolist()
                has_real_correlation = any(
                    self._has_real_correlation_data(market1, market2)
                    for market1 in player_markets
                    for market2 in player_markets
                    if market1 != market2
                )
                
                if has_real_correlation:
                    selected_props.extend(player_props.to_dict('records'))
                    same_player_added += 1
                    print(f"   📊 {player}: {len(player_props)} props (real correlation data available)")
        
        # Add high-EV props for cross-player relationships  
        remaining_props = quality_ev[~quality_ev['Player'].isin([p['Player'] for p in selected_props])]
        if not remaining_props.empty and len(selected_props) < 30:
            top_remaining = remaining_props.nlargest(15, 'Splash_EV_Percentage')
            selected_props.extend(top_remaining.to_dict('records'))
            print(f"   ⭐ Added {len(top_remaining)} high-EV props for cross-correlations")
        
        print(f"   📈 Total: {same_player_added} players with real correlation data")
        return selected_props
    
    def _has_real_correlation_data(self, market1, market2):
        """Check if we have real correlation data for this market pair"""
        # Check real data first
        for category_name, correlations in self.correlations.items():
            market_pair = tuple(sorted([market1, market2]))
            if market_pair in correlations:
                return True
        
        # Check loaded real correlations file
        if self.real_correlations:
            pair_key = f"{sorted([market1, market2])[0]}_vs_{sorted([market1, market2])[1]}"
            return pair_key in self.real_correlations
        
        return False
    
    def _calculate_real_correlation(self, combo_props):
        """
        Calculate correlation using real data with source tracking
        """
        if len(combo_props) < 2:
            return {'score': 0, 'source': 'none', 'confidence': 0}
        
        total_correlation = 0
        pair_count = 0
        sources_used = []
        
        for i, prop1 in enumerate(combo_props):
            for prop2 in combo_props[i+1:]:
                corr_info = self._get_real_correlation_pair(prop1, prop2)
                total_correlation += abs(corr_info['correlation'])  # Use absolute value
                sources_used.append(corr_info['source'])
                pair_count += 1
        
        avg_correlation = total_correlation / pair_count if pair_count > 0 else 0
        
        # Determine primary source
        if 'real_data' in sources_used:
            primary_source = 'real_data'
            confidence = 0.95
        elif 'pitcher_knowledge' in sources_used:
            primary_source = 'baseball_knowledge'
            confidence = 0.75
        else:
            primary_source = 'theoretical'
            confidence = 0.50
        
        return {
            'score': avg_correlation,
            'source': primary_source,
            'confidence': confidence,
            'sources_used': list(set(sources_used))
        }
    
    def _get_real_correlation_pair(self, prop1, prop2):
        """Get correlation for a specific pair using best available data"""
        market1, market2 = prop1['Market'], prop2['Market']
        player1, player2 = prop1['Player'], prop2['Player']
        
        market_pair = tuple(sorted([market1, market2]))
        
        # Priority 1: Real data correlations
        if market_pair in self.correlations['real_data']:
            base_corr = self.correlations['real_data'][market_pair]
            
            # Same player gets full correlation
            if player1 == player2:
                return {'correlation': base_corr, 'source': 'real_data'}
            else:
                # Different players get reduced correlation
                return {'correlation': base_corr * 0.7, 'source': 'real_data_cross_player'}
        
        # Priority 2: Baseball knowledge correlations
        for category, correlations in self.correlations.items():
            if category != 'real_data' and market_pair in correlations:
                base_corr = correlations[market_pair]
                
                if player1 == player2:
                    return {'correlation': base_corr, 'source': category}
                elif 'opposing' in category:
                    return {'correlation': base_corr * 0.8, 'source': category}
                else:
                    return {'correlation': base_corr * 0.6, 'source': category}
        
        # Default: weak correlation
        if player1 == player2:
            return {'correlation': 0.25, 'source': 'same_player_default'}
        else:
            return {'correlation': 0.05, 'source': 'different_player_default'}
    
    def _create_data_driven_parlay(self, combo_props, correlation_info):
        """Create parlay opportunity with real data backing"""
        individual_evs = [prop['Splash_EV_Percentage'] for prop in combo_props]
        avg_ev = np.mean(individual_evs)
        correlation_score = correlation_info['score']
        
        # Data-driven strength score
        data_strength_score = correlation_score * (1 + avg_ev * 8) * correlation_info['confidence']
        
        # Enhanced quality assessment
        if correlation_info['source'] == 'real_data' and correlation_score >= 0.45 and avg_ev >= 0.035:
            quality = "Data-Backed Excellent"
            risk_level = "Low"
        elif correlation_info['source'] == 'real_data' and correlation_score >= 0.35 and avg_ev >= 0.025:
            quality = "Data-Backed Good" 
            risk_level = "Medium"
        elif correlation_score >= 0.40 and avg_ev >= 0.03:
            quality = "Knowledge-Based Good"
            risk_level = "Medium"
        else:
            quality = "Speculative"
            risk_level = "High"
        
        # Enhanced confidence calculation
        books_used = [prop['Num_Books_Used'] for prop in combo_props]
        avg_books = np.mean(books_used)
        ev_consistency = 1 - (np.std(individual_evs) / np.mean(individual_evs)) if np.mean(individual_evs) > 0 else 0
        
        # Boost confidence for real data
        data_confidence_boost = 0.2 if correlation_info['source'] == 'real_data' else 0
        confidence = min(1.0, (avg_books / 10) * 0.6 + ev_consistency * 0.2 + correlation_info['confidence'] * 0.2 + data_confidence_boost)
        
        return {
            'game_id': f"parlay_{hash(str(combo_props)) % 10000}",
            'props': combo_props,
            'correlation_score': correlation_score,
            'individual_evs': individual_evs,
            'parlay_ev_estimate': sum(individual_evs) * (1 + correlation_score * 0.25),
            'data_strength_score': data_strength_score,
            'confidence': confidence,
            'risk_level': risk_level,
            'quality_tier': quality,
            'correlation_type': self._identify_correlation_type(combo_props),
            'data_source': correlation_info['source'],
            'data_confidence': correlation_info['confidence'],
            'reasoning': self._explain_data_driven_correlation(combo_props, correlation_info)
        }
    
    def _identify_correlation_type(self, combo_props):
        """Identify correlation type with data source info"""
        players = set(prop['Player'] for prop in combo_props)
        
        if len(players) == 1:
            return 'Same Player (Real Data)' if len(combo_props) == 2 else 'Same Player Multi-Prop'
        else:
            markets = [prop['Market'] for prop in combo_props]
            pitcher_markets = any('pitcher_' in market for market in markets)
            batter_markets = any('batter_' in market for market in markets)
            
            if pitcher_markets and batter_markets:
                return 'Pitcher vs Batter'
            else:
                return 'Multi-Player'
    
    def _explain_data_driven_correlation(self, combo_props, correlation_info):
        """Explain correlation with data backing"""
        if len(combo_props) != 2:
            return f"Multi-prop correlation ({correlation_info['source']})"
        
        prop1, prop2 = combo_props
        market1, market2 = prop1['Market'], prop2['Market']
        
        # Real data explanations
        if correlation_info['source'] == 'real_data':
            explanations = {
                ('batter_hits', 'batter_total_bases'): f"Real data: {correlation_info['score']:.3f} correlation from 40,460+ games",
                ('batter_hits', 'batter_runs_scored'): f"Real data: {correlation_info['score']:.3f} correlation from 40,460+ games", 
                ('batter_runs_scored', 'batter_total_bases'): f"Real data: {correlation_info['score']:.3f} correlation from 40,460+ games"
            }
            
            market_pair = tuple(sorted([market1, market2]))
            return explanations.get(market_pair, f"Real data correlation: {correlation_info['score']:.3f}")
        
        # Baseball knowledge explanations
        return f"Baseball knowledge correlation ({correlation_info['source']}): {correlation_info['score']:.3f}"
    
    def _describe_combo(self, combo_props):
        """Describe combination briefly"""
        if len(combo_props) == 2:
            p1, p2 = combo_props
            return f"{p1['Player']} {p1['Market']} + {p2['Player']} {p2['Market']}"
        return f"{len(combo_props)} props"
    
    def _is_valid_parlay(self, combo_props):
        """Validate parlay - same as before"""
        player_markets = [(prop['Player'], prop['Market']) for prop in combo_props]
        if len(set(player_markets)) != len(player_markets):
            return False
        
        for i, prop1 in enumerate(combo_props):
            for prop2 in combo_props[i+1:]:
                if (prop1['Player'] == prop2['Player'] and 
                    prop1['Market'] == prop2['Market'] and
                    prop1['Line'] == prop2['Line']):
                    return False
        
        return True
    
    def generate_parlay_report(self, parlay_opportunities, top_n=10):
        """Generate report highlighting real data correlations"""
        if not parlay_opportunities:
            return "No parlay opportunities found with current criteria."
        
        report = []
        report.append("📊 DATA-DRIVEN BASEBALL PARLAY OPPORTUNITIES")
        report.append("=" * 65)
        report.append(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Total Opportunities: {len(parlay_opportunities)}")
        
        # Show data source breakdown
        source_counts = {}
        for parlay in parlay_opportunities:
            source = parlay.get('data_source', 'unknown')
            source_counts[source] = source_counts.get(source, 0) + 1
        
        report.append(f"Data Sources: {source_counts}")
        report.append("")
        
        for i, parlay in enumerate(parlay_opportunities[:top_n], 1):
            data_source = parlay.get('data_source', 'unknown')
            data_confidence = parlay.get('data_confidence', 0)
            
            report.append(f"#{i} - {parlay['quality_tier']} ({parlay['risk_level']} Risk)")
            report.append(f"Correlation: {parlay['correlation_score']:.3f} | Source: {data_source} (confidence: {data_confidence:.2f})")
            report.append(f"Est. Parlay EV: {parlay['parlay_ev_estimate']:.3f} | Overall Confidence: {parlay['confidence']:.2f}")
            report.append(f"Logic: {parlay['reasoning']}")
            report.append("")
            
            for j, prop in enumerate(parlay['props'], 1):
                report.append(f"  {j}. {prop['Player']} - {prop['Market']} {prop['Line']} ({prop['Bet_Type']})")
                report.append(f"     EV: {prop['Splash_EV_Percentage']:.3f} | Books: {prop['Num_Books_Used']}")
            
            report.append("-" * 40)
        
        return "\n".join(report)

# Keep existing methods for compatibility
def main():
    """Example usage"""
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
