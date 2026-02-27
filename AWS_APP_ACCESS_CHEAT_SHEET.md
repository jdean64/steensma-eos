# AWS App Access Cheat Sheet — Steensma

**Last Updated:** February 27, 2026  
**Cognito User Pool:** `us-east-1_9oIaLOcpR` (Region: us-east-1)  
**Auth Domain:** `steensma-auth.auth.us-east-1.amazoncognito.com`  
**Console URL:** https://console.aws.amazon.com/cognito/v2/idp/user-pools/us-east-1_9oIaLOcpR  
**Identity Center Console:** https://console.aws.amazon.com/singlesignon

---

## Architecture Overview

```
User Browser
    → https://{app}.coresteensma.com (nginx, TLS via Let's Encrypt)
    → nginx auth_request → oauth2-proxy (port 4181-4188)
    → Cognito Hosted UI → AWS Identity Center (SSO login)
    → Callback → oauth2-proxy validates token + checks cognito:groups
    → nginx proxies to backend app (port 5001-8087)
```

**Key concept:** Users authenticate via **AWS Identity Center** (SSO), NOT Cognito passwords. Cognito acts as the OIDC layer between Identity Center and oauth2-proxy. Cognito groups control which apps each user can access.

---

## Current App Inventory (Feb 27, 2026)

| App | Domain | Proxy Port | Cognito Client ID | Backend Port | Backend Status |
|-----|--------|-----------|-------------------|-------------|---------------|
| Shop | shop.coresteensma.com | 4181 | `3bvoh4vqfrj872jrtoi34pcsim` | 5001 | ✅ Running (python) |
| Warranty | warranty.coresteensma.com | 4182 | `5j8mrpmni5n85bpshmagq94580` | 8081 | ✅ Running (gunicorn) |
| Western | western.coresteensma.com | 4183 | `5fp9ql1abe89nanuonpaqas8js` | 8083 | ✅ Running (python3) |
| KPI | kpi.coresteensma.com | 4184 | `3ge7jiiv6nknnuteiteaiam3k` | 8084 | ✅ Running (python) |
| Parts | parts.coresteensma.com | 4185 | `3sjlih9a86kr6ejt2jaq6b4s4p` | 8085 | ✅ Running (gunicorn) |
| HAI | hai.coresteensma.com | 4186 | `1k42g7ntofr509aheb3h6cq4s9` | 8086 | ✅ Running (gunicorn) |
| Havyn | havyn.coresteensma.com | 4187 | `5l6igsgmovuuhkm2j54kdb2td0` | 8087 | ❌ Backend not listening |
| EOS | eos.coresteensma.com | 4188 | `2ct71va1p5birq81lbodgjj783` | 5002 | ✅ Running (gunicorn) |

> All 8 oauth2-proxy instances are **active and running**.  
> Shop has its own dedicated Cognito client (created Feb 26, 2026).  
> All other apps share the original EOS client IDs (all still pointing to the same Cognito User Pool).

---

## Authentication Flow — How It Works

1. User visits `https://shop.coresteensma.com`
2. nginx sends `auth_request` to `oauth2-proxy` at `/oauth2/auth`
3. If no valid session cookie → **401** → redirect to `/oauth2/sign_in`
4. oauth2-proxy redirects to **Cognito Hosted UI**
5. Cognito redirects to **AWS Identity Center** (federated IdP)
6. User logs in with their **AWS SSO credentials** (email + password + MFA)
7. Identity Center sends SAML assertion back to Cognito
8. Cognito issues authorization code → redirect to `/oauth2/callback`
9. oauth2-proxy exchanges code for tokens, **checks `cognito:groups`** claim
10. If user is in `{app}-users` group → **202** → access granted
11. If user is NOT in group → **403 Forbidden**

---

## Cognito Groups (Access Control)

All 8 groups have been created in Cognito. Each oauth2-proxy config enforces its group:

| Group Name | Controls Access To | Config Setting |
|-----------|-------------------|---------------|
| `shop-users` | shop.coresteensma.com | `allowed_groups = ["shop-users"]` |
| `warranty-users` | warranty.coresteensma.com | `allowed_groups = ["warranty-users"]` |
| `western-users` | western.coresteensma.com | `allowed_groups = ["western-users"]` |
| `kpi-users` | kpi.coresteensma.com | `allowed_groups = ["kpi-users"]` |
| `parts-users` | parts.coresteensma.com | `allowed_groups = ["parts-users"]` |
| `hai-users` | hai.coresteensma.com | `allowed_groups = ["hai-users"]` |
| `havyn-users` | havyn.coresteensma.com | `allowed_groups = ["havyn-users"]` |
| `eos-users` | eos.coresteensma.com | `allowed_groups = ["eos-users"]` |

Each config also has: `oidc_groups_claim = "cognito:groups"`

---

## Users & Group Assignments

