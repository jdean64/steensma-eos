# AWS IAM Identity Center Integration - Deployment Guide
**Project:** havyn.coresteensma.com SSO Integration  
**Date:** February 13, 2026  
**Status:** Ready for Deployment

---

## 🎯 What Was Built

Complete AWS IAM Identity Center (SSO) integration for steensma-eos platform with:

✅ **SAML 2.0 Authentication Module** (`saml_auth.py`)  
✅ **Hybrid Authentication** (SSO + Password fallback)  
✅ **Database Migration** (SSO fields added)  
✅ **Configuration Scripts** (Easy setup)  
✅ **Single Sign-On Routes** (Login, ACS, Logout, Metadata)  
✅ **Automatic User Provisioning** (Creates users on first login)  
✅ **Role Mapping** (AWS groups → EOS roles)

---

## 📁 Files Added/Modified

### New Files Created:
```
steensma-eos/
├── saml_auth.py                    # Core SAML authentication logic
├── saml_routes.py                  # Flask routes for SAML endpoints
├── configure_saml.py               # Interactive configuration script
├── migrate_add_sso_fields.py       # Database migration (COMPLETED ✅)
└── AWS_SSO_DEPLOYMENT_GUIDE.md     # This file
```

### Files Modified:
```
steensma-eos/
├── auth.py                         # Added is_saml_enabled() and hybrid auth helpers
├── routes.py                       # Updated login/logout for SAML support
├── app_multitenant.py              # Registered SAML routes
└── requirements.txt                # Added python3-saml, bcrypt
```

### Database Changes:
```sql
-- Already applied via migrate_add_sso_fields.py ✅
ALTER TABLE users ADD COLUMN sso_identity VARCHAR(255);
ALTER TABLE users ADD COLUMN sso_provider VARCHAR(50);
ALTER TABLE users ADD COLUMN federated_id VARCHAR(255);
CREATE INDEX idx_users_sso_identity ON users(sso_identity);
```

---

## 🚀 Deployment Steps

### Phase 1: Install Dependencies (2 minutes)

```bash
cd /home/ubuntu/SteensmaNumbers/steensma-eos

# Install SAML libraries
pip install python3-saml==1.16.0
pip install bcrypt==4.1.2

# Verify installation
python3 -c "from onelogin.saml2.auth import OneLogin_Saml2_Auth; print('✅ SAML library installed')"
```

**If you get xmlsec errors:**
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y libxml2-dev libxmlsec1-dev libxmlsec1-openssl pkg-config

# Then retry pip install
pip install python3-saml==1.16.0
```

---

### Phase 2: Configure AWS Identity Center Application (15 minutes)

#### Step 1: Create SAML Application in AWS

1. **Open AWS Console:** https://console.aws.amazon.com/singlesignon
2. **Navigate to:** Applications tab
3. **Click:** "Add application"
4. **Select:** "Add custom SAML 2.0 application"

#### Step 2: Fill in Application Details

```
Display name: Steensma EOS Platform
Description: Vision/Traction Organizer, Rocks, Scorecard, Issues
Application start URL: https://havyn.coresteensma.com
```

#### Step 3: Configure SAML Settings

```
Application ACS URL: https://havyn.coresteensma.com/saml/acs
Application SAML audience: https://havyn.coresteensma.com/saml/metadata
```

#### Step 4: Configure Attribute Mappings

Click "Attribute mappings" and add:

| Application attribute | Maps to this string value or user attribute | Format         |
|-----------------------|---------------------------------------------|----------------|
| Subject               | ${user:email}                               | emailAddress   |
| email                 | ${user:email}                               | basic          |
| firstName             | ${user:givenName}                           | basic          |
| lastName              | ${user:familyName}                          | basic          |
| groups                | ${user:groups}                              | basic          |

#### Step 5: Assign Users and Groups

1. Click "Assign users" tab
2. Assign groups:
   - Steensma-Admins
   - Steensma-Managers
   - Steensma-Users
   - (or assign individual users for testing)

#### Step 6: Get Configuration Details

After saving, AWS will show you:

1. **IAM Identity Center SAML metadata URL**  
   Something like: `https://portal.sso.us-east-1.amazonaws.com/saml/metadata/XXXX`

2. **SSO Login URL**  
   Something like: `https://portal.sso.us-east-1.amazonaws.com/saml/assertion/XXXX`

3. **Certificate**  
   Download or copy the X.509 certificate

