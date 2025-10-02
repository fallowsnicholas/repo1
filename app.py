import streamlit as st

# Page configuration
st.set_page_config(
    page_title="EV Sports - MLB Dashboard",
    page_icon="⚾",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Hide Streamlit elements and add custom CSS
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display:none;}
    header[data-testid="stHeader"] {display: none;}
    
    .main .block-container {
        padding-top: 0rem;
        padding-left: 0rem;
        padding-right: 0rem;
        max-width: none;
        padding-bottom: 0rem;
    }
    
    /* Hide the navigation buttons */
    .stButton > button {
        display: none;
    }
</style>
""", unsafe_allow_html=True)

# Session state for navigation
if 'activeView' not in st.session_state:
    st.session_state.activeView = 'individual'

# Static data - exactly from your original
individualEVs = [
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

# Header Navigation
st.markdown("""
<div style="background: white; border-bottom: 1px solid #e5e7eb; height: 64px; display: flex; align-items: center;">
    <div style="max-width: 1280px; margin: 0 auto; padding: 0 24px; display: flex; align-items: center; justify-content: space-between; width: 100%;">
        <span style="font-size: 24px; font-weight: 700; color: #111827;">EV Sports</span>
        <span style="font-size: 14px; color: #6b7280;">Last Updated: 2 hours ago</span>
    </div>
</div>
""", unsafe_allow_html=True)

# League Selection Ribbon
st.markdown("""
<div style="background: #f9fafb; border-bottom: 1px solid #e5e7eb; height: 56px; display: flex; align-items: center;">
    <div style="max-width: 1280px; margin: 0 auto; padding: 0 24px; display: flex; gap: 32px; width: 100%;">
        <div style="padding: 16px; font-size: 14px; font-weight: 500; color: #111827; position: relative;">
            MLB
            <div style="position: absolute; bottom: 0; left: 0; right: 0; height: 2px; background: #111827;"></div>
        </div>
        <div style="padding: 16px; font-size: 14px; font-weight: 500; color: #9ca3af; cursor: not-allowed;">NFL</div>
        <div style="padding: 16px; font-size: 14px; font-weight: 500; color: #9ca3af; cursor: not-allowed;">NBA</div>
    </div>
</div>
""", unsafe_allow_html=True)

# View Selection Ribbon with click handlers
individual_active = "color: #111827;" if st.session_state.activeView == 'individual' else "color: #6b7280;"
parlays_active = "color: #111827;" if st.session_state.activeView == 'parlays' else "color: #6b7280;"
individual_underline = '<div style="position: absolute; bottom: 0; left: 0; right: 0; height: 2px; background: #111827;"></div>' if st.session_state.activeView == 'individual' else ''
parlays_underline = '<div style="position: absolute; bottom: 0; left: 0; right: 0; height: 2px; background: #111827;"></div>' if st.session_state.activeView == 'parlays' else ''

# Create clickable navigation using Streamlit columns
nav_col1, nav_col2, nav_col3 = st.columns([1, 1, 8])

with nav_col1:
    if st.button("Individual EVs", key="nav1", help="Switch to Individual EVs view"):
        st.session_state.activeView = 'individual'
        st.rerun()

with nav_col2:
    if st.button("Correlation Parlays", key="nav2", help="Switch to Correlation Parlays view"):
        st.session_state.activeView = 'parlays'
        st.rerun()

# Display the visual navigation ribbon
st.markdown(f"""
<div style="background: white; border-bottom: 1px solid #e5e7eb; height: 56px; display: flex; align-items: center; margin-top: -3rem; margin-bottom: 1rem;">
    <div style="max-width: 1280px; margin: 0 auto; padding: 0 24px; display: flex; gap: 32px; width: 100%;">
        <div style="padding: 16px; font-size: 14px; font-weight: 500; {individual_active} position: relative;">
            Individual EVs
            {individual_underline}
        </div>
        <div style="padding: 16px; font-size: 14px; font-weight: 500; {parlays_active} position: relative;">
            Correlation Parlays
            {parlays_underline}
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Main Content Area
st.markdown('<div style="max-width: 1280px; margin: 0 auto; padding: 48px 24px;">', unsafe_allow_html=True)

