from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from accounts.models import CustomUser, MentorProfile, UserProfile
from billing.models import MentorWalletTransaction, Payment, WalletTransaction
from billing.services.payment_service import calculate_commission_cents
from general.models import Session, SessionInvitation

SCENARIO_TAG_PREFIX = "[financial_scenario]"


def ensure_test_users():
    mentor_email = "test_mentor@local.test"
    client_email = "test_client@local.test"

    mentor_user, _ = CustomUser.objects.get_or_create(
        email=mentor_email,
        defaults={"is_email_verified": True, "is_active": True},
    )
    mentor_user.is_email_verified = True
    mentor_user.is_active = True
    mentor_user.save(update_fields=["is_email_verified", "is_active"])

    client_user, _ = CustomUser.objects.get_or_create(
        email=client_email,
        defaults={"is_email_verified": True, "is_active": True},
    )
    client_user.is_email_verified = True
    client_user.is_active = True
    client_user.save(update_fields=["is_email_verified", "is_active"])

    mentor_profile, _ = MentorProfile.objects.get_or_create(
        user=mentor_user,
        defaults={
            "first_name": "Test",
            "last_name": "Mentor",
            "price_per_hour": Decimal("100.00"),
            "wallet_balance_cents": 0,
        },
    )
    mentor_profile.wallet_balance_cents = 0
    if mentor_profile.price_per_hour is None:
        mentor_profile.price_per_hour = Decimal("100.00")
    mentor_profile.save(update_fields=["wallet_balance_cents", "price_per_hour"])

    client_profile, _ = UserProfile.objects.get_or_create(
        user=client_user,
        defaults={
            "first_name": "Test",
            "last_name": "Client",
            "wallet_balance_cents": 0,
        },
    )
    client_profile.wallet_balance_cents = 0
    client_profile.save(update_fields=["wallet_balance_cents"])

    return mentor_user, client_user


def assert_scenarios_enabled():
    if not settings.ALLOW_TEST_SCENARIOS:
        raise Exception("Test scenarios disabled in this environment.")


def simulate_successful_stripe_payment(amount_cents, mentor, client):
    if not settings.STRIPE_SECRET_KEY:
        raise Exception("Missing STRIPE_SECRET_KEY. Stripe test mode must be enabled.")

    import stripe

    stripe.api_key = settings.STRIPE_SECRET_KEY
    intent = stripe.PaymentIntent.create(
        amount=int(amount_cents),
        currency="usd",
        confirm=True,
        payment_method="pm_card_visa",
        payment_method_types=["card"],
        metadata={
            "source": "financial_scenario_runner",
            "mentor_id": str(mentor.id),
            "client_id": str(client.id),
        },
    )
    if intent.status != "succeeded":
        raise Exception(f"Stripe intent not succeeded: {intent.status}")
    return intent.id


@transaction.atomic()
def cleanup_scenario_data(scenario_name):
    marker = f"{SCENARIO_TAG_PREFIX}:{scenario_name}"
    scenario_sessions = Session.objects.filter(note__icontains=marker)
    session_ids = list(scenario_sessions.values_list("id", flat=True))

    if session_ids:
        WalletTransaction.objects.filter(related_session_id__in=session_ids).delete()
        MentorWalletTransaction.objects.filter(related_session_id__in=session_ids).delete()
        SessionInvitation.objects.filter(session_id__in=session_ids).delete()
        Payment.objects.filter(session_id__in=session_ids).delete()
        scenario_sessions.delete()


@transaction.atomic()
def create_paid_confirmed_session(
    *,
    scenario_name,
    amount_cents=10000,
    hours_from_now=48,
    duration_minutes=60,
):
    mentor_user, client_user = ensure_test_users()
    mentor_profile = mentor_user.mentor_profile
    client_profile = client_user.user_profile

    start = timezone.now() + timedelta(hours=hours_from_now)
    end = start + timedelta(minutes=duration_minutes)
    marker = f"{SCENARIO_TAG_PREFIX}:{scenario_name}"

    session = Session.objects.create(
        created_by=mentor_user,
        start_datetime=start,
        end_datetime=end,
        status="draft",
        session_price=Decimal(amount_cents) / Decimal(100),
        note=marker,
    )
    session.attendees.add(client_user)
    mentor_profile.sessions.add(session)
    client_profile.sessions.add(session)

    session.status = "invited"
    session.save(update_fields=["status"])
    SessionInvitation.objects.get_or_create(
        session=session,
        mentor=mentor_profile,
        invited_email=client_user.email,
        defaults={"invited_user": client_user, "expires_at": end},
    )

    stripe_pi_id = simulate_successful_stripe_payment(amount_cents, mentor_user, client_user)
    payment = Payment.objects.create(
        stripe_payment_intent_id=stripe_pi_id,
        mentor=mentor_profile,
        client=client_profile,
        session=session,
        amount_cents=amount_cents,
        currency="usd",
        platform_commission_cents=calculate_commission_cents(amount_cents),
        status="succeeded",
    )

    session.payment = payment
    session.payment_method = "stripe"
    session.paid_at = timezone.now()
    session.status = "confirmed"
    session.save(update_fields=["payment", "payment_method", "paid_at", "status"])
    return session
