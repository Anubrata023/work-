"""
Interpretable Explanation Generator
Uses model coefficients and historical data to explain predictions.
"""
import pandas as pd
import numpy as np
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))

PROJECT_ROOT = Path(__file__).parent.parent


def load_coefficients():
    """Load coefficient table for explaining predictions."""
    coef_path = PROJECT_ROOT / "models" / "coefficients.csv"
    if coef_path.exists():
        return pd.read_csv(coef_path)
    return None


def generate_explanation(h3_cell, hour, ccis_df, predicted_ccis=None):
    """
    Generate a plain-English explanation for a given cell and hour.
    """
    cell_data = ccis_df[(ccis_df['h3_cell'] == h3_cell) & (ccis_df['hour'] == hour)]
    if cell_data.empty:
        return "No data available for this zone."

    row = cell_data.iloc[0]
    current_ccis = row['ccis']

    # Historical average for this cell
    history = ccis_df[ccis_df['h3_cell'] == h3_cell]
    avg_ccis = history['ccis'].mean() if not history.empty else current_ccis
    peak_hour = history.groupby('hour')['ccis'].mean().idxmax() if not history.empty else 18

    parts = []

    # 1. Relative to historical average
    if current_ccis > avg_ccis * 1.5:
        parts.append(f"This zone has {current_ccis / avg_ccis:.1f}x higher CCIS than its historical average.")

    # 2. Peak hour
    if peak_hour == hour:
        parts.append("This is the historical peak hour for this zone.")

    # 3. Time-of-day context
    if 17 <= hour <= 20:
        parts.append("Evening rush hour typically sees higher parking violations.")
    elif 12 <= hour <= 14:
        parts.append("Lunch hour shows elevated violations near commercial areas.")

    # 4. Day-of-week context
    if 'day_of_week' in row:
        dow = int(row['day_of_week'])
        if dow in [4, 5]:
            parts.append("Weekend evenings historically have higher activity.")

    # 5. Coefficients
    coefs = load_coefficients()
    if coefs is not None:
        top_feature = coefs.iloc[0]['feature']
        if top_feature == 'lag_1':
            parts.append("Strongest predictor: previous hour's congestion level.")
        elif top_feature == 'historical_mean':
            parts.append("Strongest predictor: this zone's long-term average.")

    # 6. Forecast
    if predicted_ccis is not None:
        if predicted_ccis > current_ccis * 1.2:
            parts.append(
                f"Forecast: CCIS predicted to rise to {predicted_ccis:.1f} in 90 minutes - proactive deployment recommended.")
        elif predicted_ccis < current_ccis * 0.8:
            parts.append(f"Forecast: CCIS predicted to drop to {predicted_ccis:.1f} - conditions improving.")
        else:
            parts.append(f"Forecast: CCIS stable around {predicted_ccis:.1f} - continue monitoring.")

    return " ".join(parts) if parts else f"Zone has CCIS {current_ccis:.1f}, indicating moderate congestion."


if __name__ == "__main__":
    ccis_path = PROJECT_ROOT / "data" / "processed" / "ccis_with_predictions.csv"
    if not ccis_path.exists():
        print("Run forecast_model.py first.")
        sys.exit(1)

    df = pd.read_csv(ccis_path)
    sample_cell = df['h3_cell'].iloc[0]
    sample_hour = df['hour'].iloc[0]

    # Try to get prediction
    if 'predicted' in df.columns:
        pred_row = df[(df['h3_cell'] == sample_cell) & (df['hour'] == sample_hour)]
        pred = pred_row['predicted'].iloc[0] if not pred_row.empty else None
    else:
        pred = None

    explanation = generate_explanation(sample_cell, sample_hour, df, pred)
    print(f"Explanation for {sample_cell} at {sample_hour}:00")
    print(explanation)