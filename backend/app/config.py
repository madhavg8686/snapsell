import os

DB_PATH = os.environ.get("SNAPSELL_DB", "/data/snapsell.db")
SECRET_KEY = os.environ.get("SNAPSELL_SECRET", "dev-insecure-secret-change-me")

FREE_CREDITS = int(os.environ.get("SNAPSELL_FREE_CREDITS", "5"))

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET", "")
RAZORPAY_WEBHOOK_SECRET = os.environ.get("RAZORPAY_WEBHOOK_SECRET", "")

STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

PUBLIC_SITE_URL = os.environ.get("SNAPSELL_SITE_URL", "http://localhost:5173")

# Owner dashboard. Empty disables /api/admin/* entirely.
ADMIN_PASSWORD = os.environ.get("SNAPSELL_ADMIN_PASSWORD", "")

# Payment provider: "razorpay", "stripe", or "" (auto-detect from configured keys).
PAYMENT_PROVIDER = os.environ.get("SNAPSELL_PAYMENT_PROVIDER", "")


def active_provider() -> str:
    if PAYMENT_PROVIDER:
        return PAYMENT_PROVIDER
    if RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET:
        return "razorpay"
    if STRIPE_SECRET_KEY:
        return "stripe"
    return "none"
