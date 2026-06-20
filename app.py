"""
GridLock Zero - Complete Dashboard
Flipkart GridLock Hackathon 2026
"""
import streamlit as st
import streamlit.components.v1 as components
import json
import pandas as pd
import numpy as np
import pydeck as pdk
from pathlib import Path
import sys

st.set_page_config(
    page_title="GridLock Zero",
    page_icon="\U0001F6A6",
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
    @keyframes ripple-glow {
        0% {
            box-shadow: 0 0 0 0 rgba(155, 81, 224, 0.4);
        }
        70% {
            box-shadow: 0 0 0 10px rgba(155, 81, 224, 0);
        }
        100% {
            box-shadow: 0 0 0 0 rgba(155, 81, 224, 0);
        }
    }
    .cascade-ripple-card {
        background-color: rgba(155, 81, 224, 0.05);
        border: 1px solid #9B51E0;
        border-radius: 8px;
        padding: 12px 15px;
        margin-top: 10px;
        margin-bottom: 15px;
        animation: ripple-glow 2s infinite;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# DATA LOADING
# -----------------------------------------------------------------------------
@st.cache_data
def load_ccis_data_resolution(granularity_label):
    res_map = {
        "City View": 6,
        "Zone View": 8,
        "Street View": 9
    }
    res = res_map.get(granularity_label, 8)
    
    df = None
    if res == 8:
        # Load from pre-calculated CCIS scores if available
        path = Path(__file__).parent / "data" / "processed" / "ccis_with_predictions.csv"
        if not path.exists():
            path = Path(__file__).parent / "data" / "processed" / "ccis_scores.csv"
        if path.exists():
            df = pd.read_csv(path)
            if 'latitude' in df.columns and 'longitude' in df.columns:
                df = df.rename(columns={'latitude': 'lat', 'longitude': 'lon'})
            if 'h3_8' in df.columns and 'h3_cell' not in df.columns:
                df = df.rename(columns={'h3_8': 'h3_cell'})
            if 'location' not in df.columns:
                df['location'] = df['h3_cell']
                
    if df is None:
        try:
            from utils.multi_granularity import recalculate_ccis_resolution
            df = recalculate_ccis_resolution(res)
            if 'latitude' in df.columns and 'longitude' in df.columns:
                df = df.rename(columns={'latitude': 'lat', 'longitude': 'lon'})
            if 'h3_cell' not in df.columns and f'h3_{res}' in df.columns:
                df = df.rename(columns={f'h3_{res}': 'h3_cell'})
            if 'location' not in df.columns:
                df['location'] = df['h3_cell']
        except Exception as e:
            st.error(f"Error loading resolution data: {e}")
            return pd.DataFrame(columns=['h3_cell', 'hour', 'ccis', 'lat', 'lon', 'status', 'color', 'location', 'poi', 'is_anomaly'])
            
    # Run Anomaly Detector to calculate POI and is_anomaly
    try:
        from utils.anomaly_detector import IsolationForestAnomalyDetector
        detector = IsolationForestAnomalyDetector()
        df = detector.fit_predict(df)
    except Exception as e:
        st.warning(f"Could not run anomaly detection: {e}")
        if 'poi' not in df.columns:
            df['poi'] = df['ccis'].clip(0.0, 10.0)
        if 'is_anomaly' not in df.columns:
            df['is_anomaly'] = False
            
    return df

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

day_filter = st.sidebar.selectbox(
    "Day of the Week",
    ["All Days", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
    index=0,
    help="Select a specific day of the week or aggregate all days to spot weekly trends."
)

st.sidebar.markdown("---")

granularity = st.sidebar.selectbox(
    "Zoom Level",
    ["City View", "Zone View", "Street View"],
    index=1
)

ccis_df = load_ccis_data_resolution(granularity)

# Map granularity to numerical zoom levels
zoom_map = {
    "City View": 11,
    "Zone View": 13,
    "Street View": 16
}
zoom_level = zoom_map.get(granularity, 13)

st.sidebar.markdown("---")

overlay_mode = st.sidebar.selectbox(
    "Map Overlay Style",
    ["Congestion Impact (CCIS)", "Violation Density", "Dual View (Color=CCIS, Size=Violations)"],
    index=2,
    help="Dual view colors markers by CCIS severity and scales size by violation count."
)

st.sidebar.markdown("---")
st.sidebar.caption("Data source: BTP GridLock Dataset")
st.sidebar.caption(f"Records loaded: {len(ccis_df):,}")

# -----------------------------------------------------------------------------
# FILTER DATA
# -----------------------------------------------------------------------------
day_map = {
    "Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3,
    "Friday": 4, "Saturday": 5, "Sunday": 6
}

if day_filter == "All Days":
    hour_data = ccis_df[ccis_df['hour'] == hour].copy()
    if not hour_data.empty:
        agg_config = {
            'lat': 'first',
            'lon': 'first',
            'location': 'first'
        }
        if 'ccis' in hour_data.columns:
            agg_config['ccis'] = 'mean'
        if 'violation_count' in hour_data.columns:
            agg_config['violation_count'] = 'mean'
        if 'speed_drop' in hour_data.columns:
            agg_config['speed_drop'] = 'mean'
            
        hour_data = hour_data.groupby('h3_cell').agg(agg_config).reset_index()
        
        if 'ccis' in hour_data.columns:
            hour_data['status'] = 'green'
            hour_data.loc[hour_data['ccis'] > 6, 'status'] = 'critical'
            hour_data.loc[(hour_data['ccis'] > 3) & (hour_data['ccis'] <= 6), 'status'] = 'monitor'
            color_map = {
                'critical': '#FF4B4B',
                'monitor': '#FFA500',
                'green': '#00CC66'
            }
            hour_data['color'] = hour_data['status'].map(color_map)
else:
    day_val = day_map.get(day_filter, 0)
    if 'day_of_week' in ccis_df.columns:
        hour_data = ccis_df[(ccis_df['hour'] == hour) & (ccis_df['day_of_week'] == day_val)].copy()
    else:
        hour_data = ccis_df[ccis_df['hour'] == hour].copy()

# -----------------------------------------------------------------------------
# MAIN CONTENT
# -----------------------------------------------------------------------------
st.title("GridLock Zero")
st.caption("Real-time Parking Congestion Intelligence & Dispatch System")

if persona == "BTP Mode":
    st.info("BTP Mode - Enforcement priorities, dispatch recommendations, and hotspot management.")
else:
    st.info("Flipkart Mode - Delivery routing optimization, cost savings, and zone avoidance.")

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
# MAP SECTION
# -----------------------------------------------------------------------------
st.subheader(f"\U0001F4CD Congestion Heatmap \u2014 {granularity}")

# Prepare data points
data_points = []
if not hour_data.empty and 'lat' in hour_data.columns and 'lon' in hour_data.columns:
    for _, row in hour_data.iterrows():
        data_points.append({
            'lat': float(row['lat']),
            'lon': float(row['lon']),
            'ccis': float(row['ccis']),
            'violation_count': int(row.get('violation_count', 0)),
            'speed_drop': float(row.get('speed_drop', 0.0)),
            'location': str(row.get('location', 'Unknown')),
            'poi': float(row.get('poi', 0.0)),
            'is_anomaly': bool(row.get('is_anomaly', False))
        })

# Include Cascade Points if present in session state
if st.session_state.get('cascade_points'):
    for pt in st.session_state['cascade_points']:
        if pt['step'] > 0:
            data_points.append({
                'lat': float(pt['lat']),
                'lon': float(pt['lon']),
                'ccis': float(pt['propagated_ccis']),
                'violation_count': 0,
                'speed_drop': 0.0,
                'location': str(pt['location']),
                'poi': 0.0,
                'is_anomaly': False,
                'is_cascade': True,
                'cascade_step': int(pt['step'])
            })

if not data_points:
    data_points = [
        {'lat': 12.9716, 'lon': 77.5946, 'ccis': 7.8, 'violation_count': 12, 'speed_drop': 4.5, 'location': 'MG Road'},
        {'lat': 12.9783, 'lon': 77.6408, 'ccis': 6.9, 'violation_count': 8, 'speed_drop': 3.1, 'location': 'Indiranagar'},
        {'lat': 12.9279, 'lon': 77.6279, 'ccis': 5.4, 'violation_count': 5, 'speed_drop': 2.0, 'location': 'Koramangala'},
    ]

# Prepare route data
std_route = st.session_state.get('std_route', [])
opt_route = st.session_state.get('opt_route', [])
if std_route and isinstance(std_route, list) and len(std_route) > 0:
    pass
else:
    std_route = []
if opt_route and isinstance(opt_route, list) and len(opt_route) > 0:
    pass
else:
    opt_route = []

vehicle_type = st.session_state.get('vehicle_type', 'Car')

# Display map
try:
    html_path = Path(__file__).parent / "map_template.html"
    if html_path.exists():
        with open(html_path, 'r', encoding='utf-8') as f:
            map_html = f.read()

        # Map Overlay Mode replacement
        overlay_mode_map = {
            "Congestion Impact (CCIS)": "ccis",
            "Violation Density": "violations",
            "Dual View (Color=CCIS, Size=Violations)": "dual"
        }
        overlay_mode_value = overlay_mode_map.get(overlay_mode, "dual")

        # Replace placeholders
        map_html = map_html.replace(
            'var dataPoints = {{ data_points|safe }};',
            f'var dataPoints = {json.dumps(data_points)};'
        )
        map_html = map_html.replace(
            '{{ overlay_mode }}',
            f'"{overlay_mode_value}"'
        )
        map_html = map_html.replace(
            'var stdRoute = {{ std_route|safe }};',
            f'var stdRoute = {json.dumps(std_route)};'
        )
        map_html = map_html.replace(
            'var optRoute = {{ opt_route|safe }};',
            f'var optRoute = {json.dumps(opt_route)};'
        )
        map_html = map_html.replace(
            '{{ vehicle_type }}',
            vehicle_type
        )
        map_html = map_html.replace(
            '{{ zoom_level }}',
            str(zoom_level)
        )

        components.html(map_html, height=650)
        st.caption("\U0001F4CD Map with CCIS data points. Hover for details.")
    else:
        st.error("map_template.html not found.")
except Exception as e:
    st.error(f"Map error: {e}")
    # Fallback to Pydeck
    deck, map_data, _ = render_map(hour_data, clustered_df, hour, persona, zoom_level)
    st.pydeck_chart(deck)

# -----------------------------------------------------------------------------
# RENDER MAP FUNCTION (Fallback - Pydeck)
# -----------------------------------------------------------------------------
def render_map(hour_data, clustered_df, hour, persona, zoom_level=11):
    """
    Constructs a Pydeck map. Uses real data if available, otherwise fallback demo.
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
            zoom=zoom_level,
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
st.markdown("---")

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# TWO-COLUMN LAYOUT (ENFORCEMENT PRIORITIZATION ENGINE)
# -----------------------------------------------------------------------------
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("\U0001F5A5\ufe0f Enforcement Priority Queue (EPQ)")
    if not hour_data.empty:
        # Calculate dynamic priority score
        hour_data['priority_score'] = (hour_data['ccis'] * 0.7) + (hour_data.get('violation_count', 0) * 0.3)
        top_hotspots = hour_data.nlargest(10, 'priority_score')
        
        display_cols = ['location', 'priority_score', 'violation_count', 'speed_drop', 'ccis']
        display_names = {
            'location': 'Location',
            'priority_score': 'Priority Score',
            'violation_count': 'Violations (Active)',
            'speed_drop': 'Speed Drop (km/h)',
            'ccis': 'CCIS Score'
        }
        df_to_show = top_hotspots[display_cols].rename(columns=display_names)
        st.dataframe(df_to_show, use_container_width=True)
    else:
        st.info("No hotspots detected.")

with col_right:
    st.subheader("\U0001F4CB Zone Details")
    if not hour_data.empty and 'h3_cell' in hour_data.columns:
        if 'priority_score' not in hour_data.columns:
            hour_data['priority_score'] = (hour_data['ccis'] * 0.7) + (hour_data.get('violation_count', 0) * 0.3)
        sorted_zones = hour_data.sort_values(by='priority_score', ascending=False)
        
        zone_options = {}
        for _, r in sorted_zones.iterrows():
            loc_label = f"{r.get('location', r['h3_cell'])[:35]} (Priority: {r['priority_score']:.1f})"
            zone_options[loc_label] = r['h3_cell']
            
        selected_label = st.selectbox("Select a prioritized zone to inspect:", list(zone_options.keys()))
        if selected_label:
            selected_zone = zone_options.get(selected_label)
            st.session_state['selected_zone'] = selected_zone
            zone_row = hour_data[hour_data['h3_cell'] == selected_zone].iloc[0]
            location_name = zone_row.get('location', selected_zone)

            loc_lower = location_name.lower()
            if 'metro' in loc_lower or 'station' in loc_lower:
                risk_profile = "\U0001F687 High Metro Station Spillover Risk"
            elif 'market' in loc_lower or 'mall' in loc_lower or 'commercial' in loc_lower or 'layout' in loc_lower:
                risk_profile = "\U0001F6CD\ufe0f High Commercial Density Spillover Risk"
            elif 'highway' in loc_lower or 'road' in loc_lower or 'junction' in loc_lower:
                risk_profile = "\U0001F6E3\ufe0f Carriageway & Intersection Choking Risk"
            else:
                risk_profile = "\U0001F4CD Localized Spillover / Event Risk"

            rec_action = (
                "&#128680; Immediate proactive dispatch & enforcement" if zone_row['ccis'] > 6 else
                "&#128993; Monitor closely / patrol warning" if zone_row['ccis'] > 3 else
                "&#9989; Routine patrol check"
            )

            # Anomaly Detection columns
            poi_score = zone_row.get('poi', 0.0)
            is_anomaly = zone_row.get('is_anomaly', False)
            
            anomaly_html = ""
            if is_anomaly:
                anomaly_html = f"""
                <div style="background-color: rgba(255, 75, 75, 0.1); border: 1px solid #FF4B4B; padding: 10px; border-radius: 8px; margin-top: 10px;">
                    <span style="color: #FF4B4B; font-weight: bold;">&#9888; ANOMALY ALERT:</span> 
                    Statistically anomalous deviation from historical baseline activity detected at this hour!
                </div>
                """

            st.markdown(f"""
            <div style="background-color:#1A1C23; padding:15px; border-radius:10px; border-left:5px solid {zone_row['color']}; margin-bottom:10px;">
                <p style="margin: 4px 0; color: #FFF;"><strong>&#128205; Full Location:</strong> {location_name}</p>
                <p style="margin: 4px 0; color: #DDD;"><strong>&#127380; Zone ID:</strong> {zone_row['h3_cell']}</p>
                <p style="margin: 4px 0; color: #DDD;"><strong>&#9888; Illegal Parking Violations:</strong> {int(zone_row.get('violation_count', 0))} active cases</p>
                <p style="margin: 4px 0; color: #DDD;"><strong>&#128201; Quantified Speed Drop:</strong> {zone_row.get('speed_drop', 0.0):.1f} km/h reduction</p>
                <p style="margin: 4px 0; color: #DDD;"><strong>&#128680; Congestion Index (CCIS):</strong> {zone_row['ccis']:.1f}</p>
                <p style="margin: 4px 0; color: #DDD;"><strong>&#128160; Parking Obstruction Index (POI):</strong> {poi_score:.1f} / 10</p>
                <p style="margin: 4px 0; color: #DDD;"><strong>&#127919; Spillover Risk Profile:</strong> {risk_profile}</p>
                <p style="margin: 4px 0; color: #FFF;"><strong>&#9889; Recommended Action:</strong> {rec_action}</p>
                {anomaly_html}
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
                st.subheader("\U0001F4A1 Why this zone?")
                st.info(explanation)
            except Exception:
                pass

            # Historical Trend Panel (GAMMA Day 4)
            try:
                from utils.historical_trends import get_historical_trends
                st.markdown("---")
                st.subheader("\U0001F4C8 Historical CCIS Trend (Last 14 Days)")
                trends_df = get_historical_trends(ccis_df, selected_zone, days=14)
                if not trends_df.empty:
                    st.line_chart(trends_df, x='Date', y='CCIS', color='#FF4B4B', height=200)
                else:
                    st.caption("No historical trend data available.")
            except Exception as e:
                st.warning(f"Could not load historical trend: {e}")

            # Cascade Propagation Model (GAMMA Day 2)
            st.markdown("---")
            st.subheader("\U0001F50A Congestion Cascade & Propagation")
            show_cascade = st.checkbox("Enable Spatial Cascade Propagation", value=False, help="Predict how congestion spreads from this cell to neighboring cells.")
            
            if show_cascade:
                cascade_steps = st.slider("Propagation Depth (Hops)", min_value=1, max_value=4, value=2, step=1)
                cascade_attenuation = st.slider("Attenuation Factor (decay per hop)", min_value=0.1, max_value=0.9, value=0.6, step=0.1)
                
                # Cascade Ripple Notification UI Block (GAMMA Day 4 spec)
                st.markdown(f"""
                <div class="cascade-ripple-card">
                    <h5 style="margin: 0 0 5px 0; color: #9B51E0;">&#128266; Congestion Cascade Ripple Active</h5>
                    <p style="margin: 0; font-size: 0.9em; color: #DDD;">
                        Modeling spillovers from <b>{location_name}</b>. Neighboring cells within <b>{cascade_steps} hop(s)</b> are monitored with <b>{cascade_attenuation} decay rate</b>.
                    </p>
                </div>
                """, unsafe_allow_html=True)
                
                try:
                    from models.cascade_propagator import CascadePropagator
                    propagator = CascadePropagator(ccis_df)
                    cascade_list = propagator.predict_propagation(selected_zone, hour, steps=cascade_steps, attenuation=cascade_attenuation)
                    
                    if cascade_list:
                        # Convert to DataFrame
                        cascade_df = pd.DataFrame(cascade_list)
                        
                        # Store in session state for leaflet overlay
                        st.session_state['cascade_points'] = cascade_list
                        
                        # Show interactive table of affected cells (sorting by step, CCIS)
                        cascade_df_sorted = cascade_df.sort_values(by=['step', 'propagated_ccis'], ascending=[True, False])
                        
                        # Render spillover warning if there is any critical neighbor
                        critical_spillovers = len(cascade_df_sorted[(cascade_df_sorted['risk_level'] == 'Critical Spillover') & (cascade_df_sorted['step'] > 0)])
                        if critical_spillovers > 0:
                            st.warning(f"\u26A0\ufe0f **Spillover Alert:** {critical_spillovers} neighboring cell(s) at critical risk of congestion spread.")
                            
                        display_cascade_cols = ['step', 'location', 'propagated_ccis', 'risk_level']
                        display_cascade_names = {
                            'step': 'Hop Distance',
                            'location': 'Neighboring Location',
                            'propagated_ccis': 'Predicted CCIS',
                            'risk_level': 'Spillover Risk Level'
                        }
                        
                        st.dataframe(
                            cascade_df_sorted[display_cascade_cols].rename(columns=display_cascade_names),
                            use_container_width=True
                        )
                    else:
                        st.info("No cascade neighbors detected.")
                except Exception as e:
                    st.error(f"Error calculating cascade: {e}")
            else:
                if 'cascade_points' in st.session_state:
                    del st.session_state['cascade_points']

            if persona == "BTP Mode":
                if st.button("\U0001F6A8 Dispatch Proactive Enforcement Cobra Team", key="dispatch_btn"):
                    st.success(f"\U0001F6A8 Cobra team successfully dispatched to zone {selected_zone}! Priority enforcement action initiated.")
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
    st.subheader("\U0001F4C8 Traffic Flow Impact Quantification & Correlation")
    st.caption("AI-modeled interaction between active illegal parking violations and traffic flow velocity degradation (speed drop).")
    
    if not hour_data.empty:
        scatter_df = hour_data[['violation_count', 'speed_drop', 'location']].dropna().copy()
        scatter_df.columns = ['Active Violations', 'Speed Drop (km/h)', 'Location']
        
        st.scatter_chart(
            scatter_df,
            x='Active Violations',
            y='Speed Drop (km/h)',
            color='#FF4B4B',
            size='Active Violations',
            use_container_width=True
        )
        st.info("\U0001F4DD **Analytical Insight:** Clusters in the upper-right indicate choke points near metro stations and commercial hubs where illegal parking directly degrades carriageway speed by up to 1.0 km/h per violation.")
    else:
        st.info("No correlation data available.")

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
            st.metric("Estimated Cost", f"\u20B9{total_cost:,.0f}")

        if st.button("View Detailed Cost Savings"):
            st.info(f"Rerouting around the top 5 hotspots could save approximately \u20B9{total_cost*0.3:,.0f} per day.")

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

        # ---- VEHICLE TYPE SELECTOR ----
        vehicle_type = st.radio(
            "\U0001F697 Select Vehicle Type",
            ["Car", "Bike"],
            index=0,
            horizontal=True,
            help="Car = 25 km/h avg speed, Bike = 35 km/h avg speed"
        )
        if vehicle_type == "Car":
            avg_speed_kmh = 25
            vehicle_icon = "\U0001F697"
        else:
            avg_speed_kmh = 35
            vehicle_icon = "\U0001F3CD\uFE0F"

        st.caption(f"Using {vehicle_icon} {vehicle_type} speed: {avg_speed_kmh} km/h (city average)")
        st.markdown("---")

        if st.button("\U0001F680 Plan Optimal Route", key="route_btn"):
            start_coords = locations[start_loc]
            end_coords = locations[end_loc]

            with st.spinner("Calculating route avoiding congestion zones..."):
                try:
                    from utils.route_planner import download_bengaluru_graph, calculate_route, get_route_distance, get_route_streets
                    G = download_bengaluru_graph()
                    std_route, std_path = calculate_route(G, start_coords[0], start_coords[1], end_coords[0], end_coords[1])
                    if not ccis_df.empty:
                        opt_route, opt_path = calculate_route(G, start_coords[0], start_coords[1], end_coords[0], end_coords[1], ccis_df, hour)
                    else:
                        opt_route = std_route
                        opt_path = std_path

                    # Get actual distances
                    std_distance_m = get_route_distance(G, std_path)
                    opt_distance_m = get_route_distance(G, opt_path)

                    # Get street names
                    std_streets = get_route_streets(G, std_path)
                    opt_streets = get_route_streets(G, opt_path)

                    # Calculate times
                    std_time_min = (std_distance_m / 1000) / avg_speed_kmh * 60
                    opt_time_min = (opt_distance_m / 1000) / avg_speed_kmh * 60
                    time_saved = std_time_min - opt_time_min

                    # Store in session state
                    st.session_state['std_route'] = std_route
                    st.session_state['opt_route'] = opt_route
                    st.session_state['start_coords'] = start_coords
                    st.session_state['end_coords'] = end_coords
                    st.session_state['std_distance_m'] = std_distance_m
                    st.session_state['opt_distance_m'] = opt_distance_m
                    st.session_state['std_time_min'] = std_time_min
                    st.session_state['opt_time_min'] = opt_time_min
                    st.session_state['time_saved'] = time_saved
                    st.session_state['vehicle_type'] = vehicle_type
                    st.session_state['vehicle_icon'] = vehicle_icon
                    st.session_state['std_streets'] = std_streets
                    st.session_state['opt_streets'] = opt_streets
                    st.session_state['route_calculated'] = True
                    st.rerun()
                except Exception as e:
                    st.error(f"\u274C Route error: {e}")

        # ---- ROUTE COMPARISON DISPLAY ----
        if 'std_route' in st.session_state and st.session_state['std_route']:
            if st.session_state.get('route_calculated'):
                st.success("\U0001F680 Optimal Route successfully planned! The map has been updated.")
                st.session_state['route_calculated'] = False

            std_distance_m = st.session_state.get('std_distance_m', 0)
            opt_distance_m = st.session_state.get('opt_distance_m', 0)
            std_distance_km = std_distance_m / 1000.0
            opt_distance_km = opt_distance_m / 1000.0

            # Speeds: Car=25 km/h, Bike=35 km/h
            std_time_car = (std_distance_km / 25) * 60
            opt_time_car = (opt_distance_km / 25) * 60
            time_saved_car = std_time_car - opt_time_car

            std_time_bike = (std_distance_km / 35) * 60
            opt_time_bike = (opt_distance_km / 35) * 60
            time_saved_bike = std_time_bike - opt_time_bike

            vehicle_icon_display = st.session_state.get('vehicle_icon', '\U0001F697')
            vehicle_type_display = st.session_state.get('vehicle_type', 'Car')

            car_color = '#00CC66' if time_saved_car > 0 else '#DDD'
            car_saved_text = f"Time Saved: {time_saved_car:.1f} mins" if time_saved_car > 0 else "No Time Saved"

            bike_color = '#00CC66' if time_saved_bike > 0 else '#DDD'
            bike_saved_text = f"Time Saved: {time_saved_bike:.1f} mins" if time_saved_bike > 0 else "No Time Saved"

            car_opt_time_str = f"{opt_time_car:.1f} mins"
            car_std_time_str = f"{std_time_car:.1f} mins"
            car_opt_dist_str = f"{opt_distance_km:.2f} km"
            car_std_dist_str = f"{std_distance_km:.2f} km"

            bike_opt_time_str = f"{opt_time_bike:.1f} mins"
            bike_std_time_str = f"{std_time_bike:.1f} mins"
            bike_opt_dist_str = f"{opt_distance_km:.2f} km"
            bike_std_dist_str = f"{std_distance_km:.2f} km"

            st.markdown("---")
            st.subheader("\u23F1\ufe0f Travel Time Comparison")

            # Draw side-by-side travel times cards
            col_car, col_bike = st.columns(2)

            with col_car:
                st.markdown(
                    f"""
                    <div style="background-color: #1A1C23; padding: 15px; border-radius: 10px; border: 1px solid #333; margin-bottom: 10px;">
                        <h4 style="margin: 0 0 10px 0;">&#128663; Car Mode (25 km/h)</h4>
                        <p style="margin: 4px 0; color: #DDD;"><b>Optimized Time:</b> <span style="color: #00CC66; font-size: 1.1em; font-weight: bold;">{car_opt_time_str}</span></p>
                        <p style="margin: 4px 0; color: #BBB;">Standard Time: {car_std_time_str}</p>
                        <p style="margin: 4px 0; color: #999; font-size: 0.9em;">Distance: {car_opt_dist_str} (Standard: {car_std_dist_str})</p>
                        <p style="margin: 8px 0 0 0; color: {car_color}; font-weight: bold;">
                            &#9201; {car_saved_text}
                        </p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            with col_bike:
                st.markdown(
                    f"""
                    <div style="background-color: #1A1C23; padding: 15px; border-radius: 10px; border: 1px solid #333; margin-bottom: 10px;">
                        <h4 style="margin: 0 0 10px 0;">&#127949; Bike Mode (35 km/h)</h4>
                        <p style="margin: 4px 0; color: #DDD;"><b>Optimized Time:</b> <span style="color: #00CC66; font-size: 1.1em; font-weight: bold;">{bike_opt_time_str}</span></p>
                        <p style="margin: 4px 0; color: #BBB;">Standard Time: {bike_std_time_str}</p>
                        <p style="margin: 4px 0; color: #999; font-size: 0.9em;">Distance: {bike_opt_dist_str} (Standard: {bike_std_dist_str})</p>
                        <p style="margin: 8px 0 0 0; color: {bike_color}; font-weight: bold;">
                            &#9201; {bike_saved_text}
                        </p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            st.markdown("### \U0001F5FA\ufe0f Route Street Summaries")
            std_streets = st.session_state.get('std_streets', [])
            opt_streets = st.session_state.get('opt_streets', [])

            st.markdown(
                f"""
                <div style="background-color: #1A1C23; padding: 15px; border-radius: 10px; border: 1px solid #333; margin-bottom: 10px;">
                    <p style="margin: 5px 0;">&#128309; <b>Standard Route:</b> via {', '.join(std_streets) if std_streets else 'Direct/Unnamed roads'}</p>
                    <p style="margin: 5px 0;">&#128994; <b>Optimized Route:</b> via {', '.join(opt_streets) if opt_streets else 'Direct/Unnamed roads'}</p>
                </div>
                """,
                unsafe_allow_html=True
            )

            fuel_saved = (std_distance_m - opt_distance_m) / 1000 * 0.08
            if fuel_saved > 0:
                st.info(f"\U0001F4B0 **Cost & Fuel Savings:** Rerouting around congestion hotspots saves approximately \u20B9{fuel_saved:.2f} per delivery in fuel (estimated at \u20B98/km).")

        with st.expander("\U0001F6A6 Route Status", expanded=True):
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

# --- PREDICTIVE WHAT-IF SIMULATOR INTERFACE SECTION ---
st.markdown("---")
st.subheader("\U0001F9EA Strategic Optimization Sandbox Simulator")

sim_col1, sim_col2 = st.columns([1, 2])

if not hour_data.empty:
    if 'priority_score' not in hour_data.columns:
        hour_data['priority_score'] = (hour_data['ccis'] * 0.7) + (hour_data.get('violation_count', 0) * 0.3)
    sorted_zones = hour_data.sort_values(by='priority_score', ascending=False)
    
    active_cell = st.session_state.get('selected_zone')
    if not active_cell or active_cell not in hour_data['h3_cell'].values:
        active_cell = sorted_zones['h3_cell'].iloc[0]
        
    active_row = hour_data[hour_data['h3_cell'] == active_cell].iloc[0]
    active_location = active_row.get('location', active_cell)
else:
    active_cell = "Global Node"
    active_location = "Global Node"

with sim_col1:
    st.markdown(f"**Target Zone:** {active_location}")
    st.caption("Adjust prospective tactical assets to model real-time impact:")
    sim_officers = st.slider("Force Size Deployment Footprint", 1, 12, 4)
    sim_duration = st.slider("Force Allocation Duration Window (Hours)", 1, 8, 3)

with sim_col2:
    from models.what_if_simulator import WhatIfSimulator
    sim_engine = WhatIfSimulator(ccis_df)
    
    results = sim_engine.simulate_enforcement(
        cell=active_cell,
        hour=hour,
        officers=sim_officers,
        duration=sim_duration
    )

    st.success(f"\u2705 Automated Impact Projections for {active_location[:35]}... at {hour}:00")
    c1, c2 = st.columns(2)
    c1.metric("Projected Constraint Relief Rate", f"{results['violation_reduction_pct']}%",
              delta="Optimization Vector")
    c2.metric("Estimated Commuter-Hours Saved", f"{results['total_hours_saved']} Hrs")

# -----------------------------------------------------------------------------
# FOOTER
# -----------------------------------------------------------------------------
st.markdown("---")
st.caption("GridLock Zero (c) 2026 | Built for Flipkart GridLock Hackathon | Powered by BTP Data")