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

def _extract_numbers(line):
    """Extract dollar amounts from a line using regex (handles thousands commas)"""
    # Match patterns like: 76,134.30 or (2,198.50) or 0.00 or -1,234.56
    matches = re.findall(r'[\(\-]?\d[\d,]*\.\d{2}\)?', line)
    return [parse_money(m) for m in matches]

def _is_data_line(line):
    """Check if a line looks like numeric financial data"""
    numbers = _extract_numbers(line)
    return len(numbers) >= 4

def _extract_values(lines, i, key, data):
    """Extract 4 numeric values from the line after (or before) a label line"""
    # Try next line first
    if i + 1 < len(lines):
        numbers = _extract_numbers(lines[i + 1])
        if len(numbers) >= 4:
            data[key]['month'] = numbers[0]
            data[key]['ytd'] = numbers[1]
            data[key]['py_month'] = numbers[2]
            data[key]['py_ytd'] = numbers[3]
            return True
    # Try previous line (some statements have data before label)
    if i - 1 >= 0:
        numbers = _extract_numbers(lines[i - 1])
        if len(numbers) >= 4:
            data[key]['month'] = numbers[0]
            data[key]['ytd'] = numbers[1]
            data[key]['py_month'] = numbers[2]
            data[key]['py_ytd'] = numbers[3]
            return True
    return False

def find_site_lead_file(division_name=None):
    """Find the Site Lead Statement text file for a specific division"""
    if not DATASHEETS_DIR.exists():
        return None

    txt_files = [
        DATASHEETS_DIR / f
        for f in os.listdir(DATASHEETS_DIR)
        if f.lower().endswith('.txt')
    ]

    if not txt_files:
        return None

    # Division-specific file matching - collect all matches, return newest
    if division_name:
        name_lower = division_name.lower()
        matches = []
        for path in txt_files:
            fname = path.name.lower()
            if name_lower == 'kalamazoo' and ('kz ' in fname or 'kazoo' in fname) and 'site lead' in fname:
                matches.append(path)
            elif name_lower == 'generator' and 'gen ' in fname and 'site lead' in fname:
                matches.append(path)
            elif name_lower == 'plainwell':
                if 'site lead' in fname and 'kz' not in fname and 'gen' not in fname:
                    matches.append(path)
        if matches:
            # Return the most recently modified matching file
            matches.sort(key=os.path.getmtime, reverse=True)
            return str(matches[0])

    # Fallback: sort by modification time (most recent first)
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

def parse_site_lead_statement(filepath=None, division_name=None):
    """
    Parse Site Lead Statement file to extract gross profit data
    Returns: dict with new_equipment, parts, labor sales (month and YTD)
    """
    if filepath is None:
        filepath = find_site_lead_file(division_name)

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
            'file_date': os.path.getmtime(filepath),
            'file_name': os.path.basename(filepath)
        }

        # State tracking
        in_gross_profit = False

        for i, line in enumerate(lines):
            # Start of GROSS PROFIT section
            if line.upper() == 'GROSS PROFIT':
                in_gross_profit = True
                continue

            # End of GROSS PROFIT section (when we hit COST OF GOODS SOLD)
            if 'COST OF GOODS SOLD' in line.upper():
                in_gross_profit = False
                continue

            if in_gross_profit:
                upper = line.upper()
                # NEW EQUIPMENT SALES line
                if 'NEW EQUIPMENT SALES' in upper:
                    _extract_values(lines, i, 'new_equipment', data)

                # PARTS SALES line (but not SERVICE PARTS SALES)
                elif upper.strip() == 'PARTS SALES' or upper.startswith('PARTS SALES'):
                    _extract_values(lines, i, 'parts', data)

                # SERVICE LABOR SALES line
                elif 'SERVICE LABOR SALES' in upper:
                    _extract_values(lines, i, 'labor', data)

            # Look for Total GROSS PROFIT line (after COST OF GOODS SOLD section)
            if 'Total GROSS PROFIT' in line:
                numbers = _extract_numbers(line)
                if len(numbers) >= 4:
                    data['gross_profit']['month'] = numbers[0]
                    data['gross_profit']['ytd'] = numbers[1]
                    data['gross_profit']['py_month'] = numbers[2]
                    data['gross_profit']['py_ytd'] = numbers[3]

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
