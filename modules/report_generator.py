from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
import os

def generate_report(data):
    os.makedirs("outputs", exist_ok=True)
    doc = SimpleDocTemplate("outputs/cbam_report.pdf", pagesize=A4)
    styles = getSampleStyleSheet()

    content = []

    # Title
    content.append(Paragraph("CBAM Emissions Report", styles["Title"]))
    content.append(Spacer(1, 12))

    # Section 1: Company Info
    content.append(Paragraph("1. Company & Shipment Details", styles["Heading2"]))
    content.append(Paragraph(f"Company: {data['company']}", styles["Normal"]))
    content.append(Paragraph(f"Shipment: {data['shipment_tonnes']} tonnes", styles["Normal"]))
    content.append(Paragraph(f"Destination: {data['destination']}", styles["Normal"]))
    content.append(Spacer(1, 12))

    # Section 2: Emissions
    content.append(Paragraph("2. Embedded Emissions", styles["Heading2"]))
    content.append(Paragraph(
        f"Emissions per tonne: {data['emissions_per_tonne']} tCO2",
        styles["Normal"]
    ))
    content.append(Spacer(1, 12))

    # Section 3: Calculation
    content.append(Paragraph("3. Calculation Methodology", styles["Heading2"]))
    content.append(Paragraph(
        "Total emissions calculated using Scope 1 and Scope 2 data "
        "from sustainability reports and grid emission factors.",
        styles["Normal"]
    ))
    content.append(Spacer(1, 12))

    # Section 4: EU Comparison
    content.append(Paragraph("4. EU Default Comparison", styles["Heading2"]))
    content.append(Paragraph(
        "EU default emission factor: 3.5 tCO2 per tonne",
        styles["Normal"]
    ))
    content.append(Spacer(1, 12))

    # Section 5: Tax Liability
    content.append(Paragraph("5. Carbon Tax Liability", styles["Heading2"]))
    content.append(Paragraph(
        f"Estimated tax: €{data['tax_liability']}",
        styles["Normal"]
    ))
    content.append(Paragraph(
        f"Confidence interval: {data['confidence_interval']}",
        styles["Normal"]
    ))
    content.append(Spacer(1, 12))

    # Section 6: Declaration
    content.append(Paragraph("6. Declaration", styles["Heading2"]))
    content.append(Paragraph(
        "This report is generated for academic simulation of EU CBAM compliance.",
        styles["Normal"]
    ))

    doc.build(content)

    return "outputs/cbam_report.pdf"
