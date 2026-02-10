"""
Billing configuration — single source of truth for platform fees and product prices.

All monetary amounts are in cents (integer) unless otherwise noted.
Safe to import from views, services, and (read-only) expose to templates when needed.
"""

# Platform commission taken from each paid session (0.15 = 15%)
PLATFORM_COMMISSION_PERCENT = 0.15

# AI credits packages: slug -> price in cents, optional "credits" for display
# Adjust keys to match dashboard_mentor package names (e.g. "small", "medium", "large") if needed
AI_CREDITS_PACKAGES = {
    "small": {"price_cents": 999, "credits": 10},
    "medium": {"price_cents": 2499, "credits": 30},
    "large": {"price_cents": 4999, "credits": 75},
}

# Profile boosting / promotions: slug -> price in cents (placeholder for future)
BOOSTING_PRICES = {
    # "featured_week": 1999,
    # "highlight_month": 4999,
}

# Future subscription tiers: list of dicts (placeholder for mentor/client subscriptions)
SUBSCRIPTION_TIERS = [
    # {"slug": "monthly_basic", "price_cents": 990, "interval": "month", "name": "Monthly Basic"},
    # {"slug": "annual_basic", "price_cents": 9900, "interval": "year", "name": "Annual Basic"},
]
