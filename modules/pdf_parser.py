# modules/pdf_parser.py
# Extracts emissions data from MCF Ltd sustainability report
# and calculates CBAM-compliant emissions using grid emission factor

import pdfplumber
import pandas as pd
import re
import os


# ─────────────────────────────────────────
# FUNCTION 1: Load Grid Emission Factor
# ─────────────────────────────────────────
def load_grid_factor(csv_path):
    """
    Reads Karnataka grid emission factor from CSV.
    Returns factor as float. Default 0.97 if file missing.
    """

    if not os.path.exists(csv_path):
        print(f"WARNING: CSV not found at {csv_path}")
        print("Using default Karnataka factor: 0.97")
        return 0.97

    df = pd.read_csv(csv_path)

    karnataka = df[df['State'] == 'Karnataka']

    if not karnataka.empty:
        factor = float(karnataka['grid_factor_tco2_per_mwh'].values[0])
        print(f"Grid factor loaded: {factor} tCO2/MWh (Karnataka)")
        return factor

    print("WARNING: Karnataka not in CSV. Using default: 0.97")
    return 0.97


# ─────────────────────────────────────────
# FUNCTION 2: Extract All Page Text
# ─────────────────────────────────────────
def extract_text_by_page(pdf_path):
    """
    Opens PDF and reads text from every page.
    Returns dictionary {page_number: page_text}
    """

    if not os.path.exists(pdf_path):
        print(f"ERROR: PDF not found at {pdf_path}")
        return {}

    pages = {}

    with pdfplumber.open(pdf_path) as pdf:
        print(f"PDF opened. Total pages: {len(pdf.pages)}")

        for i, page in enumerate(pdf.pages):
            text = page.extract_text()

            if text:
                pages[i + 1] = text

    print(f"Text extracted from {len(pages)} pages.")
    return pages


# ─────────────────────────────────────────
# FUNCTION 3: Extract Scope 1
# ─────────────────────────────────────────
def extract_scope1(pages):
    """
    Finds Scope 1 emissions value in the PDF.

    WHY NEXT LINE LOGIC:
    The PDF splits the table row across 2 lines:
    Line 24: 'Total Scope 1 emissions (Break-up of the GHG into'
    Line 25: 'tCOe 2,96,036 2,81,059'   <- value is HERE

    So we find the keyword line then read the NEXT line for value.
    Returns Scope 1 in tCO2e as float.
    """

    for page_num, text in pages.items():
        text_lower = text.lower()

        if 'total scope 1 emissions' in text_lower:
            lines = text.split('\n')

            for i, line in enumerate(lines):
                line_lower = line.lower()

                if 'total scope 1 emissions' in line_lower:

                    if i + 1 < len(lines):
                        next_line = lines[i + 1]

                        numbers = re.findall(r'[\d,]+(?:\.\d+)?', next_line)

                        cleaned = []
                        for num in numbers:
                            try:
                                value = float(num.replace(',', ''))
                                if value > 1000:
                                    cleaned.append(value)
                            except ValueError:
                                continue

                        if cleaned:
                            print(f"Scope 1 found on page {page_num}: "
                                  f"{cleaned[0]} tCO2e")
                            return cleaned[0]

    print("WARNING: Scope 1 not found. Returning None.")
    return None


