"""
modules/tax_risk_model.py

Carbon Tax Risk Prediction Model for Carbon-Trace Mangalore
Predicts carbon tax liability (€) under EU CBAM-like conditions.
"""

import os
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score
from sklearn.preprocessing import StandardScaler
import warnings

warnings.filterwarnings("ignore")

# ─── Constants ────────────────────────────────────────────────────────────────

DATA_PATH = "data/tax_risk_data.csv"
FEATURES = ["shipment_tonnes", "distance_km", "carbon_price_eur", "emissions_per_tonne", "season"]
TARGET = "tax_liability"

RISK_LOW_THRESHOLD = 500_000
RISK_HIGH_THRESHOLD = 900_000
CONFIDENCE_MARGIN = 0.08  # ±8%

# ─── Global model state ────────────────────────────────────────────────────────

_model: GradientBoostingRegressor = None
_scaler: StandardScaler = None
_is_trained: bool = False


# ─── Data Generation (fallback if CSV missing) ────────────────────────────────

def _generate_synthetic_data(n_samples: int = 2000) -> pd.DataFrame:
    """Generate synthetic training data based on CBAM-like tax logic."""
    np.random.seed(42)

    shipment_tonnes = np.random.uniform(1_000, 50_000, n_samples)
    distance_km = np.random.uniform(500, 20_000, n_samples)
    carbon_price_eur = np.random.uniform(30, 120, n_samples)
    emissions_per_tonne = np.random.uniform(0.3, 3.0, n_samples)
    season = np.random.randint(1, 5, n_samples)

    # Approximate CBAM formula: tonnes × emissions_factor × carbon_price
    # with distance and season as modifiers
    base_tax = shipment_tonnes * emissions_per_tonne * carbon_price_eur
    distance_factor = 1 + (distance_km / 100_000)
    season_factor = np.where(season == 1, 1.05,
                    np.where(season == 2, 0.97,
                    np.where(season == 3, 1.00, 1.03)))
    noise = np.random.normal(0, 0.03, n_samples)

    tax_liability = base_tax * distance_factor * season_factor * (1 + noise)
    tax_liability = np.clip(tax_liability, 0, None)

    return pd.DataFrame({
        "shipment_tonnes": shipment_tonnes,
        "distance_km": distance_km,
        "carbon_price_eur": carbon_price_eur,
        "emissions_per_tonne": emissions_per_tonne,
        "season": season.astype(int),
        "tax_liability": tax_liability,
    })


# ─── Data Loading ─────────────────────────────────────────────────────────────

def _load_data() -> pd.DataFrame:
    """Load dataset from CSV or fall back to synthetic data."""
    if os.path.exists(DATA_PATH):
        print(f"[INFO] Loading data from: {DATA_PATH}")
        df = pd.read_csv(DATA_PATH)

        required_cols = FEATURES + [TARGET]
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            raise ValueError(f"[ERROR] Missing columns in CSV: {missing}")

        df = df[required_cols].dropna()
        print(f"[INFO] Loaded {len(df)} records from CSV.")
    else:
        print(f"[WARNING] '{DATA_PATH}' not found. Using synthetic data.")
        os.makedirs("data", exist_ok=True)
        df = _generate_synthetic_data()
        df.to_csv(DATA_PATH, index=False)
        print(f"[INFO] Synthetic dataset saved to: {DATA_PATH}")

    return df


# ─── Model Training ───────────────────────────────────────────────────────────

