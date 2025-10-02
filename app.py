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

    /* Style the tab buttons to look like ribbon */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0px;
        background-color: white;
        border-bottom: none !important;
        height: 56px;
        display: flex;
        align-items: center;
        padding-left: 0px;
    }

    .stTabs [data-baseweb="tab"] {
        height: 56px;
        padding: 16px 32px 16px 0px;
        background-color: transparent;
        border: none;
        color: #6b7280;
        font-size: 14px;
        font-weight: 500;
        position: relative;
    }

    .stTabs [aria-selected="true"] {
        color: #111827 !important;
        background-color: transparent !important;
    }

    /* Remove the underlines */
    .stTabs [aria-selected="true"]::after {
        display: none;
    }

    /* Remove any additional tab indicators */
    .stTabs [data-baseweb="tab-border"] {
        display: none !important;
    }

    .stTabs [data-baseweb="tab-highlight"] {
        display: none !important;
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
header_col1, header_col2 = st.columns([3, 1])
with header_col1:
    st.markdown('<h1 style="font-size: 24px; font-weight: 700; color: #111827; margin: 0;">EV Sports</h1>', unsafe_allow_html=True)
with header_col2:
    st.markdown('<p style="font-size: 14px; color: #6b7280; margin: 0; text-align: right;">Last Updated: 2 hours ago</p>', unsafe_allow_html=True)

st.markdown('<hr style="margin: 1rem 0; border: none; border-top: 1px solid #e5e7eb;">', unsafe_allow_html=True)

# League Selection (visual only)
league_col1, league_col2, league_col3, league_col4 = st.columns([1, 1, 1, 18])
with league_col1:
    st.markdown('<div style="color: #111827; font-weight: 500; padding-bottom: 8px; font-size: 14px;">MLB</div>', unsafe_allow_html=True)
with league_col2:
    st.markdown('<div style="color: #9ca3af; font-size: 14px; padding-bottom: 8px;">NFL</div>', unsafe_allow_html=True)
with league_col3:
    st.markdown('<div style="color: #9ca3af; font-size: 14px; padding-bottom: 8px;">NBA</div>', unsafe_allow_html=True)

st.markdown('<div style="margin: 1rem 0;"></div>', unsafe_allow_html=True)

# Navigation using Streamlit tabs (styled to look like ribbon)
tab1, tab2 = st.tabs(["Individual EVs", "Correlation Parlays"])

with tab1:
    # Individual EVs View
    st.markdown("<br>", unsafe_allow_html=True)
    
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

with tab2:
    # Parlays View
    st.markdown("<br>", unsafe_allow_html=True)
    
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
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown("""
<div style="padding: 2rem; text-align: center; color: #6b7280; border-top: 1px solid #e5e7eb;">
    <small>EV Sports Dashboard • Built with Streamlit</small>
</div>
""", unsafe_allow_html=True)
