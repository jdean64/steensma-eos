# EOS Platform - Ready for Print Function Development

**Repository:** https://github.com/jdean64/steensma-eos
**Latest Commit:** 7f75570 - Complete multi-tenant EOS platform with Q1 2026 data
**Status:** ✅ All changes pushed to GitHub

## Access Information

**URL:** http://eos.coresteensma.com (port 5002)

**Login Credentials (All users):**
- **Username:** brian, kurt, tammy, or jeff
- **Password:** EOS2026!

## Current System Status

### Three Active Divisions
1. **Plainwell** (ID: 1) - 8 rocks
2. **Kalamazoo** (ID: 2) - 6 rocks, 7 1-year goals, 7 issues
3. **Generator** (ID: 3) - 4 rocks, 5 1-year goals

### Functional Pages
✅ Parent Dashboard (division selector)
✅ Division Dashboards (6-card layout)
✅ Vision/VTO (complete with all data)
✅ Rocks (quarterly priorities)
✅ Scorecard (13-week measurables)
✅ Issues (IDS workflow)
✅ Todos (action items)
✅ L10 Meetings (full meeting system)
✅ Accountability Chart (org structure)

## Print Function Development

### Pages to Make Printable
1. Vision/VTO - `/division/<id>/vision`
2. Rocks - `/division/<id>/rocks`
3. Scorecard - `/division/<id>/scorecard`
4. Issues - `/division/<id>/issues`
5. Todos - `/division/<id>/todos`
6. L10 Meeting View - `/division/<id>/l10/<meeting_id>`

### Template Files to Update
```
templates/vision.html
templates/rocks.html
templates/scorecard.html
templates/issues_new.html
templates/todos.html
templates/view_l10_meeting.html
```

### CSS Print Media Query Pattern
```css
@media print {
    /* Hide UI elements */
    .header-right, .btn-logout, .back-link { display: none; }
    
    /* Clean layout */
    body { background: white; }
    .container { max-width: 100%; }
    
    /* Page breaks */
    .page-break { page-break-before: always; }
    .avoid-break { page-break-inside: avoid; }
    
    /* Remove shadows */
    .card, .section { box-shadow: none; }
}
```

### Add Print Button to Headers
```html
<button onclick="window.print()" class="btn-print no-print">
    🖨️ Print
</button>
```

Then add CSS:
```css
@media print {
    .no-print { display: none; }
}
```

## Running the Application

**From server:**
```bash
cd /home/ubuntu/eosplatform
source venv/bin/activate
python app_multitenant.py
```

**From home (after pulling from GitHub):**
```bash
git clone git@github.com:jdean64/steensma-eos.git eosplatform
cd eosplatform
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app_multitenant.py
```

Access at: http://localhost:5002

## Database Access (if needed)

**On server:**
```bash
cd /home/ubuntu/eosplatform
source venv/bin/activate
sqlite3 eos_data.db
```

**Query examples:**
```sql
-- Check rocks
SELECT * FROM rocks WHERE division_id = 2 AND is_active = 1;

-- Check VTO
SELECT * FROM vto WHERE division_id = 3 AND is_active = 1;

-- Check users
SELECT id, username, full_name FROM users;
```

## File Structure

```
/home/ubuntu/eosplatform/
├── app_multitenant.py          # Main application entry
├── auth.py                     # Authentication & RBAC
├── routes.py                   # Core routes (login, dashboards)
├── rocks_routes.py             # Quarterly rocks
├── scorecard_routes.py         # Weekly measurables
├── issues_routes.py            # Issues with IDS
├── todos_routes.py             # Action items
├── vision_routes.py            # VTO display
├── l10_routes.py               # L10 meetings
├── accountability_routes.py    # Org chart
├── eos_data.db                 # SQLite database
├── templates/                  # HTML templates
├── datasheets/                 # VTO docx files
└── PRINT_FUNCTION_NOTES.md     # Print dev notes
```

## Notes

- All templates use server-side rendering (Jinja2)
- Multi-tenant architecture with organization_id and division_id
- Flask debug mode enabled (auto-reloads on file changes)
- All divisions have complete Q1 2026 data
- Print function recommendations in PRINT_FUNCTION_NOTES.md

Have a great evening! The system is ready for print development. 🚀
