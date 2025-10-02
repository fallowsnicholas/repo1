import streamlit as st
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="EV Sports - MLB Dashboard",
    page_icon="⚾",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS - Exact Honda-inspired design
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
</style>
""", unsafe_allow_html=True)

def main():
    """Main Streamlit app - Static version with sample data"""
    
    # Static sample data - exactly from the React component
    individual_evs = [
        {'player': 'Shohei Ohtani', 'market': 'Total Bases', 'line': '2.5', 'ev': '8.4%'},
        {'player': 'Aaron Judge', 'market': 'Hits', 'line': '1.5', 'ev': '7.2%'},
        {'player': 'Mookie Betts', 'market': 'Runs Scored', 'line': '0.5', 'ev': '6.8%'},
        {'player': 'Juan Soto', 'market': 'RBIs', 'line': '1.5', 'ev': '5.9%'},
        {'player': 'Ronald Acuña Jr.', 'market': 'Total Bases', 'line': '1.5', 'ev': '5.3%'},
    ]
    
    parlays = [
        {
            'id': 'PARLAY_001',
            'legs': [
                {'player': 'Gerrit Cole', 'market': 'Strikeouts', 'line': '6.5', 'ev': '4.2%'},
                {'player': 'Pete Alonso', 'market': 'Hits', 'line': '1.5', 'ev': '3.8%'},
                {'player': 'Francisco Lindor', 'market': 'Total Bases', 'line': '1.5', 'ev': '3.5%'}
            ],
            'totalEV': '12.1%'
        },
        {
            'id': 'PARLAY_002',
            'legs': [
                {'player': 'Spencer Strider', 'market': 'Strikeouts', 'line': '7.5', 'ev': '5.1%'},
                {'player': 'Freddie Freeman', 'market': 'Hits', 'line': '1.5', 'ev': '4.2%'}
            ],
            'totalEV': '9.8%'
        }
    ]
    
    # Session state for navigation
    if 'active_view' not in st.session_state:
        st.session_state.active_view = 'individual'
    
    # Header Navigation
    st.markdown(f"""
    <div class="header-nav">
        <div class="header-content">
            <div class="logo">EV Sports</div>
            <div class="last-updated">Last Updated: {datetime.now().strftime('%H:%M:%S')}</div>
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
    
    # Simple navigation buttons (visible)
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
    
    # Individual EVs View
    if st.session_state.active_view == 'individual':
        st.markdown(f"""
        <div class="content-header">
            <h1 class="page-title">Individual EV Opportunities</h1>
            <span class="result-count">{len(individual_evs)} opportunities found</span>
        </div>
        """, unsafe_allow_html=True)
        
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
    
    # Correlation Parlays View
    elif st.session_state.active_view == 'parlays':
        st.markdown(f"""
        <div class="content-header">
            <h1 class="page-title">Correlation Parlays</h1>
            <span class="result-count">{len(parlays)} parlays found</span>
        </div>
        """, unsafe_allow_html=True)
        
        # Action buttons
        st.markdown("""
        <div class="action-buttons">
            <button class="action-btn">Refresh</button>
            <button class="action-btn">Filter</button>
        </div>
        """, unsafe_allow_html=True)
        
        # Parlay cards
        for parlay in parlays:
            st.markdown(f"""
            <div class="parlay-card">
                <div class="parlay-header">
                    {parlay['id']} • {len(parlay['legs'])} Legs
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
    
    st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
