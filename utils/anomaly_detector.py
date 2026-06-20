"""
Isolation Forest Anomaly Detection Engine
Identifies statistically anomalous parking violation deviations and calculates the Parking Obstruction Index (POI).
"""
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
import joblib
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).parent.parent

class IsolationForestAnomalyDetector:
    def __init__(self, contamination=0.1, model_name="isolation_forest.pkl"):
        self.contamination = contamination
        self.model_path = PROJECT_ROOT / "models" / model_name
        self.clf = None

    def fit_predict(self, df):
        """
        Fit Isolation Forest model and predict anomalies on the provided dataframe.
        Adds 'is_anomaly' and 'poi' columns to the dataframe.
        """
        df_clean = df.copy()
        
        # Ensure required columns exist
        if 'baseline_count' not in df_clean.columns:
            df_clean['baseline_count'] = 0.0
        if 'violation_count' not in df_clean.columns:
            df_clean['violation_count'] = 0.0
        if 'speed_drop' not in df_clean.columns:
            df_clean['speed_drop'] = 0.0
        if 'ccis' not in df_clean.columns:
            df_clean['ccis'] = 0.0

        # Calculate deviation from historical baseline
        df_clean['baseline_deviation'] = df_clean['violation_count'] - df_clean['baseline_count']

        # Select features for training
        features = ['violation_count', 'speed_drop', 'ccis', 'baseline_deviation']
        X = df_clean[features].fillna(0.0)

        # Train/load isolation forest model
        self.clf = IsolationForest(contamination=self.contamination, random_state=42)
        self.clf.fit(X)

        # Save model
        try:
            joblib.dump(self.clf, self.model_path)
        except Exception as e:
            print(f"Warning: Could not save anomaly detector model: {e}")

        # Predict anomaly: -1 for anomaly, 1 for normal
        preds = self.clf.predict(X)
        df_clean['is_anomaly'] = (preds == -1)

        # Compute raw anomaly score (more negative means more anomalous)
        # We invert it: negative of decision_function (so higher means more anomalous)
        anomaly_scores = -self.clf.decision_function(X) # range is roughly [-0.5, 0.5]
        
        # Normalize anomaly scores to [0, 1] for indexing
        min_s = anomaly_scores.min()
        max_s = anomaly_scores.max()
        if max_s > min_s:
            normalized_scores = (anomaly_scores - min_s) / (max_s - min_s)
        else:
            normalized_scores = np.zeros_like(anomaly_scores)

        # Calculate Parking Obstruction Index (POI) on a 0-10 scale
        # Incorporates violation count, speed drop (congestion severity), and statistical anomalousness
        df_clean['poi'] = (df_clean['ccis'] * 0.6 + normalized_scores * 4.0)
        df_clean['poi'] = df_clean['poi'].clip(0.0, 10.0).round(2)

        return df_clean

if __name__ == "__main__":
    print("Testing Isolation Forest Anomaly Detection...")
    ccis_path = PROJECT_ROOT / "data" / "processed" / "ccis_scores.csv"
    if ccis_path.exists():
        ccis_df = pd.read_csv(ccis_path)
        detector = IsolationForestAnomalyDetector()
        result = detector.fit_predict(ccis_df)
        print(f"Successfully processed {len(result)} records.")
        print(f"Anomalies detected: {result['is_anomaly'].sum()} ({result['is_anomaly'].mean()*100:.1f}%)")
        print(f"POI statistics: min={result['poi'].min()}, max={result['poi'].max()}, mean={result['poi'].mean():.2f}")
    else:
        print(f"Data file not found at {ccis_path}. Creating sample evaluation run...")
        # Create a mock dataframe
        np.random.seed(42)
        mock_df = pd.DataFrame({
            'violation_count': np.random.poisson(lam=5, size=100),
            'baseline_count': np.random.poisson(lam=4, size=100),
            'speed_drop': np.random.uniform(0.0, 1.0, size=100),
            'ccis': np.random.uniform(0.0, 8.0, size=100)
        })
        detector = IsolationForestAnomalyDetector()
        result = detector.fit_predict(mock_df)
        print(f"Mock run complete. Anomalies: {result['is_anomaly'].sum()}")
        print(result[['violation_count', 'baseline_count', 'ccis', 'poi', 'is_anomaly']].head(10))
