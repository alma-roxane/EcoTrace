# modules/emissions_calc.py
# Calculates CBAM-compliant embedded emissions for urea
# Uses output from pdf_parser.py as input
# Supports renewable energy proof verification for Scope 2

import os

EU_DEFAULT_UREA = 1.6        # tCO2e per tonne of urea
EU_CARBON_PRICE = 65.0       # EUR per tonne CO2e
DEFAULT_SHIPMENT_MT = 10000  # 10,000 tonnes to Marseille

VALID_PROOF_TYPES = [
    "REC",   # Renewable Energy Certificate
    "GoO",   # Guarantee of Origin certificate
    "PPA",   # Power Purchase Agreement
    "TPV"    # Third Party Verified sustainability report
]


# ─────────────────────────────────────────
# FUNCTION 1: Determine Scope 2

def determine_scope2(scope2_reported, scope2_cbam,
                     renewable_proof=None):
    """
    Decides which Scope 2 value to use based on
    whether company has provided valid renewable proof.

    Under EU CBAM FAQ (official document, page 21):
    Market-based certificates like REC and GoO can
    justify using actual emission factors ONLY if
    verified by an accredited third party.

    Args:
        scope2_reported : value from company report (0 for MCF)
        scope2_cbam     : grid factor calculation (9,074 for MCF)
        renewable_proof : proof type string or None

    Returns:
        tuple (scope2_value, proof_status, reason)
    """

    # Case 1: Valid proof provided
    # Company has REC, GoO, PPA or TPV certificate
    if renewable_proof in VALID_PROOF_TYPES:

        print(f"\n--- SCOPE 2 DETERMINATION ---")
        print(f"  Proof type      : {renewable_proof} ")
        print(f"  Status          : Valid renewable proof accepted")
        print(f"  Scope 2 used    : {scope2_reported} tCO2e")
        print(f"  Reason          : Company verified renewable energy use")

        return (
            scope2_reported,       # use 0 from report
            "VERIFIED",            # proof status
            f"{renewable_proof} certificate accepted"
        )
    
    # Case 2: Proof provided but not a recognised type
    # Company uploaded something but it is not valid
    elif renewable_proof is not None:

        print(f"\n--- SCOPE 2 DETERMINATION ---")
        print(f"  Proof type      : {renewable_proof} ")
        print(f"  Status          : Invalid proof type")
        print(f"  Valid types are : {VALID_PROOF_TYPES}")
        print(f"  Scope 2 used    : {scope2_cbam} tCO2e")
        print(f"  Reason          : Falling back to grid calculation")

        return (
            scope2_cbam,           # use grid calculation
            "INVALID_PROOF",       # proof status
            f"{renewable_proof} is not a recognised proof type"
        )
    
    # Case 3: No proof provided at all
    # Default to CBAM grid factor calculation
    else:

        print(f"\n--- SCOPE 2 DETERMINATION ---")
        print(f"  Proof type      : None provided")
        print(f"  Status          : No renewable proof")
        print(f"  Scope 2 used    : {scope2_cbam} tCO2e")
        print(f"  Reason          : CBAM grid factor applied")

        return (
            scope2_cbam,           # use grid calculation
            "NO_PROOF",            # proof status
            "No renewable energy proof provided"
        )
    
    # ─────────────────────────────────────────
# FUNCTION 2: Allocate Scope 1 To Urea
# ─────────────────────────────────────────
def allocate_scope1(scope1_total, urea_share_pct):
    """
    Applies urea production share to total plant Scope 1.

    WHY:
    Scope 1 from report = entire plant emissions
    CBAM needs urea specific emissions only
    Same 56.7% share used as electricity allocation

    Args:
        scope1_total   : total plant Scope 1 from PDF (tCO2e)
        urea_share_pct : urea percentage of total production

    Returns:
        scope1 allocated to urea in tCO2e
    """

    # Safety check — scope1 must exist
    if scope1_total is None:
        print("WARNING: Scope 1 is None. Cannot allocate.")
        return None

    # Safety check — share must be valid percentage
    if urea_share_pct is None or urea_share_pct <= 0 or urea_share_pct > 100:
        print(f"WARNING: Invalid urea share {urea_share_pct}%")
        return None

    # Convert percentage to decimal
    # 56.7% → 0.567
    urea_share_decimal = urea_share_pct / 100

    # Apply share to total Scope 1
    scope1_urea = scope1_total * urea_share_decimal

    scope1_urea = round(scope1_urea, 2)

    print(f"\n--- SCOPE 1 ALLOCATION ---")
    print(f"  Total plant Scope 1 : {scope1_total:,.2f} tCO2e")
    print(f"  Urea share          : {urea_share_pct}%")
    print(f"  Scope 1 for urea    : {scope1_urea:,.2f} tCO2e")

    return scope1_urea

