"""
Session booking payment — create and capture Stripe PaymentIntent.

Used when a client books a paid session. All Stripe logic lives here.
Commission is calculated for future payout; no Connect in Phase 2.
"""
from billing import config
from billing.services.stripe_service import get_client, is_configured


class BillingError(Exception):
    """Raised when payment fails; message is safe to show to user."""

    def __init__(self, message: str, payment_intent_id: str = None):
        self.message = message
        self.payment_intent_id = payment_intent_id
        super().__init__(message)


def session_price_cents(mentor_profile) -> int:
    """
    One session = one price. Mentor defines price per session.
    Uses mentor_profile.price_per_session (no duration multiplication).
    Returns amount in cents.
    """
    price = mentor_profile.price_per_session
    if price is None:
        return 0
    return int(round(float(price) * 100))


def calculate_commission_cents(amount_cents: int) -> int:
    """Platform commission from billing config. Not paid out in Phase 2."""
    return int(round(amount_cents * config.PLATFORM_COMMISSION_PERCENT))


def create_booking_payment_intent(
    *,
    amount_cents: int,
    mentor_profile,
    client_email: str,
    client_id: int = None,
    is_first_session: bool = False,
    session_description: str = None,
    slot_key: str | None = None,
    currency: str = "usd",
) -> dict:
    """
    Create a Stripe PaymentIntent only (do not confirm).

    IMPORTANT:
    - One PaymentIntent represents one booking attempt.
    - Frontend must reuse this same PaymentIntent (client_secret) for retries
      via confirmCardPayment(client_secret, {payment_method: {card: element}}).
    - This function MUST NOT be called again for retries of the same attempt.

    Returns:
        {
            "payment_intent_id": "pi_xxx",
            "client_secret": "pi_xxx_secret_xxx",
            "amount_cents": int,
        }

    Raises:
        BillingError: when Stripe is not configured or create fails.
    """
    if not is_configured():
        raise BillingError("Payment is not configured. Please try again later.")

    if amount_cents <= 0:
        raise BillingError("Invalid amount for payment.")

    stripe = get_client()
    metadata = {
        "mentor_id": str(mentor_profile.user.id),
        "client_email": (client_email or "")[:500],
        "session_type": "mentoring",
        "is_first_session": "true" if is_first_session else "false",
    }
    if client_id is not None:
        metadata["client_id"] = str(client_id)

    idempotency_key = None
    try:
        # Idempotency key: booking:{mentor_id}:{slot_key}:{client_email}
        safe_email = (client_email or "").lower()
        safe_slot = slot_key or "no-slot"
        idempotency_key = f"booking:{mentor_profile.user.id}:{safe_slot}:{safe_email}"
    except Exception:
        idempotency_key = None

    try:
        create_kwargs = dict(
            amount=amount_cents,
            currency=currency,
            # Do NOT attach payment_method here; frontend will supply it
            # via confirmCardPayment using Elements. This allows safe retries
            # with different cards against the same PaymentIntent.
            confirm=False,
            capture_method="automatic",
            description=session_description or "Mentoring session",
            metadata=metadata,
            payment_method_types=["card"],  # Explicitly use card only (no automatic_payment_methods needed)
        )
        if idempotency_key:
            create_kwargs["idempotency_key"] = idempotency_key
        intent = stripe.PaymentIntent.create(**create_kwargs)
    except stripe.error.StripeError as e:
        err = getattr(e, "error", e)
        msg = getattr(err, "user_message", None) or str(e)
        if not msg or "api" in msg.lower():
            msg = "Payment could not be set up. Please try again."
        raise BillingError(msg)

    return {
        "payment_intent_id": intent.id,
        "client_secret": intent.client_secret,
        "amount_cents": amount_cents,
    }


def verify_payment_intent_succeeded(
    payment_intent_id: str,
    expected_amount_cents: int,
    expected_mentor_id: str,
) -> dict:
    """
    Retrieve PaymentIntent and verify it has succeeded (after frontend confirmCardPayment).
    Use before completing booking.

    Returns:
        {"payment_intent_id": str, "amount_cents": int}

    Raises:
        BillingError: if PI not found, not succeeded, or amount/mentor mismatch.
    """
    if not is_configured():
        raise BillingError("Payment is not configured.")
    if not payment_intent_id or not expected_mentor_id:
        raise BillingError("Invalid payment verification.")

    stripe = get_client()
    try:
        intent = stripe.PaymentIntent.retrieve(payment_intent_id)
    except stripe.error.StripeError as e:
        raise BillingError("Payment could not be verified. Please try again.")

    if intent.status != "succeeded":
        raise BillingError(
            "Payment has not been completed. Please complete the payment step and try again."
        )
    if intent.amount != expected_amount_cents:
        raise BillingError("Payment amount does not match. Please try again.")
    mentor_id = (intent.metadata or {}).get("mentor_id")
    if mentor_id != str(expected_mentor_id):
        raise BillingError("Payment does not match this booking. Please try again.")

    return {
        "payment_intent_id": intent.id,
        "amount_cents": intent.amount,
    }
