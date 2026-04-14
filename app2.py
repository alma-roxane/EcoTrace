from modules.report_generator import generate_report
import streamlit as st
import pandas as pd
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# ===================== MODEL IMPORT =====================
try:
    from modules.tax_risk_model import predict_tax_risk
except ImportError:
    def predict_tax_risk(shipment_dict):
        tonnes = shipment_dict.get("shipment_tonnes", 1000)
        price = shipment_dict.get("carbon_price_eur", 75)
        emissions = shipment_dict.get("emissions_per_tonne", 2.0)
        tax = tonnes * emissions * price
        score = "Low" if tax < 50000 else ("Medium" if tax < 150000 else "High")
        return {
            "tax_liability": round(tax, 2),
            "risk_score": score,
            "confidence_interval": (round(tax * 0.92, 2), round(tax * 1.08, 2)),
        }

# ===================== CONSTANTS =====================
EU_DEFAULT_EMISSIONS = 3.5

DESTINATION_DISTANCES = {
    "Marseille": 9000,
    "Rotterdam": 10000,
    "Hamburg": 10500,
}

# ===================== PAGE CONFIG =====================
st.set_page_config(
    page_title="Carbon-Trace Mangalore",
    page_icon="🌿",
    layout="wide",
)

# ===================== SESSION STATE =====================
if "report_path" not in st.session_state:
    st.session_state.report_path = None

if "tax_liability" not in st.session_state:
    st.session_state.tax_liability = None

if "risk_score" not in st.session_state:
    st.session_state.risk_score = None

if "ci" not in st.session_state:
    st.session_state.ci = None

# ===================== HEADER =====================
st.title("🌿 Carbon-Trace Mangalore")
st.subheader("EU CBAM Carbon Intelligence Dashboard")

# ===================== INPUT =====================
st.header("📦 Shipment Input")

col1, col2 = st.columns(2)

with col1:
    shipment_tonnes = st.number_input("Shipment (tonnes)", value=1000.0)
    emissions_per_tonne = st.number_input("Emissions (tCO₂/t)", value=2.0)

with col2:
    carbon_price_eur = st.slider("Carbon Price (€)", 50, 100, 75)
    destination = st.selectbox("Destination", list(DESTINATION_DISTANCES.keys()))

distance_km = DESTINATION_DISTANCES[destination]

# ===================== CALCULATE =====================
if st.button("🔍 Calculate Tax Risk"):

    shipment_dict = {
        "shipment_tonnes": shipment_tonnes,
        "distance_km": distance_km,
        "carbon_price_eur": carbon_price_eur,
        "emissions_per_tonne": emissions_per_tonne,
        "season": 2,
    }

    result = predict_tax_risk(shipment_dict)

    # ✅ STORE RESULTS
    st.session_state.tax_liability = result.get("tax_liability", 0)
    st.session_state.risk_score = result.get("risk_score", "Unknown")
    st.session_state.ci = result.get("confidence_interval", (0, 0))

# ===================== RESULTS =====================
if st.session_state.tax_liability is not None:

    st.header("⚡ Results")

    st.metric("💶 Tax Liability (€)", f"{st.session_state.tax_liability:,.0f}")
    st.metric("🎯 Risk Score", st.session_state.risk_score)
    st.write(
        f"Confidence Interval: €{st.session_state.ci[0]:,.0f} – €{st.session_state.ci[1]:,.0f}"
    )

    # ===================== REPORT BUTTON =====================
    if st.button("📄 Generate CBAM Report"):

        st.session_state.report_path = generate_report({
            "company": "MCF",
            "shipment_tonnes": shipment_tonnes,
            "destination": destination,
            "emissions_per_tonne": emissions_per_tonne,
            "tax_liability": st.session_state.tax_liability,
            "confidence_interval": st.session_state.ci
        })

        st.success("Report Generated ✅")

# ===================== DOWNLOAD =====================
if st.session_state.report_path:

    with open(st.session_state.report_path, "rb") as file:
        st.download_button(
            "⬇ Download CBAM Report",
            data=file,
            file_name="cbam_report.pdf",
            mime="application/pdf"
        )

# ===================== SAVINGS =====================
st.header("💰 Savings Summary")

default_tax = shipment_tonnes * EU_DEFAULT_EMISSIONS * carbon_price_eur
actual_tax = shipment_tonnes * emissions_per_tonne * carbon_price_eur
savings = default_tax - actual_tax

st.write(f"EU Default Tax: €{default_tax:,.0f}")
st.write(f"Your Tax: €{actual_tax:,.0f}")
st.write(f"💚 Savings: €{savings:,.0f}")