import pdfplumber
import pandas as pd
import re
import os

def load_grid_emission(csv_path):
    df = pd.read_csv(csv_path)
    
    ''' Returns Karanatka's grid emission factor in kg CO2e/kWh '''

    if not os.path.exists(csv_path):
        print(f"Error: CSV file not found at {csv_path}")
        return None
    
    #Filter 
    karnataka_row = df[df['State'] == 'Karnataka']

    if karnataka_row.empty:
        print("Error: Karnataka not found in CSV.")
        return None
    else:
         factor = float(karnataka_row['grid_factor_tco2_per_mwh'].values[0])
         print(f"Grid factor loaded: {factor} tCO2/MWh (Karnataka)")
         return factor

def extract_text_by_page(pdf_path):
    '''Opens the PDF and reads text from every page.
    Returns a dictionary: {page_number: page_text}'''

    if not os.path.exists(pdf_path):
        print(f"Error: PDF file not found at {pdf_path}")
        return None
    pages = {}

    with pdfplumber.open(pdf_path) as pdf:
        print(f"PDF opened successfully: {pdf_path}")
        print(f"Total pages: {len(pdf.pages)}")

        #loop through pages
        for i in range(len(pdf.pages)):
            page = pdf.pages[i]
            text = page.extract_text()
            if text:
                pages[i+1] = text #Page numbers start at 1
                print(f"Page {i+1} text extracted.")
            else:
                print(f"Warning: No text found on page {i+1}.")

    return pages
    
def extract_scope1(pages):

    '''Searches for Scope 1 emissions value in the PDF.'''
    '''Returns the value in kg CO2e or None if not found.'''

    #Keywords to look for
    scope1_keywords = ["scope 1", 
                "direct Emissions", 
                "scope 1 Emissions",
                "total scope 1"]
    #Loop through pages and search for keywords
    for page_num, text in pages.items():
        text_lower = text.lower()

        if any(keyword in text_lower for keyword in scope1_keywords):
            #Split
            lines = text_lower.splitlines()
            for line in lines:
                if 'scope1' in line and 'scope2' not in line:
                    numbers = re.findall(r'[\d,]+(?:\.\d+)?', line)

        # Clean commas and convert to float
                    cleaned = []
                    for num in numbers:
                        try:
                            value = float(num.replace(',', ''))
                            # Scope 1 should be a large number > 1000
                            if value > 1000:
                                cleaned.append(value)
                        except ValueError:
                            continue
                    # Return the first valid large number found
                    if cleaned:
                        print(f"Scope 1 found on page {page_num}: {cleaned[0]} tCO2e")
                        return cleaned[0]
    # If not found anywhere
    print("WARNING: Scope 1 not found in PDF. Returning None.")
    return None


def extract_electricity(pages):
    """
    Searches for purchased electricity value in the PDF.
    Found on Page 28 of MCF report.
    Value is in Lakh kWh — we convert to MWh for CBAM.
    Returns tuple: (lakh_kwh, mwh)
    """

    electricity_keywords = [
        "purchased",
        "electricity",
        "lakh kwh"
    ]

    for page_num, text in pages.items():
        text_lower = text.lower()

        # Check if electricity data is on this page
        if 'lakh kwh' in text_lower and 'purchased' in text_lower:

            lines = text.split('\n')

            for line in lines:
                line_lower = line.lower()

                # Look for purchased electricity line
                if 'purchased' in line_lower and 'lakh kwh' in line_lower:

                    # Find numbers in this line
                    numbers = re.findall(r'[\d,]+(?:\.\d+)?', line)

                    cleaned = []
                    for num in numbers:
                        try:
                            value = float(num.replace(',', ''))
                            # Purchased electricity around 100-200 lakh kWh
                            if value > 10:
                                cleaned.append(value)
                        except ValueError:
                            continue

                    if cleaned:
                        lakh_kwh = cleaned[0]
                        # Convert Lakh kWh to MWh
                        # 1 Lakh kWh = 100,000 kWh = 100 MWh
                        mwh = lakh_kwh * 100

                        print(f"Electricity found on page {page_num}: {lakh_kwh} Lakh kWh = {mwh} MWh")
                        return lakh_kwh, mwh

    print("WARNING: Electricity data not found. Returning None.")
    return None, None

def extract_production(pages):
    '''Searches for urea production value in the pdf
     Returns production in metric tonnes (MT) as float.'''
    
    production_keywords = [
        "urea production",
        "production of urea",
        "urea produced"
    ]

    for page_num,text in pages.items():
        text_lower = text.lower()

        if any(keyword in text_lower for keyword in production_keywords):
            lines = text.split('\n')

            for line in lines:
                line_lower = line.lower()

                if 'urea' in line_lower and 'production' in line_lower:
                    numbers = re.findall(r'[\d,]+(?:\.\d+)?', line)

                    cleaned = []
                    for num in numbers:
                        try:
                            value = float(num.replace(',', ''))
                            # Urea production around 1000-2000 MT
                            if value > 10000:
                                cleaned.append(value)
                        except ValueError:
                            continue

                    if cleaned:
                        print(f"Production found on page {page_num}: {cleaned[0]} MT")
                        return cleaned[0]   
    print("WARNING: Urea production not found. Returning None.")
    return None
    

if __name__ == "__main__":
    

    #Path 
    PDF_PATH = "/home/user/Desktop/Projects/PBL/data/sample_reports/MCFAR2024-25FINAL.pdf"
    CSV_PATH = "/home/user/Desktop/Projects/PBL/data/grid_emission_factors.csv"

    #Run 
    result = parse_pdf(PDF_PATH, CSV_PATH)
    
    if result:
        print("Parsing successful!")

    else:
        print("Parsing failed - check file paths.")