"""Product catalog: the five AI tools and the credit packs that fund them."""

TOOLS = {
    "listing": {
        "name": "Listing Writer",
        "blurb": "Item details in, a marketplace-ready title, description and tags out.",
        "cost": 1,
        "inputs": [
            {"key": "item", "label": "What are you selling?", "placeholder": "iPhone 12 128GB blue, 86% battery, small scratch on back", "type": "textarea"},
            {"key": "platform", "label": "Platform", "placeholder": "OLX / Facebook Marketplace / eBay / Vinted", "type": "text"},
            {"key": "tone", "label": "Tone", "placeholder": "honest and friendly", "type": "text"},
        ],
    },
    "pricing": {
        "name": "Price Coach",
        "blurb": "A defensible asking price, a walk-away floor and the reasoning to quote buyers.",
        "cost": 1,
        "inputs": [
            {"key": "item", "label": "Item + condition", "placeholder": "2019 Honda Activa 5G, 22k km, one owner", "type": "textarea"},
            {"key": "market", "label": "Market / city", "placeholder": "Pune, India", "type": "text"},
            {"key": "urgency", "label": "How fast do you need to sell?", "placeholder": "within 2 weeks", "type": "text"},
        ],
    },
    "haggle": {
        "name": "Haggle Reply",
        "blurb": "Paste a lowball offer, get three replies that hold your price without killing the deal.",
        "cost": 1,
        "inputs": [
            {"key": "message", "label": "Buyer's message", "placeholder": "last price 4000? i can pick up today", "type": "textarea"},
            {"key": "item", "label": "Item + your asking price", "placeholder": "PS4 Slim, asking 12000", "type": "text"},
            {"key": "floor", "label": "Your minimum price", "placeholder": "10500", "type": "text"},
        ],
    },
    "scam": {
        "name": "Scam Check",
        "blurb": "Risk score and red flags for any buyer message before you ship or share details.",
        "cost": 1,
        "inputs": [
            {"key": "message", "label": "Buyer's message", "placeholder": "I'll send my courier, just pay the shipping deposit via this link", "type": "textarea"},
            {"key": "context", "label": "Context", "placeholder": "Selling a laptop, buyer contacted on WhatsApp", "type": "text"},
        ],
    },
    "crosspost": {
        "name": "Cross-Post Pack",
        "blurb": "One listing rewritten for four marketplaces, each within its own length and style rules.",
        "cost": 2,
        "inputs": [
            {"key": "listing", "label": "Your existing listing text", "placeholder": "Paste the listing you already wrote", "type": "textarea"},
            {"key": "platforms", "label": "Target platforms", "placeholder": "OLX, Facebook Marketplace, eBay, Vinted", "type": "text"},
        ],
    },
}

PACKS = {
    "starter": {"name": "Starter", "credits": 60, "usd": 500, "inr": 39900, "blurb": "Enough for a weekend clear-out."},
    "seller": {"name": "Seller", "credits": 200, "usd": 1200, "inr": 99900, "blurb": "Best value for regular flippers.", "popular": True},
    "pro": {"name": "Pro", "credits": 700, "usd": 2900, "inr": 239900, "blurb": "For resellers running stock weekly."},
}


def pack_amount(pack_id: str, currency: str) -> int:
    pack = PACKS[pack_id]
    return pack["inr"] if currency.upper() == "INR" else pack["usd"]
