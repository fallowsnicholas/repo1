# test_correlation_standalone.py
# Standalone script to test correlation analysis without running full pipeline

import pandas as pd
import numpy as np
from datetime import datetime
from simplified_correlation_analyzer import SimplifiedCorrelationAnalyzer
import json
import os
import gspread
from google.oauth2.service_account import Credentials

def load_ev_data_from_sheets():
    """
    Load existing EV results from Google Sheets for testing
    """
    try:
        print("Loading EV data from Google Sheets...")
        
        # Connect to sheets
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        service_account_info = json.loads(os.environ['GOOGLE_SERVICE_ACCOUNT_CREDENTIALS'])
        credentials = Credentials.from_service_account_info(service_account_info, scopes=scopes)
        client = gspread.authorize(credentials)
        
        # Read EV results
        spreadsheet = client.open("MLB_Splash_Data")
        worksheet = spreadsheet.worksheet("EV_RESULTS")
        
        data = worksheet.get_all_records()
        if not data:
            print("No EV data found in sheets")
            return pd.DataFrame()
        
        df = pd.DataFrame(data)
        print(f"Loaded {len(df)} EV opportunities from sheets")
        return df
        
    except Exception as e:
        print(f"Could not load from sheets: {e}")
        return create_sample_data()

def create_sample_data():
    """
    Create realistic sample data for testing when sheets aren't available
    """
    print("Creating sample EV data for testing...")
    
    sample_data = [
        # Same player correlations (should create parlays)
        {'Player': 'Aaron Judge', 'Market': 'hits', 'Line': '1.5', 'Bet_Type': 'over', 
         'Splash_EV_Percentage': 0.045, 'Num_Books_Used': 6, 'True_Prob': 0.62},
        {'Player': 'Aaron Judge', 'Market': 'total_bases', 'Line': '2.5', 'Bet_Type': 'over', 
         'Splash_EV_Percentage': 0.038, 'Num_Books_Used': 7, 'True_Prob': 0.58},
        {'Player': 'Aaron Judge', 'Market': 'runs', 'Line': '0.5', 'Bet_Type': 'over', 
         'Splash_EV_Percentage': 0.051, 'Num_Books_Used': 8, 'True_Prob': 0.65},
        
        # Pitcher correlations 
        {'Player': 'Gerrit Cole', 'Market': 'strikeouts', 'Line': '7.5', 'Bet_Type': 'over', 
         'Splash_EV_Percentage': 0.052, 'Num_Books_Used': 8, 'True_Prob': 0.63},
        {'Player': 'Gerrit Cole', 'Market': 'earned_runs', 'Line': '2.5', 'Bet_Type': 'under', 
         'Splash_EV_Percentage': 0.041, 'Num_Books_Used': 5, 'True_Prob': 0.59},
        {'Player': 'Gerrit Cole', 'Market': 'hits_allowed', 'Line': '5.5', 'Bet_Type': 'under', 
         'Splash_EV_Percentage': 0.033, 'Num_Books_Used': 6, 'True_Prob': 0.56},
        
        # Different players (should have lower correlation)
        {'Player': 'Mookie Betts', 'Market': 'hits', 'Line': '1.5', 'Bet_Type': 'over', 
         'Splash_EV_Percentage': 0.042, 'Num_Books_Used': 7, 'True_Prob': 0.61},
        {'Player': 'Ronald Acuna Jr.', 'Market': 'runs', 'Line': '0.5', 'Bet_Type': 'over', 
         'Splash_EV_Percentage': 0.047, 'Num_Books_Used': 6, 'True_Prob': 0.64},
        
        # Lower EV props (should be filtered out)
        {'Player': 'Jose Altuve', 'Market': 'hits', 'Line': '1.5', 'Bet_Type': 'over', 
         'Splash_EV_Percentage': 0.015, 'Num_Books_Used': 4, 'True_Prob': 0.52},
    ]
    
    return pd.DataFrame(sample_data)

def test_correlation_analysis():
    """
    Test the correlation analysis with real or sample data
    """
    print("="*60)
    print("TESTING CORRELATION ANALYSIS")
    print("="*60)
    
    # Try to load real data, fall back to sample data
    ev_df = load_ev_data_from_sheets()
    
    if ev_df.empty:
        print("Using sample data for testing")
        ev_df = create_sample_data()
    
    print(f"\nAnalyzing {len(ev_df)} EV opportunities...")
    print(f"Data preview:")
    print(ev_df[['Player', 'Market', 'Splash_EV_Percentage']].head(10))
    
    # Run correlation analysis
    analyzer = SimplifiedCorrelationAnalyzer()
    parlays = analyzer.identify_simple_parlays(ev_df, max_parlay_size=3)
    
    # Generate report
    report = analyzer.generate_parlay_report(parlays)
    print("\n" + report)
    
    # Save results to file for inspection
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Save detailed results as JSON
    results_file = f"parlay_test_results_{timestamp}.json"
    with open(results_file, 'w') as f:
        # Convert numpy types to native Python types for JSON serialization
        parlays_for_json = []
        for parlay in parlays:
            parlay_copy = parlay.copy()
            parlay_copy['correlation_score'] = float(parlay_copy['correlation_score'])
            parlay_copy['estimated_value'] = float(parlay_copy['estimated_value'])
            parlay_copy['avg_individual_ev'] = float(parlay_copy['avg_individual_ev'])
            parlay_copy['confidence'] = float(parlay_copy['confidence'])
            parlay_copy['individual_evs'] = [float(x) for x in parlay_copy['individual_evs']]
            parlays_for_json.append(parlay_copy)
        
        json.dump({
            'test_date': datetime.now().isoformat(),
            'total_ev_opportunities': len(ev_df),
            'parlay_opportunities_found': len(parlays),
            'parlays': parlays_for_json
        }, f, indent=2)
    
    print(f"\nDetailed results saved to: {results_file}")
    
    # Save report as text file
    report_file = f"parlay_report_{timestamp}.txt"
    with open(report_file, 'w') as f:
        f.write(report)
    
    print(f"Report saved to: {report_file}")
    
    return parlays

if __name__ == "__main__":
    test_correlation_analysis()
