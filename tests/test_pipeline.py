"""
End-to-End Pipeline Verification Test
Verifies integration of dynamic multi-granularity aggregation, Isolation Forest anomaly detection,
M/D/1 delay calculations, cascade propagation, and historical trend generator.
"""
import pandas as pd
import numpy as np
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT))

from utils.multi_granularity import recalculate_ccis_resolution
from utils.anomaly_detector import IsolationForestAnomalyDetector
from utils.historical_trends import get_historical_trends
from models.cascade_propagator import CascadePropagator
from models.hours_saved_calculator import calculate_hours_saved
from models.what_if_simulator import WhatIfSimulator

def run_integration_test():
    print("=" * 60)
    print("RUNNING END-TO-END PIPELINE INTEGRATION TEST")
    print("=" * 60)

    # 1. Multi-granularity aggregation
    print("\n[1/5] Testing Multi-Granularity Aggregation (Resolution 8)...")
    df_res8 = recalculate_ccis_resolution(resolution=8)
    assert not df_res8.empty, "Resolution 8 aggregation returned empty DataFrame"
    print(f"  Success: Aggregated {len(df_res8)} records for resolution 8.")

    # 2. Anomaly detection
    print("\n[2/5] Testing Isolation Forest Anomaly Detection & POI...")
    detector = IsolationForestAnomalyDetector()
    df_anom = detector.fit_predict(df_res8)
    assert 'poi' in df_anom.columns, "POI column missing after anomaly detection"
    assert 'is_anomaly' in df_anom.columns, "is_anomaly column missing after anomaly detection"
    print(f"  Success: POI and Anomaly columns added.")
    print(f"  Anomalies: {df_anom['is_anomaly'].sum()} detected (Contamination: {df_anom['is_anomaly'].mean()*100:.1f}%)")

    # 3. M/D/1 hours saved & Simulator
    print("\n[3/5] Testing M/D/1 Queuing Theory Simulator...")
    sample_cell = df_anom['h3_cell'].iloc[0]
    sample_hour = df_anom['hour'].iloc[0]
    simulator = WhatIfSimulator(df_anom)
    sim_res = simulator.simulate_enforcement(sample_cell, sample_hour, officers=4, duration=3)
    assert 'violation_reduction_pct' in sim_res, "violation_reduction_pct missing in simulator results"
    assert 'total_hours_saved' in sim_res, "total_hours_saved missing in simulator results"
    print(f"  Success: M/D/1 calculation output: {sim_res}")

    # 4. Cascade Propagation
    print("\n[4/5] Testing Cascade Propagation Model...")
    propagator = CascadePropagator(df_anom)
    cascade_nodes = propagator.predict_propagation(sample_cell, sample_hour, steps=2, attenuation=0.6)
    assert len(cascade_nodes) > 0, "No cascade propagation nodes generated"
    print(f"  Success: Propagated to {len(cascade_nodes)} nodes (source + neighbors).")

    # 5. Historical Trends
    print("\n[5/5] Testing Historical Trends Generator...")
    trends = get_historical_trends(df_anom, sample_cell, days=7)
    assert not trends.empty, "Trends generator returned empty DataFrame"
    print(f"  Success: Generated historical trends:")
    print(trends.to_string())

    print("\n" + "=" * 60)
    print("ALL INTEGRATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    run_integration_test()
