# modules/ml_predictor.py
# Predicts missing Scope 1 or Scope 2 emissions
# using Random Forest Regressor trained on historical plant data
# Used when PDF report has incomplete emissions data

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.preprocessing import StandardScaler
import joblib
import os

# ─────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────

# Path to training data
TRAINING_DATA_PATH = "/home/user/Desktop/Projects/PBL/data/training_data.csv"

# Path to save trained model
MODEL_PATH = "/home/user/Desktop/Projects/PBL/models/emissions_model.pkl"

# Path to save scaler
SCALER_PATH = "/home/user/Desktop/Projects/PBL/models/scaler.pkl"

# Features the model uses to predict
FEATURE_COLUMNS = [
    "natural_gas_mmbtu",
    "electricity_kwh_per_mt_urea",
    "urea_production_mt",
    "capacity_utilization_pct",
    "energy_intensity_gj_per_mt",
    "year"
]

# What the model predicts
TARGET_SCOPE1 = "scope1_tco2e"
TARGET_SCOPE2 = "scope2_tco2e"

# ─────────────────────────────────────────
# FUNCTION 1: Load Training Data
# ─────────────────────────────────────────
def load_training_data(csv_path=TRAINING_DATA_PATH):
    """
    Loads the training dataset from CSV.
    Validates columns and checks for missing values.

    Returns:
        pandas DataFrame or None if error
    """

    # Check file exists
    if not os.path.exists(csv_path):
        print(f"ERROR: Training data not found at {csv_path}")
        return None

    # Load CSV
    df = pd.read_csv(csv_path)

    print(f"Training data loaded: {len(df)} rows")
    print(f"Columns: {list(df.columns)}")

    # Check all required columns exist
    required = FEATURE_COLUMNS + [TARGET_SCOPE1, TARGET_SCOPE2]
    missing_cols = [col for col in required if col not in df.columns]

    if missing_cols:
        print(f"ERROR: Missing columns: {missing_cols}")
        return None

    # Check for missing values
    null_counts = df[required].isnull().sum()
    if null_counts.any():
        print(f"WARNING: Missing values found:\n{null_counts}")
        # Drop rows with missing values
        df = df.dropna(subset=required)
        print(f"Rows after dropping nulls: {len(df)}")

    print(f"Training data ready: {len(df)} clean rows")
    return df

# ─────────────────────────────────────────
# FUNCTION 2: Train Model
# ─────────────────────────────────────────
def train_model(df):
    """
    Trains a Random Forest model to predict
    Scope 1 and Scope 2 emissions.

    WHY RANDOM FOREST:
    - Works well with small datasets (50 rows)
    - Handles non-linear relationships
    - Does not overfit easily
    - Gives feature importance scores

    Args:
        df: pandas DataFrame with training data

    Returns:
        tuple (model_scope1, model_scope2, scaler)
    """

    print("\n--- TRAINING ML MODEL ---")

    # Step 1: Separate features and targets
    X = df[FEATURE_COLUMNS]             # input features
    y_scope1 = df[TARGET_SCOPE1]        # target: scope 1
    y_scope2 = df[TARGET_SCOPE2]        # target: scope 2

    print(f"Features shape : {X.shape}")
    print(f"Scope1 range   : {y_scope1.min():.0f} - {y_scope1.max():.0f}")
    print(f"Scope2 range   : {y_scope2.min():.0f} - {y_scope2.max():.0f}")

    # Step 2: Scale features
    # StandardScaler converts all features to same scale
    # So natural_gas (millions) doesn't dominate year (2024)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Step 3: Split into train and test sets
    # 80% for training, 20% for testing
    # random_state=42 ensures same split every run
    X_train, X_test, y1_train, y1_test = train_test_split(
        X_scaled, y_scope1,
        test_size=0.2,
        random_state=42
    )

    # Same split for scope2
    _, _, y2_train, y2_test = train_test_split(
        X_scaled, y_scope2,
        test_size=0.2,
        random_state=42
    )
    # Step 4: Train Scope 1 model
    print("\nTraining Scope 1 model...")

    model_scope1 = RandomForestRegressor(
        n_estimators=100,    # 100 decision trees in the forest
        max_depth=5,         # each tree max 5 levels deep
        random_state=42,     # reproducible results
        min_samples_split=3  # need 3 samples to split a node
    )
    model_scope1.fit(X_train, y1_train)

    # Step 5: Evaluate Scope 1 model
    y1_pred = model_scope1.predict(X_test)
    mae1 = mean_absolute_error(y1_test, y1_pred)
    r2_1 = r2_score(y1_test, y1_pred)

    print(f"Scope 1 Model Performance:")
    print(f"  MAE : {mae1:.2f} tCO2e")
    print(f"  R²  : {r2_1:.4f}")
    print(f"  R²=1 is perfect, R²=0 means model learns nothing")

    # Step 6: Train Scope 2 model
    print("\nTraining Scope 2 model...")

    model_scope2 = RandomForestRegressor(
        n_estimators=100,
        max_depth=5,
        random_state=42,
        min_samples_split=3
    )
    model_scope2.fit(X_train, y2_train)

    # Evaluate Scope 2 model
    y2_pred = model_scope2.predict(X_test)
    mae2 = mean_absolute_error(y2_test, y2_pred)
    r2_2 = r2_score(y2_test, y2_pred)

    print(f"Scope 2 Model Performance:")
    print(f"  MAE : {mae2:.2f} tCO2e")
    print(f"  R²  : {r2_2:.4f}")

    # Step 7: Print feature importance
    # Shows which input features matter most
    print("\nFeature Importance (Scope 1):")
    importance = model_scope1.feature_importances_
    for col, imp in sorted(
        zip(FEATURE_COLUMNS, importance),
        key=lambda x: x[1],
        reverse=True
    ):
        bar = "█" * int(imp * 30)
        print(f"  {col:<35} {bar} {imp:.4f}")

    return model_scope1, model_scope2, scaler

