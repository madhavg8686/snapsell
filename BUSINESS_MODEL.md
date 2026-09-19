# SnapSell — business model

## The product

Five AI tools aimed at one person: someone selling used things on OLX, Facebook
Marketplace, eBay or Vinted.

| Tool | Job it does | Price |
| --- | --- | --- |
| Listing Writer | item details → title, description, tags, photo shot list | 1 credit |
| Price Coach | asking price, realistic range, walk-away floor, drop plan | 1 credit |
| Haggle Reply | three replies to a lowball offer that never go under your floor | 1 credit |
| Scam Check | risk score + red flags for a buyer message | 1 credit |
| Cross-Post Pack | one listing rewritten for four marketplaces | 2 credits |

## Why this niche and not "another AI writer"

- **The buyer already has money on the line.** Someone listing a ₹40,000 scooter
  will spend ₹399 to sell it faster or avoid a courier scam. Generic copy tools
  have to argue about ROI; this one doesn't.
- **Naturally repeat, naturally bursty.** People clear out their homes in
  bursts — 8 items in one weekend, nothing for four months. That kills
  subscriptions but suits credits perfectly.
- **Scam Check is the hook.** It is the only tool here that is about fear, not
  convenience, and fear converts. It is also the most shareable ("paste your
  sketchy buyer message here") — cheap organic distribution in the
  marketplace-seller and flipping communities where paid acquisition is useless.
- **Five tools, one wallet.** Each tool raises credits burned per item without
  raising acquisition cost.

## Pricing

| Pack | Credits | USD | INR | Per credit |
| --- | --- | --- | --- | --- |
| Starter | 60 | $5 | ₹399 | ~8.3¢ |
| Seller | 200 | $12 | ₹999 | ~6.0¢ |
| Pro | 700 | $29 | ₹2,399 | ~4.1¢ |

New accounts get 5 free credits — enough to finish one real listing end to end,
which is the moment the product proves itself.

## Unit economics

- Model cost per run with `gpt-4o-mini`: roughly $0.0003–$0.0008.
- Revenue per credit: $0.041–$0.083.
- **Gross margin: >95%** at every pack size.
- Hosting: one Fly.io machine + static frontend ≈ $0–5/month at this scale.

## The path to $30/day

$30/day ≈ **2.5 Seller packs per day** ≈ 75 packs/month.

| Lever | Needed for $30/day |
| --- | --- |
| Visitors/day at 3% visitor→paid | ~85 |
| Signups/day at 25% signup→paid | ~10 |
| Or: returning buyers | ~45 repeat customers buying one $12 pack every 18 days |

85 visitors/day is a low bar, and it is reachable without ad spend:

1. **Free tool as the front door.** Scam Check with no signup for the first
   run — it is the query people already search ("is this buyer a scam").
2. **SEO on transactional long tails.** "how to price a used <item> in <city>",
   "what to reply when a buyer lowballs", one page per marketplace. These pages
   are cheap to produce because the product itself generates the examples.
3. **Community distribution.** r/Flipping, r/eBaySellers, Vinted and OLX seller
   groups, local resale WhatsApp/Telegram groups. Post the Scam Check output,
   not the landing page.
4. **Referral credits.** 10 free credits when an invited friend buys a pack.

## Risks, stated plainly

- No moat in the prompts. The defensibility is the niche wedge, the free-tool
  funnel and the SEO surface, not the model.
- Marketplaces could ship this natively; that is why the product is
  cross-marketplace, which no single marketplace will build.
- $30/day is a traffic problem, not a product problem. Without step 1–4 above
  being worked weekly, the app earns $0 no matter how good it is.
