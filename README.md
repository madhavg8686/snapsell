# SnapSell

AI toolkit for secondhand marketplace sellers — listing writer, price coach,
haggle replies, scam check and cross-post pack, sold as credits.

See [BUSINESS_MODEL.md](BUSINESS_MODEL.md) for pricing and the revenue model.

## Layout

```
backend/   FastAPI app (auth, credits, tools, Razorpay + Stripe checkout)
frontend/  static site (no build step)
```

## Run locally

```bash
python3 -m venv .venv && .venv/bin/pip install -e backend
SNAPSELL_DB=./snapsell.db .venv/bin/uvicorn app.main:app --app-dir backend --port 8000
python3 -m http.server 5173 --directory frontend
```

`frontend/config.js` points the site at the API; set it to `http://localhost:8000`
for local work.

## Configuration

| Variable | Purpose |
| --- | --- |
| `OPENAI_API_KEY` | enables real generation (otherwise the tools return a demo template) |
| `OPENAI_BASE_URL` / `OPENAI_MODEL` | point at any OpenAI-compatible provider, default `gpt-4o-mini` |
| `SNAPSELL_SECRET` | signing key for session tokens — set this in production |
| `SNAPSELL_DB` | SQLite path, default `/data/snapsell.db` |
| `SNAPSELL_FREE_CREDITS` | credits granted on signup, default 5 |
| `SNAPSELL_SITE_URL` | public site URL, used for Stripe return URLs |
| `SNAPSELL_ADMIN_PASSWORD` | unlocks the owner dashboard at `/admin.html`; unset disables it |

### Owner dashboard

`/admin.html` shows revenue, signups, tool usage and recent orders. It reads
`GET /api/admin/stats`, which requires the `X-Admin-Password` header. With
`SNAPSELL_ADMIN_PASSWORD` unset the route returns 404 and the page cannot be
unlocked.

### Payments

Configure **one** provider; the API auto-detects which is live.

Razorpay (India, UPI/cards/netbanking, settles to an Indian bank account):

| Variable | Where it comes from |
| --- | --- |
| `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET` | Dashboard → Account & Settings → API Keys |
| `RAZORPAY_WEBHOOK_SECRET` | Dashboard → Webhooks, when adding the endpoint |

Webhook endpoint: `POST <api>/api/webhooks/razorpay`, events `payment.captured`
and `order.paid`. Credits are also granted immediately from the browser via the
checkout signature, with the webhook as the backstop.

Stripe (international):

| Variable | Where it comes from |
| --- | --- |
| `STRIPE_SECRET_KEY` | Dashboard → Developers → API keys |
| `STRIPE_WEBHOOK_SECRET` | Dashboard → Developers → Webhooks |

Webhook endpoint: `POST <api>/api/webhooks/stripe`, event
`checkout.session.completed`.

Payouts go to whichever bank account is set in the gateway dashboard — the app
never touches bank details.
