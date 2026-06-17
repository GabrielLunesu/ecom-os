# Ecom-OS — Go-live runbook (fresh Hermes VPS → tested)

Run these on the always-on VPS (your Hermes agent can run them, or you over SSH). The CS email
loop is server-side, so you can test it before setting up any public URL/tunnel.

## 1. Docker (not preinstalled on Hermes)
```bash
curl -fsSL https://get.docker.com | sh
docker compose version            # expect Compose v2
```

## 2. Code + config
```bash
git clone https://github.com/GabrielLunesu/ecom-os
cd ecom-os
cp .env.prod.example .env
python3 -c "import secrets;print(secrets.token_urlsafe(48))"   # -> LOCAL_AUTH_TOKEN
```
Edit `.env` and set:
```
AUTH_MODE=local
LOCAL_AUTH_TOKEN=<paste the token above>
BASE_URL=http://localhost:8000
CS_RUNTIME=flow                 # safe deterministic flows for the first run
POSTGRES_PASSWORD=<strong password>
COMPOSIO_API_KEY=<your Composio key>
SHOPIFY_STORE_URL=stv0xe-c4.myshopify.com
SHOPIFY_ACCESS_TOKEN=<your shpat_ token>
# TUNNEL_TOKEN= (leave empty for now)
```
(You can also leave the keys empty and set them later in the dashboard — but for the first boot
`up.sh` requires COMPOSIO_API_KEY + SHOPIFY_STORE_URL, so set at least those.)

## 3. Launch
```bash
./scripts/deploy/up.sh           # builds prod images, starts the stack, waits for health
```
Expect: `✓ Ecom-OS is up.`

## 4. Confirm both providers are live
```bash
T=$(grep '^LOCAL_AUTH_TOKEN=' .env | cut -d= -f2-)
curl -s -H "Authorization: Bearer $T" http://127.0.0.1:8080/api/v1/ecom/connections
```
Expect `"ready": true` (shopify + inbox connected).

## 5. Set the store profile (so the agent never guesses)
```bash
SID=$(curl -s -H "Authorization: Bearer $T" http://127.0.0.1:8080/api/v1/ecom/stores \
      | python3 -c "import sys,json;print(json.load(sys.stdin)[0]['id'])")
curl -s -X PUT -H "Authorization: Bearer $T" -H "Content-Type: application/json" \
  -d '{"name":"Chicago Outlet Shop","public_url":"chicagooutletshop.com",
       "support_email":"info@chicagooutletshop.com","support_name":"Chicago Outlet Support",
       "tracking_url":"","facts":"US outlet store. Free returns within 30 days."}' \
  http://127.0.0.1:8080/api/v1/ecom/stores/$SID/profile
```

## 6. Test it
1. From a **personal** email (not the support inbox), email `info@chicagooutletshop.com`
   — subject `Where is my order #1001?`, body `Hi, where is order #1001?`.
2. Run the loop once:
   ```bash
   curl -s -X POST -H "Authorization: Bearer $T" http://127.0.0.1:8080/api/v1/ecom/cs/run
   ```
3. Confirm the ticket resolved + read the reply:
   ```bash
   curl -s -H "Authorization: Bearer $T" http://127.0.0.1:8080/api/v1/ecom/tickets
   ```
4. Check your personal inbox — a styled HTML reply with the tracking link
   (`https://chicagooutletshop.com/account`) and the "Chicago Outlet Support" signature.

Also try a **refund**: subject `I want a refund for order #1001` → you get a 10%-off offer (reply
"no" → 20% → then it files a refund for human approval). Never an auto-refund.

## 7. Always-on + the dashboard
- **Always-on:** have the Hermes agent register a `cronjob` every ~2 min that runs the
  `POST /cs/run` curl above. New mail is then handled automatically.
- **Dashboard UI:** create a Cloudflare Tunnel, route your hostname → `http://proxy:80`, put the
  `TUNNEL_TOKEN` in `.env`, set `BASE_URL`/`CORS_ORIGINS` to the hostname, re-run `./scripts/deploy/up.sh`.
  Open the hostname, log in with `LOCAL_AUTH_TOKEN`, and manage flows, store profile, keys, and
  watch tickets live.

## 8. Upgrade the brain (optional, after the test passes)
Set `ANTHROPIC_API_KEY` and `CS_RUNTIME=hermes` (or `llm`) in `.env`, re-run `./scripts/deploy/up.sh`.

## Keep current
```bash
./scripts/deploy/update.sh        # pull latest, rebuild, migrate in place (data preserved)
```
