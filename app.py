import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json
import os
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="EV Sports - MLB Dashboard",
    page_icon="⚾",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS - Exact Honda-inspired design from your JavaScript file
st.markdown("""
<style>
    /* Hide Streamlit default elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display:none;}
    header[data-testid="stHeader"] {display: none;}
    
    /* Reset main container */
    .main .block-container {
        padding-top: 0rem;
        padding-left: 0rem;
        padding-right: 0rem;
        max-width: none;
        padding-bottom: 0rem;
    }
    
    /* Header Navigation */
    .header-nav {
        background: white;
        border-bottom: 1px solid #e5e7eb;
        height: 64px;
        display: flex;
        align-items: center;
    }
    
    .header-content {
        max-width: 1280px;
        margin: 0 auto;
        padding: 0 24px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        width: 100%;
    }
    
    .logo {
        font-size: 24px;
        font-weight: 700;
        color: #111827;
    }
    
    .last-updated {
        font-size: 14px;
        color: #6b7280;
    }
    
    /* League Ribbon */
    .league-ribbon {
        background: #f9fafb;
        border-bottom: 1px solid #e5e7eb;
        height: 56px;
        display: flex;
        align-items: center;
    }
    
    .league-content {
        max-width: 1280px;
        margin: 0 auto;
        padding: 0 24px;
        display: flex;
        gap: 32px;
        width: 100%;
    }
    
    .league-tab {
        padding: 16px;
        font-size: 14px;
        font-weight: 500;
        position: relative;
        cursor: pointer;
        transition: color 0.15s;
    }
    
    .league-tab.active {
        color: #111827;
    }
    
    .league-tab.active::after {
        content: '';
        position: absolute;
        bottom: 0;
        left: 0;
        right: 0;
        height: 2px;
        background: #111827;
    }
    
    .league-tab.disabled {
        color: #9ca3af;
        cursor: not-allowed;
    }
    
    /* View Ribbon */
    .view-ribbon {
        background: white;
        border-bottom: 1px solid #e5e7eb;
        height: 56px;
        display: flex;
        align-items: center;
    }
    
    .view-content {
        max-width: 1280px;
        margin: 0 auto;
        padding: 0 24px;
        display: flex;
        gap: 32px;
        width: 100%;
    }
    
    .view-tab {
        padding: 16px;
        font-size: 14px;
        font-weight: 500;
        color: #6b7280;
        position: relative;
        cursor: pointer;
        transition: color 0.15s;
    }
    
    .view-tab:hover {
        color: #111827;
    }
    
    .view-tab.active {
        color: #111827;
    }
    
    .view-tab.active::after {
        content: '';
        position: absolute;
        bottom: 0;
        left: 0;
        right: 0;
        height: 2px;
        background: #111827;
    }
    
    /* Main Content */
    .main-content {
        max-width: 1280px;
        margin: 0 auto;
        padding: 48px 24px;
    }
    
    .content-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 24px;
    }
    
    .page-title {
        font-size: 30px;
        font-weight: 300;
        color: #111827;
        margin: 0;
    }
    
    .result-count {
        font-size: 14px;
        color: #6b7280;
    }
    
    /* Action Buttons */
    .action-buttons {
        display: flex;
        gap: 16px;
        margin-bottom: 24px;
    }
    
    .action-btn {
        padding: 8px 16px;
        font-size: 14px;
        font-weight: 500;
        color: #374151;
        background: white;
        border: 1px solid #d1d5db;
        border-radius: 2px;
        cursor: pointer;
        transition: background-color 0.15s;
    }
    
    .action-btn:hover {
        background: #f9fafb;
    }
    
    /* Clean Table */
    .clean-table {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 2px;
        overflow: hidden;
    }
    
    .clean-table table {
        width: 100%;
        border-collapse: collapse;
    }
    
    .clean-table thead {
        background: #f9fafb;
    }
    
    .clean-table th {
        padding: 16px 24px;
        text-align: left;
        font-size: 12px;
        font-weight: 500;
        color: #6b7280;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        border-bottom: 1px solid #e5e7eb;
    }
    
    .clean-table th:last-child {
        text-align: right;
    }
    
    .clean-table td {
        padding: 16px 24px;
        border-bottom: 1px solid #e5e7eb;
        font-size: 14px;
    }
    
    .clean-table tr:hover {
        background: #f9fafb;
    }
    
    /* Parlay Cards */
    .parlay-card {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 2px;
        overflow: hidden;
        margin-bottom: 24px;
    }
    
    .parlay-header {
        background: #f9fafb;
        padding: 12px 24px;
        border-bottom: 1px solid #e5e7eb;
        font-size: 12px;
        font-weight: 500;
        color: #6b7280;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    /* Status messages */
    .status-message {
        padding: 24px;
        text-align: center;
        color: #6b7280;
        font-size: 16px;
    }
    
    .error-message {
        color: #dc2626;
        background: #fef2f2;
        border: 1px solid #fecaca;
        border-radius: 4px;
        padding: 16px;
        margin: 24px 0;
    }
    
    .loading-message {
        color: #2563eb;
        background: #eff6ff;
        border: 1px solid #bfdbfe;
        border-radius: 4px;
        padding: 16px;
        margin: 24px 0;
    }
</style>
""", unsafe_allow_html=True)