# ─────────────────────────────────────────
# FUNCTION 3: Save Model
# ─────────────────────────────────────────
def save_model(model_scope1, model_scope2, scaler):
    """
    Saves trained models and scaler to disk.
    So we don't retrain every time app runs.

    Args:
        model_scope1 : trained Scope 1 model
        model_scope2 : trained Scope 2 model
        scaler       : fitted StandardScaler
    """

    # Create models folder if it doesn't exist
    os.makedirs("models", exist_ok=True)

    # Save both models together in one file
    model_bundle = {
        "model_scope1" : model_scope1,
        "model_scope2" : model_scope2,
        "scaler"       : scaler,
        "features"     : FEATURE_COLUMNS
    }

    joblib.dump(model_bundle, MODEL_PATH)
    print(f"\nModel saved to: {MODEL_PATH}")

    # ─────────────────────────────────────────
# FUNCTION 4: Load Model
# ─────────────────────────────────────────
def load_model():
    """
    Loads previously trained model from disk.
    If model doesn't exist, trains a new one.

    Returns:
        model_bundle dictionary or None
    """

    # If model file exists load it
    if os.path.exists(MODEL_PATH):
        model_bundle = joblib.load(MODEL_PATH)
        print(f"Model loaded from: {MODEL_PATH}")
        return model_bundle

    # Otherwise train a new model
    print("No saved model found. Training new model...")

    df = load_training_data()
    if df is None:
        return None

    model_scope1, model_scope2, scaler = train_model(df)
    save_model(model_scope1, model_scope2, scaler)

    return {
        "model_scope1" : model_scope1,
        "model_scope2" : model_scope2,
        "scaler"       : scaler,
        "features"     : FEATURE_COLUMNS
    }

# ─────────────────────────────────────────
# FUNCTION 5: Predict Missing Values
# ─────────────────────────────────────────
def predict_missing(parsed_data):
    """
    Main function — detects which values are missing
    from the PDF parser output and predicts them.

    This is called when pdf_parser returns None
    for scope1 or scope2.

    Args:
        parsed_data: dictionary from pdf_parser.parse_pdf()

    Returns:
        updated dictionary with predicted values filled in
    """

    print("\n--- ML PREDICTOR ---")

    # Check what is missing
    scope1 = parsed_data.get("scope1_tco2e")
    scope2_reported = parsed_data.get("scope2_reported_tco2e")
    urea_production = parsed_data.get("urea_production_mt")

    # If nothing is missing return as is
    if scope1 is not None and scope2_reported is not None:
        print("No missing values detected. ML prediction not needed.")
        return parsed_data

    print(f"Missing values detected:")
    print(f"  scope1  : {scope1}")
    print(f"  scope2  : {scope2_reported}")

    # Build feature vector for prediction
    # Use available data from parser
    natural_gas = parsed_data.get(
        "natural_gas_mmbtu", 2017011  # default from 2024-25
    )
    electricity_per_mt = parsed_data.get(
        "electricity_kwh_per_mt_urea", 425.25
    )
    capacity_util = parsed_data.get(
        "capacity_utilization_pct", 116.8
    )
    energy_intensity = parsed_data.get(
        "energy_intensity_gj_per_mt", 5.2
    )
    year = parsed_data.get("year", "2024-25")

    # Convert year string to number
    # "2024-25" → 2024
    try:
        year_num = int(str(year).split("-")[0])
    except:
        year_num = 2024

    # Build feature row
    features = [[
        natural_gas,
        electricity_per_mt,
        urea_production if urea_production else 443322,
        capacity_util,
        energy_intensity,
        year_num
    ]]

    print(f"\nFeature vector for prediction:")
    for col, val in zip(FEATURE_COLUMNS, features[0]):
        print(f"  {col}: {val}")

        # Load model
    model_bundle = load_model()
    if model_bundle is None:
        print("ERROR: Could not load or train model.")
        return parsed_data

    model_scope1 = model_bundle["model_scope1"]
    model_scope2 = model_bundle["model_scope2"]
    scaler       = model_bundle["scaler"]

    # Scale features using same scaler as training
    features_scaled = scaler.transform(features)

    # Predict missing values
    result = parsed_data.copy()

    if scope1 is None:
        predicted_scope1 = model_scope1.predict(features_scaled)[0]
        predicted_scope1 = round(predicted_scope1, 2)
        result["scope1_tco2e"] = predicted_scope1
        result["scope1_predicted"] = True
        print(f"\n✅ Scope 1 PREDICTED: {predicted_scope1} tCO2e")
    else:
        result["scope1_predicted"] = False
        print(f"✅ Scope 1 from report: {scope1} tCO2e")

    if scope2_reported is None:
        predicted_scope2 = model_scope2.predict(features_scaled)[0]
        predicted_scope2 = round(predicted_scope2, 2)
        result["scope2_reported_tco2e"] = predicted_scope2
        result["scope2_predicted"] = True
        print(f"✅ Scope 2 PREDICTED: {predicted_scope2} tCO2e")
    else:
        result["scope2_predicted"] = False
        print(f"✅ Scope 2 from report: {scope2_reported} tCO2e")

    return result

