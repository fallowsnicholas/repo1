import streamlit as st
import pandas as pd

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
    
    /* Hide the actual Streamlit buttons */
    .stButton > button {
        display: none !important;
    }
    
    /* Custom table styling */
    .stDataFrame th {
        background-color: #f9fafb !important;
        color: #6b7280 !important;
        font-weight: 500 !important;
        text-transform: uppercase !important;
        font-size: 12px !important;
        letter-spacing: 0.5px !important;
    }
    
    .stDataFrame td {
        font-size: 14px !important;
    }
    
    .stDataFrame tr:nth-child(even) {
        background-color: #ffffff !important;
    }
    
    .stDataFrame tr:hover {
        background-color: #f9fafb !important;
    }
    
    /* Clickable ribbon styling */
    .ribbon-button {
        padding: 16px;
        font-size: 14px;
        font-weight: 500;
        position: relative;
        cursor: pointer;
        display: inline-block;
        text-decoration: none;
        border: none;
        background: none;
        transition: color 0.2s ease;
    }
    
    .ribbon-button:hover {
        color: #374151 !important;
    }
    
    .ribbon-button.active {
        color: #111827 !important;
    }
    
    .ribbon-button.inactive {
        color: #6b7280 !important;
    }
    
    .ribbon-button.active::after {
        content: '';
        position: absolute;
        bottom: 0;
        left: 0;
        right: 0;
        height: 2px;
        background: #111827;
    }
</style>
""", unsafe_allow_html=True)

# Session state for navigation
if 'activeView' not in st.session_state:
    st.session_state.activeView = 'individual'

# Static data
individualEVs = [
    {'Player': 'Shohei Ohtani', 'Market': 'Total Bases', 'Line': '2.5', 'EV %': '8.4%'},
    {'Player': 'Aaron Judge', 'Market': 'Hits', 'Line': '1.5', 'EV %': '7.2%'},
    {'Player': 'Mookie Betts', 'Market': 'Runs Scored', 'Line': '0.5', 'EV %': '6.8%'},
    {'Player': 'Juan Soto', 'Market': 'RBIs', 'Line': '1.5', 'EV %': '5.9%'},
    {'Player': 'Ronald Acuña Jr.', 'Market': 'Total Bases', 'Line': '1.5', 'EV %': '5.3%'},
]

parlays = [
    {
        'id': 'PARLAY_001',
        'legs': [
            {'Player': 'Gerrit Cole', 'Market': 'Strikeouts', 'Line': '6.5', 'EV %': '4.2%'},
            {'Player': 'Pete Alonso', 'Market': 'Hits', 'Line': '1.5', 'EV %': '3.8%'},
            {'Player': 'Francisco Lindor', 'Market': 'Total Bases', 'Line': '1.5', 'EV %': '3.5%'}
        ],
        'totalEV': '12.1%'
    },
    {
        'id': 'PARLAY_002',
        'legs': [
            {'Player': 'Spencer Strider', 'Market': 'Strikeouts', 'Line': '7.5', 'EV %': '5.1%'},
            {'Player': 'Freddie Freeman', 'Market': 'Hits', 'Line': '1.5', 'EV %': '4.2%'}
        ],
        'totalEV': '9.8%'
    }
]

# Header
st.markdown("""
<div style="background: white; border-bottom: 1px solid #e5e7eb; height: 64px; display: flex; align-items: center;">
    <div style="max-width: 1280px; margin: 0 auto; padding: 0 24px; display: flex; align-items: center; justify-content: space-between; width: 100%;">
        <span style="font-size: 24px; font-weight: 700; color: #111827;">EV Sports</span>
        <span style="font-size: 14px; color: #6b7280;">Last Updated: 2 hours ago</span>
    </div>
</div>
""", unsafe_allow_html=True)

# League Selection Ribbon (non-functional, just like yours)
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

# Hidden navigation buttons (functional but invisible)
col1, col2, col3 = st.columns([1, 1, 8])

with col1:
    if st.button("nav_individual", key="nav1"):
        st.session_state.activeView = 'individual'
        st.rerun()

with col2:
    if st.button("nav_parlays", key="nav2"):
        st.session_state.activeView = 'parlays'
        st.rerun()

# View Selection Ribbon (looks identical to league ribbon but functional)
individual_class = "active" if st.session_state.activeView == 'individual' else "inactive"
parlays_class = "active" if st.session_state.activeView == 'parlays' else "inactive"
individual_underline = '<div style="position: absolute; bottom: 0; left: 0; right: 0; height: 2px; background: #111827;"></div>' if st.session_state.activeView == 'individual' else ''
parlays_underline = '<div style="position: absolute; bottom: 0; left: 0; right: 0; height: 2px; background: #111827;"></div>' if st.session_state.activeView == 'parlays' else ''

st.markdown(f"""
<div style="background: white; border-bottom: 1px solid #e5e7eb; height: 56px; display: flex; align-items: center;">
    <div style="max-width: 1280px; margin: 0 auto; padding: 0 24px; display: flex; gap: 32px; width: 100%;">
        <div class="ribbon-button {individual_class}" onclick="document.querySelector('[data-testid=\\\"column\\\"] button').click()" 
             style="padding: 16px; font-size: 14px; font-weight: 500; color: {'#111827' if st.session_state.activeView == 'individual' else '#6b7280'}; position: relative; cursor: pointer;">
            Individual EVs
            {individual_underline}
        </div>
        <div class="ribbon-button {parlays_class}" onclick="document.querySelectorAll('[data-testid=\\\"column\\\"] button')[1].click()"
             style="padding: 16px; font-size: 14px; font-weight: 500; color: {'#111827' if st.session_state.activeView == 'parlays' else '#6b7280'}; position: relative; cursor: pointer;">
            Correlation Parlays
            {parlays_underline}
        </div>
    </div>
