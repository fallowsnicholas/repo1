# 🏈 EV Sports Dashboard

A sports betting Expected Value (EV) calculator that fetches props from Splash Sports and compares them against odds from multiple sportsbooks to find +EV opportunities.

## 📊 Features

- **Multi-Sport Support:** MLB, NFL, WNBA
- **Real-Time Data:** Fetches current props and odds
- **EV Calculation:** Automatically calculates expected value
- **Correlation Parlays:** Finds optimal parlay combinations (MLB)
- **Auto-Refresh:** GitHub Actions workflow updates data on demand
- **Web Dashboard:** Clean Dash interface to view opportunities

## 🏗️ Tech Stack

- **Frontend:** Dash (Python web framework)
- **Backend:** Python with GitHub Actions for data pipeline
- **Data Storage:** Google Sheets (as database)
- **Hosting:** Render.com (free tier) - see `DEPLOY_TO_RENDER.md`
- **APIs:**
  - Splash Sports (prop data)
  - The Odds API (sportsbook odds)
  - ESPN API (game schedules)

## 🚀 Quick Start

### Local Development

```bash
# 1. Clone the repo
git clone https://github.com/fallowsnicholas/repo1.git
cd repo1

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
# Create .env file with your API keys (see .env.example)

# 5. Run the dashboard
python dash_app.py

# 6. Open browser to http://localhost:8050
```

### Deploy to Render (Free)

See detailed guide: [`DEPLOY_TO_RENDER.md`](DEPLOY_TO_RENDER.md)

**Quick version:**
1. Sign up at [render.com](https://render.com)
2. Connect this GitHub repo
3. Use settings from `render.yaml`
4. Add your environment variables
5. Deploy!

## 🔑 Required Environment Variables

```bash
GOOGLE_SERVICE_ACCOUNT_CREDENTIALS={"type": "service_account", ...}
GITHUB_TOKEN=ghp_xxxxxxxxxxxxx
GITHUB_REPO_OWNER=fallowsnicholas
GITHUB_REPO_NAME=repo1
ODDS_API_KEY=your_odds_api_key
SCRAPERAPI_KEY=your_scraper_key
SCRAPFLY_KEY=your_scrapfly_key
ZENROWS_KEY=your_zenrows_key
```

## 📁 Project Structure

```
repo1/
├── dash_app.py                          # Main dashboard application
├── sports_config.py                     # Sport-specific configurations
├── .github/workflows/
│   └── multi-sport-pipeline.yml         # Automated data pipeline
├── fetch_splash_json.py                 # Step 1: Fetch Splash props
├── process_splash_data.py               # Step 1b: Process Splash data
├── extract_splash_matchups_optimized.py # Step 2: Extract matchups from Splash
├── fetch_odds_data.py                   # Step 3: Fetch odds from API
├── match_lines.py                       # Step 4: Match Splash to odds
├── calculate_ev.py                      # Step 5: Calculate expected values
├── find_pitcher_anchors.py              # Step 6: Find parlay anchors (MLB)
├── build_parlays.py                     # Step 7: Build correlation parlays
├── debug_sheets_data.py                 # Debug tool for Google Sheets
├── oldcode/                             # Legacy Streamlit version (archived)
├── requirements.txt                     # Python dependencies
├── render.yaml                          # Render.com deployment config
└── DEPLOY_TO_RENDER.md                  # Deployment guide
```

## 🔄 How It Works

### Data Pipeline (Splash-First Approach)

The workflow has been optimized to minimize API calls:

```
1. Fetch Splash Props → Get ALL props with projections
2. Extract Matchups → Determine which games have props
3. Fetch Odds → Get odds ONLY for games with props
4. Match Lines → Match Splash props to odds data
5. Calculate EV → Compute expected value for each prop
6. Find Anchors → Identify high-EV anchors (MLB)
7. Build Parlays → Create optimal correlation parlays (MLB)
```

**Key Optimization:** By fetching Splash first, we only get odds for games that actually have props, reducing API calls by ~70%.

### Dashboard Features

- **Sport Tabs:** Switch between MLB, NFL, WNBA
- **View Modes:** Individual EVs or Correlation Parlays
- **Market Filters:** Filter by prop type (strikeouts, hits, etc.)
- **Refresh Button:** Trigger data pipeline to get fresh props
- **Real-Time Updates:** Watch pipeline progress in real-time

## 🐛 Debugging

If data isn't updating:

```bash
# Check what's in Google Sheets
python debug_sheets_data.py --sport MLB

# Check recent workflow runs
# Visit: https://github.com/fallowsnicholas/repo1/actions
```

## 📊 API Call Budget

Approximate API calls per refresh:
- **Splash API:** 1-3 calls (via ScraperAPI/ScrapFly/ZenRows)
- **Odds API:** ~15 calls (only for games with Splash props)
- **ESPN API:** 0 calls (using Odds API game list now)

**Old approach:** ~50+ Odds API calls per refresh
**New approach:** ~15 Odds API calls per refresh
**Savings:** 70% reduction in API usage

## 🔧 Maintenance

### Update Dependencies

```bash
pip install --upgrade -r requirements.txt
pip freeze > requirements.txt
```

### Backup Google Sheets

Google Sheets auto-saves, but you can export manually:
- Go to your spreadsheet
- File → Download → CSV

### Monitor API Usage

- **Odds API:** Check usage at [the-odds-api.com/account](https://the-odds-api.com/account)
- **ScraperAPI:** Check at [scraperapi.com/dashboard](https://scraperapi.com/dashboard)

## 📜 License

Private project - Not for public distribution

## 🙏 Acknowledgments

- Built with [Dash by Plotly](https://dash.plotly.com/)
- Data from [Splash Sports](https://splashsports.com/)
- Odds from [The Odds API](https://the-odds-api.com/)

## 📝 Notes

- **oldcode/**: Contains legacy Streamlit version (no longer used)
- **Render Free Tier:** App sleeps after 15 min of inactivity
- **GitHub Actions:** Free for public repos, 2000 minutes/month for private

---

**Last Updated:** November 2024
