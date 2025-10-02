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
    
    /* Custom table styling */
    .stDataFrame {
        width: 100%;
    }
    
    .stDataFrame > div {
        width: 100%;
    }
    
    /* Hide default streamlit buttons when not needed */
    .row-widget.stButton {
        text-align: center;
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
<div style="background: white; border-bottom: 1px solid #e5e7eb; padding: 1rem 2rem; display: flex; justify-content: space-between; align-items: center;">
    <h1 style="margin: 0; font-size: 24px; font-weight: 700; color: #111827;">EV Sports</h1>
    <span style="font-size: 14px; color: #6b7280;">Last Updated: 2 hours ago</span>
</div>
""", unsafe_allow_html=True)

# League Selection
st.markdown("""
<div style="background: #f9fafb; border-bottom: 1px solid #e5e7eb; padding: 0.5rem 2rem;">
    <span style="color: #111827; font-weight: 500; border-bottom: 2px solid #111827; padding-bottom: 0.5rem;">MLB</span>
    <span style="color: #9ca3af; margin-left: 2rem;">NFL</span>
    <span style="color: #9ca3af; margin-left: 2rem;">NBA</span>
</div>
""", unsafe_allow_html=True)

# Navigation
col1, col2, col3 = st.columns([2, 2, 6])

with col1:
    if st.button("📊 Individual EVs", use_container_width=True):
        st.session_state.activeView = 'individual'
        st.rerun()

with col2:
    if st.button("🎯 Correlation Parlays", use_container_width=True):
        st.session_state.activeView = 'parlays'
        st.rerun()

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
    
    # Custom styling for the dataframe
    st.markdown("""
    <style>
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
    </style>
    """, unsafe_allow_html=True)
    
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
