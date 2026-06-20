"""
Cascade Propagation Model
Predicts how congestion spreads to neighboring road cells across multiple hops.
"""
import h3
import pandas as pd
import numpy as np
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).parent.parent

class CascadePropagator:
    def __init__(self, ccis_df):
        self.ccis_df = ccis_df

    def predict_propagation(self, start_cell, start_hour, steps=3, attenuation=0.6):
        """
        Predict how congestion spreads from start_cell at start_hour over N steps (hops).
        Returns a list of dictionaries with neighbor cell information.
        """
        # Get start cell baseline CCIS
        cell_data = self.ccis_df[(self.ccis_df['h3_cell'] == start_cell) & (self.ccis_df['hour'] == start_hour)]
        if cell_data.empty:
            base_ccis = 5.0
            base_location = f"Hex {start_cell}"
        else:
            base_ccis = float(cell_data['ccis'].iloc[0])
            base_location = cell_data['location'].iloc[0] if not pd.isna(cell_data['location'].iloc[0]) else f"Hex {start_cell}"

        try:
            start_lat, start_lon = h3.cell_to_latlng(start_cell)
        except Exception:
            start_lat, start_lon = 12.9716, 77.5946

        # Initialize results with start cell (step 0)
        propagation_results = {
            start_cell: {
                'h3_cell': start_cell,
                'step': 0,
                'propagated_ccis': base_ccis,
                'lat': start_lat,
                'lon': start_lon,
                'location': base_location,
                'risk_level': 'Source'
            }
        }

        # Propagate outward ring by ring
        for step in range(1, steps + 1):
            # Compute ring cells
            try:
                # grid_ring gets hexes at exactly distance `step`
                ring_cells = h3.grid_ring(start_cell, step)
            except Exception:
                try:
                    # Fallback if grid_ring fails
                    disk = h3.grid_disk(start_cell, step)
                    inner_disk = h3.grid_disk(start_cell, step - 1)
                    ring_cells = disk - inner_disk
                except Exception:
                    ring_cells = []

            for cell in ring_cells:
                # Propagated CCIS based on distance attenuation
                prop_ccis = base_ccis * (attenuation ** step)
                
                # Check if cell already mapped (keep max propagated CCIS)
                if cell in propagation_results:
                    if prop_ccis > propagation_results[cell]['propagated_ccis']:
                        propagation_results[cell]['propagated_ccis'] = round(prop_ccis, 2)
                        propagation_results[cell]['step'] = step
                else:
                    # Lookup cell coordinates and location name in main dataset
                    cell_match = self.ccis_df[self.ccis_df['h3_cell'] == cell]
                    if not cell_match.empty:
                        lat = float(cell_match['lat'].iloc[0] if 'lat' in cell_match.columns else cell_match['latitude'].iloc[0])
                        lon = float(cell_match['lon'].iloc[0] if 'lon' in cell_match.columns else cell_match['longitude'].iloc[0])
                        loc_name = cell_match['location'].iloc[0]
                        if pd.isna(loc_name):
                            loc_name = f"Hex {cell} (Neighbor)"
                    else:
                        try:
                            lat, lon = h3.cell_to_latlng(cell)
                        except Exception:
                            lat, lon = start_lat, start_lon
                        loc_name = f"Hex {cell} (Neighbor)"

                    # Risk level assessment
                    if prop_ccis > 6.0:
                        risk = "Critical Spillover"
                    elif prop_ccis > 3.0:
                        risk = "Moderate Risk"
                    else:
                        risk = "Low Alert"

                    propagation_results[cell] = {
                        'h3_cell': cell,
                        'step': step,
                        'propagated_ccis': round(prop_ccis, 2),
                        'lat': lat,
                        'lon': lon,
                        'location': loc_name,
                        'risk_level': risk
                    }

        return list(propagation_results.values())

if __name__ == "__main__":
    print("Testing Cascade Propagation Model...")
    # Load dataset
    ccis_path = PROJECT_ROOT / "data" / "processed" / "ccis_scores.csv"
    if ccis_path.exists():
        ccis_df = pd.read_csv(ccis_path)
        if 'lat' not in ccis_df.columns and 'latitude' in ccis_df.columns:
            ccis_df = ccis_df.rename(columns={'latitude': 'lat', 'longitude': 'lon'})
        if 'h3_cell' not in ccis_df.columns and 'h3_8' in ccis_df.columns:
            ccis_df = ccis_df.rename(columns={'h3_8': 'h3_cell'})
            
        propagator = CascadePropagator(ccis_df)
        sample_cell = ccis_df['h3_cell'].iloc[0]
        results = propagator.predict_propagation(sample_cell, start_hour=18, steps=2, attenuation=0.5)
        print(f"Spillover nodes found for source cell {sample_cell}: {len(results)}")
        for r in results[:5]:
            print(f"  Step {r['step']}: {r['location']} | Propagated CCIS={r['propagated_ccis']} ({r['risk_level']})")
    else:
        print("Data file not found. Run pipeline first.")
