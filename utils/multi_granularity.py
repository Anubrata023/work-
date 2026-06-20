"""
Multi-Granularity Aggregation Engine
Recalculates CCIS scores and aggregates geographical data at H3 resolutions 6, 8, and 9.
"""
import pandas as pd
import numpy as np
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).parent.parent

def recalculate_ccis_resolution(resolution=8):
    """
    Dynamically aggregates the processed dataset to the target H3 resolution
    and computes CCIS scores.
    Resolutions:
      - 6: City View (~3.2km spacing)
      - 8: Zone View (~460m spacing)
      - 9: Street View (~100m spacing)
    """
    processed_path = PROJECT_ROOT / "data" / "processed" / "processed_data.csv"
    if not processed_path.exists():
        # Fallback to loading raw data if processed_data does not exist
        raise FileNotFoundError(f"Processed dataset not found at {processed_path}. Please run indexer first.")

    df = pd.read_csv(processed_path)
    h3_col = f'h3_{resolution}'
    if h3_col not in df.columns:
        raise ValueError(f"Resolution column {h3_col} not present in processed dataset.")

    print(f"Aggregating data for H3 resolution {resolution}...")

    # 1. Compute baseline activity counts per (cell, hour, day_of_week)
    baseline_grouped = df.groupby([h3_col, 'hour', 'day_of_week']).size().reset_index(name='baseline_count')
    baseline_grouped = baseline_grouped.rename(columns={h3_col: 'h3_cell'})

    # 2. Aggregate active violation cases per (cell, hour)
    agg = df.groupby([h3_col, 'hour']).agg({
        'latitude': ['count', 'first'],
        'longitude': 'first',
        'location': 'first'
    }).reset_index()
    agg.columns = ['h3_cell', 'hour', 'violation_count', 'lat', 'lon', 'location']

    # 3. Merge active counts with baseline (which duplicates for each day of week)
    merged = agg.merge(baseline_grouped, on=['h3_cell', 'hour'], how='left')

    # Fill missing baselines with global average
    global_avg = baseline_grouped['baseline_count'].mean()
    merged['baseline_count'] = merged['baseline_count'].fillna(global_avg)

    # 4. Speed drop calculation: (violations - baseline) / baseline, capped [0, 1]
    # For display, represent speed drop in km/h (capped to 10 km/h)
    speed_drop_fraction = (merged['violation_count'] - merged['baseline_count']) / merged['baseline_count']
    merged['speed_drop'] = speed_drop_fraction.clip(0.0, 1.0) * 10.0
    merged['speed_drop'] = merged['speed_drop'].round(2)

    # 5. CCIS formula: violation_count * speed_drop_fraction
    merged['ccis'] = merged['violation_count'] * (merged['speed_drop'] / 10.0)
    merged['ccis'] = merged['ccis'].round(2)

    # 6. Status and color mapping
    merged['status'] = 'green'
    merged.loc[merged['ccis'] > 6.0, 'status'] = 'critical'
    merged.loc[(merged['ccis'] > 3.0) & (merged['ccis'] <= 6.0), 'status'] = 'monitor'

    color_map = {
        'critical': '#FF4B4B',
        'monitor': '#FFA500',
        'green': '#00CC66'
    }
    merged['color'] = merged['status'].map(color_map)

    # Ensure location is non-null
    merged['location'] = merged['location'].fillna(merged['h3_cell'])

    return merged

if __name__ == "__main__":
    print("Testing Multi-Granularity Aggregation Engine...")
    try:
        for res in [6, 8, 9]:
            df_res = recalculate_ccis_resolution(res)
            print(f"H3 Resolution {res} Aggregation Complete:")
            print(f"  Shape: {df_res.shape}")
            print(f"  Critical Zones: {len(df_res[df_res['status']=='critical'])}")
            print(f"  Avg CCIS: {df_res['ccis'].mean():.2f}")
    except Exception as e:
        print(f"Error: {e}")
