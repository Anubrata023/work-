"""
Data Loader for GridLock Hackathon Dataset
Loads raw CSV, cleans, parses timestamps, extracts features.
"""
import pandas as pd
import numpy as np
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

def load_dataset(file_name="gridlock_data.csv"):
    """
    Load the raw dataset from data/raw/.
    """
    file_path = PROJECT_ROOT / "data" / "raw" / file_name
    if not file_path.exists():
        raise FileNotFoundError(f"Dataset not found at {file_path}")
    print(f"Loading dataset from {file_path}...")
    df = pd.read_csv(file_path)
    print(f"Loaded {len(df):,} rows and {len(df.columns)} columns.")
    return df

def clean_dataframe(df):
    """
    Clean and preprocess the dataframe.
    """
    print("Cleaning data...")
    df_clean = df.copy()

    # 1. Remove duplicates
    df_clean = df_clean.drop_duplicates()

    # 2. Parse timestamp (ISO8601 with microseconds and timezone)
    if 'created_datetime' in df_clean.columns:
        df_clean['timestamp'] = pd.to_datetime(
            df_clean['created_datetime'],
            format='ISO8601',
            utc=True,
            errors='coerce'
        )
        df_clean['hour'] = df_clean['timestamp'].dt.hour
        df_clean['day_of_week'] = df_clean['timestamp'].dt.dayofweek  # Mon=0
        df_clean['date'] = df_clean['timestamp'].dt.date

    # 3. Ensure lat/lon are numeric
    if 'latitude' in df_clean.columns:
        df_clean['latitude'] = pd.to_numeric(df_clean['latitude'], errors='coerce')
    if 'longitude' in df_clean.columns:
        df_clean['longitude'] = pd.to_numeric(df_clean['longitude'], errors='coerce')

    # 4. Drop rows missing location
    df_clean = df_clean.dropna(subset=['latitude', 'longitude'])

    # 5. Parse violation_type (which is like '["NO PARKING"]')
    if 'violation_type' in df_clean.columns:
        def parse_violation_list(val):
            if pd.isna(val):
                return []
            if isinstance(val, str):
                val = val.strip('[]')
                if val:
                    items = re.findall(r'"([^"]*)"', val)
                    if not items:
                        items = [x.strip().strip('"') for x in val.split(',') if x.strip()]
                    return items
            return []

        df_clean['violation_types_parsed'] = df_clean['violation_type'].apply(parse_violation_list)
        df_clean['primary_violation'] = df_clean['violation_types_parsed'].apply(
            lambda x: x[0] if x else 'UNKNOWN'
        )
        df_clean['violation_count'] = df_clean['violation_types_parsed'].apply(len)

    # 6. Filter to Bengaluru bounds
    df_clean = df_clean[
        (df_clean['latitude'].between(12.5, 13.5)) &
        (df_clean['longitude'].between(77.3, 78.0))
    ]

    print(f"Cleaning complete. Final shape: {df_clean.shape[0]:,} rows")
    return df_clean

if __name__ == "__main__":
    # Run this script directly to generate cleaned_data.csv
    df = load_dataset()
    df_clean = clean_dataframe(df)
    output_path = PROJECT_ROOT / "data" / "processed" / "cleaned_data.csv"
    df_clean.to_csv(output_path, index=False)
    print(f"Saved cleaned data to {output_path}")