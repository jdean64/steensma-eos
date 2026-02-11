# Print Function Development Notes

## Current Status (Feb 11, 2026)
Working on print functionality for EOS Platform pages.

## Data Now Available for Printing

### Generator Division
- **Rocks (4):**
  1. Review phone tree and adjust as needed - Tammy
  2. Finish PDF Quote with Financing options, program fees, margins, etc - Adam
  3. Finish the Contractor Program and start distribution - Adam
  4. Design and begin Service Agreement Initiative to increase agreement customers - Jason

- **1-Year Goals (5):**
  1. Develop contractor business for Gen division
  2. Expand Generator sales and service territory to North and West
  3. Increase Service Agreement participation by 1000 (4500 to 5500)
  4. Develop and execute plan to increase Fleet participation to 25%+
  5. Investigate alternative revenue (Battery Wall, smoke/CO detectors, Ecobee)

### Kalamazoo Division
- **Rocks (6):**
  1. Get Matt H and Jeff N. on road preseason with commercial guys - Jack
  2. Setup Help/Web Support – hire one person - Ryan
  3. Store Transfers – Parts, Paperwork, and Process - Jack
  4. Parts Receiving Process - JT
  5. Setup Process Efficiency - John Deere Product - Ryan
  6. Repair Order Write up's – collect more accurate information - Mike/JT

- **1-Year Goals (7):**
  1. Research & execute expanding road sales with Matt H and Jeff N.
  2. Research and execute plan to expand John Deere sales including CUTs
  3. Research and execute plan to expand extended warranty sales
  4. Decide on and train up CSR for Web Support
  5. Growth (Road Sales and outbound selling)
  6. Inventory Levels (Lost Sales, Better on Hand Inventory)
  7. Assistant Site Lead Identified

- **Issues (7):**
  1. Inventory Clean up
  2. Woods Equipment – Dead Stock
  3. Back Order Reporting
  4. CSR Shop Support
  5. Government Sales – successor for Tom Myland
  6. More Service Techs and Training for Techs
  7. CSR Help – better training process for new CSR's

### Plainwell Division
- **Rocks:** 8 existing rocks (already in system)
- **1-Year Goals:** Available in VTO
- **Issues:** 4 existing issues

## Print Function Recommendations

### Pages to Support Printing
1. **Vision/VTO Page** - Full strategic overview
2. **Rocks Page** - Quarterly priorities with status
3. **Scorecard Page** - 13-week measurables
4. **Issues Page** - Current issues list with IDS stages
5. **Todos Page** - Action items with owners
6. **L10 Meeting View** - Complete meeting agenda

### CSS Print Media Query Template
```css
@media print {
    /* Hide navigation and non-essential UI */
    .header-right, .btn-logout, .back-link { display: none; }
    
    /* Optimize layout for paper */
    body { background: white; }
    .container { max-width: 100%; padding: 20px; }
    
    /* Page breaks */
    .page-break { page-break-before: always; }
    .avoid-break { page-break-inside: avoid; }
    
    /* Remove shadows and borders for clean print */
    .card, .section { box-shadow: none; }
}
```

### JavaScript Print Helper
```javascript
function printPage() {
    window.print();
}

// Add print button to pages
<button onclick="printPage()" class="no-print">🖨️ Print</button>
```

### Template Additions Needed
Add to each printable template:
- Print button in header
- Print-friendly CSS media queries
- Page break markers for multi-page content
- Clean header/footer for printed pages

## Next Steps
1. Add print stylesheets to all main templates
2. Add print buttons to page headers
3. Test print layouts on different page sizes
4. Consider PDF export option (using browser print-to-PDF)