</div>

<script>
// Add click handlers after the page loads
document.addEventListener('DOMContentLoaded', function() {{
    // Find all ribbon buttons
    const ribbonButtons = document.querySelectorAll('.ribbon-button');
    const streamlitButtons = document.querySelectorAll('[data-testid="column"] button');
    
    if (ribbonButtons.length >= 2 && streamlitButtons.length >= 2) {{
        ribbonButtons[0].addEventListener('click', function() {{
            streamlitButtons[0].click();
        }});
        
        ribbonButtons[1].addEventListener('click', function() {{
            streamlitButtons[1].click();
        }});
    }}
}});

// Also try immediate binding
setTimeout(function() {{
    const ribbonButtons = document.querySelectorAll('.ribbon-button');
    const streamlitButtons = document.querySelectorAll('[data-testid="column"] button');
    
    if (ribbonButtons.length >= 2 && streamlitButtons.length >= 2) {{
        ribbonButtons[0].onclick = function() {{ streamlitButtons[0].click(); }};
        ribbonButtons[1].onclick = function() {{ streamlitButtons[1].click(); }};
    }}
}}, 100);
</script>
""", unsafe_allow_html=True)

# Add some spacing
st.markdown("<br>", unsafe_allow_html=True)

# Main Content
if st.session_state.activeView == 'individual':
    # Individual EVs View
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("## Individual EV Opportunities")
    with col2:
        st.markdown(f"**{len(individualEVs)} opportunities found**")
    
    # Convert to DataFrame and display
    df = pd.DataFrame(individualEVs)
    
    st.dataframe(
        df, 
        use_container_width=True, 
        hide_index=True,
        column_config={
            "Player": st.column_config.TextColumn("Player", width="medium"),
            "Market": st.column_config.TextColumn("Market", width="medium"),
            "Line": st.column_config.TextColumn("Line", width="small"),
            "EV %": st.column_config.TextColumn("EV %", width="small")
        }
    )

elif st.session_state.activeView == 'parlays':
    # Parlays View
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("## Correlation Parlays")
    with col2:
        st.markdown(f"**{len(parlays)} parlays found**")
    
    # Action buttons
    col1, col2, col3 = st.columns([1, 1, 8])
    with col1:
        if st.button("🔄 Refresh"):
            st.success("Data refreshed!")
    with col2:
        if st.button("🔍 Filter"):
            st.info("Filter options coming soon!")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Display each parlay
    for parlay in parlays:
        with st.container():
            st.markdown(f"""
            <div style="background: #f9fafb; padding: 0.75rem 1.5rem; border: 1px solid #e5e7eb; border-radius: 4px; margin-bottom: 1rem;">
                <strong>{parlay['id']}</strong> • {len(parlay['legs'])} Legs • Total EV: <span style="color: #059669; font-weight: 600;">{parlay['totalEV']}</span>
            </div>
            """, unsafe_allow_html=True)
            
            # Convert parlay legs to DataFrame
            parlay_df = pd.DataFrame(parlay['legs'])
            
            st.dataframe(
                parlay_df, 
                use_container_width=True, 
                hide_index=True,
                column_config={
                    "Player": st.column_config.TextColumn("Player", width="medium"),
                    "Market": st.column_config.TextColumn("Market", width="medium"),
                    "Line": st.column_config.TextColumn("Line", width="small"),
                    "EV %": st.column_config.TextColumn("EV %", width="small")
                }
            )
            
            st.markdown("<br>", unsafe_allow_html=True)

# Footer
st.markdown("""
<div style="margin-top: 3rem; padding: 2rem; text-align: center; color: #6b7280; border-top: 1px solid #e5e7eb;">
    <small>EV Sports Dashboard • Built with Streamlit</small>
</div>
""", unsafe_allow_html=True)
