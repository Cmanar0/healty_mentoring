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
    attempt_id: str | None = None,
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
    commission_cents = calculate_commission_cents(amount_cents)
    metadata = {
        "mentor_id": str(mentor_profile.user.id),
        "client_email": (client_email or "")[:500],
        "session_type": "mentoring",
        "is_first_session": "true" if is_first_session else "false",
        "platform_commission_cents": str(commission_cents),
    }
    if client_id is not None:
        metadata["client_id"] = str(client_id)

    # Idempotency key must be unique per "attempt" (one open of payment UI).
    # Using attempt_id from frontend avoids "same key, different parameters" when
    # the same user/slot is tried again after we changed API (e.g. removed payment_method).
    idempotency_key = None
    if (attempt_id or "").strip():
        try:
            safe_email = (client_email or "").lower()
            safe_slot = slot_key or "no-slot"
            safe_attempt = (attempt_id or "").strip()[:64]
            idempotency_key = f"booking:{mentor_profile.user.id}:{safe_slot}:{safe_email}:{safe_attempt}"
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


def create_wallet_topup_payment_intent(
    *,
    amount_cents: int,
    user_profile,
    attempt_id: str | None = None,
    currency: str = "usd",
) -> dict:
    """
    Create a Stripe PaymentIntent for wallet top-up. No mentor; no commission.
    Webhook will create Payment and call add_credit. Metadata: payment_type=wallet_topup.
    """
    if not is_configured():
        raise BillingError("Payment is not configured. Please try again later.")
    if amount_cents <= 0:
        raise BillingError("Invalid amount for wallet top-up.")
    stripe = get_client()
    metadata = {
        "payment_type": "wallet_topup",
        "client_id": str(user_profile.id),
        "platform_commission_cents": "0",
    }
    idempotency_key = None
    if (attempt_id or "").strip():
        idempotency_key = f"wallet_topup:{user_profile.id}:{(attempt_id or '').strip()[:64]}"
    try:
        create_kwargs = dict(
            amount=amount_cents,
            currency=currency,
            confirm=False,
            capture_method="automatic",
            description="Wallet top-up",
            metadata=metadata,
            payment_method_types=["card"],
        )
        if idempotency_key:
            create_kwargs["idempotency_key"] = idempotency_key
        intent = stripe.PaymentIntent.create(**create_kwargs)
    except stripe.error.StripeError as e:
        err = getattr(e, "error", e)
        msg = getattr(err, "user_message", None) or str(e)
        if not msg or "api" in msg.lower():
            msg = "Could not start wallet top-up. Please try again."
        raise BillingError(msg)
    return {
        "payment_intent_id": intent.id,
        "client_secret": intent.client_secret,
        "amount_cents": amount_cents,
    }


def create_session_accept_payment_intent(
    *,
    session,
    user_profile,
    attempt_id: str | None = None,
    currency: str = "usd",
) -> dict:
    """
    Create a Stripe PaymentIntent for paying to accept an invited session.
    Metadata: payment_type=session_accept, session_id, mentor_id, client_id.
    Webhook will create Payment and set Payment.session; accept_invitation then confirms session.
    """
    if not is_configured():
        raise BillingError("Payment is not configured. Please try again later.")
    mentor_user = getattr(session, "created_by", None)
    if not mentor_user or not hasattr(mentor_user, "mentor_profile"):
        raise BillingError("Session has no mentor.")
    mentor_profile = mentor_user.mentor_profile
    amount_cents = int(round(float(session.session_price or 0) * 100))
    if amount_cents <= 0:
        raise BillingError("This session has no price.")
    stripe = get_client()
    commission_cents = calculate_commission_cents(amount_cents)
    metadata = {
        "payment_type": "session_accept",
        "session_id": str(session.id),
        "mentor_id": str(mentor_user.id),
        "client_id": str(user_profile.id),
        "platform_commission_cents": str(commission_cents),
    }
    idempotency_key = None
    if (attempt_id or "").strip():
        idempotency_key = f"session_accept:{session.id}:{user_profile.id}:{(attempt_id or '').strip()[:64]}"
    try:
        create_kwargs = dict(
            amount=amount_cents,
            currency=currency,
            confirm=False,
            capture_method="automatic",
            description=f"Session #{session.id}",
            metadata=metadata,
            payment_method_types=["card"],
        )
        if idempotency_key:
            create_kwargs["idempotency_key"] = idempotency_key
        intent = stripe.PaymentIntent.create(**create_kwargs)
    except stripe.error.StripeError as e:
        err = getattr(e, "error", e)
        msg = getattr(err, "user_message", None) or str(e)
        if not msg or "api" in msg.lower():
            msg = "Could not start payment. Please try again."
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


def get_mentor_earnings_cents(mentor_profile) -> int:
    """
    Mentor earnings = sum of (amount - commission) for sessions that are
    payout_available or paid_out. Never use completed.
    """
    from django.db.models import Sum
    from billing.models import Payment
    payouts = Payment.objects.filter(
        mentor=mentor_profile,
        status="succeeded",
        session__isnull=False,
        session__status__in=["payout_available", "paid_out"],
    )
    total = 0
    for p in payouts.only("amount_cents", "platform_commission_cents"):
        total += int((p.amount_cents or 0) - (p.platform_commission_cents or 0))
    return int(total)
