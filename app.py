from modules.report_generator import generate_report
from modules.pdf_parser import parse_pdf
from modules.report_summarizer import summarize_report
import streamlit as st
import pandas as pd
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from modules.tax_risk_model import predict_tax_risk
except ImportError:
    def predict_tax_risk(shipment_dict):
        tonnes = shipment_dict.get("shipment_tonnes", 1000)
        dist = shipment_dict.get("distance_km", 9000)
        price = shipment_dict.get("carbon_price_eur", 75)
        emissions = shipment_dict.get("emissions_per_tonne", 2.0)
        tax = tonnes * emissions * price
        score = "Low" if tax < 50000 else ("Medium" if tax < 150000 else "High")
        return {
            "tax_liability_eur": round(tax, 2),
            "risk_score": score,
            "confidence_interval": (round(tax * 0.92, 2), round(tax * 1.08, 2)),
        }

EU_DEFAULT_EMISSIONS = 3.5
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GRID_FACTOR_CSV = os.path.join(BASE_DIR, "data", "grid_emission_factors.csv")
TEMP_PDF_PATH = os.path.join(BASE_DIR, "temp.pdf")

DESTINATION_DISTANCES = {
    "Marseille": 9000,
    "Rotterdam": 10000,
    "Hamburg": 10500,
}


def _safe_number(value, default=0.0):
    return float(value) if value is not None else float(default)


def _season_from_month(month):
    if month in (1, 2, 3):
        return 1
    if month in (4, 5, 6):
        return 2
    if month in (7, 8, 9):
        return 3
    return 4

