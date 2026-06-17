# Ecom-OS — Realtime email handling

By default the CS loop runs on a ~2 min cron poll. **Realtime** makes it instant: Composio's
`OUTLOOK_MESSAGE_TRIGGER` watches the inbox and POSTs a webhook the moment an email arrives, which
runs the loop immediately. The cron stays on as a fallback.

## How it works
```
new email ─▶ Composio OUTLOOK_MESSAGE_TRIGGER ─▶ POST /api/v1/ecom/webhooks/email?token=… ─▶ run CS loop now
```
- The webhook route is NOT behind user auth (Composio can't send a bearer); it's authed by a
  shared secret in the URL (`ECOM_WEBHOOK_SECRET`, or derived from `LOCAL_AUTH_TOKEN`). It returns
  202 immediately and runs the loop in the background, so a slow loop never makes Composio retry.

## Enable it (after the tunnel is up, so the URL is public)
1. Enable the trigger: `POST /api/v1/ecom/realtime/enable` (or the **Enable** button in
   Settings → Realtime). This creates the Composio trigger instance for the inbox.
2. Get the webhook URL: `GET /api/v1/ecom/realtime` returns `webhook_url`
   (`https://<your-host>/api/v1/ecom/webhooks/email?token=…`).
3. In your **Composio project webhook settings**, set the delivery URL to that `webhook_url`.
   (The dashboard shows it to copy.)

That's it — new emails are now handled in seconds. Verified: enabling creates the trigger; the
receiver returns 401 on a bad token and 202 on a valid one (loop scheduled).
