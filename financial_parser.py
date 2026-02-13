"""
Financial Data Parser for EOS Platform
Parses Site Lead Statement files to extract gross profit metrics
"""

import os
import re
from pathlib import Path

DATASHEETS_DIR = Path(__file__).parent / 'datasheets'

def parse_money(value):
    """Convert string dollar amount to float"""
    if value is None:
        return 0.0
    s = str(value).strip()
    if not s:
        return 0.0
    # Remove $ and commas
    s = s.replace('$', '').replace(',', '')
    # Handle parentheses as negative
    if s.startswith('(') and s.endswith(')'):
        s = '-' + s[1:-1]
    try:
        return float(s)
    except:
        return 0.0

def find_site_lead_file():
    """Find the most recent Site Lead Statement text file"""
    if not DATASHEETS_DIR.exists():
        return None
    
    txt_files = [
        DATASHEETS_DIR / f
        for f in os.listdir(DATASHEETS_DIR)
        if f.lower().endswith('.txt')
    ]
    
    if not txt_files:
        return None
    
    # Sort by modification time (most recent first)
    txt_files_sorted = sorted(txt_files, key=os.path.getmtime, reverse=True)
    
    # Check first few files for Site Lead content
    for path in txt_files_sorted[:5]:
        try:
            with open(path, 'r') as f:
                head = ''.join([next(f) for _ in range(3)])
            if 'Site lead Statement' in head or 'Site Lead' in head:
                return str(path)
        except Exception:
            continue
    
    return None

def parse_site_lead_statement(filepath=None):
    """
    Parse Site Lead Statement file to extract gross profit data
    Returns: dict with new_equipment, parts, labor sales (month and YTD)
    """
    if filepath is None:
        filepath = find_site_lead_file()
    
    if not filepath or not os.path.exists(filepath):
        return {
            'new_equipment': {'month': 0.0, 'ytd': 0.0, 'py_month': 0.0, 'py_ytd': 0.0},
            'parts': {'month': 0.0, 'ytd': 0.0, 'py_month': 0.0, 'py_ytd': 0.0},
            'labor': {'month': 0.0, 'ytd': 0.0, 'py_month': 0.0, 'py_ytd': 0.0},
            'gross_profit': {'month': 0.0, 'ytd': 0.0, 'py_month': 0.0, 'py_ytd': 0.0},
            'file_date': None
        }
    
    try:
        with open(filepath, 'r') as f:
            lines = [line.strip() for line in f.readlines()]
        
        data = {
            'new_equipment': {'month': 0.0, 'ytd': 0.0, 'py_month': 0.0, 'py_ytd': 0.0},
            'parts': {'month': 0.0, 'ytd': 0.0, 'py_month': 0.0, 'py_ytd': 0.0},
            'labor': {'month': 0.0, 'ytd': 0.0, 'py_month': 0.0, 'py_ytd': 0.0},
            'gross_profit': {'month': 0.0, 'ytd': 0.0, 'py_month': 0.0, 'py_ytd': 0.0},
            'file_date': os.path.getmtime(filepath)
        }
        
        # State tracking
        in_gross_profit = False
        
        for i, line in enumerate(lines):
            # Start of GROSS PROFIT section
            if line.upper() == 'GROSS PROFIT':
                in_gross_profit = True
                continue
            
            # End of GROSS PROFIT section (when we hit COST OF G GOODS SOLD)
            if 'COST OF GOODS SOLD' in line.upper():
                in_gross_profit = False
                continue
            
            if in_gross_profit:
                # NEW EQUIPMENT SALES line
                if 'NEW EQUIPMENT SALES' in line.upper():
                    # Next line contains the values: month,ytd,py_month,py_ytd
                    if i + 1 < len(lines):
                        values = lines[i + 1].split(',')
                        if len(values) >= 4:
                            data['new_equipment']['month'] = parse_money(values[0])
                            data['new_equipment']['ytd'] = parse_money(values[1])
                            data['new_equipment']['py_month'] = parse_money(values[2])
                            data['new_equipment']['py_ytd'] = parse_money(values[3])
                
                # PARTS SALES line
                elif 'PARTS SALES' in line.upper() and 'EQUIPMENT' not in line.upper():
                    if i + 1 < len(lines):
                        values = lines[i + 1].split(',')
                        if len(values) >= 4:
                            data['parts']['month'] = parse_money(values[0])
                            data['parts']['ytd'] = parse_money(values[1])
                            data['parts']['py_month'] = parse_money(values[2])
                            data['parts']['py_ytd'] = parse_money(values[3])
                
                # SERVICE LABOR SALES line
                elif 'SERVICE LABOR SALES' in line.upper() or 'LABOR SALES' in line.upper():
                    if i + 1 < len(lines):
                        values = lines[i + 1].split(',')
                        if len(values) >= 4:
                            data['labor']['month'] = parse_money(values[0])
                            data['labor']['ytd'] = parse_money(values[1])
                            data['labor']['py_month'] = parse_money(values[2])
                            data['labor']['py_ytd'] = parse_money(values[3])
            
            # Look for Total GROSS PROFIT line (after COST OF GOODS SOLD section)
            if 'Total GROSS PROFIT' in line:
                values = line.split(',')
                # Remove text portion
                values = [v for v in values if any(c.isdigit() or c in '$()-.' for c in v)]
                if len(values) >= 4:
                    data['gross_profit']['month'] = parse_money(values[0])
                    data['gross_profit']['ytd'] = parse_money(values[1])
                    data['gross_profit']['py_month'] = parse_money(values[2])
                    data['gross_profit']['py_ytd'] = parse_money(values[3])
        
        return data
    
    except Exception as e:
        print(f"Error parsing site lead statement: {e}")
        import traceback
        traceback.print_exc()
        return {
            'new_equipment': {'month': 0.0, 'ytd': 0.0, 'py_month': 0.0, 'py_ytd': 0.0},
            'parts': {'month': 0.0, 'ytd': 0.0, 'py_month': 0.0, 'py_ytd': 0.0},
            'labor': {'month': 0.0, 'ytd': 0.0, 'py_month': 0.0, 'py_ytd': 0.0},
            'gross_profit': {'month': 0.0, 'ytd': 0.0, 'py_month': 0.0, 'py_ytd': 0.0},
            'file_date': None,
            'error': str(e)
        }
