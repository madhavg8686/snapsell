import httpx

from .config import OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL

SYSTEM_PROMPTS = {
    "listing": (
        "You write secondhand marketplace listings that sell fast without overpromising. "
        "Return markdown with sections: **Title** (max 70 chars), **Description** (short paragraphs "
        "plus a bullet spec list), **Tags** (comma separated), **Photo shot list** (3 shots). "
        "Never invent specs the seller did not state; if something important is missing, add a "
        "'Fill this in' placeholder."
    ),
    "pricing": (
        "You are a pricing analyst for secondhand goods. Return markdown with: **Asking price**, "
        "**Realistic sale range**, **Walk-away floor**, **Why** (3 bullets referencing condition, "
        "demand and season), **Price drop plan** (what to do at day 7 and day 14). Use the currency "
        "of the stated market. State clearly that figures are estimates, not verified comps."
    ),
    "haggle": (
        "You coach private sellers through price negotiation. Return markdown with three labelled "
        "replies: **Hold firm**, **Small concession**, **Bundle/close now**. Each reply is at most 3 "
        "sentences, sounds like a normal person texting, and never goes below the seller's stated "
        "minimum price. End with one line: **Read on this buyer** — what their message signals."
    ),
    "scam": (
        "You screen marketplace buyer messages for fraud. Return markdown with: **Risk: LOW/MEDIUM/HIGH**, "
        "**Red flags** (bullets quoting the exact phrases), **What they are likely after**, "
        "**Safe next step** (one concrete action). Be decisive but note that you are a heuristic "
        "assistant, not a guarantee."
    ),
    "crosspost": (
        "You adapt one listing for multiple marketplaces. For each requested platform return a "
        "markdown section with a platform-appropriate title, body, and any platform-specific field "
        "(category, condition, hashtags). Respect each platform's norms: eBay is spec-heavy, "
        "Facebook Marketplace is casual and short, OLX leads with price and location, Vinted is "
        "fashion-focused with hashtags."
    ),
}


def build_user_prompt(tool: str, payload: dict) -> str:
    lines = [f"{key}: {value}" for key, value in payload.items() if str(value).strip()]
    return "\n".join(lines) if lines else "(no details provided)"


def _fallback(tool: str, payload: dict) -> str:
    detail = build_user_prompt(tool, payload)
    return (
        "**Demo mode**\n\n"
        "No model API key is configured on this deployment, so here is a structured template "
        "instead of a generated answer.\n\n"
        f"Tool requested: `{tool}`\n\n"
        "Your input:\n\n```\n" + detail + "\n```\n\n"
        "Set `OPENAI_API_KEY` on the API service to enable live generation."
    )


async def generate(tool: str, payload: dict) -> str:
    if not OPENAI_API_KEY:
        return _fallback(tool, payload)
    body = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPTS[tool]},
            {"role": "user", "content": build_user_prompt(tool, payload)},
        ],
        "temperature": 0.7,
    }
    async with httpx.AsyncClient(timeout=90) as client:
        resp = await client.post(
            f"{OPENAI_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
            json=body,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
