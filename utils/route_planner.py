"""
Route Planner using OSMnx and NetworkX
"""
import osmnx as ox
import networkx as nx
import pandas as pd
import pickle
from pathlib import Path
import sys
import h3

sys.path.append(str(Path(__file__).parent.parent))
PROJECT_ROOT = Path(__file__).parent.parent
GRAPH_CACHE_PATH = PROJECT_ROOT / "models" / "bengaluru_graph.pkl"

def download_bengaluru_graph(force=False):
    if not force and GRAPH_CACHE_PATH.exists():
        print("Loading cached graph...")
        with open(GRAPH_CACHE_PATH, 'rb') as f:
            return pickle.load(f)
    print("Downloading Bengaluru network (2-3 min)...")
    G = ox.graph_from_place("Bengaluru, India", network_type="drive", simplify=True)
    with open(GRAPH_CACHE_PATH, 'wb') as f:
        pickle.dump(G, f)
    return G

def get_nearest_node(G, lat, lon):
    return ox.distance.nearest_nodes(G, lon, lat)

def assign_congestion_weights(G, ccis_df, hour):
    print(f"Assigning congestion weights for hour {hour}:00...")
    hour_ccis = ccis_df[ccis_df['hour'] == hour]
    ccis_dict = dict(zip(hour_ccis['h3_cell'], hour_ccis['ccis']))
    count = 0
    for u, v, data in G.edges(data=True):
        u_lat = G.nodes[u]['y']; u_lon = G.nodes[u]['x']
        v_lat = G.nodes[v]['y']; v_lon = G.nodes[v]['x']
        mid_lat = (u_lat + v_lat) / 2
        mid_lon = (u_lon + v_lon) / 2
        try:
            h3_cell = h3.latlng_to_cell(mid_lat, mid_lon, 8)
        except:
            continue
        ccis = ccis_dict.get(h3_cell, 0)
        base = data.get('length', 100)
        if ccis > 3:
            data['congestion_weight'] = base * (1 + (ccis/3)*5)
        else:
            data['congestion_weight'] = base
        count += 1
    print(f"  Assigned weights to {count} edges.")
    return G

def calculate_route(G, start_lat, start_lon, end_lat, end_lon, ccis_df=None, hour=None):
    start_node = get_nearest_node(G, start_lat, start_lon)
    end_node = get_nearest_node(G, end_lat, end_lon)
    if ccis_df is not None and hour is not None:
        print("Calculating congestion-aware route...")
        G = assign_congestion_weights(G, ccis_df, hour)
        try:
            path = nx.shortest_path(G, start_node, end_node, weight='congestion_weight')
        except nx.NetworkXNoPath:
            print("  No path, using length.")
            path = nx.shortest_path(G, start_node, end_node, weight='length')
    else:
        print("Calculating standard shortest path...")
        path = nx.shortest_path(G, start_node, end_node, weight='length')
    coords = [(G.nodes[n]['y'], G.nodes[n]['x']) for n in path]
    return coords, path

# -----------------------------------------------------------------------------
# ✅ NEW FUNCTION: Get total distance of a route path
# -----------------------------------------------------------------------------
def get_route_distance(G, path):
    """
    Calculate the total distance (in meters) of a route path.
    """
    total_distance = 0
    for i in range(len(path) - 1):
        u = path[i]
        v = path[i + 1]
        edge_data = G.get_edge_data(u, v)
        if edge_data:
            # Edge data may have multiple keys (for parallel roads)
            if 0 in edge_data:
                total_distance += edge_data[0].get('length', 0)
            else:
                first_key = list(edge_data.keys())[0]
                total_distance += edge_data[first_key].get('length', 0)
    return total_distance

def get_route_streets(G, path):
    """
    Get unique street names traversed by the path, maintaining order.
    """
    streets = []
    for i in range(len(path) - 1):
        u = path[i]
        v = path[i + 1]
        edge_data = G.get_edge_data(u, v)
        if edge_data:
            name = None
            if 0 in edge_data:
                name = edge_data[0].get('name')
            else:
                first_key = list(edge_data.keys())[0]
                name = edge_data[first_key].get('name')
            
            if name:
                if isinstance(name, list):
                    streets.extend(name)
                else:
                    streets.append(name)
    
    unique_streets = []
    for s in streets:
        if isinstance(s, str) and s not in unique_streets:
            unique_streets.append(s)
    return unique_streets

if __name__ == "__main__":
    G = download_bengaluru_graph()
    start = (12.9716, 77.5946)
    end = (12.9783, 77.6408)
    ccis_path = PROJECT_ROOT / "data" / "processed" / "ccis_scores.csv"
    if ccis_path.exists():
        ccis_df = pd.read_csv(ccis_path)
        route, path = calculate_route(G, start[0], start[1], end[0], end[1], ccis_df, hour=18)
        print(f"Route has {len(route)} points.")
    else:
        route, path = calculate_route(G, start[0], start[1], end[0], end[1])
        print(f"Route has {len(route)} points.")