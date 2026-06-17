#!/usr/bin/env python3
"""One-shot Shopify OAuth bootstrap.

Runs the Authorization Code grant against the brand's own Shopify app to mint a
permanent OFFLINE Admin API access token, then writes it to .env.local as
SHOPIFY_ACCESS_TOKEN. Used only when Composio's managed OAuth is unavailable; the
resulting token is treated as a server-side secret (never logged, never committed).

Usage:
    python3 scripts/bootstrap/shopify_oauth.py

Requires in .env.local: SHOPIFY_CLIENT_ID, SHOPIFY_SECRET_KEY, SHOPIFY_STORE_URL.
You must add http://localhost:53682/callback to the app's Allowed redirection URL(s).
"""
from __future__ import annotations

import hashlib
import hmac
import http.server
import json
import os
import secrets
import subprocess
import sys
import threading
import urllib.parse
import urllib.request
from pathlib import Path

PORT = 53682
REDIRECT_URI = f"http://localhost:{PORT}/callback"
ENV_PATH = Path(__file__).resolve().parents[2] / ".env.local"

# Read-first scope set. Deliberately excludes write_orders so this connection can
# never issue refunds (Invariant 2 — refunds get a separate scoped connection).
SCOPES = ",".join(
    [
        "read_orders",
        "read_customers",
        "read_fulfillments",
        "read_assigned_fulfillment_orders",
        "read_shipping",
        "read_locations",
        "read_products",
        "read_inventory",
        "read_content",
        "read_price_rules",
        "read_discounts",
        "write_discounts",
        "read_publications",
    ]
)


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    for line in ENV_PATH.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        env[k.strip()] = v.strip()
    return env


def write_token(token: str) -> None:
    """Persist SHOPIFY_ACCESS_TOKEN to .env.local without echoing it."""
    lines = ENV_PATH.read_text().splitlines()
    out, found = [], False
    for line in lines:
        if line.startswith("SHOPIFY_ACCESS_TOKEN="):
            out.append(f"SHOPIFY_ACCESS_TOKEN={token}")
            found = True
        else:
            out.append(line)
    if not found:
        out.append(f"SHOPIFY_ACCESS_TOKEN={token}")
    ENV_PATH.write_text("\n".join(out) + "\n")


def main() -> int:
    env = load_env()
    client_id = env.get("SHOPIFY_CLIENT_ID", "")
    secret = env.get("SHOPIFY_SECRET_KEY", "")
    shop = env.get("SHOPIFY_STORE_URL", "")
    if not (client_id and secret and shop):
        print("ERROR: SHOPIFY_CLIENT_ID / SHOPIFY_SECRET_KEY / SHOPIFY_STORE_URL missing")
        return 1

    state = secrets.token_urlsafe(24)
    result: dict[str, object] = {}
    done = threading.Event()

    def verify_hmac(params: dict[str, list[str]]) -> bool:
        provided = params.get("hmac", [""])[0]
        msg = "&".join(
            f"{k}={v[0]}" for k, v in sorted(params.items()) if k not in ("hmac", "signature")
        )
        digest = hmac.new(secret.encode(), msg.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(digest, provided)

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *_args):  # silence access logs (avoid leaking query)
            pass

        def do_GET(self):  # noqa: N802
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path != "/callback":
                self.send_response(404)
                self.end_headers()
                return
            params = urllib.parse.parse_qs(parsed.query)
            ok = (
                params.get("state", [""])[0] == state
                and verify_hmac(params)
                and "code" in params
            )
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            if ok:
                result["code"] = params["code"][0]
                self.wfile.write(
                    b"<h2>Shopify connected.</h2><p>You can close this tab and "
                    b"return to the terminal.</p>"
                )
            else:
                self.wfile.write(b"<h2>Validation failed.</h2><p>state/hmac mismatch.</p>")
            done.set()

    server = http.server.HTTPServer(("localhost", PORT), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    auth_url = (
        f"https://{shop}/admin/oauth/authorize?"
        + urllib.parse.urlencode(
            {
                "client_id": client_id,
                "scope": SCOPES,
                "redirect_uri": REDIRECT_URI,
                "state": state,
                # no grant_options[]=per-user -> offline (permanent) token
            }
        )
    )
    print("Opening Shopify authorize page in your browser…")
    print("If you see 'redirect_uri is not whitelisted', add this to the app's")
    print(f"Allowed redirection URL(s):  {REDIRECT_URI}")
    print(f"\nAuthorize URL:\n{auth_url}\n")
    try:
        subprocess.run(["open", auth_url], check=False)
    except Exception:
        pass

    if not done.wait(timeout=300):
        print("ERROR: timed out waiting for callback (5 min).")
        return 2
    server.shutdown()

    code = result.get("code")
    if not code:
        print("ERROR: OAuth callback validation failed (state/hmac).")
        return 3

    # Exchange code -> offline access token
    body = json.dumps(
        {"client_id": client_id, "client_secret": secret, "code": code}
    ).encode()
    req = urllib.request.Request(
        f"https://{shop}/admin/oauth/access_token",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.loads(resp.read())

    token = payload.get("access_token", "")
    granted = payload.get("scope", "")
    if not token:
        print("ERROR: no access_token in exchange response.")
        return 4

    write_token(token)
    print("\n[OK] Offline access token written to .env.local as SHOPIFY_ACCESS_TOKEN")
    print(f"[OK] Granted scopes: {granted}")
    print("(token value not printed by design)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
