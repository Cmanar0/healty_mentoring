"""
Reusable Stripe service — initializes SDK from settings and exposes a minimal API.

Use this module for all server-side Stripe operations; do not put Stripe logic in views.
Secret key is never exposed; only backend code uses this.
"""
import stripe
from django.conf import settings


def is_configured() -> bool:
    """Return True if Stripe secret key is set and non-empty."""
    key = getattr(settings, "STRIPE_SECRET_KEY", None) or ""
    return bool(key.strip())


def get_client():
    """
    Return the Stripe SDK module (stripe) with API key set.
    Use for Stripe API calls, e.g. stripe_service.get_client().Balance.retrieve()
    """
    if not is_configured():
        raise RuntimeError("Stripe is not configured: STRIPE_SECRET_KEY is missing or empty.")
    stripe.api_key = settings.STRIPE_SECRET_KEY
    return stripe


def check_api_ok() -> bool:
    """
    Perform a minimal Stripe API call to verify the key works.
    Returns True if the request succeeds, False otherwise (e.g. invalid key, network error).
    """
    if not is_configured():
        return False
    try:
        get_client().Balance.retrieve()
        return True
    except Exception:
        return False