# ─────────────────────────────────────────
# FUNCTION 3: Calculate Embedded Emissions

def calculate_embedded(scope1_urea, scope2_urea,
                        urea_production_mt):
    """
    Core CBAM formula — calculates embedded emissions
    per tonne of urea.

    Formula:
    Embedded = (Scope1_urea + Scope2_urea) / Production

    This single certified number is what MCF submits
    to the EU importer for CBAM compliance.

    Args:
        scope1_urea        : Scope 1 allocated to urea
        scope2_urea        : Scope 2 after proof decision
        urea_production_mt : total urea produced this year

    Returns:
        tuple (embedded_tco2_per_tonne, total_urea_emissions)
    """

    # Safety checks — all three values must exist
    if scope1_urea is None:
        print("ERROR: Scope 1 missing. Cannot calculate.")
        return None

    if scope2_urea is None:
        print("ERROR: Scope 2 missing. Cannot calculate.")
        return None

    if urea_production_mt is None or urea_production_mt == 0:
        print("ERROR: Production is zero. Cannot divide.")
        return None

    # Add Scope 1 and Scope 2 together
    total_urea_emissions = scope1_urea + scope2_urea

    print(f"\n--- EMBEDDED EMISSIONS CALCULATION ---")
    print(f"  Scope 1 (urea)  : {scope1_urea:,.2f} tCO2e")
    print(f"  Scope 2 (urea)  : {scope2_urea:,.2f} tCO2e")
    print(f"  Total emissions : {total_urea_emissions:,.2f} tCO2e")

    # THE CORE CBAM FORMULA
    embedded = total_urea_emissions / urea_production_mt

    # Round to 4 decimal places for precision
    embedded = round(embedded, 4)

    print(f"  Production      : {urea_production_mt:,.0f} MT")
    print(f"  Embedded rate   : {total_urea_emissions:,.2f}"
          f" / {urea_production_mt:,.0f}")
    print(f"                  = {embedded} tCO2/tonne")

    return embedded, round(total_urea_emissions, 2)


# ─────────────────────────────────────────
# FUNCTION 4: Calculate Shipment Emissions
# ─────────────────────────────────────────
def calculate_shipment_emissions(embedded_tco2_per_tonne,
                                  shipment_mt=DEFAULT_SHIPMENT_MT):
    """
    Calculates total CO2 for this specific shipment.

    Different from embedded rate:
    Embedded rate      = certified value per tonne
    Shipment emissions = for THIS specific export order

    Args:
        embedded_tco2_per_tonne : certified CBAM rate
        shipment_mt             : size of shipment in MT

    Returns:
        total shipment emissions in tCO2e
    """

    # Safety checks
    if embedded_tco2_per_tonne is None:
        print("ERROR: Embedded rate missing.")
        return None

    if shipment_mt <= 0:
        print("ERROR: Shipment size must be greater than 0.")
        return None

    # Multiply certified rate by shipment size
    shipment_emissions = embedded_tco2_per_tonne * shipment_mt
    shipment_emissions = round(shipment_emissions, 2)

    print(f"\n--- SHIPMENT EMISSIONS ---")
    print(f"  Embedded rate   : {embedded_tco2_per_tonne} tCO2/t")
    print(f"  Shipment size   : {shipment_mt:,} MT")
    print(f"  Total emissions : {shipment_emissions:,.2f} tCO2e")

    return shipment_emissions

# ─────────────────────────────────────────
# FUNCTION 5: Calculate Avoided Tax