| Name | Email | Identity Center | Cognito Groups |
|------|-------|----------------|---------------|
| Jeff Dean | jdean64@gmail.com | ✅ Yes | All 8 groups (admin) |
| Brian | brian@steensmalawn.com | ✅ Yes | shop-users, eos-users, warranty-users |
| Kurt | kurt@steensmalawn.com | ✅ Yes | shop-users, eos-users |
| Tammy | tammy@steensmalawn.com | ✅ Yes | kpi-users, eos-users |
| Steensma (shared) | *(AWS SSO account)* | ✅ Yes | **⚠️ Needs group assignment — see below** |

### ⚠️ Onboarding Users Who Authenticate via Identity Center

When a user logs in via Identity Center **for the first time**, Cognito auto-creates a **federated user** (username like `IdentityCenter_abc123`). This federated user has **NO group memberships** by default.

**To grant access:**
1. Have the user attempt to log in (they'll get 403 Forbidden)
2. Go to **Cognito Console → Users** → find the auto-created federated user
3. Click the user → **Group memberships** → Add to the appropriate groups
4. User signs out (`https://{app}.coresteensma.com/oauth2/sign_out`) and logs back in
5. Now the token includes cognito:groups and oauth2-proxy allows access

This applies to ALL users who authenticate through Identity Center, including the Steensma shared account.

---

## Quick Reference: Where Things Live on the Server

| What | Path |
|------|------|
| oauth2-proxy configs | `/etc/oauth2-proxy/oauth2-proxy-{app}.cfg` |
| oauth2-proxy service | `systemctl {start/stop/restart} oauth2-proxy@{app}` |
| nginx configs | `/etc/nginx/sites-enabled/{app}.coresteensma.com` |
| EOS app | `/home/ubuntu/eosplatform/` |
| Shop app | `/home/ubuntu/shopmgr/` |
| Warranty app | `/var/www/warranty_agent/` |
| Western app | `/home/ubuntu/westernai/` |
| KPI app | `/home/ubuntu/kpi/` |
| Parts app | `/home/ubuntu/partsai/` |
| HAI app | `/home/ubuntu/hai/` |

---

## oauth2-proxy Config Template

Each app's config at `/etc/oauth2-proxy/oauth2-proxy-{app}.cfg` follows this pattern:

```ini
# OAuth2 Proxy - {app}.coresteensma.com
provider = "oidc"
oidc_issuer_url = "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_9oIaLOcpR"
client_id = "CLIENT_ID_HERE"
client_secret = "CLIENT_SECRET_HERE"
login_url = "https://steensma-auth.auth.us-east-1.amazoncognito.com/oauth2/authorize"
redirect_url = "https://{app}.coresteensma.com/oauth2/callback"
redeem_url = "https://steensma-auth.auth.us-east-1.amazoncognito.com/oauth2/token"
oidc_jwks_url = "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_9oIaLOcpR/.well-known/jwks.json"
http_address = "127.0.0.1:{proxy_port}"
cookie_name = "_steensma_{app}"
cookie_secret = "RANDOM_32_BYTE_BASE64"
cookie_domains = [".coresteensma.com"]
cookie_secure = true
cookie_httponly = true
cookie_samesite = "lax"
cookie_expire = "12h"
email_domains = ["*"]
scope = "openid email profile"
reverse_proxy = true
set_xauthrequest = true
pass_access_token = false
skip_provider_button = true
whitelist_domains = [".coresteensma.com"]
upstreams = ["static://202"]
insecure_oidc_allow_unverified_email = true
session_store_type = "redis"
redis_connection_url = "redis://127.0.0.1:6379"
redis_connection_idle_timeout = 300

# Cognito group-based access control
oidc_groups_claim = "cognito:groups"
allowed_groups = ["{app}-users"]
```

**Critical fields:**
- `redirect_url` — MUST match the Cognito app client's callback URL exactly
- `client_secret` — copy carefully from Cognito Console (regenerate if token exchange fails with `invalid_client_secret`)
- `allowed_groups` — enforces per-app access; user must be in this Cognito group

---

## How to Create a New Cognito App Client

1. Go to **Cognito Console** → User Pool → **App integration** tab
2. Scroll to **App clients and analytics** → **Create app client**
3. Fill in:
   - **App client name:** `{app}.coresteensma.com`
   - **Authentication flows:** ALLOW_USER_SRP_AUTH, ALLOW_REFRESH_TOKEN_AUTH
   - **Generate client secret:** ✅ Yes
4. Under **Hosted UI:**
   - **Callback URL:** `https://{app}.coresteensma.com/oauth2/callback`
   - **Sign-out URL:** `https://{app}.coresteensma.com/`
   - **Identity providers:** Select **AWS Identity Center** (NOT just "Cognito user pool")
   - **OAuth grant types:** Authorization code grant
   - **Scopes:** openid, email, profile
5. Click **Create** → Copy the **Client ID** and **Client Secret**

> ⚠️ **You MUST select AWS Identity Center as the Identity Provider** in the Hosted UI settings. If you only select "Cognito user pool", users will see the Cognito login form instead of being redirected to AWS SSO.

---

## How to Update an App's Client ID on the Server

```bash
# 1. Edit the config (replace {app} with: shop, warranty, eos, etc.)
sudo nano /etc/oauth2-proxy/oauth2-proxy-{app}.cfg

# 2. Change these two lines:
#    client_id = "NEW_CLIENT_ID_HERE"
#    client_secret = "NEW_CLIENT_SECRET_HERE"

# 3. Restart just that app's proxy:
sudo systemctl restart oauth2-proxy@{app}

# 4. Verify it's running:
sudo systemctl status oauth2-proxy@{app}
```

---

## How to Add a New User

### Step 1: Create in AWS Identity Center
1. Go to **IAM Identity Center** (https://console.aws.amazon.com/singlesignon)
2. **Users** → **Add user**
3. Enter: username, email, first/last name
4. User receives email to set password + MFA

### Step 2: User Logs In (Creates Federated Identity)
1. User visits any app (e.g. `https://shop.coresteensma.com`)
2. They authenticate through Identity Center
3. Cognito auto-creates a federated user entry
4. User gets 403 Forbidden (no group memberships yet)

### Step 3: Assign Groups in Cognito
1. Go to **Cognito Console** → **Users** tab
2. Find the **federated user** (auto-created, may have a prefix like `IdentityCenter_`)
3. Click user → **Group memberships** → Add to appropriate groups
4. User signs out and logs back in → access granted

---

## Troubleshooting

### User gets 403 Forbidden after login
**Cause:** User authenticated successfully but is not in the required Cognito group.  
**Fix:** Find the user in Cognito → add to the `{app}-users` group → sign out and back in.

### User sees Cognito login form instead of AWS SSO
**Cause:** The Cognito app client's Hosted UI doesn't have AWS Identity Center as an IdP.  
**Fix:** Cognito Console → App integration → click the app client → Hosted UI → add AWS Identity Center as identity provider.

### Token exchange fails with `invalid_client_secret`
**Cause:** Client secret in oauth2-proxy config doesn't match Cognito.  
**Fix:** Cognito Console → App integration → click the app client → copy the Client secret → update config → restart proxy. Client secrets are long (48+ chars) — copy carefully.

### Proxy returns 500 Internal Server Error
**Cause:** Usually a token exchange failure. Check logs:
```bash
sudo journalctl -u oauth2-proxy@{app} --since "5 minutes ago" --no-pager
```

### User authenticated but app shows error page
**Cause:** Backend app not running.  
**Fix:** Check backend: `sudo ss -tlnp | grep :{port}` → restart the app service.

---

## Common Commands

```bash
# Check all proxy statuses
systemctl list-units 'oauth2-proxy@*'

# Restart a specific app's proxy
sudo systemctl restart oauth2-proxy@shop

# Restart all proxies
for app in shop warranty western kpi parts hai havyn eos; do
    sudo systemctl restart oauth2-proxy@$app
done

# Check nginx config before reloading
sudo nginx -t && sudo systemctl reload nginx

# View proxy logs for an app (live tail)
sudo journalctl -u oauth2-proxy@eos -f --no-pager

# View recent proxy logs
sudo journalctl -u oauth2-proxy@shop --since "10 minutes ago" --no-pager

# Restart the EOS app itself
sudo systemctl restart eosplatform

# Check what's running on a port
sudo ss -tlnp | grep :4181

# Clear a user's session (force re-login)
# User visits: https://{app}.coresteensma.com/oauth2/sign_out

# Check all backend health
for port in 5001 5002 8081 8083 8084 8085 8086 8087; do
    echo -n "Port $port: "
    sudo ss -tlnp | grep ":$port " >/dev/null && echo "UP" || echo "DOWN"
done
```

---

## Setup Completion Status

- [x] Create separate Cognito app client for **Shop** ✅ (Feb 26, 2026)
- [x] Add Brian, Kurt, Tammy as Cognito users ✅ (Feb 26, 2026)
- [x] Create all 8 Cognito groups ✅ (Feb 26, 2026)
- [x] Assign users to groups ✅ (Feb 26, 2026)
- [x] Add `allowed_groups` + `oidc_groups_claim` to all 8 proxy configs ✅ (Feb 26, 2026)
- [x] Add `redirect_url` to all 8 proxy configs ✅ (Feb 27, 2026)
- [x] Add AWS Identity Center as IdP on Shop client ✅ (Feb 27, 2026)
- [x] Fix Shop client secret (token exchange) ✅ (Feb 27, 2026)
- [x] Verify Jeff (jdean64@gmail.com) can access Shop via SSO ✅ (Feb 27, 2026)
- [x] Verify EOS login works via SSO ✅ (Feb 27, 2026)
- [ ] Assign Steensma shared account to Cognito groups (need federated user created first)
- [ ] Verify each user can only access their assigned apps
- [ ] Confirm Brian, Kurt, Tammy received invite emails and set passwords
- [ ] Test group restriction (user NOT in group gets 403)
- [ ] Verify all 7 remaining apps work end-to-end with correct IdP
- [ ] Start Havyn backend (port 8087 not listening)
