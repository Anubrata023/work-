"""
Tactical Allocation Matrix Engine
Processes target cell values to recommend field unit enforcement footprints.
"""
import pandas as pd


def calculate_officer_count(ccis_score):
    """Allocates ground forces proportionally based on the grid breach index."""
    if ccis_score >= 6.0:
        return 5  # Critical congestion node
    elif ccis_score >= 3.0:
        return 2  # Moderate congestion node
    return 1  # Minimal maintenance patrol


def get_dispatch_details(h3_cell, ccis_df, raw_df):
    """Compiles local insights for targeted tactical responses."""
    cell_rows = ccis_df[ccis_df['h3_cell'] == h3_cell]
    if cell_rows.empty:
        return None

    target = cell_rows.iloc[0]
    score = target['ccis']

    return {
        'h3_cell': h3_cell,
        'ccis': score,
        'recommended_officers': calculate_officer_count(score),
        'location_alias': f"Strategic Interdiction sector ({h3_cell[:8]})"
    }