def calculate_avoided_tax(embedded_tco2_per_tonne,
                           shipment_mt=DEFAULT_SHIPMENT_MT,
                           carbon_price=EU_CARBON_PRICE):
    """
    Calculates carbon tax under two scenarios and
    shows how much MCF saves by using our system.

    Scenario 1: EU default rate (without our system)
    Scenario 2: Certified rate  (with our system)
    Saving    : difference between the two

    Args:
        embedded_tco2_per_tonne : our certified CBAM rate
        shipment_mt             : shipment size in MT
        carbon_price            : EU carbon price EUR/tCO2

    Returns:
        dictionary with full tax breakdown
    """

    if embedded_tco2_per_tonne is None:
        print("ERROR: Cannot calculate tax. Missing rate.")
        return None

    # SCENARIO 1 — EU default
    # What MCF pays WITHOUT our system
    eu_default_tax = EU_DEFAULT_UREA * shipment_mt * carbon_price

    # SCENARIO 2 — Certified rate
    # What MCF pays WITH our system
    your_tax = embedded_tco2_per_tonne * shipment_mt * carbon_price

    # SAVING — value our system creates
    avoided_tax = eu_default_tax - your_tax

    print(f"\n--- CARBON TAX COMPARISON ---")
    print(f"  EU default rate : {EU_DEFAULT_UREA} tCO2/t")
    print(f"  Certified rate  : {embedded_tco2_per_tonne} tCO2/t")
    print(f"  Carbon price    : €{carbon_price}/tCO2")
    print(f"  Shipment size   : {shipment_mt:,} MT")
    print(f"\n  EU default tax  : €{eu_default_tax:,.2f}")
    print(f"  Your tax        : €{your_tax:,.2f}")
    print(f"  Avoided tax  : €{avoided_tax:,.2f}")

    return {
        "eu_default_rate"    : EU_DEFAULT_UREA,
        "certified_rate"     : embedded_tco2_per_tonne,
        "carbon_price_eur"   : carbon_price,
        "shipment_mt"        : shipment_mt,
        "eu_default_tax_eur" : round(eu_default_tax, 2),
        "your_tax_eur"       : round(your_tax, 2),
        "avoided_tax_eur"    : round(avoided_tax, 2)
    }