# ─────────────────────────────────────────
# FUNCTION 6: Retrain Model
# ─────────────────────────────────────────
def retrain_model():
    """
    Forces retraining of model from scratch.
    Call this when new training data is added.

    Returns:
        True if successful, False if failed
    """

    print("\n--- RETRAINING MODEL ---")

    df = load_training_data()
    if df is None:
        return False

    model_scope1, model_scope2, scaler = train_model(df)
    save_model(model_scope1, model_scope2, scaler)

    print("Model retrained and saved successfully.")
    return True

# ─────────────────────────────────────────
# RUN THIS FILE DIRECTLY TO TEST
# ─────────────────────────────────────────
if __name__ == "__main__":

    print("="*50)
    print("TEST 1: Train model on training data")
    print("="*50)
    retrain_model()

    print("\n" + "="*50)
    print("TEST 2: Predict with complete data (nothing missing)")
    print("="*50)

    # Simulate complete parsed data
    complete_data = {
        "year"                  : "2024-25",
        "scope1_tco2e"          : 296036.0,
        "scope2_reported_tco2e" : 0.0,
        "urea_production_mt"    : 443322.0,
        "urea_share_pct"        : 56.72
    }
    result1 = predict_missing(complete_data)
    print(f"scope1 predicted: {result1.get('scope1_predicted')}")

    print("\n" + "="*50)
    print("TEST 3: Predict with missing Scope 1")
    print("="*50)

    # Simulate incomplete parsed data
    incomplete_data = {
        "year"                  : "2022-23",
        "scope1_tco2e"          : None,      # MISSING
        "scope2_reported_tco2e" : 2100.0,
        "urea_production_mt"    : 420000.0,
        "urea_share_pct"        : 56.5,
        "natural_gas_mmbtu"     : 2100000,
        "electricity_kwh_per_mt_urea" : 445.0,
        "capacity_utilization_pct"    : 110.7,
        "energy_intensity_gj_per_mt"  : 4.8
    }
    result2 = predict_missing(incomplete_data)
    print(f"\nPredicted Scope 1 : {result2['scope1_tco2e']} tCO2e")
    print(f"Actual Scope 1    : ~275,000 tCO2e (expected range)")

    print("\n" + "="*50)
    print("TEST 4: Predict with missing Scope 2")
    print("="*50)

    incomplete_data2 = {
        "year"                  : "2021-22",
        "scope1_tco2e"          : 270000.0,
        "scope2_reported_tco2e" : None,      # MISSING
        "urea_production_mt"    : 410000.0,
        "urea_share_pct"        : 56.3,
        "natural_gas_mmbtu"     : 2150000,
        "electricity_kwh_per_mt_urea" : 450.0,
        "capacity_utilization_pct"    : 108.0,
        "energy_intensity_gj_per_mt"  : 4.9
    }
    result3 = predict_missing(incomplete_data2)
    print(f"\nPredicted Scope 2 : {result3['scope2_reported_tco2e']} tCO2e")
    print(f"Expected range    : 2,000 - 2,500 tCO2e")