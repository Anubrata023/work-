"""
H3 Spatial Indexing Pipeline
Converts lat/lon to H3 cell IDs at three resolutions.
"""
import pandas as pd
import h3
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))
from data.loader import load_dataset, clean_dataframe

PROJECT_ROOT = Path(__file__).parent.parent
RESOLUTIONS = [6, 8, 9]  # City, Zone, Street


def add_h3_cell_ids(df, lat_col='latitude', lon_col='longitude'):
    """
    For each row, compute H3 cell IDs at all resolutions.

    Why: H3 hexagons are the spatial foundation. We use 3 resolutions
    because different stakeholders need different zoom levels:
    - Resolution 6 (~3km): City planners see city-wide patterns
    - Resolution 8 (~500m): Zone supervisors see neighborhood hotspots
    - Resolution 9 (~200m): Beat officers see exact enforcement locations
    """
    print("Adding H3 cell IDs...")
    for res in RESOLUTIONS:
        col_name = f'h3_{res}'
        print(f"  Computing H3 resolution {res}...")
        # h3.latlng_to_cell converts coordinates to a hex cell ID
        df[col_name] = df.apply(
            lambda row: h3.latlng_to_cell(row[lat_col], row[lon_col], res),
            axis=1
        )
    return df


def compute_baseline_activity(df, resolution=8):
    """
    Compute the baseline (average) violation count per (cell, hour, day_of_week).

    Why: This is the "normal" level of activity. We compare current activity
    to this baseline to detect anomalies and compute CCIS.

    The output column is explicitly named 'h3_cell' for consistency across files.
    """
    h3_col = f'h3_{resolution}'
    print(f"Computing baseline activity for resolution {resolution}...")

    # Group by cell, hour, and day of week
    grouped = df.groupby([h3_col, 'hour', 'day_of_week']).size().reset_index(name='baseline_count')

    # Rename the first column to 'h3_cell' explicitly
    grouped = grouped.rename(columns={h3_col: 'h3_cell'})

    # Normalize to 0-1 so baselines are comparable across cells
    max_val = grouped['baseline_count'].max()
    if max_val > 0:
        grouped['baseline_activity'] = grouped['baseline_count'] / max_val
    else:
        grouped['baseline_activity'] = 0

    return grouped


def compute_cell_aggregates(df, resolution=8):
    """
    For each (cell, hour), get violation count and average coordinates.

    Why: This reduces data from millions of rows to manageable aggregates
    that can be processed quickly for CCIS computation.
    """
    h3_col = f'h3_{resolution}'
    print(f"Computing cell aggregates for resolution {resolution}...")

    grouped = df.groupby([h3_col, 'hour']).agg({
        'latitude': ['count', 'first'],
        'longitude': 'first'
    }).reset_index()

    # Flatten the multi-level column names
    grouped.columns = ['h3_cell', 'hour', 'violation_count', 'lat', 'lon']

    return grouped


if __name__ == "__main__":
    print("=" * 60)
    print("H3 SPATIAL INDEXING PIPELINE")
    print("=" * 60)

    # Load cleaned data
    cleaned_path = PROJECT_ROOT / "data" / "processed" / "cleaned_data.csv"
    if not cleaned_path.exists():
        print("ERROR: cleaned_data.csv not found. Run loader.py first.")
        sys.exit(1)

    df = pd.read_csv(cleaned_path)
    print(f"Loaded {len(df):,} cleaned rows.")

    # Add H3 cells at all resolutions
    df = add_h3_cell_ids(df)

    # Save full processed data (this will be used by GAMMA for cascade modeling)
    processed_path = PROJECT_ROOT / "data" / "processed" / "processed_data.csv"
    df.to_csv(processed_path, index=False)
    print(f"Saved processed data to {processed_path}")

    # Compute and save baseline activity (used by CCIS engine)
    baseline = compute_baseline_activity(df, resolution=8)
    baseline_path = PROJECT_ROOT / "data" / "processed" / "baseline_activity.csv"
    baseline.to_csv(baseline_path, index=False)
    print(f"Saved baseline activity to {baseline_path}")
    print(f"  Columns: {baseline.columns.tolist()}")  # Debug: show column names

    # Compute and save cell aggregates at all resolutions
    for res in RESOLUTIONS:
        agg = compute_cell_aggregates(df, resolution=res)
        agg_path = PROJECT_ROOT / "data" / "processed" / f"cell_aggregates_h3_{res}.csv"
        agg.to_csv(agg_path, index=False)
        print(f"Saved aggregates for H3-{res} to {agg_path}")

    print("\nH3 Pipeline Complete.")