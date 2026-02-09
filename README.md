# EOS Platform - Complete Setup Guide

## 🎯 What You Built

**Live URL:** https://eos.coresteensma.com

A complete EOS (Entrepreneurial Operating System) strategic platform for Steensma Plainwell with:
- ✅ 6-card dashboard (Rocks, Scorecard, Issues, To-Dos, Vision, Accountability)
- ✅ Google Sheet synchronization (same pattern as shop dashboard)
- ✅ Detail pages for each EOS component
- ✅ SSL certificate + nginx proxy
- ✅ Systemd services (auto-start on reboot)
- ✅ Same authentication as other Steensma sites

---

## 📊 Architecture

```
Google Sheets (Your EOS Master Data)
    ↓
Export as CSV → Upload to Google Drive /eos folder
    ↓
eosplatform-gdrive-sync.service (checks every 60s)
    ↓
/home/ubuntu/eosplatform/datasheets/*.csv
    ↓
eosplatform.service (Flask app on port 5002)
    ↓
nginx proxy → https://eos.coresteensma.com
```

**Key Separation:**
- `shop.coresteensma.com` = Daily operations (tactical)
- `eos.coresteensma.com` = Strategic planning (quarterly/annual)
- `havyn.coresteensma.com` = Mission control (all systems)

---

## 🗂️ Google Sheets Structure

### **Create 6 Separate Google Sheets (or 6 tabs in one sheet):**

### 1. **Rocks Sheet** (Quarterly Priorities)

| Column | Description | Example |
|--------|-------------|---------|
| Description | What needs to be accomplished | "Install 4th technician" |
| Owner | Who is accountable | "Jeff" |
| Status | Current state | "ON TRACK", "COMPLETE", "AT RISK", "BLOCKED", "NOT STARTED" |
| DueDate | Deadline | "3/31/2026" |
| Progress | Percentage complete (0-100) | 60 |

**Format:** Pipe-delimited when exported
```
Description|Owner|Status|DueDate|Progress
Install 4th technician|Jeff|ON TRACK|3/31/2026|60
```

---

### 2. **Scorecard Sheet** (Weekly Metrics)

| Column | What It Is | Notes |
|--------|------------|-------|
| Metric | Name of measurable | "Revenue", "Shop Efficiency", "Customer Satisfaction" |
| Owner | Who owns this number | "Jeff", "Operations", "Don" |
| Goal | Target value | "$100K", "85%", "< 5" |
| Week1-Week13 | Last 13 weeks of data | Actual numbers only |
| Status | Health indicator | "GREEN", "YELLOW", "RED" |

**Format:**
```
Metric|Owner|Goal|Week1|Week2|Week3|...|Week13|Status
Revenue|Jeff|$100K|95000|102000|98000|...|101000|GREEN
Shop Efficiency|Operations|85%|82|86|84|...|85|GREEN
```

**Status Logic:**
- 🟢 GREEN = On track, hitting goal
- 🟡 YELLOW = Slightly off, needs attention
- 🔴 RED = Off track, immediate action required

---

### 3. **Issues Sheet** (Problems to Solve)

| Column | Description | Example |
|--------|-------------|---------|
| Issue | The problem | "Property Management - Parking overflow" |
| Priority | Urgency level | "HIGH", "MEDIUM", "LOW" |
| Owner | Who owns resolution | "Jeff" |
| DateAdded | When identified | "1/15/2026" |
| Status | Current state | "OPEN", "IN PROGRESS", "RESOLVED" |

**Format:**
```
Issue|Priority|Owner|DateAdded|Status
Property Management|HIGH|Jeff|1/15/2026|OPEN
```

**Note:** Only OPEN and IN PROGRESS issues show on dashboard

---

### 4. **To-Dos Sheet** (Action Items)

| Column | What It Is | Example |
|--------|------------|---------|
| Task | What needs to be done | "Review Q1 financials with accountant" |
| Owner | Who will do it | "Jeff" |
| DueDate | When it's due | "2/15/2026" |
| Status | Current state | "OPEN", "COMPLETE" |
| Source | Where it came from | "Meeting", "Rock", "Issue" |

**Format:**
```
Task|Owner|DueDate|Status|Source
Review Q1 financials|Jeff|2/15/2026|OPEN|Meeting
```

**Dashboard shows:**
- Total open to-dos
- Due this week (next 7 days)
- Overdue (past due date)

---

### 5. **VTO Sheet** (Vision/Traction Organizer)

| Section | Content |
|---------|---------|
| Quarter | Q1 2026 |
| Core Values | Integrity, Excellence, Accountability, Innovation |
| Core Focus | What you do best |
| 10-Year Target | Big hairy audacious goal |
| 3-Year Picture | Where you'll be in 3 years |
| 1-Year Plan (2026) | This year's objectives |
| Marketing Strategy | How you attract customers |

**Format:**
```
Section|Content
Quarter|Q1 2026
Core Values|Integrity, Excellence, Accountability
10-Year Target|$50M revenue, 5 locations, #1 dealer in MI
```

