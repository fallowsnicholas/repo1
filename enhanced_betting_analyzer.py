# enhanced_betting_analyzer.py
import pandas as pd
import numpy as np
from datetime import datetime
import logging
from ev_calculator import EVCalculator
from correlation_analyzer import CorrelationAnalyzer  # Fixed import
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedBettingAnalyzer:
    """
    Combines EV calculation with correlation analysis for comprehensive betting analysis
    """
    
    def __init__(self, google_creds_json=None):
        self.ev_calculator = EVCalculator(google_creds_json)
        self.correlation_analyzer = CorrelationAnalyzer()  # Fixed class name
        
        # Configuration parameters
        self.config = {
            'ev_threshold': 0.01,
            'min_correlation': 0.3,
            'max_parlay_size': 4,
            'min_books': 3,
            'min_true_prob': 0.50
        }
    
    def run_comprehensive_analysis(self, save_results=True):
        """Run both EV and correlation analysis"""
        try:
            logger.info("Starting comprehensive betting analysis...")
            start_time = datetime.now()
            
            # Step 1: Run EV Analysis
            logger.info("Step 1: Running EV analysis...")
            ev_results = self.ev_calculator.run_full_analysis(save_to_sheets=save_results)
            
            if ev_results.empty:
                logger.warning("No EV opportunities found. Skipping correlation analysis.")
                return {
                    'ev_results': ev_results,
                    'parlay_opportunities': [],
                    'summary': self._generate_summary(ev_results, [])
                }
            
            # Step 2: Correlation Analysis
            logger.info("Step 2: Analyzing correlations for parlay opportunities...")
            parlay_opportunities = self.correlation_analyzer.identify_correlated_props(
                ev_results,
                min_correlation=self.config['min_correlation'],
                max_parlay_size=self.config['max_parlay_size']
            )
            
            # Step 3: Save comprehensive results
            if save_results:
                self._save_comprehensive_results(ev_results, parlay_opportunities)
            
            # Step 4: Generate summary
            summary = self._generate_summary(ev_results, parlay_opportunities)
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            logger.info(f"Comprehensive analysis completed in {duration:.2f} seconds")
            
            return {
                'ev_results': ev_results,
                'parlay_opportunities': parlay_opportunities,
                'summary': summary,
                'analysis_time': end_time.isoformat(),
                'duration_seconds': duration
            }
            
        except Exception as e:
            logger.error(f"Error in comprehensive analysis: {e}")
            raise
    
    def _save_comprehensive_results(self, ev_results, parlay_opportunities):
        """Save both individual and parlay results to Google Sheets"""
        try:
            client = self.ev_calculator.connect_to_sheets()
            
            # Save individual EV results
            if not ev_results.empty:
                self.ev_calculator.save_results_to_sheets(ev_results, client, "EV_RESULTS")
            
            # Save parlay opportunities
            if parlay_opportunities:
                parlay_df = self._format_parlay_results(parlay_opportunities)
                self._save_parlay_results(parlay_df, client, "PARLAY_OPPORTUNITIES")
            
        except Exception as e:
            logger.error(f"Error saving comprehensive results: {e}")
    
    def _format_parlay_results(self, parlay_opportunities):
        """Format parlay opportunities into a DataFrame for saving"""
        formatted_data = []
        
        for i, parlay in enumerate(parlay_opportunities, 1):
            # Create a summary row for each parlay
            prop_summary = " | ".join([
                f"{prop['Player']} {prop['Market']} {prop['Line']} ({prop['Bet_Type']})"
                for prop in parlay['props']
            ])
            
            formatted_data.append({
                'Parlay_ID': f"PARLAY_{i:03d}",
                'Game_ID': parlay['game_id'],
                'Num_Props': len(parlay['props']),
                'Props_Summary': prop_summary,
                'Correlation_Score': parlay['correlation_score'],
                'Individual_EVs': json.dumps(parlay['individual_evs']),
                'Parlay_EV_Estimate': parlay['parlay_ev_estimate'],
                'Confidence': parlay['confidence'],
                'Risk_Level': parlay['risk_level'],
                'Correlation_Type': parlay.get('correlation_type', 'Unknown'),
                'Reasoning': parlay.get('reasoning', 'Standard correlation analysis'),
                'Analysis_Time': datetime.now().isoformat()
            })
        
        return pd.DataFrame(formatted_data)
    
    def _save_parlay_results(self, parlay_df, client, worksheet_name="PARLAY_OPPORTUNITIES"):
        """Save parlay results to Google Sheets"""
        try:
            spreadsheet = client.open("MLB_Splash_Data")
            
            # Try to get existing worksheet or create new one
            try:
                worksheet = spreadsheet.worksheet(worksheet_name)
            except:
                worksheet = spreadsheet.add_worksheet(title=worksheet_name, rows=1000, cols=20)
            
            # Clear and update
            worksheet.clear()
            
            metadata = [
                ['Parlay Analysis Results', ''],
                ['Last Updated', datetime.now().isoformat()],
                ['Total Opportunities', len(parlay_df)],
                ['']
            ]
            
            all_data = metadata + [parlay_df.columns.tolist()] + parlay_df.values.tolist()
            worksheet.update(range_name='A1', values=all_data)
            
            logger.info(f"Saved {len(parlay_df)} parlay opportunities to {worksheet_name}")
            
        except Exception as e:
            logger.error(f"Error saving parlay results: {e}")
    
    def _generate_summary(self, ev_results, parlay_opportunities):
        """Generate comprehensive analysis summary"""
        summary = {
            'individual_props': {
                'total_opportunities': len(ev_results),
                'avg_ev': ev_results['Splash_EV_Percentage'].mean() if not ev_results.empty else 0,
                'best_ev': ev_results['Splash_EV_Percentage'].max() if not ev_results.empty else 0,
                'top_markets': ev_results.groupby('Market').size().to_dict() if not ev_results.empty else {}
            },
            'parlay_analysis': {
                'total_parlays': len(parlay_opportunities),
                'avg_correlation': np.mean([p['correlation_score'] for p in parlay_opportunities]) if parlay_opportunities else 0,
                'risk_breakdown': self._get_risk_breakdown(parlay_opportunities),
                'top_parlay_ev': max([p['parlay_ev_estimate'] for p in parlay_opportunities]) if parlay_opportunities else 0
            },
            'recommendations': self._generate_recommendations(ev_results, parlay_opportunities)
        }
        
        return summary
    
    def _get_risk_breakdown(self, parlay_opportunities):
        """Get breakdown of parlays by risk level"""
        risk_counts = {'Low': 0, 'Medium': 0, 'High': 0}
        for parlay in parlay_opportunities:
            risk_level = parlay.get('risk_level', 'Unknown')
            if risk_level in risk_counts:
                risk_counts[risk_level] += 1
        return risk_counts
    
    def _generate_recommendations(self, ev_results, parlay_opportunities):
        """Generate actionable recommendations"""
        recommendations = []
        
        # Individual prop recommendations
        if not ev_results.empty:
            top_individual = ev_results.iloc[0]
            recommendations.append({
                'type': 'individual',
                'priority': 'high',
                'description': f"Best individual prop: {top_individual['Player']} {top_individual['Market']} {top_individual['Line']}",
                'ev': top_individual['Splash_EV_Percentage'],
                'confidence': 'high' if top_individual['Num_Books_Used'] >= 5 else 'medium'
            })
        
        # Parlay recommendations
        if parlay_opportunities:
            # High-confidence, low-risk parlays
            safe_parlays = [p for p in parlay_opportunities if p.get('risk_level') == 'Low' and p.get('confidence', 0) > 0.7]
            if safe_parlays:
                best_safe = max(safe_parlays, key=lambda x: x['parlay_ev_estimate'])
                recommendations.append({
                    'type': 'parlay',
                    'priority': 'high',
                    'description': f"Best safe parlay: {len(best_safe['props'])} props with {best_safe['correlation_score']:.3f} correlation",
                    'ev': best_safe['parlay_ev_estimate'],
                    'risk_level': best_safe['risk_level']
                })
            
            # High-value medium-risk parlays
            medium_risk = [p for p in parlay_opportunities if p.get('risk_level') == 'Medium' and p['parlay_ev_estimate'] > 0.1]
            if medium_risk:
                best_medium = max(medium_risk, key=lambda x: x['parlay_ev_estimate'])
                recommendations.append({
                    'type': 'parlay',
                    'priority': 'medium',
                    'description': f"High-value medium-risk parlay: {len(best_medium['props'])} props",
                    'ev': best_medium['parlay_ev_estimate'],
                    'risk_level': best_medium['risk_level']
                })
        
        return recommendations
    
    def print_analysis_report(self, analysis_results):
        """Print a comprehensive analysis report"""
        ev_results = analysis_results['ev_results']
        parlay_opportunities = analysis_results['parlay_opportunities']
        summary = analysis_results['summary']
        
        print("\n" + "="*60)
        print("🎯 COMPREHENSIVE BETTING ANALYSIS REPORT")
        print("="*60)
        
        # Individual Props Summary
        print(f"\n📊 INDIVIDUAL PROPS ANALYSIS")
        print(f"Total Opportunities: {summary['individual_props']['total_opportunities']}")
        if summary['individual_props']['total_opportunities'] > 0:
            print(f"Average EV: {summary['individual_props']['avg_ev']:.3f}")
            print(f"Best EV: {summary['individual_props']['best_ev']:.3f}")
            
            print("\nTop 5 Individual Opportunities:")
            for i, (_, row) in enumerate(ev_results.head().iterrows(), 1):
                print(f"  {i}. {row['Player']} - {row['Market']} {row['Line']} ({row['Bet_Type']})")
                print(f"     EV: {row['Splash_EV_Percentage']:.3f} | Books: {row['Num_Books_Used']} | Best Odds: {row['Best_Odds']}")
        
        # Parlay Analysis
        print(f"\n🎲 PARLAY ANALYSIS")
        print(f"Total Parlay Opportunities: {summary['parlay_analysis']['total_parlays']}")
        if summary['parlay_analysis']['total_parlays'] > 0:
            print(f"Average Correlation: {summary['parlay_analysis']['avg_correlation']:.3f}")
            print(f"Risk Breakdown: {summary['parlay_analysis']['risk_breakdown']}")
            
            # Top parlay opportunities
            top_parlays = sorted(parlay_opportunities, key=lambda x: x['parlay_ev_estimate'], reverse=True)[:3]
            print(f"\nTop 3 Parlay Opportunities:")
            for i, parlay in enumerate(top_parlays, 1):
                risk_level = parlay.get('risk_level', 'Unknown')
                confidence = parlay.get('confidence', 0)
                correlation_type = parlay.get('correlation_type', 'Standard')
                
                print(f"\n  #{i} - {risk_level} Risk | {correlation_type} (Confidence: {confidence:.2f})")
                print(f"      Correlation: {parlay['correlation_score']:.3f} | Est. EV: {parlay['parlay_ev_estimate']:.3f}")
                for j, prop in enumerate(parlay['props'], 1):
                    ev_val = prop.get('Splash_EV_Percentage', 0)
                    print(f"      {j}. {prop['Player']} {prop['Market']} {prop['Line']} (EV: {ev_val:.3f})")
        
        # Recommendations
        print(f"\n🎯 RECOMMENDATIONS")
        for rec in summary['recommendations']:
            priority_emoji = "🔥" if rec['priority'] == 'high' else "⭐" if rec['priority'] == 'medium' else "💡"
            print(f"{priority_emoji} {rec['description']}")
            print(f"   EV: {rec['ev']:.3f} | Priority: {rec['priority']}")
        
        print("\n" + "="*60)

def main():
    """Main execution function"""
    try:
        analyzer = EnhancedBettingAnalyzer()
        results = analyzer.run_comprehensive_analysis(save_results=True)
        analyzer.print_analysis_report(results)
        
    except Exception as e:
        logger.error(f"Error in main execution: {e}")
        print(f"❌ Analysis failed: {e}")

if __name__ == "__main__":
    main()
