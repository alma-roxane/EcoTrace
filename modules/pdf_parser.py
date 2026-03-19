import pdfplumber
import pandas as pd
import re
import os

def load_grid_emission(csv_path):
    df = pd.read_csv(csv_path)
    return df


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