# ─────────────────────────────────────────
# FUNCTION 6: Master Calculate Function
# ─────────────────────────────────────────
def calculate_all(parsed_data,
                  shipment_mt=DEFAULT_SHIPMENT_MT,
                  carbon_price=EU_CARBON_PRICE,
                  renewable_proof=None):
    """
    Master function — calls all functions above in order.
    This is the ONLY function other modules need to call.

    Args:
        parsed_data     : dictionary from pdf_parser.parse_pdf()
        shipment_mt     : size of export shipment in MT
        carbon_price    : EU carbon price in EUR/tCO2
        renewable_proof : proof type string or None
                          e.g. "REC", "GoO", "PPA", "TPV"

    Returns:
        complete CBAM emissions and tax breakdown dictionary
    """

    print("\n" + "="*50)
    print("CARBON-TRACE MANGALORE — EMISSIONS CALCULATOR")
    print("="*50)

    # Step 1: Pull values from parser output
    # Using .get() so missing keys return None safely
    scope1_total    = parsed_data.get("scope1_tco2e")
    scope2_reported = parsed_data.get("scope2_reported_tco2e")
    scope2_cbam     = parsed_data.get("scope2_cbam_tco2e")
    urea_production = parsed_data.get("urea_production_mt")
    urea_share_pct  = parsed_data.get("urea_share_pct")
    year            = parsed_data.get("year")

    # Step 2: Determine which Scope 2 to use
    # Based on whether renewable proof is provided
    scope2_urea, proof_status, proof_reason = determine_scope2(
        scope2_reported,
        scope2_cbam,
        renewable_proof
    )

    # Step 3: Allocate Scope 1 to urea only
    scope1_urea = allocate_scope1(scope1_total, urea_share_pct)

    # Step 4: Calculate embedded emissions per tonne
    result = calculate_embedded(
        scope1_urea,
        scope2_urea,
        urea_production
    )

    # calculate_embedded returns tuple — unpack safely
    if result is None:
        print("ERROR: Embedded calculation failed.")
        return {}

    embedded, total_urea_emissions = result

    # Step 5: Calculate this shipment's emissions
    shipment_emissions = calculate_shipment_emissions(
        embedded,
        shipment_mt
    )

    # Step 6: Calculate avoided tax
    tax_breakdown = calculate_avoided_tax(
        embedded,
        shipment_mt,
        carbon_price
    )

    # Step 7: Build final result dictionary
    final_result = {
        # Reporting info
        "year"                       : year,

        # Proof verification
        "renewable_proof_type"       : renewable_proof,
        "proof_status"               : proof_status,
        "proof_reason"               : proof_reason,

        # Scope breakdown
        "scope1_total_tco2e"         : scope1_total,
        "scope1_urea_tco2e"          : scope1_urea,
        "scope2_urea_tco2e"          : scope2_urea,
        "total_urea_emissions_tco2e" : total_urea_emissions,

        # Production
        "urea_production_mt"         : urea_production,
        "urea_share_pct"             : urea_share_pct,

        # CBAM certified value
        "embedded_tco2_per_tonne"    : embedded,
        "eu_default_tco2_per_tonne"  : EU_DEFAULT_UREA,

        # Shipment
        "shipment_mt"                : shipment_mt,
        "shipment_emissions_tco2e"   : shipment_emissions,

        # Tax breakdown
        "carbon_price_eur"           : carbon_price,
        "eu_default_tax_eur"         : tax_breakdown["eu_default_tax_eur"],
        "your_tax_eur"               : tax_breakdown["your_tax_eur"],
        "avoided_tax_eur"            : tax_breakdown["avoided_tax_eur"]
    }

    # Step 8: Print final summary
    print("\n" + "="*50)
    print("FINAL CBAM EMISSIONS REPORT")
    print("="*50)
    print(f"  Year                  : {year}")
    print(f"  Renewable proof       : {renewable_proof} "
          f"({proof_status})")
    print(f"  Scope 1 (urea)        : {scope1_urea:,.2f} tCO2e")
    print(f"  Scope 2 (urea)        : {scope2_urea:,.2f} tCO2e")
    print(f"  Total urea emissions  : {total_urea_emissions:,.2f} tCO2e")
    print(f"  Urea production       : {urea_production:,.0f} MT")
    print(f"  Embedded rate         : {embedded} tCO2/tonne")
    print(f"  EU default rate       : {EU_DEFAULT_UREA} tCO2/tonne")
    print(f"  Shipment size         : {shipment_mt:,} MT")
    print(f"  Shipment emissions    : {shipment_emissions:,.2f} tCO2e")
    print(f"  EU default tax        : €{tax_breakdown['eu_default_tax_eur']:,.2f}")
    print(f"  Your tax              : €{tax_breakdown['your_tax_eur']:,.2f}")
    print(f"  Avoided tax        : €{tax_breakdown['avoided_tax_eur']:,.2f}")
    print("="*50 + "\n")

    return final_result


# ─────────────────────────────────────────
# RUN THIS FILE DIRECTLY TO TEST

if __name__ == "__main__":

    import sys
    sys.path.append(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    from modules.pdf_parser import parse_pdf

    PDF_PATH = "/home/user/Desktop/Projects/PBL/data/sample_reports/MCFAR2024-25FINAL.pdf"
    CSV_PATH = "data/grid_emission_factors.csv"

    # Step 1: Parse PDF
    parsed_data = parse_pdf(PDF_PATH, CSV_PATH)

    if parsed_data:

        print("\n--- TEST 1: No proof provided ---")
        result1 = calculate_all(parsed_data,
                                renewable_proof=None)

        print("\n--- TEST 2: Valid REC proof ---")
        result2 = calculate_all(parsed_data,
                                renewable_proof="REC")

        print("\n--- TEST 3: Invalid proof type ---")
        result3 = calculate_all(parsed_data,
                                renewable_proof="ISO14001")

        # Compare all three results
        print("\n--- COMPARISON ---")
        print(f"  No proof  → {result1['embedded_tco2_per_tonne']} tCO2/t"
              f" | Tax: €{result1['your_tax_eur']:,.2f}")
        print(f"  REC proof → {result2['embedded_tco2_per_tonne']} tCO2/t"
              f" | Tax: €{result2['your_tax_eur']:,.2f}")
        print(f"  Bad proof → {result3['embedded_tco2_per_tonne']} tCO2/t"
              f" | Tax: €{result3['your_tax_eur']:,.2f}")
    else:
        print("Parser failed — check file paths.")