**Save these details - you'll need them for the next step!**

---

### Phase 3: Configure Application (5 minutes)

```bash
cd /home/ubuntu/SteensmaNumbers/steensma-eos

# Run interactive configuration script
python3 configure_saml.py
```

The script will prompt you for:
1. Application name (default: Steensma EOS Platform)
2. Application URL (enter: https://havyn.coresteensma.com)
3. AWS metadata URL (from Phase 2, Step 6)
4. AWS SSO URL (from Phase 2, Step 6)
5. AWS logout URL (optional, press Enter to skip)
6. X.509 Certificate (paste from Phase 2, Step 6)

This creates `saml_settings.json` with your configuration.

**Verify configuration file was created:**
```bash
ls -la saml_settings.json
cat saml_settings.json | jq '.' # Pretty print (if jq installed)
```

---

### Phase 4: Test SAML Configuration (10 minutes)

#### Option A: Development Testing (Port 5001)

```bash
cd /home/ubuntu/SteensmaNumbers/steensma-eos

# Run dev server
python3 app_multitenant.py
# Or use Flask CLI
export FLASK_APP=app_multitenant.py
export FLASK_ENV=development
flask run --host=0.0.0.0 --port=5001
```

#### Open in browser:
```
http://localhost:5001/login
```

You should see:
- Standard login form (username/password)
- New "Sign in with AWS SSO" button (if SAML is configured)

#### Test SSO Flow:
1. Click "Sign in with AWS SSO"
2. Should redirect to AWS Identity Center login
3. Login with your AWS SSO credentials
4. Should redirect back to `/saml/acs`
5. Should create user (if first time) and log you in
6. Should redirect to dashboard

#### Check Logs:
```bash
# Look for SAML-related logs
tail -f /home/ubuntu/eosplatform/app.log  # If log file exists
# OR check terminal output for errors
```

#### Test Password Fallback:
1. Logout (should go to /saml/logout if you used SSO)
2. Go back to /login
3. Try logging in with password (should still work)

---

### Phase 5: Production Deployment (20 minutes)

#### Update Nginx Configuration

**File:** `/etc/nginx/sites-available/havyn.coresteensma.com` (or wherever it's configured)

```nginx
server {
    listen 80;
    server_name havyn.coresteensma.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name havyn.coresteensma.com;
    
    # SSL certificates (you should already have these)
    ssl_certificate /etc/letsencrypt/live/havyn.coresteensma.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/havyn.coresteensma.com/privkey.pem;
    
    # ❌ REMOVE THIS LINE (no more htpasswd!)
    # auth_basic "Restricted Access";
    # auth_basic_user_file /etc/nginx/.htpasswd;
    
    # Proxy to Flask app
    location / {
        proxy_pass http://127.0.0.1:5000;  # Or whatever port you're using
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Important for SAML POST requests
        proxy_read_timeout 600;
        proxy_connect_timeout 600;
        proxy_send_timeout 600;
    }
    
    # SAML endpoints - no caching
    location /saml/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;
    }
}
```

**Test nginx config:**
```bash
sudo nginx -t
```

**Reload nginx:**
```bash
sudo systemctl reload nginx
```

#### Update Systemd Service

**File:** `/etc/systemd/system/eosplatform.service`

Check it includes the updated code:

```ini
[Unit]
Description=Steensma EOS Platform
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/eosplatform
Environment="PATH=/home/ubuntu/.local/bin:/usr/bin"
Environment="SECRET_KEY=YOUR_ACTUAL_SECRET_KEY_HERE"
ExecStart=/usr/bin/python3 app_multitenant.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Copy updated files to production:**
```bash
# Assuming /home/ubuntu/eosplatform is your production directory
cd /home/ubuntu/SteensmaNumbers/steensma-eos

# Copy new files
cp saml_auth.py /home/ubuntu/eosplatform/
cp saml_routes.py /home/ubuntu/eosplatform/
cp configure_saml.py /home/ubuntu/eosplatform/
cp saml_settings.json /home/ubuntu/eosplatform/

# Copy updated files
cp auth.py /home/ubuntu/eosplatform/
cp routes.py /home/ubuntu/eosplatform/
cp app_multitenant.py /home/ubuntu/eosplatform/
cp requirements.txt /home/ubuntu/eosplatform/

# Install dependencies in production
cd /home/ubuntu/eosplatform
pip3 install -r requirements.txt
```

**Restart service:**
```bash
sudo systemctl daemon-reload
sudo systemctl restart eosplatform.service
sudo systemctl status eosplatform.service
```

**Check logs:**
```bash
sudo journalctl -u eosplatform.service -f
```

---

### Phase 6: User Testing (15 minutes)

#### Create Test Users in AWS SSO

1. Go to AWS Identity Center → Users
2. Add test users (or use existing ones)
3. Assign to "Steensma-Admins" group
4. Users will receive email to set password

#### Test Complete Flow

1. **Open:** https://havyn.coresteensma.com
2. **Expected:** Redirect to /login
3. **Click:** "Sign in with AWS SSO"
4. **Expected:** Redirect to AWS Identity Center
5. **Login:** With AWS SSO credentials
6. **Expected:** Redirect back to havyn.coresteensma.com
7. **Expected:** User created automatically (if first time)
8. **Expected:** Dashboard loads with proper permissions
9. **Test permissions:** Based on group assignment
10. **Logout:** Should clear session and AWS SSO session

#### Test Edge Cases

- [ ] Password login still works
- [ ] Logout from SSO actually logs out
- [ ] Second login is faster (user already exists)
- [ ] Group changes in AWS reflect immediately
- [ ] Invalid user is rejected
- [ ] Expired session redirects to login

---

## 🔒 Security Checklist

Before going live:

- [ ] **SECRET_KEY:** Change in production (not the default!)
- [ ] **HTTPS:** SSL certificate valid and working
- [ ] **Session security:** Secure cookies enabled (SESSION_COOKIE_SECURE = True)
- [ ] **htpasswd removed:** No duplicate authentication
- [ ] **SAML cert valid:** Check expiration date
- [ ] **Emergency access:** Keep one password-auth admin account
- [ ] **Audit logs:** Verify SSO_LOGIN/SSO_LOGOUT events are logged
- [ ] **Backup database:** Before cutover
- [ ] **Firewall rules:** Port 5000 only accessible from localhost
- [ ] **CloudTrail enabled:** In AWS to track SSO access

---

## 🔍 Troubleshooting Guide

### Problem: "SAML not configured" error

**Solution:**
```bash
cd /home/ubuntu/eosplatform
ls -la saml_settings.json
# Should exist and be readable

# If missing, run configuration again
python3 configure_saml.py
```

### Problem: Certificate validation fails

**Solution:**
```bash
# Check certificate in saml_settings.json
cat saml_settings.json | grep x509cert

# Certificate should be base64 string, no headers
# Update certificate from AWS console if needed
```

### Problem: User created but no permissions

**Solution:**
```bash
# Check group mapping in saml_auth.py
python3 << 'EOF'
import sqlite3
conn = sqlite3.connect('eos_data.db')
cursor = conn.cursor()

# Check users
cursor.execute("SELECT id, username, email, sso_provider FROM users")
for row in cursor.fetchall():
    print(f"User: {row}")

# Check user_roles
cursor.execute("SELECT user_id, role_id FROM user_roles")
for row in cursor.fetchall():
    print(f"Role assignment: {row}")
    
conn.close()
EOF
```

**If roles missing:**
- Check AWS SSO group assignment
- Check group names match exactly (case-sensitive)
- Verify attribute mapping includes "groups"

### Problem: Redirect loop

**Solution:**
1. Clear browser cookies for havyn.coresteensma.com
2. Check nginx isn't adding auth_basic
3. Check Flask session configuration
4. Verify ACS URL matches exactly in AWS and code

### Problem: 404 on /saml/acs

**Solution:**
```bash
# Verify routes are registered
cd /home/ubuntu/eosplatform
python3 << 'EOF'
from app_multitenant import app
print("Routes:")
for rule in app.url_map.iter_rules():
    print(f"  {rule.rule} -> {rule.endpoint}")
EOF
```

Should show:
- `/saml/login`
- `/saml/acs`
- `/saml/logout`
- `/saml/metadata`

### Problem: XMLSec errors

**Solution:**
```bash
# Install system dependencies
sudo apt-get update
sudo apt-get install -y libxml2-dev libxmlsec1-dev libxmlsec1-openssl pkg-config

# Reinstall python3-saml
pip3 uninstall python3-saml
pip3 install python3-saml==1.16.0
```

---

## 📊 Monitoring & Maintenance

### Check SSO Health

```bash
# Check if SAML is configured
curl -s http://localhost:5000/saml/metadata | head -n 5

# Should return XML metadata
```

### View SSO Login Events

```sql
sqlite3 eos_data.db << 'EOF'
SELECT 
    timestamp,
    users.username,
    action,
    changes
FROM audit_log
JOIN users ON audit_log.user_id = users.id
WHERE action IN ('SSO_LOGIN', 'SSO_LOGOUT', 'LOGIN', 'LOGOUT')
ORDER BY timestamp DESC
LIMIT 20;
EOF
```

### Certificate Expiration

AWS Identity Center certificates typically expire after 1 year. Set reminder:

```bash
# Check certificate expiration (if using openssl)
python3 << 'EOF'
import json
from datetime import datetime
with open('saml_settings.json') as f:
    settings = json.load(f)
    cert = settings['idp']['x509cert']
    print(f"Certificate: {cert[:50]}...")
    # AWS certificates: check AWS console for expiration date
EOF
```

**When certificate expires:**
1. AWS will provide new certificate in console
2. Run `python3 configure_saml.py` again
3. Or manually update `saml_settings.json`
4. Restart application

---

## 🎯 Success Metrics

After successful deployment:

- ✅ Zero htpasswd authentication (retired!)
- ✅ All users login via AWS SSO
- ✅ Password login available as backup
- ✅ Audit trail shows SSO_LOGIN events
- ✅ Users provisioned automatically on first login
- ✅ Permissions based on AWS group membership
- ✅ Single logout clears both app and AWS sessions

---

## 🚀 Phase 2: Microsoft Entra ID Integration (Future)

Once AWS SSO is stable, you can connect Microsoft Entra ID:

### Quick Preview:

1. **In Azure Portal:**
   - Add "AWS IAM Identity Center" enterprise application
   - Configure SAML/SCIM sync
   - Enable automatic user provisioning
   - Map Azure AD groups to AWS SSO groups

2. **In AWS Identity Center:**
   - Change identity source from "Identity Center directory" to "External identity provider"
   - Upload Azure AD SAML metadata
   - Configure attribute mappings

3. **Result:**
   - Users login with Office 365 credentials
   - AWS SSO acts as passthrough
   - Your apps (havyn.coresteensma.com, heirloom-app, etc.) work unchanged

**Effort:** 4-8 hours (well-documented by Microsoft and AWS)

---

## 📞 Support & Documentation

### AWS Documentation:
- [IAM Identity Center User Guide](https://docs.aws.amazon.com/singlesignon/latest/userguide/)
- [Custom SAML 2.0 Applications](https://docs.aws.amazon.com/singlesignon/latest/userguide/samlapps.html)

### Library Documentation:
- [python3-saml](https://github.com/onelogin/python3-saml)

### Internal Documentation:
- Main implementation plan: `/home/ubuntu/SteensmaNumbers/AWS_IAM_SSO_IMPLEMENTATION_PLAN.md`
- Quick start guide: `/home/ubuntu/SteensmaNumbers/AWS_SSO_QUICKSTART.md`
- This deployment guide: `/home/ubuntu/SteensmaNumbers/steensma-eos/AWS_SSO_DEPLOYMENT_GUIDE.md`

---

## ✅ Deployment Checklist

Use this as your final checklist:

### Pre-Deployment
- [ ] Database migration completed
- [ ] Dependencies installed
- [ ] AWS application configured
- [ ] saml_settings.json created
- [ ] Test in development (port 5001)
- [ ] Emergency admin account identified

### Production Deployment
- [ ] Files copied to production directory
- [ ] requirements.txt installed
- [ ] Nginx configuration updated (htpasswd removed)
- [ ] Nginx config tested and reloaded
- [ ] Systemd service restarted
- [ ] Service status confirmed running
- [ ] HTTPS working correctly
- [ ] /saml/metadata accessible

### Post-Deployment Testing
- [ ] SSO login works
- [ ] User auto-provisioned
- [ ] Permissions correct (based on AWS groups)
- [ ] Password login still works (backup)
- [ ] Logout clears sessions
- [ ] Audit logs show SSO events
- [ ] Multiple users tested
- [ ] Edge cases tested

### Documentation
- [ ] Users notified of new login method
- [ ] IT team trained on AWS SSO console
- [ ] Emergency procedures documented
- [ ] Certificate expiration reminder set

---

**🎉 You're ready to deploy! Good luck!**

Questions? Check the troubleshooting section or AWS documentation.
