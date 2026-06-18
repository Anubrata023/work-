"""
GridLock Zero - Complete Dashboard
Flipkart GridLock Hackathon 2026
"""
import streamlit as st
import pandas as pd
import numpy as np
import pydeck as pdk
from pathlib import Path
import sys

st.set_page_config(
    page_title="GridLock Zero",
    page_icon="🚦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------------------------------------------------------
# CUSTOM CSS
# -----------------------------------------------------------------------------
st.markdown("""
<style>
    .main { background-color: #0E1117; }
    .stSidebar { background-color: #1A1C23; border-right: 1px solid #333; }
    
    .stButton>button {
        background-color: #FF4B4B;
        color: white;
        border-radius: 8px;
        font-weight: bold;
        border: none;
        padding: 10px 20px;
        width: 100%;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #CC0000;
        box-shadow: 0 4px 15px rgba(255,75,75,0.4);
        color: white;
    }
    
    h1, h2, h3, h4, h5, h6 {
        color: #FFFFFF;
    }
    .stInfo {
        background-color: #1A1C23 !important;
        border-left: 4px solid #FF4B4B !important;
        color: #DDDDDD !important;
    }
    .stDataFrame {
        background-color: #1A1C23;
        border-radius: 8px;
    }
    .zone-card {
        background-color: #1A1C23;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #FF4B4B;
        margin-bottom: 10px;
    }
    .zone-card p {
        color: #DDDDDD;
        margin: 5px 0;
    }
    .zone-card strong {
        color: #FFFFFF;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# DATA LOADING
# -----------------------------------------------------------------------------
@st.cache_data
def load_ccis_data():
    path = Path(__file__).parent / "data" / "processed" / "ccis_scores.csv"
    if path.exists():
        df = pd.read_csv(path)
        if 'latitude' in df.columns and 'longitude' in df.columns:
            df = df.rename(columns={'latitude': 'lat', 'longitude': 'lon'})
        if 'h3_8' in df.columns and 'h3_cell' not in df.columns:
            df = df.rename(columns={'h3_8': 'h3_cell'})
        if 'location' not in df.columns:
            df['location'] = df['h3_cell']
        return df
    return pd.DataFrame(columns=['h3_cell', 'hour', 'ccis', 'lat', 'lon', 'status', 'color', 'location'])

@st.cache_data
def load_clustered_data():
    path = Path(__file__).parent / "data" / "processed" / "clustered_hotspots.csv"
    if path.exists():
        df = pd.read_csv(path)
        if 'centroid_lat' in df.columns and 'centroid_lon' in df.columns:
            df = df.rename(columns={'centroid_lat': 'lat', 'centroid_lon': 'lon'})
        if 'location' not in df.columns:
            df['location'] = df['h3_cell']
        return df
    return pd.DataFrame()

# -----------------------------------------------------------------------------
# LOAD DATA
# -----------------------------------------------------------------------------
ccis_df = load_ccis_data()
clustered_df = load_clustered_data()

# -----------------------------------------------------------------------------
# SIDEBAR
# -----------------------------------------------------------------------------
st.sidebar.title("GridLock Zero")
st.sidebar.caption("Parking Intelligence & Dispatch")

persona = st.sidebar.radio(
    "Select View",
    ["BTP Mode", "Flipkart Mode"],
    index=0
)

st.sidebar.markdown("---")

hour = st.sidebar.slider(
    "Time of Day",
    min_value=0,
    max_value=23,
    value=18,
    step=1,
    format="%d:00"
)

st.sidebar.markdown("---")

granularity = st.sidebar.selectbox(
    "Zoom Level",
    ["City View", "Zone View", "Street View"],
    index=1
)

st.sidebar.markdown("---")
st.sidebar.caption("Data source: BTP GridLock Dataset")
st.sidebar.caption(f"Records loaded: {len(ccis_df):,}")

# -----------------------------------------------------------------------------
# FILTER DATA
# -----------------------------------------------------------------------------
hour_data = ccis_df[ccis_df['hour'] == hour].copy()

# -----------------------------------------------------------------------------
# MAIN CONTENT
# -----------------------------------------------------------------------------
st.title("GridLock Zero")
st.caption("Real-time Parking Congestion Intelligence & Dispatch System")

if persona == "BTP Mode":
    st.info("BTP Mode – Enforcement priorities, dispatch recommendations, and hotspot management.")
else:
    st.info("Flipkart Mode – Delivery routing optimization, cost savings, and zone avoidance.")

st.markdown("---")

# -----------------------------------------------------------------------------
# METRICS
# -----------------------------------------------------------------------------
if not hour_data.empty:
    total_zones = len(hour_data)
    critical_zones = len(hour_data[hour_data['status'] == 'critical']) if 'status' in hour_data.columns else 0
    monitor_zones = len(hour_data[hour_data['status'] == 'monitor']) if 'status' in hour_data.columns else 0
    avg_ccis = hour_data['ccis'].mean() if 'ccis' in hour_data.columns else 0
else:
    total_zones = critical_zones = monitor_zones = 0
    avg_ccis = 0

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Active Zones", total_zones)
with col2:
    st.metric("Critical", critical_zones)
with col3:
    st.metric("Monitor", monitor_zones)
with col4:
    st.metric("Avg CCIS", f"{avg_ccis:.1f}")

st.markdown("---")

# -----------------------------------------------------------------------------
# MAP SECTION - GUARANTEED TO RENDER
# -----------------------------------------------------------------------------
st.subheader(f"Congestion Heatmap – {granularity}")

# -----------------------------------------------------------------------------
# RENDER MAP FUNCTION - ALWAYS RETURNS A MAP
# -----------------------------------------------------------------------------
def render_map(hour_data, clustered_df, hour):
    """
    Renders a Pydeck map. Always returns something, even with demo data.
    """
    # Step 1: Try to get real data
    map_data = pd.DataFrame()
    data_source = "none"

    # Try hour_data first
    if not hour_data.empty:
        if 'lat' in hour_data.columns and 'lon' in hour_data.columns:
            map_data = hour_data[['lat', 'lon', 'ccis', 'color', 'location']].dropna()
            if not map_data.empty:
                data_source = "hour_data"

    # Try clustered data second
    if map_data.empty and not clustered_df.empty:
        if 'lat' in clustered_df.columns and 'lon' in clustered_df.columns:
            if 'hour' in clustered_df.columns:
                temp = clustered_df[clustered_df['hour'] == hour]
            else:
                temp = clustered_df
            map_data = temp[['lat', 'lon', 'ccis', 'color', 'location']].dropna()
            if not map_data.empty:
                data_source = "clustered_data"

    # Step 2: Fallback to demo data if no real data
    if map_data.empty:
        np.random.seed(42)
        map_data = pd.DataFrame({
            'lat': np.random.uniform(12.85, 13.05, 80),
            'lon': np.random.uniform(77.50, 77.70, 80),
            'ccis': np.random.uniform(1, 8, 80),
            'color': ['#FF4B4B' if c > 6 else '#FFA500' if c > 3 else '#00CC66' for c in np.random.uniform(1, 8, 80)],
            'location': ['Demo Zone ' + str(i) for i in range(80)]
        })
        data_source = "demo"
        st.info("Using demo data. Run data pipeline for real data.")

    # Step 3: Prepare tooltips
    if 'location' in map_data.columns:
        map_data['tooltip'] = map_data.apply(
            lambda r: f"Location: {str(r['location'])[:50]}\nCCIS: {r['ccis']:.1f}", axis=1
        )
    else:
        map_data['tooltip'] = map_data.apply(lambda r: f"CCIS: {r['ccis']:.1f}", axis=1)

    # Step 4: Convert colors
    def hex_to_rgb(hex_color):
        hex_color = hex_color.lstrip('#')
        return [int(hex_color[i:i+2], 16) for i in (0, 2, 4)]

    map_data['fill_color'] = map_data['color'].apply(hex_to_rgb)

    # Step 5: Build the deck
    deck = pdk.Deck(
        map_style="mapbox://styles/mapbox/dark-v11",
        initial_view_state=pdk.ViewState(
            latitude=12.9716,
            longitude=77.5946,
            zoom=11,
            pitch=45,
        ),
        layers=[
            pdk.Layer(
                "ScatterplotLayer",
                data=map_data,
                get_position="[lon, lat]",
                get_radius=200,
                get_fill_color="fill_color",
                pickable=True,
                opacity=0.8,
                tooltip={"text": "{tooltip}"}
            )
        ]
    )

    # Step 6: Add route layers if they exist
    if 'std_route' in st.session_state and st.session_state['std_route']:
        try:
            std_route = st.session_state['std_route']
            std_df = pd.DataFrame(std_route, columns=['lat', 'lon'])
            opt_route = st.session_state['opt_route']
            opt_df = pd.DataFrame(opt_route, columns=['lat', 'lon'])
            start = st.session_state['start_coords']
            end = st.session_state['end_coords']

            route_layers = [
                pdk.Layer(
                    "PathLayer",
                    data=[{'path': [[row['lon'], row['lat']] for _, row in std_df.iterrows()]}],
                    get_path="path",
                    get_color=[0, 100, 255, 200],
                    width_min_pixels=4,
                    pickable=True,
                    auto_highlight=True
                ),
                pdk.Layer(
                    "PathLayer",
                    data=[{'path': [[row['lon'], row['lat']] for _, row in opt_df.iterrows()]}],
                    get_path="path",
                    get_color=[0, 255, 100, 220],
                    width_min_pixels=5,
                    pickable=True,
                    auto_highlight=True
                ),
                pdk.Layer(
                    "ScatterplotLayer",
                    data=[{'lat': start[0], 'lon': start[1]}],
                    get_position='[lon, lat]',
                    get_color=[0, 255, 0, 255],
                    get_radius=200,
                    pickable=True
                ),
                pdk.Layer(
                    "ScatterplotLayer",
                    data=[{'lat': end[0], 'lon': end[1]}],
                    get_position='[lon, lat]',
                    get_color=[255, 0, 0, 255],
                    get_radius=200,
                    pickable=True
                )
            ]
            deck.layers.extend(route_layers)
            st.caption("Blue = Standard Route | Green = Congestion-Aware Route")
        except Exception as e:
            st.warning(f"Route layers not shown: {e}")

    # Step 7: Return the deck and data info
    return deck, map_data, data_source

# -----------------------------------------------------------------------------
# RENDER THE MAP
# -----------------------------------------------------------------------------
try:
    deck, map_data, data_source = render_map(hour_data, clustered_df, hour)
    st.pydeck_chart(deck)

    # Show data source info
    if data_source == "demo":
        st.info("Map showing demo data. To use real data, run: python utils/ccis_engine.py")
    elif data_source == "hour_data":
        st.success(f"Map showing real data from CCIS file. {len(map_data)} points displayed.")
    elif data_source == "clustered_data":
        st.success(f"Map showing clustered hotspots. {len(map_data)} cluster points displayed.")

except Exception as e:
    st.error(f"Error rendering map: {e}")
    # Emergency fallback: render a simple map with demo data
    np.random.seed(42)
    emergency_data = pd.DataFrame({
        'lat': np.random.uniform(12.85, 13.05, 50),
        'lon': np.random.uniform(77.50, 77.70, 50),
        'ccis': np.random.uniform(1, 8, 50),
        'color': ['#FF4B4B' if c > 6 else '#FFA500' if c > 3 else '#00CC66' for c in np.random.uniform(1, 8, 50)],
        'location': ['Emergency Zone ' + str(i) for i in range(50)]
    })
    emergency_data['tooltip'] = emergency_data.apply(lambda r: f"Location: {r['location']}\nCCIS: {r['ccis']:.1f}", axis=1)

    def hex_to_rgb(h):
        h = h.lstrip('#')
        return [int(h[i:i+2], 16) for i in (0, 2, 4)]
    emergency_data['fill_color'] = emergency_data['color'].apply(hex_to_rgb)

    emergency_deck = pdk.Deck(
        map_style="mapbox://styles/mapbox/dark-v11",
        initial_view_state=pdk.ViewState(lat=12.9716, lon=77.5946, zoom=11, pitch=45),
        layers=[
            pdk.Layer(
                "ScatterplotLayer",
                data=emergency_data,
                get_position="[lon, lat]",
                get_radius=200,
                get_fill_color="fill_color",
                pickable=True,
                opacity=0.8,
                tooltip={"text": "{tooltip}"}
            )
        ]
    )
    st.pydeck_chart(emergency_deck)
    st.info("Emergency fallback map displayed. The main renderer encountered an error.")

st.markdown("---")

# -----------------------------------------------------------------------------
# TWO-COLUMN LAYOUT
# -----------------------------------------------------------------------------
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Top Hotspots")
    if not hour_data.empty and 'ccis' in hour_data.columns:
        top_hotspots = hour_data.nlargest(5, 'ccis')
        if 'location' in top_hotspots.columns:
            st.dataframe(
                top_hotspots[['location', 'ccis', 'status']].rename(
                    columns={'location': 'Location', 'ccis': 'CCIS', 'status': 'Status'}
                ),
                use_container_width=True
            )
        else:
            st.dataframe(top_hotspots[['h3_cell', 'ccis', 'status']], use_container_width=True)
    else:
        st.info("No hotspots detected.")

with col_right:
    st.subheader("Zone Details")
    if not hour_data.empty and 'h3_cell' in hour_data.columns:
        zone_list = hour_data['h3_cell'].unique()
        selected_zone = st.selectbox("Select a zone to inspect:", zone_list)
        if selected_zone:
            zone_row = hour_data[hour_data['h3_cell'] == selected_zone].iloc[0]
            location_name = zone_row.get('location', selected_zone)

            st.markdown(f"""
            <div style="background-color:#1A1C23; padding:15px; border-radius:10px; border-left:5px solid {zone_row['color']}; margin-bottom:10px;">
                <p><strong>Full Location:</strong> {location_name}</p>
                <p><strong>Zone ID:</strong> {zone_row['h3_cell']}</p>
                <p><strong>CCIS:</strong> {zone_row['ccis']:.1f}</p>
                <p><strong>Status:</strong> {zone_row['status'].upper()}</p>
                <p><strong>Recommended Action:</strong> {
                    "Immediate dispatch" if zone_row['ccis'] > 6 else
                    "Monitor closely" if zone_row['ccis'] > 3 else
                    "Routine patrol"
                }</p>
            </div>
            """, unsafe_allow_html=True)

            try:
                from utils.explainer import generate_explanation
                pred = None
                if 'predicted' in ccis_df.columns:
                    pred_row = ccis_df[(ccis_df['h3_cell'] == selected_zone) & (ccis_df['hour'] == hour)]
                    pred = pred_row['predicted'].iloc[0] if not pred_row.empty else None
                explanation = generate_explanation(selected_zone, hour, ccis_df, pred)
                st.markdown("---")
                st.subheader("Why this zone?")
                st.info(explanation)
            except Exception:
                pass

            if persona == "BTP Mode":
                if st.button("Dispatch Cobra Team", key="dispatch_btn"):
                    st.success(f"Cobra team dispatched to zone {selected_zone}!")
            else:
                if st.button("Reroute Fleet", key="reroute_btn"):
                    st.success(f"Fleet rerouted around zone {selected_zone}.")
    else:
        st.info("No zone data available.")

st.markdown("---")

# -----------------------------------------------------------------------------
# PERSONA-SPECIFIC DETAILS
# -----------------------------------------------------------------------------
if persona == "BTP Mode":
    st.subheader("BTP Enforcement Summary")
    if not hour_data.empty:
        critical_zones = hour_data[hour_data['status'] == 'critical']
        if not critical_zones.empty:
            st.warning(f"Critical zones ({len(critical_zones)}) require immediate action:")
            for idx, row in critical_zones.iterrows():
                loc = row.get('location', row['h3_cell'])
                st.write(f"- {loc} (CCIS: {row['ccis']:.1f})")
        else:
            st.success("No critical zones at this hour.")
    else:
        st.info("No data for this hour.")

    st.markdown("---")
    st.subheader("Download Report")
    if st.button("Generate PDF Enforcement Report", key="pdf_btn"):
        try:
            from utils.report_generator import generate_enforcement_report
            from datetime import datetime
            hotspots = hour_data.nlargest(10, 'ccis')
            if not hotspots.empty:
                pdf_bytes = generate_enforcement_report(
                    ccis_df, hotspots,
                    date_str=datetime.now().strftime("%B %d, %Y")
                )
                st.download_button(
                    label="Download Report",
                    data=pdf_bytes,
                    file_name=f"enforcement_report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                    mime="application/pdf"
                )
            else:
                st.warning("No hotspots to report.")
        except Exception as e:
            st.error(f"Error generating report: {e}")

else:  # Flipkart Mode
    st.subheader("Flipkart Logistics Optimization")
    if not hour_data.empty:
        avg_ccis = hour_data['ccis'].mean()
        est_delay_min = avg_ccis * 2.5
        total_affected = len(hour_data) * 5
        cost_per_delivery = est_delay_min * 0.5
        total_cost = total_affected * cost_per_delivery

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Avg Delay per Vehicle", f"{est_delay_min:.1f} min")
        with col2:
            st.metric("Deliveries Affected", f"{total_affected:,}")
        with col3:
            st.metric("Estimated Cost", f"₹{total_cost:,.0f}")

        if st.button("View Detailed Cost Savings"):
            st.info(f"Rerouting around the top 5 hotspots could save approximately ₹{total_cost*0.3:,.0f} per day.")

        st.markdown("---")
        st.subheader("Fleet Route Optimizer")
        st.caption("Select start and end locations to see optimized routes.")

        locations = {
            "MG Road": (12.9716, 77.5946),
            "Indiranagar": (12.9783, 77.6408),
            "Koramangala": (12.9279, 77.6279),
            "Whitefield": (12.9698, 77.7500),
            "Hebbal": (13.0354, 77.5970),
            "Electronic City": (12.8399, 77.6770),
            "Jayanagar": (12.9323, 77.5802),
            "Yelahanka": (13.1007, 77.5883)
        }

        col_start, col_end = st.columns(2)
        with col_start:
            start_loc = st.selectbox("Start Location", list(locations.keys()), key="start")
        with col_end:
            end_loc = st.selectbox("Destination", list(locations.keys()), key="end")

        if st.button("Plan Optimal Route", key="route_btn"):
            start_coords = locations[start_loc]
            end_coords = locations[end_loc]

            with st.spinner("Calculating route avoiding congestion zones..."):
                try:
                    from utils.route_planner import download_bengaluru_graph, calculate_route
                    G = download_bengaluru_graph()
                    std_route, std_path = calculate_route(
                        G, start_coords[0], start_coords[1], end_coords[0], end_coords[1]
                    )
                    if not ccis_df.empty:
                        opt_route, opt_path = calculate_route(
                            G, start_coords[0], start_coords[1], end_coords[0], end_coords[1],
                            ccis_df, hour
                        )
                    else:
                        opt_route = std_route

                    st.session_state['std_route'] = std_route
                    st.session_state['opt_route'] = opt_route
                    st.session_state['start_coords'] = start_coords
                    st.session_state['end_coords'] = end_coords
                    st.success(f"Routes calculated! Standard: {len(std_route)} points, Optimized: {len(opt_route)} points.")

                except Exception as e:
                    st.error(f"Route error: {e}")

        with st.expander("Route Status", expanded=True):
            if 'std_route' in st.session_state and st.session_state['std_route']:
                st.success(f"Standard route loaded ({len(st.session_state['std_route'])} points).")
            else:
                st.warning("No standard route calculated yet. Click 'Plan Optimal Route'.")
            if 'opt_route' in st.session_state and st.session_state['opt_route']:
                st.success(f"Optimized route loaded ({len(st.session_state['opt_route'])} points).")
            else:
                st.warning("No optimized route calculated yet.")
    else:
        st.info("No data available.")

# -----------------------------------------------------------------------------
# FOOTER
# -----------------------------------------------------------------------------
st.markdown("---")
st.caption("GridLock Zero (c) 2026 | Built for Flipkart GridLock Hackathon | Powered by BTP Data")

# -----------------------------------------------------------------------------
# DEBUG INFO
# -----------------------------------------------------------------------------
with st.sidebar.expander("System Status", expanded=False):
    st.caption(f"CCIS records: {len(ccis_df):,}")
    st.caption(f"Clustered records: {len(clustered_df):,}")
    st.caption(f"Current hour: {hour}:00")
    st.caption(f"Persona: {persona}")
    st.caption("Data files loaded successfully." if not ccis_df.empty else "No data loaded.")
    if not ccis_df.empty:
        st.caption(f"CCIS columns: {list(ccis_df.columns)}")

# --- PREDICTIVE WHAT-IF SIMULATOR INTERFACE SECTION ---
st.markdown("---")
st.subheader("🧪 Strategic Optimization Sandbox Simulator")

sim_col1, sim_col2 = st.columns([1, 2])

with sim_col1:
    st.caption("Adjust prospective tactical assets below:")
    sim_officers = st.slider("Force Size Deployment Footprint", 1, 12, 4)
    sim_duration = st.slider("Force Allocation Duration Window (Hours)", 1, 8, 3)
    run_sim = st.button("▶️ Execute Strategic Scenario Impact Modeling", use_container_width=True)

with sim_col2:
    if run_sim:
        from models.what_if_simulator import WhatIfSimulator

        # Initialize advanced algorithm engine with your loaded data dataframe
        sim_engine = WhatIfSimulator(ccis_df)

        # Grab active grid block cell from your current dataframe records mapping selection
        active_cell = ccis_df['h3_cell'].iloc[0] if not ccis_df.empty else "Global Node"

        # Feed inputs directly into your new advanced simulation algorithm
        results = sim_engine.simulate_enforcement(
            h3_cell=active_cell,
            hour=hour,
            officer_count=sim_officers,
            duration_hours=sim_duration
        )

        st.success(f"✅ Impact Projections Modeled for Cell {active_cell} at {hour}:00")
        c1, c2 = st.columns(2)
        c1.metric("Projected Constraint Relief Rate", f"{results['violation_reduction_pct']}%",
                  delta="Optimization Vector")
        c2.metric("Estimated Commuter-Hours Saved", f"{results['total_hours_saved']} Hrs")
    else:
        st.info("💡 Select potential asset footprints and click execute to render forecasting analytics charts.")