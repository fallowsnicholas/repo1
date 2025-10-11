def main():
    """Main function for Step 4 - matching data from Google Sheets"""
    parser = argparse.ArgumentParser(description='Match Splash to Odds data for MLB, NFL, or WNBA')
    parser.add_argument('--sport', default='MLB', choices=['MLB', 'NFL', 'WNBA'],
                       help='Sport to match data for (default: MLB)')
    args = parser.parse_args()