# ─────────────────────────────────────────
# FUNCTION 4: Extract Scope 2 Reported
# ─────────────────────────────────────────
def extract_scope2_reported(pages):
    """
    Finds the REPORTED Scope 2 value from the PDF.
    For 2024-25 this is 0 because MCF uses own generation.

    Same next-line logic as Scope 1:
    Line 27: 'Total Scope 2 emissions (Break-up of the GHG into'
    Line 28: 'tCOe 0* 1,891'   <- value is HERE

    Note: 0* has asterisk — we strip it before extracting.
    Returns Scope 2 in tCO2e as float.
    """

    for page_num, text in pages.items():
        text_lower = text.lower()

        if 'total scope 2 emissions' in text_lower:
            lines = text.split('\n')

            for i, line in enumerate(lines):
                line_lower = line.lower()

                if 'total scope 2 emissions' in line_lower:

                    if i + 1 < len(lines):
                        next_line = lines[i + 1]

                        next_line_clean = next_line.replace('*', '')

                        numbers = re.findall(
                            r'[\d,]+(?:\.\d+)?',
                            next_line_clean
                        )

                        cleaned = []
                        for num in numbers:
                            try:
                                value = float(num.replace(',', ''))
                                if value >= 0:
                                    cleaned.append(value)
                            except ValueError:
                                continue

                        if cleaned:
                            print(f"Scope 2 (reported) found on page "
                                  f"{page_num}: {cleaned[0]} tCO2e")
                            return cleaned[0]

    print("WARNING: Scope 2 not found. Returning 0.")
    return 0.0


# ─────────────────────────────────────────
# FUNCTION 5: Extract Purchased Electricity
# ─────────────────────────────────────────
def extract_electricity(pages):
    """
    Finds purchased electricity from the energy table.
    Found on Page 28 of MCF report.

    Exact line looks like:
    'A. Purchased Units Lakh kWh 165.00 43.37'

    Value is in Lakh kWh — we convert to MWh for CBAM.
    1 Lakh kWh = 1,00,000 kWh = 100 MWh

    Returns tuple: (lakh_kwh, mwh)
    """

    for page_num, text in pages.items():
        text_lower = text.lower()

        if 'purchased' in text_lower and 'lakh kwh' in text_lower:
            lines = text.split('\n')

            for line in lines:
                line_lower = line.lower()

                if 'purchased' in line_lower and 'lakh kwh' in line_lower:

                    numbers = re.findall(r'[\d,]+(?:\.\d+)?', line)

                    cleaned = []
                    for num in numbers:
                        try:
                            value = float(num.replace(',', ''))
                            if value > 10:
                                cleaned.append(value)
                        except ValueError:
                            continue

                    if cleaned:
                        lakh_kwh = cleaned[0]
                        mwh = lakh_kwh * 100

                        print(f"Electricity found on page {page_num}: "
                              f"{lakh_kwh} Lakh kWh = {mwh} MWh")
                        return lakh_kwh, mwh

    print("WARNING: Electricity data not found. Returning None.")
    return None, None


# ─────────────────────────────────────────
# FUNCTION 6: Extract Urea Production
# ─────────────────────────────────────────
def extract_production(pages):
    """
    Finds total urea production volume.
    Found on Page 16 of MCF report.

    Exact line looks like:
    'Your Company achieved production of 4,43,322 MTs'

    This is the DENOMINATOR of the CBAM formula:
    Embedded = (Scope1 + Scope2) / Production

    Returns production in MT as float.
    """

    for page_num, text in pages.items():
        text_lower = text.lower()

        if 'urea' in text_lower and ('production' in text_lower
                                      or 'mts' in text_lower):
            lines = text.split('\n')

            for line in lines:
                line_lower = line.lower()

                if ('urea' in line_lower and
                    ('mts' in line_lower or 'production' in line_lower)):

                    numbers = re.findall(r'[\d,]+(?:\.\d+)?', line)

                    cleaned = []
                    for num in numbers:
                        try:
                            value = float(num.replace(',', ''))
                            if value > 100000:
                                cleaned.append(value)
                        except ValueError:
                            continue

                    if cleaned:
                        print(f"Urea production found on page "
                              f"{page_num}: {cleaned[0]} MT")
                        return cleaned[0]

    print("WARNING: Urea production not found. Returning None.")
    return None