---

### 6. **Accountability Chart** (Who Does What)

| Column | What It Is | Example |
|--------|------------|---------|
| Seat | Role name | "Site Lead - Plainwell" |
| Accountabilities | Key responsibilities | "Overall P&L, Leadership" |
| Person | Who fills the seat | "Jeff" or "Open" |
| Roles | Specific duties | "Operations, Sales coordination" |

**Format:**
```
Seat|Accountabilities|Person|Roles
Site Lead|Overall P&L, Leadership|Jeff|Operations, Sales
Technician 4|Equipment repair|Open|Service, Warranty
```

**Dashboard shows:**
- Total seats
- Filled seats
- Open positions

---

## 📋 Workflow Options

### **OPTION A: Manual CSV Upload (Simplest - Start Here)**

1. **Edit your Google Sheet** (6 tabs in one master sheet)
2. **For each tab:** File → Download → CSV (.csv)
3. **Name the files exactly:**
   - `rocks.csv`
   - `scorecard.csv`
   - `issues.csv`
   - `todos.csv`
   - `vto.csv`
   - `accountability.csv`
4. **Upload to** `/home/ubuntu/eosplatform/datasheets/`
5. **Refresh dashboard** - data updates immediately

---

### **OPTION B: Automated Google Drive Sync (Like Shop Dashboard)**

**Setup Steps:**

1. **Create Google Drive folder:** `/eos`

2. **Export sheets as CSVs** (File → Download → CSV)

3. **Upload to Google Drive /eos folder**

4. **Start sync service:**
   ```bash
   sudo systemctl start eosplatform-gdrive-sync
   sudo systemctl status eosplatform-gdrive-sync
   ```

5. **Workflow becomes:**
   - Edit Google Sheet
   - Download as CSV
   - Upload to Google Drive /eos folder
   - Site updates automatically in ~60 seconds

**Service already configured** - uses same rclone setup as shop dashboard

---

### **OPTION C: Google Sheets API (Future - Most Automated)**

- Direct API connection to Google Sheets
- Real-time updates (no CSV export needed)
- Requires OAuth2 setup + API credentials
- **Recommend:** Save this for Phase 2

---

## 🚀 Service Management

### **Check Status:**
```bash
sudo systemctl status eosplatform
sudo systemctl status eosplatform-gdrive-sync
```

### **Restart Services:**
```bash
sudo systemctl restart eosplatform
sudo systemctl restart eosplatform-gdrive-sync
```

### **View Logs:**
```bash
# Flask app logs
journalctl -u eosplatform -f

# Sync service logs
journalctl -u eosplatform-gdrive-sync -f
tail -f /home/ubuntu/eosplatform/eos_sync.log
```

### **Test Locally:**
```bash
curl -u steensma:password http://localhost:5002/health
curl -u steensma:password http://localhost:5002/api/summary
```

---

## 📁 File Locations

| What | Where |
|------|-------|
| **App Code** | `/home/ubuntu/eosplatform/app.py` |
| **Templates** | `/home/ubuntu/eosplatform/templates/` |
| **Data Files** | `/home/ubuntu/eosplatform/datasheets/*.csv` |
| **Sync Script** | `/home/ubuntu/eosplatform/eos_sync.py` |
| **Services** | `/etc/systemd/system/eosplatform*.service` |
| **Nginx Config** | `/etc/nginx/sites-available/eos.coresteensma.com` |
| **SSL Cert** | `/etc/letsencrypt/live/eos.coresteensma.com/` |
| **Logs** | `/home/ubuntu/eosplatform/eos_sync.log` |

---

## 🔐 Authentication

Uses same credentials as other Steensma sites:
- Username: `steensma`
- Password: (check `/etc/nginx/.htpasswd`)

**To update password:**
```bash
sudo htpasswd /etc/nginx/.htpasswd steensma
```

---

## 🎨 Pages Available

| URL | What It Shows |
|-----|---------------|
| `/` | 6-card dashboard (landing page) |
| `/rocks` | Quarterly rocks detail |
| `/scorecard` | Weekly metrics with 13-week trend |
| `/issues` | Full issues list |
| `/todos` | Task list with due dates |
| `/vision` | Vision/Traction Organizer |
| `/accountability` | Accountability chart |
| `/meeting` | L10 meeting page (planned) |
| `/api/summary` | JSON summary for cards |
| `/api/data` | Complete JSON dataset |
| `/health` | Health check |

---

## 📊 Sample Google Sheet Template

**Copy this structure into Google Sheets:**

### Tab 1: Rocks
```
Description | Owner | Status | DueDate | Progress
Work with Scott for continuity | Jeff | COMPLETE | 3/31/2026 | 100
Install 4th technician | Jeff | ON TRACK | 3/31/2026 | 60
CSR training decision | Don | NOT STARTED | 3/31/2026 | 0
```

