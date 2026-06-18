"""
CCIS (Causal Congestion Impact Score) Engine
Computes CCIS = violation_count * speed_drop_percentage
Includes location name, lat, lon, status, and color.
"""
import pandas as pd
import numpy as np
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))
PROJECT_ROOT = Path(__file__).parent.parent

def calculate_ccis(processed_df, baseline_df):
    """
    Merge processed data with baseline and compute CCIS per (h3_cell, hour).
    Returns DataFrame with columns:
        h3_cell, hour, violation_count, lat, lon, location,
        baseline_count, speed_drop, ccis, status, color
    """
    print("Calculating CCIS scores...")

    # Aggregate processed data by h3_8 and hour
    # Include location, first lat/lon
    agg = processed_df.groupby(['h3_8', 'hour']).agg({
        'latitude': ['count', 'first'],
        'longitude': 'first',
        'location': 'first'
    }).reset_index()

    # Flatten column names
    agg.columns = ['h3_cell', 'hour', 'violation_count', 'lat', 'lon', 'location']

    # Merge with baseline activity (already has baseline_count per cell/hour)
    merged = agg.merge(baseline_df, on=['h3_cell', 'hour'], how='left')

    # Fill missing baseline_count with global average
    global_avg = baseline_df['baseline_count'].mean()
    merged['baseline_count'] = merged['baseline_count'].fillna(global_avg)

    # Speed drop: (violations - baseline) / baseline, capped between 0 and 1
    merged['speed_drop'] = (merged['violation_count'] - merged['baseline_count']) / merged['baseline_count']
    merged['speed_drop'] = merged['speed_drop'].clip(lower=0, upper=1)

    # CCIS formula
    merged['ccis'] = merged['violation_count'] * merged['speed_drop']
    merged['ccis'] = merged['ccis'].round(2)

    # Status and color coding
    merged['status'] = 'green'
    merged.loc[merged['ccis'] > 6, 'status'] = 'critical'
    merged.loc[(merged['ccis'] > 3) & (merged['ccis'] <= 6), 'status'] = 'monitor'

    color_map = {
        'critical': '#FF4B4B',
        'monitor': '#FFA500',
        'green': '#00CC66'
    }
    merged['color'] = merged['status'].map(color_map)

    return merged

if __name__ == "__main__":
    processed_path = PROJECT_ROOT / "data" / "processed" / "processed_data.csv"
    baseline_path = PROJECT_ROOT / "data" / "processed" / "baseline_activity.csv"

    if not processed_path.exists():
        print("ERROR: processed_data.csv not found. Run h3_indexer.py first.")
        sys.exit(1)
    if not baseline_path.exists():
        print("ERROR: baseline_activity.csv not found. Run h3_indexer.py first.")
        sys.exit(1)

    processed_df = pd.read_csv(processed_path)
    baseline_df = pd.read_csv(baseline_path)

    print(f"Loaded processed data: {len(processed_df):,} rows")
    print(f"Loaded baseline data: {len(baseline_df):,} rows")

    ccis_df = calculate_ccis(processed_df, baseline_df)

    output_path = PROJECT_ROOT / "data" / "processed" / "ccis_scores.csv"
    ccis_df.to_csv(output_path, index=False)
    print(f"Saved CCIS scores to {output_path}")

    # Summary statistics
    critical = len(ccis_df[ccis_df['status'] == 'critical'])
    monitor = len(ccis_df[ccis_df['status'] == 'monitor'])
    total = len(ccis_df)
    print(f"Summary: {total} total records, {critical} critical, {monitor} monitor.")
    if not ccis_df['location'].isna().all():
        print("Location column present.")
    else:
        print("Warning: location column is empty – check your processed_data.csv.")