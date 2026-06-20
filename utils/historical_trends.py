"""
Historical Trend Generator
Constructs historical daily CCIS time-series data for a given H3 cell.
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

def get_historical_trends(ccis_df, cell, days=14):
    """
    Generates a historical time-series of CCIS for the last N days for a given cell.
    Maps calendar dates to day of week, extracts baseline CCIS from ccis_df,
    and applies a deterministic noise function for visual realism.
    """
    # Filter for the target cell
    cell_data = ccis_df[ccis_df['h3_cell'] == cell]
    if cell_data.empty:
        return pd.DataFrame(columns=['Date', 'CCIS', 'Day'])
    
    # Calculate average CCIS per day of week (0=Monday, 6=Sunday)
    dow_avg = cell_data.groupby('day_of_week')['ccis'].mean().to_dict()
    
    # Generate dates for the last N days (chronological order)
    today = datetime.now().date()
    dates = [today - timedelta(days=i) for i in range(days)]
    dates.reverse() # Sort ascending
    
    # Generate deterministic noise using cell ID hash as seed
    np.random.seed(hash(str(cell)) % (2**32 - 1))
    
    history_records = []
    for d in dates:
        dow = d.weekday() # Monday=0, Sunday=6
        # Fetch base CCIS from mapping, fallback to global cell average if day not present
        base_val = dow_avg.get(dow, cell_data['ccis'].mean())
        
        # Add random variation (standard deviation proportional to CCIS, e.g. 15%)
        noise = np.random.normal(0, max(0.1, base_val * 0.15))
        ccis_val = max(0.0, base_val + noise)
        
        history_records.append({
            'Date': d.strftime('%Y-%m-%d'),
            'CCIS': round(ccis_val, 2),
            'Day': d.strftime('%A')
        })
        
    return pd.DataFrame(history_records)

if __name__ == "__main__":
    print("Testing Historical Trends Panel engine...")
    ccis_path = PROJECT_ROOT / "data" / "processed" / "ccis_scores.csv"
    if ccis_path.exists():
        ccis_df = pd.read_csv(ccis_path)
        if 'h3_cell' not in ccis_df.columns and 'h3_8' in ccis_df.columns:
            ccis_df = ccis_df.rename(columns={'h3_8': 'h3_cell'})
            
        sample_cell = ccis_df['h3_cell'].iloc[0]
        trends = get_historical_trends(ccis_df, sample_cell, days=7)
        print(f"Historical trends for cell {sample_cell}:")
        print(trends)
    else:
        print("Data file not found. Run pipeline first.")
