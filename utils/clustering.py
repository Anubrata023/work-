"""
DBSCAN Clustering for Hotspot Detection
Groups high-CCIS cells into named enforcement zones.
"""
import pandas as pd
import numpy as np
from sklearn.cluster import DBSCAN
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))
PROJECT_ROOT = Path(__file__).parent.parent

def cluster_hotspots(ccis_df, eps=0.005, min_samples=3):
    """
    Cluster cells with CCIS > 3.
    eps is in degrees (approx 0.005 deg ≈ 500m).
    """
    print("Clustering hotspots with DBSCAN...")
    high = ccis_df[ccis_df['ccis'] > 3].copy()

    if len(high) < min_samples:
        high['cluster'] = -1
        print("  Not enough high-CCIS cells.")
        return high

    coords = high[['lat', 'lon']].values
    clustering = DBSCAN(eps=eps, min_samples=min_samples).fit(coords)
    high['cluster'] = clustering.labels_

    n_clusters = len(high[high['cluster'] != -1]['cluster'].unique())
    n_noise = len(high[high['cluster'] == -1])
    print(f"  Found {n_clusters} clusters, {n_noise} noise points.")

    # Compute cluster centroids and average CCIS
    if n_clusters > 0:
        centroids = high[high['cluster'] != -1].groupby('cluster').agg({
            'lat': 'mean',
            'lon': 'mean',
            'ccis': 'mean',
            'h3_cell': 'count'
        }).reset_index()
        centroids.columns = ['cluster', 'centroid_lat', 'centroid_lon', 'avg_ccis', 'cell_count']
        high = high.merge(centroids, on='cluster', how='left')

    return high

if __name__ == "__main__":
    ccis_path = PROJECT_ROOT / "data" / "processed" / "ccis_scores.csv"
    if not ccis_path.exists():
        print("ERROR: ccis_scores.csv not found. Run ccis_engine.py first.")
        sys.exit(1)

    ccis_df = pd.read_csv(ccis_path)
    clustered = cluster_hotspots(ccis_df)

    output_path = PROJECT_ROOT / "data" / "processed" / "clustered_hotspots.csv"
    clustered.to_csv(output_path, index=False)
    print(f"Saved clustered hotspots to {output_path}")