class MLBDataLoader:
    """Load MLB EV data from Google Sheets"""
    
    def __init__(self):
        self.client = None
        self.connection_error = None
        
    def connect_to_sheets(self):
        """Establish connection to Google Sheets"""
        try:
            if 'GOOGLE_SERVICE_ACCOUNT_CREDENTIALS' not in os.environ:
                self.connection_error = "Google Service Account credentials not found in environment variables"
                return False
                
            scopes = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
            
            service_account_info = json.loads(os.environ['GOOGLE_SERVICE_ACCOUNT_CREDENTIALS'])
            credentials = Credentials.from_service_account_info(service_account_info, scopes=scopes)
            self.client = gspread.authorize(credentials)
            return True
            
        except Exception as e:
            self.connection_error = f"Failed to connect to Google Sheets: {str(e)}"
            logger.error(f"Sheets connection error: {e}")
            return False
    
    def read_sheet_with_metadata_skip(self, worksheet_name):
        """Read Google Sheets data while skipping metadata headers"""
        try:
            spreadsheet = self.client.open("MLB_Splash_Data")
            worksheet = spreadsheet.worksheet(worksheet_name)
            
            # Get all data
            all_data = worksheet.get_all_values()
            
            if not all_data:
                return pd.DataFrame(), "Sheet is empty"
            
            # Find header row (contains actual column names)
            header_row_index = -1
            header_indicators = ['Player', 'Name', 'Market', 'Line', 'Odds', 'EV', 'Parlay_ID']
            
            for i, row in enumerate(all_data):
                if any(indicator in row for indicator in header_indicators):
                    header_row_index = i
                    break
            
            if header_row_index == -1:
                return pd.DataFrame(), "Could not find header row"
            
            # Extract headers and data
            headers = all_data[header_row_index]
            data_rows = all_data[header_row_index + 1:]
            
            # Filter out empty rows
            data_rows = [row for row in data_rows if any(cell.strip() if cell else '' for cell in row)]
            
            if not data_rows:
                return pd.DataFrame(), "No data rows found"
            
            # Create DataFrame
            df = pd.DataFrame(data_rows, columns=headers)
            df = df.dropna(how='all')
            df = df.loc[:, df.columns != '']
            
            return df, None
            
        except Exception as e:
            return pd.DataFrame(), f"Error reading {worksheet_name}: {str(e)}"
    
    def load_individual_evs(self):
        """Load individual EV opportunities from EV_RESULTS sheet"""
        df, error = self.read_sheet_with_metadata_skip("EV_RESULTS")
        
        if error:
            return [], error
        
        if df.empty:
            return [], "No EV opportunities found"
        
        # Convert to expected format
        evs = []
        for _, row in df.iterrows():
            try:
                player = row.get('Player', '')
                market = row.get('Market', '')
                line = row.get('Line', '')
                bet_type = row.get('Bet_Type', '')
                ev_pct = row.get('Splash_EV_Percentage', 0)
                
                # Convert EV to percentage if it's a decimal
                try:
                    ev_value = float(ev_pct)
                    if ev_value < 1:  # If it's decimal (0.084), convert to percentage
                        ev_display = f"{ev_value * 100:.1f}%"
                    else:  # If it's already percentage (8.4), use as is
                        ev_display = f"{ev_value:.1f}%"
                except:
                    ev_display = str(ev_pct)
                
                # Format line with bet type
                if bet_type and line:
                    line_display = f"{bet_type.title()} {line}"
                else:
                    line_display = str(line)
                
                if player and market:
                    evs.append({
                        'player': player,
                        'market': market,
                        'line': line_display,
                        'ev': ev_display,
                        'raw_ev': ev_value if 'ev_value' in locals() else 0
                    })
            except Exception as e:
                logger.warning(f"Error processing EV row: {e}")
                continue
        
        # Sort by EV descending
        evs.sort(key=lambda x: x.get('raw_ev', 0), reverse=True)
        
        return evs, None
    
    def load_correlation_parlays(self):
        """Load correlation parlays from CORRELATION_PARLAYS sheet"""
        df, error = self.read_sheet_with_metadata_skip("CORRELATION_PARLAYS")
        
        if error:
            return [], error
        
        if df.empty:
            return [], "No correlation parlays found"
        
        parlays = []
        
        for _, row in df.iterrows():
            try:
                parlay_id = row.get('Parlay_ID', '')
                if not parlay_id:
                    continue
                
                # Parse pitcher information
                pitcher_name = row.get('Pitcher_Name', '')
                pitcher_market = row.get('Pitcher_Market', '')
                pitcher_line = row.get('Pitcher_Line', '')
                pitcher_bet_type = row.get('Pitcher_Bet_Type', '')
                pitcher_ev = row.get('Pitcher_EV', 0)
                
                # Parse parlay metrics
                total_ev = row.get('Estimated_Parlay_EV', 0)
                num_batters = row.get('Num_Batters', 0)
                correlation_type = row.get('Correlation_Type', '')
                
                # Format pitcher EV
                try:
                    pitcher_ev_value = float(pitcher_ev)
                    if pitcher_ev_value < 1:
                        pitcher_ev_display = f"{pitcher_ev_value * 100:.1f}%"
                    else:
                        pitcher_ev_display = f"{pitcher_ev_value:.1f}%"
                except:
                    pitcher_ev_display = str(pitcher_ev)
                
                # Format total EV
                try:
                    total_ev_value = float(total_ev)
                    if total_ev_value < 1:
                        total_ev_display = f"{total_ev_value * 100:.1f}%"
                    else:
                        total_ev_display = f"{total_ev_value:.1f}%"
                except:
                    total_ev_display = str(total_ev)
                
                # Build legs list starting with pitcher
                legs = [{
                    'player': pitcher_name,
                    'market': pitcher_market,
                    'line': f"{pitcher_bet_type.title()} {pitcher_line}" if pitcher_bet_type and pitcher_line else pitcher_line,
                    'ev': pitcher_ev_display
                }]
                
                # Parse batter columns (Batter_1, Batter_2, etc.)
                batter_count = 1
                while f'Batter_{batter_count}' in row and row[f'Batter_{batter_count}']:
                    batter_data = row[f'Batter_{batter_count}']
                    
                    try:
                        # Parse compressed format: "Name, Market, Line, Bet_Type, EV, Best_Odds"
                        parts = [part.strip() for part in str(batter_data).split(',')]
                        if len(parts) >= 5:
                            batter_name = parts[0]
                            batter_market = parts[1]
                            batter_line = parts[2]
                            batter_bet_type = parts[3]
                            batter_ev = parts[4]
                            
                            # Format batter EV
                            try:
                                batter_ev_value = float(batter_ev)
                                if batter_ev_value < 1:
                                    batter_ev_display = f"{batter_ev_value * 100:.1f}%"
                                else:
                                    batter_ev_display = f"{batter_ev_value:.1f}%"
                            except:
                                batter_ev_display = batter_ev
                            
                            legs.append({
                                'player': batter_name,
                                'market': batter_market,
                                'line': f"{batter_bet_type.title()} {batter_line}" if batter_bet_type != 'N/A' else batter_line,
                                'ev': batter_ev_display
                            })
                    except Exception as e:
                        logger.warning(f"Error parsing batter {batter_count}: {e}")
                    
                    batter_count += 1
                
                if legs:  # Only add if we have legs
                    parlays.append({
                        'id': parlay_id,
                        'legs': legs,
                        'totalEV': total_ev_display,
                        'correlation_type': correlation_type,
                        'raw_total_ev': total_ev_value if 'total_ev_value' in locals() else 0
                    })
                    
            except Exception as e:
                logger.warning(f"Error processing parlay row: {e}")
                continue
        
        # Sort by total EV descending
        parlays.sort(key=lambda x: x.get('raw_total_ev', 0), reverse=True)
        
        return parlays, None

