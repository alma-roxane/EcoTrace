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