# Individual EVs View
if st.session_state.activeView == 'individual':
    st.markdown(f"""
    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 24px;">
        <h1 style="font-size: 30px; font-weight: 300; color: #111827; margin: 0;">Individual EV Opportunities</h1>
        <span style="font-size: 14px; color: #6b7280;">{len(individualEVs)} opportunities found</span>
    </div>
    """, unsafe_allow_html=True)
    
    # Clean Table
    table_html = """
    <div style="background: white; border: 1px solid #e5e7eb; border-radius: 2px; overflow: hidden;">
        <table style="width: 100%; border-collapse: collapse;">
            <thead style="background: #f9fafb;">
                <tr>
                    <th style="padding: 16px 24px; text-align: left; font-size: 12px; font-weight: 500; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid #e5e7eb;">Player</th>
                    <th style="padding: 16px 24px; text-align: left; font-size: 12px; font-weight: 500; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid #e5e7eb;">Market</th>
                    <th style="padding: 16px 24px; text-align: left; font-size: 12px; font-weight: 500; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid #e5e7eb;">Line</th>
                    <th style="padding: 16px 24px; text-align: right; font-size: 12px; font-weight: 500; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid #e5e7eb;">EV %</th>
                </tr>
            </thead>
            <tbody style="background: white;">
    """
    
    for i, ev in enumerate(individualEVs):
        border_style = "border-bottom: 1px solid #e5e7eb;" if i < len(individualEVs) - 1 else ""
        table_html += f"""
        <tr style="{border_style}">
            <td style="padding: 16px 24px; font-size: 14px; font-weight: 500; color: #111827;">{ev['player']}</td>
            <td style="padding: 16px 24px; font-size: 14px; color: #6b7280;">{ev['market']}</td>
            <td style="padding: 16px 24px; font-size: 14px; color: #6b7280;">{ev['line']}</td>
            <td style="padding: 16px 24px; font-size: 14px; text-align: right; font-weight: 600; color: #059669;">{ev['ev']}</td>
        </tr>
        """
    
    table_html += """
            </tbody>
        </table>
    </div>
    """
    
    st.markdown(table_html, unsafe_allow_html=True)

# Parlays View
elif st.session_state.activeView == 'parlays':
    st.markdown(f"""
    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 24px;">
        <h1 style="font-size: 30px; font-weight: 300; color: #111827; margin: 0;">Correlation Parlays</h1>
        <span style="font-size: 14px; color: #6b7280;">{len(parlays)} parlays found</span>
    </div>
    """, unsafe_allow_html=True)
    
    # Action Buttons
    button_col1, button_col2, button_col3 = st.columns([1, 1, 8])
    
    with button_col1:
        if st.button("Refresh", key="refresh_btn"):
            st.success("Data refreshed!")
            
    with button_col2:
        if st.button("Filter", key="filter_btn"):
            st.info("Filter options coming soon!")
    
    # Visual buttons (for styling)
    st.markdown("""
    <div style="display: flex; gap: 16px; margin-bottom: 24px; margin-top: -3rem;">
        <button style="padding: 8px 16px; font-size: 14px; font-weight: 500; color: #374151; background: white; border: 1px solid #d1d5db; border-radius: 2px; cursor: pointer;">Refresh</button>
        <button style="padding: 8px 16px; font-size: 14px; font-weight: 500; color: #374151; background: white; border: 1px solid #d1d5db; border-radius: 2px; cursor: pointer;">Filter</button>
    </div>
    """, unsafe_allow_html=True)
    
    # Parlay Cards
    for parlay in parlays:
        st.markdown(f"""
        <div style="background: white; border: 1px solid #e5e7eb; border-radius: 2px; overflow: hidden; margin-bottom: 24px;">
            <div style="background: #f9fafb; padding: 12px 24px; border-bottom: 1px solid #e5e7eb; font-size: 12px; font-weight: 500; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px;">
                {parlay['id']} • {len(parlay['legs'])} Legs • Total EV: {parlay['totalEV']}
            </div>
        """, unsafe_allow_html=True)
        
        # Parlay Legs Table
        legs_table = """
            <table style="width: 100%; border-collapse: collapse;">
                <thead style="background: #f9fafb;">
                    <tr>
                        <th style="padding: 12px 24px; text-align: left; font-size: 12px; font-weight: 500; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px;">Player</th>
                        <th style="padding: 12px 24px; text-align: left; font-size: 12px; font-weight: 500; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px;">Market</th>
                        <th style="padding: 12px 24px; text-align: left; font-size: 12px; font-weight: 500; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px;">Line</th>
                        <th style="padding: 12px 24px; text-align: right; font-size: 12px; font-weight: 500; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px;">EV %</th>
                    </tr>
                </thead>
                <tbody style="background: white;">
        """
        
        for i, leg in enumerate(parlay['legs']):
            border_style = "border-bottom: 1px solid #e5e7eb;" if i < len(parlay['legs']) - 1 else ""
            legs_table += f"""
            <tr style="{border_style}">
                <td style="padding: 16px 24px; font-size: 14px; font-weight: 500; color: #111827;">{leg['player']}</td>
                <td style="padding: 16px 24px; font-size: 14px; color: #6b7280;">{leg['market']}</td>
                <td style="padding: 16px 24px; font-size: 14px; color: #6b7280;">{leg['line']}</td>
                <td style="padding: 16px 24px; font-size: 14px; text-align: right; color: #6b7280;">{leg['ev']}</td>
            </tr>
            """
        
        legs_table += """
                </tbody>
            </table>
        </div>
        """
        
        st.markdown(legs_table, unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)