def _train_model() -> None:
    """Load data, train Gradient Boosting model, and store globally."""
    global _model, _scaler, _is_trained

    df = _load_data()

    X = df[FEATURES].values
    y = df[TARGET].values

    # Train / test split (80/20)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    # Feature scaling
    _scaler = StandardScaler()
    X_train_scaled = _scaler.fit_transform(X_train)
    X_test_scaled = _scaler.transform(X_test)

    # Gradient Boosting Regressor
    _model = GradientBoostingRegressor(
        n_estimators=200,
        learning_rate=0.08,
        max_depth=5,
        subsample=0.85,
        min_samples_split=5,
        random_state=42,
    )

    print("[INFO] Training Gradient Boosting Regressor...")
    _model.fit(X_train_scaled, y_train)

    # Evaluate
    y_pred = _model.predict(X_test_scaled)
    r2 = r2_score(y_test, y_pred)
    print(f"[INFO] Model R² Score on test set: {r2:.4f}")

    _is_trained = True


# ─── Risk Classification ──────────────────────────────────────────────────────

def _classify_risk(tax_value: float) -> str:
    """Classify tax liability into Low / Medium / High risk tier."""
    if tax_value < RISK_LOW_THRESHOLD:
        return "Low"
    elif tax_value <= RISK_HIGH_THRESHOLD:
        return "Medium"
    else:
        return "High"


# ─── Input Validation ─────────────────────────────────────────────────────────

def _validate_input(shipment_dict: dict) -> None:
    """Validate that all required keys are present and values are valid."""
    for key in FEATURES:
        if key not in shipment_dict:
            raise KeyError(f"[ERROR] Missing required field: '{key}'")

    for key in ["shipment_tonnes", "distance_km", "carbon_price_eur", "emissions_per_tonne"]:
        val = shipment_dict[key]
        if not isinstance(val, (int, float)) or val < 0:
            raise ValueError(f"[ERROR] '{key}' must be a non-negative number. Got: {val}")

    season = shipment_dict["season"]
    if season not in (1, 2, 3, 4):
        raise ValueError(f"[ERROR] 'season' must be 1, 2, 3, or 4. Got: {season}")


# ─── Public API ───────────────────────────────────────────────────────────────

def predict_tax_risk(shipment_dict: dict) -> dict:
    """
    Predict carbon tax liability for a given shipment.

    Parameters
    ----------
    shipment_dict : dict
        Keys: shipment_tonnes, distance_km, carbon_price_eur,
              emissions_per_tonne, season

    Returns
    -------
    dict
        {
            "tax_liability": float,
            "risk_score": str,          # "Low" | "Medium" | "High"
            "confidence_interval": list # [lower, upper]
        }
    """
    global _is_trained

    # Lazy training on first call
    if not _is_trained:
        _train_model()

    # Validate input
    _validate_input(shipment_dict)

    # Build feature vector in correct order
    X_input = np.array([[
        shipment_dict["shipment_tonnes"],
        shipment_dict["distance_km"],
        shipment_dict["carbon_price_eur"],
        shipment_dict["emissions_per_tonne"],
        shipment_dict["season"],
    ]])

    # Scale and predict
    X_scaled = _scaler.transform(X_input)
    predicted = float(_model.predict(X_scaled)[0])
    predicted = max(predicted, 0.0)  # clamp to non-negative

    # Confidence interval ±8%
    lower = round(predicted * (1 - CONFIDENCE_MARGIN), 2)
    upper = round(predicted * (1 + CONFIDENCE_MARGIN), 2)

    return {
        "tax_liability": round(predicted, 2),
        "risk_score": _classify_risk(predicted),
        "confidence_interval": [lower, upper],
    }


# ─── Entrypoint ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    sample_shipment = {
        "shipment_tonnes": 10000,
        "distance_km": 9000,
        "carbon_price_eur": 70,
        "emissions_per_tonne": 1.2,
        "season": 2,
    }

    print("\n[INPUT]")
    for k, v in sample_shipment.items():
        print(f"  {k}: {v}")

    result = predict_tax_risk(sample_shipment)

    print("\n[OUTPUT]")
    print(f"  Tax Liability        : €{result['tax_liability']:,.2f}")
    print(f"  Risk Score           : {result['risk_score']}")
    print(f"  Confidence Interval  : €{result['confidence_interval'][0]:,.2f} – €{result['confidence_interval'][1]:,.2f}")