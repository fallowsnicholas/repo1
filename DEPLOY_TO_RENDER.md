# 🚀 Deploy to Render.com (Free Alternative to Railway)

## Why Render?
- ✅ **750 hours/month FREE** (enough for 24/7 hosting)
- ✅ Auto-deploys from GitHub (like Railway)
- ✅ Easy setup
- ⚠️ Sleeps after 15 min inactivity (wakes in ~30 seconds on first request)

## 📝 Migration Steps

### 1. Sign Up for Render
1. Go to [render.com](https://render.com)
2. Sign up with your GitHub account
3. Free tier - no credit card required

### 2. Create a New Web Service
1. Click **"New +"** → **"Web Service"**
2. Connect your GitHub repository
3. Select this repo: `fallowsnicholas/repo1`
4. Click **"Connect"**

### 3. Configure the Service

**Settings to use:**
- **Name:** `ev-sports-dashboard` (or whatever you want)
- **Environment:** `Python 3`
- **Region:** Choose closest to you
- **Branch:** `main`
- **Build Command:**
  ```
  pip install -r requirements.txt
  ```
- **Start Command:**
  ```
  gunicorn dash_app:server --bind 0.0.0.0:$PORT --workers 2 --timeout 120
  ```

### 4. Add Environment Variables

Click **"Environment"** tab and add these secrets (same as Railway):

```
GOOGLE_SERVICE_ACCOUNT_CREDENTIALS = { your JSON credentials }
GITHUB_TOKEN = ghp_xxxxxxxxxxxxx
GITHUB_REPO_OWNER = fallowsnicholas
GITHUB_REPO_NAME = repo1
ODDS_API_KEY = your_odds_api_key
SCRAPERAPI_KEY = your_scraper_key
SCRAPFLY_KEY = your_scrapfly_key
ZENROWS_KEY = your_zenrows_key
```

### 5. Deploy!

Click **"Create Web Service"** - Render will:
1. Clone your repo
2. Install dependencies
3. Start your Dash app
4. Give you a URL like `https://ev-sports-dashboard.onrender.com`

---

## 🔧 Differences from Railway

### Wake-Up Time
- **Railway:** Always running
- **Render Free:** Sleeps after 15 min, takes ~30 sec to wake up

**Solution:** First page load will be slow, but then it's fast. Or upgrade to paid tier ($7/mo) for no sleep.

### Logs
- Both have logs, Render's are similar to Railway

### Auto-Deploy
- Both auto-deploy from GitHub pushes

---

## 💰 Cost Comparison

| Feature | Railway Free | Render Free | Render Paid |
|---------|-------------|-------------|-------------|
| Price | $0 (ended) | $0 | $7/mo |
| Hours | N/A | 750/mo | Unlimited |
| Sleep | No | Yes (15 min) | No |
| RAM | 512MB | 512MB | 512MB+ |
| Build Minutes | 500 | 500 | 500+ |

---

## 🆘 Troubleshooting

### App won't start
- Check logs in Render dashboard
- Make sure `gunicorn` is in requirements.txt ✅
- Verify `PORT` environment variable is set

### Environment variables not working
- Make sure they're added in Render dashboard (not .env file)
- .env file is only for local development

### Still want Railway?
Railway has paid plans starting at $5/mo if you prefer to stay.

---

## 🎯 Alternative: Run Locally (100% Free)

If you don't need public access:

1. **Keep GitHub Actions** (updates Google Sheets automatically)
2. **Run locally:** `python dash_app.py`
3. **Access at:** `http://localhost:8050`

This way:
- ✅ Data stays fresh (GitHub Actions is free)
- ✅ View dashboard whenever you need
- ✅ No hosting costs
- ⚠️ Only accessible on your computer

---

## ✅ Ready to Deploy

Everything is configured! Just:
1. Sign up at render.com
2. Connect your GitHub repo
3. Copy the settings above
4. Click deploy

Your dashboard will be live in ~5 minutes! 🚀