### Tab 2: Scorecard
```
Metric | Owner | Goal | Week1 | Week2 | ... | Status
Revenue | Jeff | $100K | 95000 | 102000 | ... | GREEN
Shop Efficiency | Ops | 85% | 82 | 86 | ... | GREEN
```

### Tab 3: Issues
```
Issue | Priority | Owner | DateAdded | Status
Property mgmt parking | HIGH | Jeff | 1/15/2026 | OPEN
Team communication | HIGH | Don | 1/20/2026 | IN PROGRESS
```

### Tab 4: To-Dos
```
Task | Owner | DueDate | Status | Source
Review Q1 financials | Jeff | 2/15/2026 | OPEN | Meeting
Order shop equipment | Don | 2/18/2026 | OPEN | Rock
```

### Tab 5: VTO
```
Section | Content
Quarter | Q1 2026
Core Values | Integrity, Excellence, Accountability
10-Year Target | $50M revenue, 5 locations
```

### Tab 6: Accountability
```
Seat | Accountabilities | Person | Roles
Site Lead - Plainwell | P&L, Leadership | Jeff | Operations, Sales
Technician 4 | Equipment repair | Open | Service, Warranty
```

---

## 🔄 Update Workflow (Daily/Weekly)

### **Weekly L10 Meeting:**
1. Review Scorecard → Update Week13 with new actuals
2. Review Rocks → Update Progress % and Status
3. Review Issues → Add new, mark resolved
4. Review To-Dos → Mark complete, add new
5. **Export each tab as CSV**
6. **Upload to server** or Google Drive
7. **Dashboard updates automatically**

### **Quarterly (Q2, Q3, Q4):**
1. Archive completed rocks
2. Create new rocks for new quarter
3. Update VTO with new quarter info
4. Review and update Accountability Chart

---

## 🎯 What Makes This Different (vs Ninety.io / EOS One)

| Feature | Ninety.io | Your Platform |
|---------|-----------|---------------|
| Cost | $11/user/month | $0 (self-hosted) |
| Data ownership | Their servers | Your server |
| Customization | Limited | Full control |
| Integration | Their API | Direct database/files |
| Privacy | Shared platform | Private instance |
| Branding | Ninety branded | Steensma branded |

**You "stole" the UX patterns but built it YOUR way.**

---

## 🚨 Troubleshooting

### **Site not loading?**
```bash
sudo systemctl status eosplatform
sudo systemctl status nginx
journalctl -u eosplatform -n 50
```

### **Data not updating?**
```bash
ls -lh /home/ubuntu/eosplatform/datasheets/
# Check file timestamps - should be recent
```

### **Sync not working?**
```bash
sudo systemctl status eosplatform-gdrive-sync
tail -50 /home/ubuntu/eosplatform/eos_sync.log
```

### **401 Authentication Error?**
- Check credentials with shop.coresteensma.com
- Should be same username/password

---

## 📈 Future Enhancements (Phase 2)

- [ ] L10 Meeting page with segue, IDS, conclude
- [ ] Historical rock trends (completion velocity)
- [ ] Scorecard graphs (13-week line charts)
- [ ] Issue aging (days open)
- [ ] To-do assignment workflow
- [ ] Mobile-responsive design
- [ ] Real-time collaborative editing
- [ ] Email notifications (overdue to-dos, etc.)
- [ ] Google Sheets API (eliminate CSV export step)
- [ ] Process documentation section

---

## ✅ Quick Start Checklist

- [x] Domain configured (eos.coresteensma.com)
- [x] SSL certificate installed
- [x] Flask app running (port 5002)
- [x] Nginx proxy configured
- [x] Systemd services enabled
- [x] Sample CSV data created
- [ ] **Your turn:** Create Google Sheet with 6 tabs
- [ ] Upload real EOS data to CSVs
- [ ] Test dashboard with your team
- [ ] Decide: Manual upload vs Google Drive sync
- [ ] Set up weekly update workflow

---

## 📞 Support

**Location:** `/home/ubuntu/eosplatform/`
**Port:** 5002
**URL:** https://eos.coresteensma.com
**Auth:** Same as shop.coresteensma.com

**Quick reference:**
```bash
# Restart app
sudo systemctl restart eosplatform

# Upload new data
scp rocks.csv ubuntu@server:/home/ubuntu/eosplatform/datasheets/

# Check logs
journalctl -u eosplatform -f
```

---

## 🎉 You Did It!

You now have a fully functional EOS strategic platform that:
- ✅ Separates tactical (shop) from strategic (EOS)
- ✅ Uses Google Sheets as the source of truth
- ✅ Provides transparent visibility for all staff
- ✅ Costs $0/month (vs $11/user for Ninety.io)
- ✅ Is 100% under your control and customizable
- ✅ Matches your vision from the voice transcript

**Next:** Populate with your real Q1 2026 rocks, scorecard metrics, and issues. Run your first L10 meeting with the live dashboard! 🚀

---

*Last updated: February 9, 2026*  
*Created in: ~2 hours (told you it was doable in a weekend!)*