st.set_page_config(
    page_title="Carbon-Trace Mangalore",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Mono:wght@300;400;500&display=swap');

    html, body, [class*="css"] {
        font-family: 'Syne', sans-serif;
    }

    .stApp {
        background: #0b0f1a;
        color: #e8eaf0;
    }

    .main .block-container {
        padding: 2rem 3rem 4rem 3rem;
        max-width: 1300px;
    }

    .hero-header {
        background: linear-gradient(135deg, #0d2137 0%, #0b3d2e 50%, #0d2137 100%);
        border: 1px solid #1e4d3a;
        border-radius: 16px;
        padding: 2.5rem 3rem;
        margin-bottom: 2.5rem;
        position: relative;
        overflow: hidden;
    }

    .hero-header::before {
        content: '';
        position: absolute;
        top: -60px; right: -60px;
        width: 220px; height: 220px;
        border-radius: 50%;
        background: radial-gradient(circle, rgba(52,211,153,0.12) 0%, transparent 70%);
    }

    .hero-title {
        font-size: 2.6rem;
        font-weight: 800;
        letter-spacing: -0.03em;
        color: #ffffff;
        margin: 0 0 0.4rem 0;
        line-height: 1.1;
    }

    .hero-subtitle {
        font-family: 'DM Mono', monospace;
        font-size: 0.85rem;
        color: #34d399;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        margin: 0;
    }

    .section-card {
        background: #111827;
        border: 1px solid #1f2d3d;
        border-radius: 14px;
        padding: 1.8rem 2rem;
        margin-bottom: 1.8rem;
        position: relative;
    }

    .section-tag {
        font-family: 'DM Mono', monospace;
        font-size: 0.7rem;
        letter-spacing: 0.18em;
        text-transform: uppercase;
        color: #6b7280;
        margin-bottom: 0.3rem;
    }

    .section-title {
        font-size: 1.25rem;
        font-weight: 700;
        color: #f1f5f9;
        margin: 0 0 1.4rem 0;
    }

    .metric-chip {
        background: #1a2535;
        border: 1px solid #263347;
        border-radius: 10px;
        padding: 1rem 1.3rem;
        margin-bottom: 0.8rem;
    }

    .metric-chip-label {
        font-family: 'DM Mono', monospace;
        font-size: 0.7rem;
        color: #6b7280;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        margin-bottom: 0.3rem;
    }

    .metric-chip-value {
        font-size: 1.6rem;
        font-weight: 800;
        color: #f1f5f9;
        line-height: 1;
    }

    .metric-chip-unit {
        font-family: 'DM Mono', monospace;
        font-size: 0.8rem;
        color: #9ca3af;
        margin-left: 0.3rem;
    }

    .savings-highlight {
        background: linear-gradient(135deg, #052e16, #064e3b);
        border: 1px solid #065f46;
        border-radius: 12px;
        padding: 1.4rem 1.8rem;
        text-align: center;
    }

    .savings-label {
        font-family: 'DM Mono', monospace;
        font-size: 0.72rem;
        color: #6ee7b7;
        text-transform: uppercase;
        letter-spacing: 0.15em;
        margin-bottom: 0.5rem;
    }

    .savings-value {
        font-size: 2.4rem;
        font-weight: 800;
        color: #34d399;
    }

    .confidence-band {
        font-family: 'DM Mono', monospace;
        font-size: 0.8rem;
        color: #9ca3af;
        background: #1a2535;
        border-radius: 6px;
        padding: 0.5rem 0.9rem;
        margin-top: 0.8rem;
        display: inline-block;
    }

    div[data-testid="stButton"] > button {
        background: linear-gradient(135deg, #065f46, #0d9488);
        color: white;
        font-family: 'Syne', sans-serif;
        font-weight: 700;
        font-size: 0.95rem;
        letter-spacing: 0.04em;
        border: none;
        border-radius: 10px;
        padding: 0.65rem 2.2rem;
        transition: all 0.2s ease;
        width: 100%;
    }

    div[data-testid="stButton"] > button:hover {
        background: linear-gradient(135deg, #047857, #0f766e);
        transform: translateY(-1px);
        box-shadow: 0 6px 20px rgba(52,211,153,0.25);
    }

    label[data-testid="stWidgetLabel"] {
        font-family: 'DM Mono', monospace !important;
        font-size: 0.75rem !important;
        color: #9ca3af !important;
        text-transform: uppercase !important;
        letter-spacing: 0.1em !important;
    }

    .stSlider [data-baseweb="slider"] div[role="slider"] {
        background: #34d399;
    }

    .divider {
        border: none;
        border-top: 1px solid #1f2d3d;
        margin: 1.5rem 0;
    }

    .badge-low {
        background: #052e16;
        color: #34d399;
        border: 1px solid #065f46;
        border-radius: 99px;
        padding: 0.25rem 0.9rem;
        font-family: 'DM Mono', monospace;
        font-size: 0.8rem;
        font-weight: 500;
    }

    .badge-medium {
        background: #1c1003;
        color: #fbbf24;
        border: 1px solid #78350f;
        border-radius: 99px;
        padding: 0.25rem 0.9rem;
        font-family: 'DM Mono', monospace;
        font-size: 0.8rem;
        font-weight: 500;
    }

    .badge-high {
        background: #1f0505;
        color: #f87171;
        border: 1px solid #7f1d1d;
        border-radius: 99px;
        padding: 0.25rem 0.9rem;
        font-family: 'DM Mono', monospace;
        font-size: 0.8rem;
        font-weight: 500;
    }

    .stSelectbox [data-baseweb="select"] {
        background: #1a2535;
    }

    [data-testid="stMetricValue"] {
        font-family: 'Syne', sans-serif;
        font-weight: 800;
        color: #f1f5f9;
    }

    .footnote {
        font-family: 'DM Mono', monospace;
        font-size: 0.68rem;
        color: #4b5563;
        margin-top: 2rem;
        text-align: center;
        letter-spacing: 0.06em;
    }
</style>
""", unsafe_allow_html=True)


st.markdown("""
<div class="hero-header">
    <p class="hero-subtitle">🌿 EU CBAM Carbon Intelligence Platform</p>
    <h1 class="hero-title">Carbon-Trace<br>Mangalore</h1>
</div>
""", unsafe_allow_html=True)


st.markdown("""
<div class="section-card">
    <p class="section-tag">Section 01</p>
    <h2 class="section-title">📦 Shipment Input Panel</h2>
</div>
""", unsafe_allow_html=True)

uploaded_file = st.file_uploader("📄 Upload Sustainability Report (PDF)", type=["pdf"])

parsed_data = None
completed_data = None
tax_result = st.session_state.get("tax_result")
report_summary = st.session_state.get("report_summary")

if uploaded_file is not None:
    with open(TEMP_PDF_PATH, "wb") as f:
        f.write(uploaded_file.read())

    try:
        parsed_data = parse_pdf(TEMP_PDF_PATH, GRID_FACTOR_CSV)
        completed_data = parsed_data if parsed_data else {}
        st.success("✅ PDF processed successfully")
        
        # Generate report summary from parsed data
        if completed_data:
            with st.spinner("📄 Generating report summary..."):
                report_summary = summarize_report(completed_data)
                st.session_state["report_summary"] = report_summary
        
    except Exception as exc:
        st.error(f"PDF processing failed: {exc}")
        completed_data = None

if completed_data:
    extracted_scope1 = _safe_number(completed_data.get("scope1_tco2e"))
    extracted_scope2 = _safe_number(
        completed_data.get("scope2_cbam_tco2e", completed_data.get("scope2_reported_tco2e"))
    )
    extracted_production = _safe_number(completed_data.get("urea_production_mt"), default=1.0)
    extracted_year = completed_data.get("year", "Unknown")

    st.markdown("""
    <div class="metric-chip" style="margin-bottom:1rem;">
        <div class="metric-chip-label">Parsed Reporting Year</div>
        <div class="metric-chip-value" style="font-size:1.05rem;">PDF Data Ready</div>
    </div>
    """, unsafe_allow_html=True)
    st.caption(f"Reporting year detected: `{extracted_year}`")

    # Display report summary
    if report_summary:
        st.markdown("""
    <div class="section-card" style="background: linear-gradient(135deg, #0d2137 0%, #0b3d2e 50%, #0d2137 100%); border: 1.5px solid #34d399; margin-bottom: 1.5rem;">
        <p class="section-tag">📄 REPORT SUMMARY</p>
        <h3 style="font-size: 1.05rem; font-weight: 600; color: #34d399; margin-bottom: 0.8rem;">Sustainability Report Summary</h3>
        <p style="font-size: 0.95rem; line-height: 1.6; color: #e8eaf0; font-family: 'DM Mono', monospace;">"""
    + report_summary.get('executive_summary', 'Summary pending...').replace('\n', '<br>') +
    """</p>
    </div>
    """, unsafe_allow_html=True)
    
    if report_summary:
        st.markdown(f"""
        <div class="section-card">
            <p class="section-tag">📊 KEY EMISSIONS METRICS</p>
            <div style="font-size: 0.9rem; line-height: 1.8; color: #e8eaf0; font-family: 'DM Mono', monospace;">
        """ + report_summary.get('key_metrics', '').replace('\n', '<br>') + 
        """</div>
        </div>
        """, unsafe_allow_html=True)


    override_col1, override_col2, override_col3 = st.columns(3)
    with override_col1:
        scope1 = st.number_input(
            "Manual Override Scope 1 (tCO₂)",
            min_value=0.0,
            value=float(round(extracted_scope1, 2)),
            step=100.0,
        )
    with override_col2:
        scope2 = st.number_input(
            "Manual Override Scope 2 (tCO₂)",
            min_value=0.0,
            value=float(round(extracted_scope2, 2)),
            step=50.0,
        )
    with override_col3:
        production = st.number_input(
            "Manual Override Production (tonnes)",
            min_value=1.0,
            value=float(round(extracted_production, 2)),
            step=100.0,
        )

    emissions_per_tonne = (scope1 + scope2) / max(production, 1.0)

    with st.expander("📊 Extracted Data"):
        st.write(completed_data)
else:
    scope1 = 0.0
    scope2 = 0.0
    production = 1.0

with st.container():
    col1, col2, col3 = st.columns([1.2, 1.2, 1])

    with col1:
        shipment_tonnes = st.number_input(
            "Shipment Size (tonnes)",
            min_value=1.0,
            max_value=100000.0,
            value=1000.0,
            step=50.0,
        )
        if completed_data:
            st.markdown(f"""
            <div class="metric-chip">
            <div class="metric-chip-label">Auto Calculated Emissions</div>
            <div class="metric-chip-value">{emissions_per_tonne:.2f}<span class="metric-chip-unit">tCO₂/t</span></div>
            </div>
            """, unsafe_allow_html=True)

        else:
            emissions_per_tonne = st.number_input(
                "Emissions per Tonne (tCO₂/t)",
                min_value=0.1,
                max_value=10.0,
                value=2.0,
                step=0.1,
                format="%.2f",
            )

    with col2:
        carbon_price_eur = st.slider(
            "Carbon Price (€/tCO₂)",
            min_value=50,
            max_value=100,
            value=75,
            step=1,
        )
        destination = st.selectbox(
            "Destination Port",
            options=list(DESTINATION_DISTANCES.keys()),
        )
        shipment_month = st.selectbox(
            "Shipment Month",
            options=list(range(1, 13)),
            index=3,
            format_func=lambda month: f"Month {month}",
        )

    with col3:
        distance_km = DESTINATION_DISTANCES[destination]
        season = _season_from_month(shipment_month)
        st.markdown(f"""
        <div class="metric-chip" style="margin-top:1.85rem;">
            <div class="metric-chip-label">🚢 Route Distance</div>
            <div class="metric-chip-value">{distance_km:,}<span class="metric-chip-unit">km</span></div>
        </div>
        <div class="metric-chip">
            <div class="metric-chip-label">📍 Destination</div>
            <div class="metric-chip-value" style="font-size:1.1rem; padding-top:0.2rem;">{destination}</div>
        </div>
        <div class="metric-chip">
            <div class="metric-chip-label">📅 Season</div>
            <div class="metric-chip-value" style="font-size:1.1rem; padding-top:0.2rem;">Q{season}</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<hr class='divider'>", unsafe_allow_html=True)


st.markdown("""
<div class="section-card" style="margin-top:0.5rem">
    <p class="section-tag">Section 02</p>
    <h2 class="section-title">📊 Emissions Summary</h2>
</div>
""", unsafe_allow_html=True)

col_a, col_b = st.columns([1, 1.5])

with col_a:
    st.markdown(f"""
    <div class="metric-chip">
        <div class="metric-chip-label">Your Reported Emissions</div>
        <div class="metric-chip-value">{emissions_per_tonne:.2f}<span class="metric-chip-unit">tCO₂/t</span></div>
    </div>
    <div class="metric-chip">
        <div class="metric-chip-label">EU Default Benchmark</div>
        <div class="metric-chip-value">{EU_DEFAULT_EMISSIONS}<span class="metric-chip-unit">tCO₂/t</span></div>
    </div>
    """, unsafe_allow_html=True)

    delta = ((emissions_per_tonne - EU_DEFAULT_EMISSIONS) / EU_DEFAULT_EMISSIONS) * 100
    direction = "below" if delta < 0 else "above"
    color = "#34d399" if delta < 0 else "#f87171"
    st.markdown(f"""
    <div style="margin-top:0.8rem; font-family:'DM Mono',monospace; font-size:0.78rem; color:{color};">
        {'▼' if delta < 0 else '▲'} {abs(delta):.1f}% {direction} EU default
    </div>
    """, unsafe_allow_html=True)

with col_b:
    emissions_chart_data = pd.DataFrame({
        "Source": ["Your Emissions", "EU Default"],
        "tCO₂ per tonne": [emissions_per_tonne, EU_DEFAULT_EMISSIONS],
    }).set_index("Source")
    st.bar_chart(emissions_chart_data, color=["#34d399"])

st.markdown("<hr class='divider'>", unsafe_allow_html=True)


st.markdown("""
<div class="section-card" style="margin-top:0.5rem">
    <p class="section-tag">Section 03</p>
    <h2 class="section-title">⚡ Tax Risk Assessment</h2>
</div>
""", unsafe_allow_html=True)

col_btn, col_res = st.columns([1, 2])

with col_btn:
    calculate = st.button("🔍 Calculate Tax Risk")

if calculate:
    shipment_dict = {
        "shipment_tonnes": shipment_tonnes,
        "distance_km": distance_km,
        "carbon_price_eur": carbon_price_eur,
        "emissions_per_tonne": emissions_per_tonne,
        "season": season,
    }

    with st.spinner("Running risk model..."):
        result = predict_tax_risk(shipment_dict)
        st.session_state["tax_result"] = result
        tax_result = result

if tax_result:
    tax_liability = tax_result.get("tax_liability", 0)
    risk_score = tax_result.get("risk_score", "Unknown")
    ci = tax_result.get("confidence_interval", (0, 0))

    col_r1, col_r2, col_r3 = st.columns(3)

    with col_r1:
        st.markdown(f"""
        <div class="metric-chip">
            <div class="metric-chip-label">💶 Tax Liability</div>
            <div class="metric-chip-value" style="font-size:1.45rem;">€{tax_liability:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)

    with col_r2:
        badge_class = f"badge-{risk_score.lower()}"
        st.markdown(f"""
        <div class="metric-chip">
            <div class="metric-chip-label">🎯 Risk Score</div>
            <div style="margin-top:0.5rem;"><span class="{badge_class}">{risk_score}</span></div>
        </div>
        """, unsafe_allow_html=True)

    with col_r3:
        st.markdown(f"""
        <div class="metric-chip">
            <div class="metric-chip-label">📐 Confidence Interval</div>
            <div class="confidence-band">€{ci[0]:,.0f} — €{ci[1]:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='margin-top:1rem;'>", unsafe_allow_html=True)
    if risk_score == "Low":
        st.success(f"✅ **Low Risk** — Your emissions are well within CBAM thresholds. Estimated tax: **€{tax_liability:,.0f}**")
    elif risk_score == "Medium":
        st.warning(f"⚠️ **Medium Risk** — Your tax liability is moderate. Consider optimisation strategies. Estimated: **€{tax_liability:,.0f}**")
    elif risk_score == "High":
        st.error(f"🚨 **High Risk** — Significant CBAM exposure detected. Immediate review recommended. Estimated: **€{tax_liability:,.0f}**")
    st.markdown("</div>", unsafe_allow_html=True)
    if st.button("📄 Generate CBAM Report"):
        report_path = generate_report({
            "company": "MCF",
            "shipment_tonnes": shipment_tonnes,
            "destination": destination,
            "emissions_per_tonne": emissions_per_tonne,
            "tax_liability": tax_liability,
            "confidence_interval": ci
        })

        if report_path and os.path.exists(report_path):
            with open(report_path, "rb") as file:
                st.download_button(
                    label="⬇ Download Report",
                    data=file,
                    file_name="cbam_report.pdf",
                    mime="application/pdf"
                )
else:
    st.markdown("""
    <div style="text-align:center; padding: 2rem; color: #4b5563; font-family:'DM Mono',monospace; font-size:0.8rem;">
        ↑ Configure inputs above and click <strong style="color:#34d399;">Calculate Tax Risk</strong>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<hr class='divider'>", unsafe_allow_html=True)


st.markdown("""
<div class="section-card" style="margin-top:0.5rem">
    <p class="section-tag">Section 04</p>
    <h2 class="section-title">💰 Savings Summary</h2>
</div>
""", unsafe_allow_html=True)

default_tax = shipment_tonnes * EU_DEFAULT_EMISSIONS * carbon_price_eur
actual_tax = shipment_tonnes * emissions_per_tonne * carbon_price_eur
savings = default_tax - actual_tax

col_s1, col_s2, col_s3 = st.columns(3)

with col_s1:
    st.markdown(f"""
    <div class="metric-chip">
        <div class="metric-chip-label">🏛️ EU Default Tax</div>
        <div class="metric-chip-value" style="font-size:1.4rem; color:#f87171;">€{default_tax:,.0f}</div>
    </div>
    """, unsafe_allow_html=True)

with col_s2:
    st.markdown(f"""
    <div class="metric-chip">
        <div class="metric-chip-label">🏭 Your Actual Tax</div>
        <div class="metric-chip-value" style="font-size:1.4rem; color:#60a5fa;">€{actual_tax:,.0f}</div>
    </div>
    """, unsafe_allow_html=True)

with col_s3:
    savings_color = "#34d399" if savings >= 0 else "#f87171"
    savings_label = "💚 You Save" if savings >= 0 else "🔴 Extra Cost"
    st.markdown(f"""
    <div class="savings-highlight">
        <div class="savings-label">{savings_label}</div>
        <div class="savings-value" style="color:{savings_color};">€{abs(savings):,.0f}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='margin-top:1.5rem;'>", unsafe_allow_html=True)

tax_chart_data = pd.DataFrame({
    "Tax Type": ["EU Default Tax", "Your Actual Tax"],
    "Amount (€)": [round(default_tax, 2), round(actual_tax, 2)],
}).set_index("Tax Type")

st.bar_chart(tax_chart_data, color=["#34d399"])

st.markdown("</div>", unsafe_allow_html=True)

st.markdown("""
<p class="footnote">
    Carbon-Trace Mangalore · EU CBAM Simulation Dashboard · Fertiliser Export Emissions Intelligence<br>
    Emissions benchmark: EU default 3.5 tCO₂/tonne · Data for illustrative purposes only
</p>
""", unsafe_allow_html=True)
