import os
import re
import uuid

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from . import auth, config, db, llm, payments
from .catalog import PACKS, TOOLS, pack_amount

app = FastAPI(title="SnapSell API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    db.init()


# ------------------------------------------------------------------ models


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s.]+\.[^@\s]+$")


class Credentials(BaseModel):
    email: str
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def valid_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not EMAIL_RE.match(value):
            raise ValueError("Enter a valid email address")
        return value


class ToolRequest(BaseModel):
    payload: dict[str, str]


class CheckoutRequest(BaseModel):
    pack_id: str
    currency: str = "INR"


class RazorpayVerify(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


# ------------------------------------------------------------------ helpers


def current_user(authorization: str | None = Header(default=None)) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Not signed in")
    user_id = auth.read_token(authorization.split(" ", 1)[1])
    if user_id is None:
        raise HTTPException(401, "Session expired, sign in again")
    with db.cursor() as cur:
        row = cur.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if row is None:
        raise HTTPException(401, "Account not found")
    return dict(row)


def public_user(row: dict) -> dict:
    return {"email": row["email"], "credits": row["credits"], "plan": row["plan"]}


def grant_credits(order_id: int) -> bool:
    """Idempotently mark an order paid and add its credits to the buyer."""
    with db.cursor() as cur:
        order = cur.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        if order is None or order["status"] == "paid":
            return False
        cur.execute("UPDATE orders SET status = 'paid' WHERE id = ?", (order_id,))
        cur.execute(
            "UPDATE users SET credits = credits + ? WHERE id = ?",
            (order["credits"], order["user_id"]),
        )
    return True


# ------------------------------------------------------------------ routes


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "provider": config.active_provider(), "ai": bool(config.OPENAI_API_KEY)}


@app.get("/api/catalog")
def catalog() -> dict:
    return {
        "tools": [{"id": key, **value} for key, value in TOOLS.items()],
        "packs": [{"id": key, **value} for key, value in PACKS.items()],
        "provider": config.active_provider(),
        "free_credits": config.FREE_CREDITS,
        "razorpay_key_id": config.RAZORPAY_KEY_ID,
    }


@app.post("/api/auth/signup")
def signup(body: Credentials) -> dict:
    email = body.email
    with db.cursor() as cur:
        if cur.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone():
            raise HTTPException(409, "That email already has an account")
        cur.execute(
            "INSERT INTO users (email, password_hash, credits) VALUES (?, ?, ?)",
            (email, auth.hash_password(body.password), config.FREE_CREDITS),
        )
        user_id = cur.lastrowid
        row = cur.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return {"token": auth.make_token(user_id), "user": public_user(dict(row))}


@app.post("/api/auth/login")
def login(body: Credentials) -> dict:
    with db.cursor() as cur:
        row = cur.execute("SELECT * FROM users WHERE email = ?", (body.email,)).fetchone()
    if row is None or not auth.verify_password(body.password, row["password_hash"]):
        raise HTTPException(401, "Wrong email or password")
    return {"token": auth.make_token(row["id"]), "user": public_user(dict(row))}


@app.get("/api/me")
def me(user: dict = Depends(current_user)) -> dict:
    with db.cursor() as cur:
        runs = cur.execute(
            "SELECT tool, cost, created_at FROM runs WHERE user_id = ? ORDER BY id DESC LIMIT 20",
            (user["id"],),
        ).fetchall()
    return {"user": public_user(user), "runs": [dict(r) for r in runs]}


@app.post("/api/tools/{tool_id}")
async def run_tool(tool_id: str, body: ToolRequest, user: dict = Depends(current_user)) -> dict:
    tool = TOOLS.get(tool_id)
    if tool is None:
        raise HTTPException(404, "Unknown tool")
    cost = tool["cost"]
    with db.cursor() as cur:
        row = cur.execute("SELECT credits FROM users WHERE id = ?", (user["id"],)).fetchone()
        if row["credits"] < cost:
            raise HTTPException(402, "Out of credits — top up to keep going")
        cur.execute("UPDATE users SET credits = credits - ? WHERE id = ?", (cost, user["id"]))
        cur.execute(
            "INSERT INTO runs (user_id, tool, cost) VALUES (?, ?, ?)", (user["id"], tool_id, cost)
        )
    try:
        output = await llm.generate(tool_id, body.payload)
    except Exception as exc:  # refund on model failure, never silently eat a credit
        with db.cursor() as cur:
            cur.execute("UPDATE users SET credits = credits + ? WHERE id = ?", (cost, user["id"]))
        raise HTTPException(502, f"Generation failed, credit refunded: {exc}") from exc
    with db.cursor() as cur:
        credits = cur.execute(
            "SELECT credits FROM users WHERE id = ?", (user["id"],)
        ).fetchone()["credits"]
    return {"output": output, "credits": credits}