@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_data():
    """Load all data with caching"""
    loader = MLBDataLoader()
    
    if not loader.connect_to_sheets():
        return None, None, loader.connection_error
    
    individual_evs, ev_error = loader.load_individual_evs()
    parlays, parlay_error = loader.load_correlation_parlays()
    
    error_message = None
    if ev_error and parlay_error:
        error_message = f"EV Data: {ev_error}; Parlay Data: {parlay_error}"
    elif ev_error:
        error_message = f"EV Data: {ev_error}"
    elif parlay_error:
        error_message = f"Parlay Data: {parlay_error}"
    
    return individual_evs, parlays, error_message

def main():
    """Main Streamlit app with real Google Sheets data"""
    
    # Initialize session state
    if 'active_view' not in st.session_state:
        st.session_state.active_view = 'individual'
    
    # Load data
    with st.spinner("Loading MLB EV data..."):
        individual_evs, parlays, error_message = load_data()
    
    # Get current time for last updated
    current_time = datetime.now().strftime('%H:%M:%S')
    
    # Header Navigation
    st.markdown(f"""
    <div class="header-nav">
        <div class="header-content">
            <div class="logo">EV Sports</div>
            <div class="last-updated">Last Updated: {current_time}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # League Selection Ribbon
    st.markdown("""
    <div class="league-ribbon">
        <div class="league-content">
            <div class="league-tab active">MLB</div>
            <div class="league-tab disabled">NFL</div>
            <div class="league-tab disabled">NBA</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # View Selection Ribbon
    individual_active = "active" if st.session_state.active_view == 'individual' else ""
    parlays_active = "active" if st.session_state.active_view == 'parlays' else ""
    
    st.markdown(f"""
    <div class="view-ribbon">
        <div class="view-content">
            <div class="view-tab {individual_active}">Individual EVs</div>
            <div class="view-tab {parlays_active}">Correlation Parlays</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Navigation buttons (hidden but functional)
    col1, col2, col3 = st.columns([1, 1, 6])
    
    with col1:
        if st.button("Individual EVs", key="nav_individual"):
            st.session_state.active_view = 'individual'
            st.rerun()
    
    with col2:
        if st.button("Correlation Parlays", key="nav_parlays"):
            st.session_state.active_view = 'parlays'
            st.rerun()
    
    # Main Content
    st.markdown('<div class="main-content">', unsafe_allow_html=True)
    
    # Show error if data loading failed
    if error_message:
        st.markdown(f"""
        <div class="error-message">
            <strong>Data Loading Error:</strong> {error_message}
        </div>
        """, unsafe_allow_html=True)
    
    # Individual EVs View
    if st.session_state.active_view == 'individual':
        ev_count = len(individual_evs) if individual_evs else 0
        
        st.markdown(f"""
        <div class="content-header">
            <h1 class="page-title">Individual EV Opportunities</h1>
            <span class="result-count">{ev_count} opportunities found</span>
        </div>
        """, unsafe_allow_html=True)
        
        if individual_evs:
            # Create table HTML
            table_html = """
            <div class="clean-table">
                <table>
                    <thead>
                        <tr>
                            <th>Player</th>
                            <th>Market</th>
                            <th>Line</th>
                            <th>EV %</th>
                        </tr>
                    </thead>
                    <tbody>
            """
            
            for ev in individual_evs:
                table_html += f"""
                    <tr>
                        <td style="font-weight: 500; color: #111827;">{ev['player']}</td>
                        <td style="color: #6b7280;">{ev['market']}</td>
                        <td style="color: #6b7280;">{ev['line']}</td>
                        <td style="text-align: right; font-weight: 600; color: #059669;">{ev['ev']}</td>
                    </tr>
                """
            
            table_html += """
                    </tbody>
                </table>
            </div>
            """
            
            st.markdown(table_html, unsafe_allow_html=True)
        else:
            st.markdown('<div class="status-message">No individual EV opportunities found. Run the MLB pipeline to generate data.</div>', unsafe_allow_html=True)
    
    # Correlation Parlays View
    elif st.session_state.active_view == 'parlays':
        parlay_count = len(parlays) if parlays else 0
        
        st.markdown(f"""
        <div class="content-header">
            <h1 class="page-title">Correlation Parlays</h1>
            <span class="result-count">{parlay_count} parlays found</span>
        </div>
        """, unsafe_allow_html=True)
        
        # Action buttons
        st.markdown("""
        <div class="action-buttons">
            <button class="action-btn" onclick="window.location.reload()">Refresh</button>
            <button class="action-btn">Filter</button>
        </div>
        """, unsafe_allow_html=True)
        
        if parlays:
            # Parlay cards
            for parlay in parlays:
                # Show correlation type if available
                correlation_info = f" • {parlay.get('correlation_type', '').title()} Correlation" if parlay.get('correlation_type') else ""
                
                st.markdown(f"""
                <div class="parlay-card">
                    <div class="parlay-header">
                        {parlay['id']} • {len(parlay['legs'])} Legs{correlation_info} • Total EV: {parlay['totalEV']}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Create table for parlay legs
                table_html = """
                <div class="clean-table">
                    <table>
                        <thead>
                            <tr>
                                <th>Player</th>
                                <th>Market</th>
                                <th>Line</th>
                                <th>EV %</th>
                            </tr>
                        </thead>
                        <tbody>
                """
                
                for leg in parlay['legs']:
                    table_html += f"""
                        <tr>
                            <td style="font-weight: 500; color: #111827;">{leg['player']}</td>
                            <td style="color: #6b7280;">{leg['market']}</td>
                            <td style="color: #6b7280;">{leg['line']}</td>
                            <td style="text-align: right; color: #6b7280;">{leg['ev']}</td>
                        </tr>
                    """
                
                table_html += """
                        </tbody>
                    </table>
                </div>
                """
                
                st.markdown(table_html, unsafe_allow_html=True)
        else:
            st.markdown('<div class="status-message">No correlation parlays found. This is normal when there are no games today or insufficient data.</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
