"""
Ridge Regression Forecasting with Residual Correction
Predicts CCIS 1 hour ahead and provides interpretable coefficients.
"""
import pandas as pd
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import r2_score, mean_absolute_error
import joblib
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))

PROJECT_ROOT = Path(__file__).parent.parent


def prepare_features(ccis_df):
    """
    Create time features, lag features, and target.
    """
    print("Preparing features for forecasting...")
    df = ccis_df.copy()

    # Time features
    df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
    df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)

    if 'day_of_week' in df.columns:
        df['day_sin'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
        df['day_cos'] = np.cos(2 * np.pi * df['day_of_week'] / 7)
    else:
        df['day_sin'] = 0
        df['day_cos'] = 0

    # Historical mean CCIS per cell
    df['historical_mean'] = df.groupby('h3_cell')['ccis'].transform('mean')

    # Lag features (previous hour's CCIS)
    df['lag_1'] = df.groupby('h3_cell')['ccis'].shift(1)
    df['lag_2'] = df.groupby('h3_cell')['ccis'].shift(2)

    # Target: CCIS 1 hour ahead
    df['target'] = df.groupby('h3_cell')['ccis'].shift(-1)

    # Drop rows with NaN
    features = ['hour_sin', 'hour_cos', 'day_sin', 'day_cos', 'historical_mean', 'lag_1', 'lag_2', 'ccis']
    df = df.dropna(subset=features + ['target'])
    return df, features


def train_model(df, features):
    """
    Train Ridge model and save artifacts.
    """
    print("Training Ridge Regression model...")
    X = df[features]
    y = df['target']

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Scale
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # Find best alpha
    best_alpha = 1.0
    best_r2 = -np.inf
    for alpha in [0.01, 0.1, 1.0, 10.0, 100.0]:
        model = Ridge(alpha=alpha)
        model.fit(X_train_scaled, y_train)
        r2 = model.score(X_test_scaled, y_test)
        if r2 > best_r2:
            best_r2 = r2
            best_alpha = alpha

    print(f"  Best alpha: {best_alpha}, R²: {best_r2:.4f}")

    # Final model
    final_model = Ridge(alpha=best_alpha)
    final_model.fit(X_train_scaled, y_train)
    y_pred = final_model.predict(X_test_scaled)
    mae = mean_absolute_error(y_test, y_pred)
    print(f"  Final MAE: {mae:.3f}")

    # Save model and scaler
    joblib.dump(final_model, PROJECT_ROOT / "models" / "ridge_model.pkl")
    joblib.dump(scaler, PROJECT_ROOT / "models" / "scaler.pkl")
    print(f"  Model saved to models/ridge_model.pkl")

    # Save coefficients
    coef_df = pd.DataFrame({
        'feature': features,
        'coefficient': final_model.coef_,
        'importance_abs': np.abs(final_model.coef_)
    }).sort_values('importance_abs', ascending=False)
    coef_df.to_csv(PROJECT_ROOT / "models" / "coefficients.csv", index=False)
    print(f"  Coefficients saved to models/coefficients.csv")

    return final_model, scaler, best_r2, mae


def add_residual_correction(df, features, model, scaler):
    """
    Add residual correction based on historical error patterns.
    """
    print("Adding residual correction...")
    X = df[features]
    X_scaled = scaler.transform(X)
    df['predicted'] = model.predict(X_scaled)
    df['error'] = df['target'] - df['predicted']

    correction = df.groupby(['h3_cell', 'hour'])['error'].mean().reset_index()
    correction.columns = ['h3_cell', 'hour', 'correction_term']
    df = df.merge(correction, on=['h3_cell', 'hour'], how='left')
    df['correction_term'] = df['correction_term'].fillna(0)
    return df


if __name__ == "__main__":
    ccis_path = PROJECT_ROOT / "data" / "processed" / "ccis_scores.csv"
    if not ccis_path.exists():
        print("ERROR: ccis_scores.csv not found. Run ccis_engine.py first.")
        sys.exit(1)

    ccis_df = pd.read_csv(ccis_path)
    print(f"Loaded {len(ccis_df):,} CCIS records.")

    df, features = prepare_features(ccis_df)
    model, scaler, r2, mae = train_model(df, features)
    df = add_residual_correction(df, features, model, scaler)

    output_path = PROJECT_ROOT / "data" / "processed" / "ccis_with_predictions.csv"
    df.to_csv(output_path, index=False)
    print(f"Saved predictions to {output_path}")

    print(f"\nForecast Model Complete!")
    print(f"  R² Score: {r2:.4f}")
    print(f"  MAE: {mae:.3f}")