# ─────────────────────────────────────────
# FUNCTION 7: Extract All Products Production
# ─────────────────────────────────────────
def extract_all_production(pages):
    """
    Extracts production volumes for ALL products
    so we can calculate urea's share of total plant.

    From MCF 2024-25 report:
    Urea                   = 4,43,322 MT  (Page 16)
    Phosphatic Fertilizers = 3,25,135 MT  (Page 16)
    Ammonium Bicarbonate   =  13,130 MT  (Page 16)

    Returns dictionary of all product volumes.
    """

    production = {
        "urea"      : None,
        "phosphatic": None,
        "abc"       : None
    }

    for page_num, text in pages.items():
        text_lower = text.lower()

        if 'production' not in text_lower:
            continue

        lines = text.split('\n')

        for line in lines:
            line_lower = line.lower()

            # Extract urea production
            if ('urea' in line_lower and
                ('mts' in line_lower or 'production' in line_lower)
                and production["urea"] is None):

                numbers = re.findall(r'[\d,]+(?:\.\d+)?', line)
                for num in numbers:
                    try:
                        value = float(num.replace(',', ''))
                        if value > 100000:
                            production["urea"] = value
                            print(f"Urea production: {value} MT")
                            break
                    except ValueError:
                        continue

            # Extract phosphatic fertilizer production
            if ('phosphatic' in line_lower and
                production["phosphatic"] is None):

                numbers = re.findall(r'[\d,]+(?:\.\d+)?', line)
                for num in numbers:
                    try:
                        value = float(num.replace(',', ''))
                        if value > 10000:
                            production["phosphatic"] = value
                            print(f"Phosphatic production: {value} MT")
                            break
                    except ValueError:
                        continue

            # Extract ammonium bicarbonate production
            if (('ammonium bi' in line_lower or 'abc' in line_lower)
                and production["abc"] is None):

                numbers = re.findall(r'[\d,]+(?:\.\d+)?', line)
                for num in numbers:
                    try:
                        value = float(num.replace(',', ''))
                        if value > 1000:
                            production["abc"] = value
                            print(f"ABC production: {value} MT")
                            break
                    except ValueError:
                        continue

    return production


# ─────────────────────────────────────────
# FUNCTION 8: Allocate Emissions To Urea
# ─────────────────────────────────────────
def allocate_to_urea(all_production, electricity_mwh, grid_factor):
    """
    Calculates urea's SHARE of total plant electricity
    and returns CBAM Scope 2 allocated to urea only.

    WHY WE DO THIS:
    Purchased electricity serves the ENTIRE plant.
    CBAM only needs urea's share.
    We use production volume as the allocation key.

    Formula:
    Urea share       = Urea MT / Total Plant MT
    Urea electricity = Total electricity x Urea share
    Scope 2 CBAM     = Urea electricity x Grid factor

    Returns dictionary with allocation details.
    """

    urea       = all_production.get("urea")       or 0
    phosphatic = all_production.get("phosphatic") or 0
    abc        = all_production.get("abc")        or 0

    total_production = urea + phosphatic + abc

    if total_production == 0:
        print("WARNING: Total production is 0. Cannot allocate.")
        return {
            "total_production_mt"  : 0,
            "urea_share_pct"       : 0,
            "urea_electricity_mwh" : 0,
            "scope2_cbam_tco2e"    : 0
        }

    urea_share           = urea / total_production
    urea_electricity_mwh = electricity_mwh * urea_share
    scope2_cbam          = urea_electricity_mwh * grid_factor

    print(f"\n--- PRODUCTION ALLOCATION ---")
    print(f"  Urea          : {urea:,.0f} MT")
    print(f"  Phosphatic    : {phosphatic:,.0f} MT")
    print(f"  ABC           : {abc:,.0f} MT")
    print(f"  Total         : {total_production:,.0f} MT")
    print(f"  Urea share    : {urea_share*100:.1f}%")
    print(f"  Urea elec     : {urea_electricity_mwh:.1f} MWh")
    print(f"  Scope 2 CBAM  : {round(scope2_cbam, 2)} tCO2e")

    return {
        "total_production_mt"  : total_production,
        "urea_share_pct"       : round(urea_share * 100, 2),
        "urea_electricity_mwh" : round(urea_electricity_mwh, 2),
        "scope2_cbam_tco2e"    : round(scope2_cbam, 2)
    }


