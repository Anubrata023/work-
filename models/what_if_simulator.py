"""
Predictive Enforcement Friction Impact Simulation Engine
Models mathematical decay curves of localized traffic disruption states.
"""
from models.hours_saved_calculator import calculate_hours_saved
import pandas as pd
import numpy as np

class WhatIfSimulator:
    def __init__(self, df):
        self.df = df

    def simulate_enforcement(self, cell, hour, officers, duration):
        """Simulates response metrics by estimating congestion clear speed parameters using M/D/1 queuing theory."""
        # Calculate proportional relief factor curves
        base_reduction = min(82.5, float(officers * 14.2))
        time_modifier = min(1.25, max(0.8, float(duration / 2.0)))
        total_reduction_pct = min(95.0, base_reduction * time_modifier)

        # Retrieve active violations and baseline from dataset for selected cell and hour
        cell_row = self.df[(self.df['h3_cell'] == cell) & (self.df['hour'] == hour)]
        if not cell_row.empty:
            violations_before = cell_row['violation_count'].iloc[0]
            baseline_count = cell_row['baseline_count'].iloc[0] if 'baseline_count' in cell_row.columns else 3.0
        else:
            violations_before = 5.0
            baseline_count = 3.0

        # Handle NaNs or zeros
        violations_before = max(1.0, float(violations_before))
        baseline_count = max(1.0, float(baseline_count))

        # Projected violations after enforcement
        violations_after = max(0.0, violations_before * (1.0 - total_reduction_pct / 100.0))

        # Model hourly volume: peak traffic times (17-20) have higher volume
        volume_factor = 1.25 if 17 <= hour <= 20 else 0.75 if 0 <= hour <= 6 else 1.0
        hourly_volume = int(1000 * volume_factor)

        total_hours_saved = calculate_hours_saved(
            violations_before=violations_before,
            violations_after=violations_after,
            baseline_count=baseline_count,
            duration_hours=float(duration),
            hourly_volume=hourly_volume
        )

        return {
            "violation_reduction_pct": round(total_reduction_pct, 1),
            "total_hours_saved": total_hours_saved
        }