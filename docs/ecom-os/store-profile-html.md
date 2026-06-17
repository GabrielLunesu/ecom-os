# Ecom-OS — Store profile + HTML email replies

## Store profile (no hallucination)
Each store has operator-set profile fields (Settings → Stores → Edit profile):
display name, **public URL**, support email, **support sender/signature**, tracking page,
and free-form **brand facts**. The CS flow uses these real values — the tracking link is
`https://{public_url}/account` (not the ugly *.myshopify.com), the signature is
`support_name`, and `facts` are available to the agent. API: `PUT /ecom/stores/{id}/profile`.
Multi-store: each store carries its own profile.

## Styled (HTML) email replies
Plain-text replies collapsed into a wall of text in Outlook. The inbox connector now sends
**HTML** (`text_to_html`): blank lines → paragraphs, single newlines → `<br>`, URLs become
clickable links. Whatever wording the merchant writes in the Flows editor renders cleanly.

Because HTML can't ride the plain-text reply comment, replies are sent as a fresh "Re:"
email; multi-turn flow threading is preserved by matching inbound replies on conversation id
**or** the most recent ticket awaiting that customer (services/tickets.py).

## Verified live
A WISMO reply used `https://chicagooutletshop.com/account` + signature "Chicago Outlet
Support", with paragraphs/links — no myshopify URL, no guessed facts. 60 backend tests green.
