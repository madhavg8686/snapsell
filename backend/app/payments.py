"""Payment gateway adapters.

Two providers are supported and selected by which keys are configured:
  * razorpay — Orders API + Checkout.js, credited via webhook or client-side signature verify
  * stripe   — Checkout Sessions, credited via webhook

Both credit the same `orders` row, so the rest of the app never branches on provider.
"""

import hashlib
import hmac
import json
import time

import httpx

from . import config


class PaymentError(Exception):
    pass


def _eq(a: str, b: str) -> bool:
    return hmac.compare_digest(a, b)


# --------------------------------------------------------------------------- razorpay


async def razorpay_create_order(amount_minor: int, currency: str, receipt: str, notes: dict) -> dict:
    if not (config.RAZORPAY_KEY_ID and config.RAZORPAY_KEY_SECRET):
        raise PaymentError("Razorpay keys are not configured")
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://api.razorpay.com/v1/orders",
            auth=(config.RAZORPAY_KEY_ID, config.RAZORPAY_KEY_SECRET),
            json={
                "amount": amount_minor,
                "currency": currency.upper(),
                "receipt": receipt[:40],
                "notes": notes,
            },
        )
    if resp.status_code >= 400:
        raise PaymentError(f"Razorpay order failed: {resp.status_code} {resp.text}")
    return resp.json()


def razorpay_verify_checkout(order_id: str, payment_id: str, signature: str) -> bool:
    """Client-side handler signature: HMAC_SHA256(order_id|payment_id, key_secret)."""
    if not config.RAZORPAY_KEY_SECRET:
        return False
    expected = hmac.new(
        config.RAZORPAY_KEY_SECRET.encode(),
        f"{order_id}|{payment_id}".encode(),
        hashlib.sha256,
    ).hexdigest()
    return _eq(expected, signature)


def razorpay_verify_webhook(raw_body: bytes, signature: str) -> bool:
    """HMAC_SHA256 of the raw request body keyed with the webhook secret."""
    if not config.RAZORPAY_WEBHOOK_SECRET:
        return False
    expected = hmac.new(
        config.RAZORPAY_WEBHOOK_SECRET.encode(), raw_body, hashlib.sha256
    ).hexdigest()
    return _eq(expected, signature or "")


# ----------------------------------------------------------------------------- stripe


async def stripe_create_checkout_session(
    amount_minor: int, currency: str, product_name: str, client_reference_id: str, email: str
) -> dict:
    if not config.STRIPE_SECRET_KEY:
        raise PaymentError("Stripe key is not configured")
    form = {
        "mode": "payment",
        "success_url": f"{config.PUBLIC_SITE_URL}/?paid=1",
        "cancel_url": f"{config.PUBLIC_SITE_URL}/?canceled=1",
        "client_reference_id": client_reference_id,
        "customer_email": email,
        "line_items[0][quantity]": "1",
        "line_items[0][price_data][currency]": currency.lower(),
        "line_items[0][price_data][unit_amount]": str(amount_minor),
        "line_items[0][price_data][product_data][name]": product_name,
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://api.stripe.com/v1/checkout/sessions",
            auth=(config.STRIPE_SECRET_KEY, ""),
            data=form,
        )
    if resp.status_code >= 400:
        raise PaymentError(f"Stripe session failed: {resp.status_code} {resp.text}")
    return resp.json()


def stripe_verify_webhook(raw_body: bytes, header: str, tolerance: int = 300) -> dict | None:
    """Verify `Stripe-Signature: t=<ts>,v1=<sig>` over `<ts>.<raw body>`."""
    if not config.STRIPE_WEBHOOK_SECRET or not header:
        return None
    parts = dict(
        piece.split("=", 1) for piece in header.split(",") if "=" in piece
    )
    timestamp = parts.get("t")
    signature = parts.get("v1")
    if not timestamp or not signature:
        return None
    if abs(time.time() - int(timestamp)) > tolerance:
        return None
    expected = hmac.new(
        config.STRIPE_WEBHOOK_SECRET.encode(),
        f"{timestamp}.".encode() + raw_body,
        hashlib.sha256,
    ).hexdigest()
    if not _eq(expected, signature):
        return None
    return json.loads(raw_body)
