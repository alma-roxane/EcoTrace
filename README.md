# 🌿 Carbon-Trace Mangalore

### EU CBAM Carbon Intelligence Platform for Fertilizer Exports

---

## 📌 Overview

**Carbon-Trace Mangalore** is an AI-powered sustainability intelligence platform designed to help fertilizer companies comply with the **EU Carbon Border Adjustment Mechanism (CBAM)**.

It automates:

* 📄 Extraction of emissions data from sustainability reports (PDF)
* 🤖 Prediction of missing emissions using Machine Learning
* 📊 Calculation of CBAM-compliant embedded emissions
* 💶 Carbon tax estimation & risk classification
* 📑 Generation of CBAM-ready reports

---

## 🚀 Key Features

### 📄 1. PDF Data Extraction

* Extracts:

  * Scope 1 emissions
  * Scope 2 emissions
  * Electricity usage
  * Urea production
* Uses **pdfplumber + regex-based parsing**

---

### 🤖 2. ML-Based Missing Data Prediction

* Uses **Random Forest Regressor**
* Predicts:

  * Missing Scope 1
  * Missing Scope 2
* Based on:

  * Natural gas usage
  * Energy intensity
  * Production volume

---

### 📊 3. CBAM Emissions Calculator

* Calculates:

  * Embedded emissions (tCO₂/tonne)
  * Shipment emissions
* Handles:

  * Renewable energy proof validation (REC, GoO, PPA, TPV)
  * Scope 1 allocation to urea

---

### 💶 4. Carbon Tax & Risk Prediction

* Uses **Gradient Boosting Regressor**
* Outputs:

  * Tax liability (€)
  * Risk category (Low / Medium / High)
  * Confidence interval (±8%)

---

### 📈 5. Interactive Dashboard (Streamlit)

* Upload PDF → auto analysis
* Manual override options
* Visual comparisons:

  * Your emissions vs EU benchmark
* Real-time tax simulation

---

### 📑 6. Report Generation

* Generates downloadable **CBAM report (PDF)**
* Includes:

  * Emissions summary
  * Tax liability
  * Methodology

---

## 🏗️ Project Structure

```
EcoTrace/
│
├── app.py                  # Streamlit dashboard (main app)
├── app2.py                 # (optional/alternate UI)
│
├── modules/
│   ├── pdf_parser.py       # Extract data from PDF
│   ├── emissions_calc.py   # CBAM emissions calculations
│   ├── ml_predictor.py     # ML prediction for missing data
│   ├── tax_risk_model.py   # Tax risk prediction model
│   ├── report_generator.py # Generate PDF report
│
├── data/
│   ├── sample_reports/     # Sample sustainability reports
│   ├── grid_emission_factors.csv
│   ├── training_data.csv
│   ├── tax_risk_data.csv
│
├── outputs/                # Generated reports
├── requirement.txt
├── README.md
```

---

## ⚙️ Installation

### 1️⃣ Clone the Repository

```bash
git clone https://github.com/your-username/EcoTrace.git
cd EcoTrace
```

### 2️⃣ Create Virtual Environment

```bash
python -m venv venv
venv\Scripts\activate   # Windows
```

### 3️⃣ Install Dependencies

```bash
pip install -r requirement.txt
```

---

## ▶️ How to Run

```bash
streamlit run app.py
```

Then open in browser:

```
http://localhost:8501
```

---

## 🧠 Workflow

```
Upload PDF
     ↓
PDF Parser (extract emissions data)
     ↓
ML Predictor (fill missing values)
     ↓
Emissions Calculator (CBAM logic)
     ↓
Tax Risk Model (AI prediction)
     ↓
Dashboard Visualization
     ↓
Generate CBAM Report
```

---

## 📊 Key Formula (CBAM)

Embedded Emissions:

\text{Embedded Emissions} = \frac{\text{Scope 1} + \text{Scope 2}}{\text{Production}}

---

## 🌍 EU Benchmark

* Default Emission Factor: **3.5 tCO₂/tonne**
* Carbon Price: **€50 – €100 / tCO₂**

---

## 🧪 Example Use Case

1. Upload MCF sustainability report PDF
2. System extracts emissions data
3. Missing values predicted using ML
4. User inputs shipment details
5. Dashboard shows:

   * Emissions per tonne
   * Tax liability
   * Risk score
6. Generate CBAM report

---

## 📌 Technologies Used

* **Python**
* **Streamlit**
* **Scikit-learn**
* **Pandas & NumPy**
* **pdfplumber**
* **ReportLab**

---

## ⚠️ Notes

* This project is for **academic simulation of CBAM compliance**
* Real-world CBAM reporting requires certified verification

---

## 👩‍💻 Authors
* Alma Roxane Periera
* Avani Linora Dsouza
* Team EcoTrace (PBL Project)

---

## ⭐ Future Enhancements

* Multi-product CBAM support
* Real-time carbon price API
* Blockchain-based emissions verification
* Company benchmarking dashboard

---