# ─────────────────────────────────────────
# FUNCTION 9: Extract Reporting Year
# ─────────────────────────────────────────
def extract_year(pages):
    """
    Finds the financial year from early pages of PDF.
    Looks for pattern like 2024-25.
    Returns year as string.
    """

    year_pattern = r'20\d{2}-\d{2}'

    for page_num in range(1, 21):
        if page_num not in pages:
            continue

        text = pages[page_num]
        matches = re.findall(year_pattern, text)

        if matches:
            year = matches[0]
            print(f"Reporting year found: {year}")
            return year

    print("WARNING: Year not found. Using default 2024-25.")
    return "2024-25"


# ─────────────────────────────────────────
# FUNCTION 10: Master Parse Function
# ─────────────────────────────────────────
def parse_pdf(pdf_path, csv_path):
    """
    Master function — calls all functions above.
    This is the ONLY function other modules import.

    Args:
        pdf_path : path to MCF sustainability report PDF
        csv_path : path to grid emission factors CSV

    Returns:
        dictionary with all extracted and calculated values
    """

    print("\n" + "="*50)
    print("CARBON-TRACE MANGALORE — PDF PARSER")
    print("="*50)

    # Step 1: Load grid factor from CSV
    grid_factor = load_grid_factor(csv_path)

    # Step 2: Extract all page text from PDF
    pages = extract_text_by_page(pdf_path)

    if not pages:
        print("ERROR: Could not read PDF.")
        return {}

    # Step 3: Extract all values from PDF
    scope1          = extract_scope1(pages)
    scope2_reported = extract_scope2_reported(pages)
    lakh_kwh, mwh   = extract_electricity(pages)
    urea_production = extract_production(pages)
    all_production  = extract_all_production(pages)
    year            = extract_year(pages)

    # Step 4: Allocate electricity and Scope 2 to urea
    allocation = allocate_to_urea(all_production, mwh, grid_factor)

    # Step 5: Build result dictionary
    result = {
        # Reporting info
        "year"                           : year,
        "source"                         : os.path.basename(pdf_path),

        # Emissions from report
        "scope1_tco2e"                   : scope1,
        "scope2_reported_tco2e"          : scope2_reported,

        # Electricity data
        "purchased_electricity_lakh_kwh" : lakh_kwh,
        "purchased_electricity_mwh"      : mwh,
        "grid_factor_tco2_per_mwh"       : grid_factor,

        # Production data
        "urea_production_mt"             : urea_production,
        "phosphatic_production_mt"       : all_production.get("phosphatic"),
        "abc_production_mt"              : all_production.get("abc"),
        "total_production_mt"            : allocation["total_production_mt"],

        # Allocation results
        "urea_share_pct"                 : allocation["urea_share_pct"],
        "urea_electricity_mwh"           : allocation["urea_electricity_mwh"],

        # Final CBAM Scope 2
        "scope2_cbam_tco2e"              : allocation["scope2_cbam_tco2e"],
    }

    # Step 6: Print summary
    print("\n--- FINAL EXTRACTION SUMMARY ---")
    for key, value in result.items():
        print(f"  {key}: {value}")
    print("="*50 + "\n")

    return result


# ─────────────────────────────────────────
# RUN THIS FILE DIRECTLY TO TEST
# ─────────────────────────────────────────
if __name__ == "__main__":

    PDF_PATH = "/home/user/Desktop/Projects/PBL/data/sample_reports/MCFAR2024-25FINAL.pdf"
    CSV_PATH = "/home/user/Desktop/Projects/PBL/data/grid_emission_factors.csv"

    result = parse_pdf(PDF_PATH, CSV_PATH)

    if result:
        print("Parser ran successfully!")
    else:
        print("Parser failed — check file paths.")