# AWS App Access Cheat Sheet — Steensma

**Last Updated:** February 26, 2026  
**Cognito User Pool:** `us-east-1_9oIaLOcpR` (Region: us-east-1)  
**Auth Domain:** `steensma-auth.auth.us-east-1.amazoncognito.com`  
**Console URL:** https://console.aws.amazon.com/cognito/v2/idp/user-pools/us-east-1_9oIaLOcpR

---

## Current App Inventory

| App | Domain | Proxy Port | Cognito Client ID | Backend Port |
|-----|--------|-----------|-------------------|-------------|
| Shop | shop.coresteensma.com | 4181 | `2ct71va1p5birq81lbodgjj783` ⚠️ shared | 8080 |
| Warranty | warranty.coresteensma.com | 4182 | `5j8mrpmni5n85bpshmagq94580` | 8081 |
| Western | western.coresteensma.com | 4183 | `5fp9ql1abe89nanuonpaqas8js` | 8083 |
| KPI | kpi.coresteensma.com | 4184 | `3ge7jiiv6nknnuteiteaiam3k` | 8084 |
| Parts | parts.coresteensma.com | 4185 | `3sjlih9a86kr6ejt2jaq6b4s4p` | 8085 |
| HAI | hai.coresteensma.com | 4186 | `1k42g7ntofr509aheb3h6cq4s9` | 8086 |
| Havyn | havyn.coresteensma.com | 4187 | `5l6igsgmovuuhkm2j54kdb2td0` | 8087 |
| EOS | eos.coresteensma.com | 4188 | `2ct71va1p5birq81lbodgjj783` ⚠️ shared | 5002 |

> ⚠️ Shop and EOS currently share the same Cognito client ID. Create a separate one for Shop (see below).

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
   - **Identity providers:** Cognito user pool
   - **OAuth grant types:** Authorization code grant
   - **Scopes:** openid, email, profile
5. Click **Create** → Copy the **Client ID** and **Client Secret**

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

## How to Control Who Sees What (Cognito Groups)

### Step 1: Create Groups in Cognito
1. Cognito Console → **Groups** tab → **Create group**
2. Create one group per app:
   - `shop-users`
   - `warranty-users`
   - `western-users`
   - `kpi-users`
   - `parts-users`
   - `hai-users`
   - `havyn-users`
   - `eos-users`

### Step 2: Assign Users to Groups
1. Cognito Console → **Users** tab → Click a user
2. **Group memberships** → **Add user to group**
3. Select the apps that user should access

Example assignments:
| User | Groups |
|------|--------|
| Jeff (jdean64@gmail.com) | All groups (admin) |
| Brian (brian@steensmalawn.com) | shop-users, eos-users, warranty-users |
| Kurt (kurt@steensmalawn.com) | shop-users, eos-users |
| Tammy (tammy@steensmalawn.com) | kpi-users, eos-users |

### Step 3: Tell the Server to Enforce Groups
After creating groups, add this line to each app's oauth2-proxy config:
```
allowed_groups = ["{app}-users"]
```
Then restart: `sudo systemctl restart oauth2-proxy@{app}`

---

## Users in the System

| Name | Email (Cognito) | EOS Username |
|------|----------------|-------------|
| Jeff Dean | jdean64@gmail.com | jeff |
| Brian | brian@steensmalawn.com | brian |
| Kurt | kurt@steensmalawn.com | kurt |
| Tammy | tammy@steensmalawn.com | tammy |

### How to Add a New User to AWS
1. Go to **IAM Identity Center** (https://console.aws.amazon.com/singlesignon)
2. **Users** → **Add user**
3. Enter: username, email, first/last name
4. User receives email to set password + MFA

### How to Add a New User to Cognito
1. Go to **Cognito Console** → **Users** tab → **Create user**
2. Enter email address
3. Choose: send invite email or set temp password
4. Add to appropriate groups

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

# View proxy logs for an app
sudo journalctl -u oauth2-proxy@eos -f --no-pager

# Restart the EOS app itself
sudo systemctl restart eosplatform

# Check what's running on a port
sudo ss -tlnp | grep :4181
```

---

## TO DO: Remaining Setup

- [ ] Create separate Cognito app client for **Shop** (currently shares with EOS)
- [ ] Add Brian, Kurt, Tammy as Cognito users
- [ ] Create Cognito groups for per-app access control
- [ ] Assign users to groups
- [ ] Add `allowed_groups` to each oauth2-proxy config