@app.post("/api/checkout")
async def checkout(body: CheckoutRequest, user: dict = Depends(current_user)) -> dict:
    pack = PACKS.get(body.pack_id)
    if pack is None:
        raise HTTPException(404, "Unknown pack")
    provider = config.active_provider()
    if provider == "none":
        raise HTTPException(503, "No payment gateway configured yet")
    currency = "INR" if provider == "razorpay" else body.currency.upper()
    if provider == "stripe" and currency == "INR":
        currency = "USD"
    amount = pack_amount(body.pack_id, currency)
    receipt = f"snap_{uuid.uuid4().hex[:16]}"

    with db.cursor() as cur:
        cur.execute(
            "INSERT INTO orders (user_id, provider, provider_ref, pack_id, amount_minor,"
            " currency, credits) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user["id"], provider, receipt, body.pack_id, amount, currency, pack["credits"]),
        )
        order_id = cur.lastrowid

    try:
        if provider == "razorpay":
            remote = await payments.razorpay_create_order(
                amount, currency, receipt, {"order_id": str(order_id), "email": user["email"]}
            )
            with db.cursor() as cur:
                cur.execute(
                    "UPDATE orders SET provider_ref = ? WHERE id = ?", (remote["id"], order_id)
                )
            return {
                "provider": "razorpay",
                "key_id": config.RAZORPAY_KEY_ID,
                "order_id": remote["id"],
                "amount": amount,
                "currency": currency,
                "name": f"SnapSell {pack['name']} pack",
            }
        session = await payments.stripe_create_checkout_session(
            amount, currency, f"SnapSell {pack['name']} pack", str(order_id), user["email"]
        )
        with db.cursor() as cur:
            cur.execute("UPDATE orders SET provider_ref = ? WHERE id = ?", (session["id"], order_id))
        return {"provider": "stripe", "url": session["url"]}
    except payments.PaymentError as exc:
        raise HTTPException(502, str(exc)) from exc


@app.post("/api/payments/razorpay/verify")
def razorpay_verify(body: RazorpayVerify, user: dict = Depends(current_user)) -> dict:
    if not payments.razorpay_verify_checkout(
        body.razorpay_order_id, body.razorpay_payment_id, body.razorpay_signature
    ):
        raise HTTPException(400, "Signature check failed")
    with db.cursor() as cur:
        order = cur.execute(
            "SELECT * FROM orders WHERE provider_ref = ? AND user_id = ?",
            (body.razorpay_order_id, user["id"]),
        ).fetchone()
    if order is None:
        raise HTTPException(404, "Order not found")
    grant_credits(order["id"])
    with db.cursor() as cur:
        credits = cur.execute(
            "SELECT credits FROM users WHERE id = ?", (user["id"],)
        ).fetchone()["credits"]
    return {"credits": credits}


@app.post("/api/webhooks/razorpay")
async def razorpay_webhook(request: Request) -> dict:
    raw = await request.body()
    if not payments.razorpay_verify_webhook(raw, request.headers.get("x-razorpay-signature", "")):
        raise HTTPException(400, "Invalid signature")
    event = await request.json()
    if event.get("event") not in {"payment.captured", "order.paid"}:
        return {"ignored": True}
    entity = next(iter(event["payload"].values()))["entity"]
    reference = entity.get("order_id") or entity.get("id")
    with db.cursor() as cur:
        order = cur.execute("SELECT id FROM orders WHERE provider_ref = ?", (reference,)).fetchone()
    if order is None:
        return {"ignored": True}
    return {"credited": grant_credits(order["id"])}


@app.post("/api/webhooks/stripe")
async def stripe_webhook(request: Request) -> dict:
    raw = await request.body()
    event = payments.stripe_verify_webhook(raw, request.headers.get("stripe-signature", ""))
    if event is None:
        raise HTTPException(400, "Invalid signature")
    if event.get("type") != "checkout.session.completed":
        return {"ignored": True}
    reference = event["data"]["object"].get("client_reference_id")
    if not reference:
        return {"ignored": True}
    return {"credited": grant_credits(int(reference))}


# The API also serves the static site when it is bundled alongside, so a single
# origin works for both and the browser needs no cross-origin configuration.
SITE_DIR = os.environ.get(
    "SNAPSELL_STATIC_DIR",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static"),
)
if os.path.isdir(SITE_DIR):
    app.mount("/", StaticFiles(directory=SITE_DIR, html=True), name="site")
