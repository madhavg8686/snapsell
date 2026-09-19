# Deploying SnapSell

One service hosts everything: the FastAPI API also serves the static site, so
there is a single URL and no CORS setup.

## 1. Deploy on Render

1. Push this repo to GitHub.
2. Render dashboard -> **New** -> **Blueprint**, pick the repo. Render reads
   [`render.yaml`](render.yaml): Docker runtime, health check on `/health`, and
   a 1 GB disk mounted at `/data` for the SQLite database.
3. When prompted, fill the secret env vars (they are marked `sync: false`):

   | Variable | Value |
   | --- | --- |
   | `OPENAI_API_KEY` | your OpenAI key — without it the tools return a demo template |
   | `RAZORPAY_KEY_ID` | Razorpay Dashboard -> Account & Settings -> API Keys |
   | `RAZORPAY_KEY_SECRET` | shown once when you generate the key |
   | `RAZORPAY_WEBHOOK_SECRET` | set in step 2 below |

4. Deploy. You get a URL like `https://snapsell-api.onrender.com` — that is the
   whole product.
5. Set `SNAPSELL_SITE_URL` to that same URL.

On Render's free plan the service sleeps when idle and the disk is unavailable;
use the Starter plan ($7/mo) for the persistent disk, or point `SNAPSELL_DB` at
a managed Postgres later if the user table outgrows SQLite.

## 2. Connect Razorpay

1. Razorpay Dashboard -> **Account & Settings** -> **API Keys** -> generate
   **Test** keys first. Put them in Render, redeploy, buy a pack with a test
   card, confirm credits land. Then swap in Live keys.
2. Razorpay Dashboard -> **Webhooks** -> **Add New Webhook**:
   - URL: `https://<your-render-url>/api/webhooks/razorpay`
   - Secret: any strong random string — paste the same value into
     `RAZORPAY_WEBHOOK_SECRET` on Render.
   - Active events: `payment.captured` and `order.paid`.
3. Razorpay Dashboard -> **Account & Settings** -> **Bank Accounts**: add the
   account that should receive settlements. Razorpay pays out on its settlement
   cycle (T+2 by default for Indian accounts). The app never sees or stores bank
   details — it only creates orders and verifies signatures.

Credits are granted twice over, safely: the browser handler verifies the
checkout signature for an instant balance update, and the webhook is the
backstop if the buyer closes the tab. `grant_credits` is idempotent, so a pack
is never credited twice.

## 3. Going live checklist

- [ ] Razorpay account KYC complete and Live mode activated
- [ ] Live keys in Render, webhook pointed at the production URL
- [ ] `SNAPSELL_SECRET` set to a long random string (Render generates one)
- [ ] One real ₹399 purchase made and refunded, settlement seen in the dashboard
- [ ] A domain pointed at the Render service (Render -> Settings -> Custom Domain)
