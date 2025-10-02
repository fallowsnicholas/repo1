# run_dashboard.py - Simple launcher for the Streamlit dashboard
import subprocess
import sys
import os

def main():
    """Launch the Streamlit dashboard"""
    
    print("🚀 Starting MLB EV Dashboard...")
    print("=" * 50)
    
    # Check if streamlit is installed
    try:
        import streamlit
        print("✅ Streamlit is available")
    except ImportError:
        print("❌ Streamlit not found. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "streamlit"])
        print("✅ Streamlit installed")
    
    # Check for required packages
    required_packages = ["pandas", "gspread", "google-auth", "plotly"]
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
            print(f"✅ {package} is available")
        except ImportError:
            print(f"❌ {package} not found. Please install: pip install {package}")
            return
    
    # Check for credentials
    if 'GOOGLE_SERVICE_ACCOUNT_CREDENTIALS' not in os.environ:
        print("⚠️ Warning: GOOGLE_SERVICE_ACCOUNT_CREDENTIALS not found in environment")
        print("   The dashboard will show an error until credentials are provided")
        print("   Set this environment variable with your service account JSON")
    else:
        print("✅ Google Service Account credentials found")
    
    print("\n🌐 Launching dashboard...")
    print("📊 Your dashboard will open in your default web browser")
    print("🔄 The dashboard will auto-refresh data every 5 minutes")
    print("💡 Use Ctrl+C to stop the dashboard")
    print("\n" + "=" * 50)
    
    # Launch Streamlit
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", "mlb_dashboard.py",
            "--server.port", "8501",
            "--server.address", "localhost",
            "--browser.serverAddress", "localhost",
            "--browser.gatherUsageStats", "false"
        ])
    except KeyboardInterrupt:
        print("\n👋 Dashboard stopped by user")
    except Exception as e:
        print(f"\n❌ Error running dashboard: {e}")

if __name__ == "__main__":
    main()
