from datetime import timedelta

from django.utils import timezone

from billing.services.session_finance_service import refund_completed_session
from testing.financial.base import cleanup_scenario_data, create_paid_confirmed_session, ensure_test_users


def run():
    print("Running: scenario_refund_within_window")
    cleanup_scenario_data("scenario_refund_within_window")
    _, client = ensure_test_users()
    session = create_paid_confirmed_session(
        scenario_name="scenario_refund_within_window",
        hours_from_now=-24,
        amount_cents=13000,
    )
    session.status = "completed"
    session.end_datetime = timezone.now() - timedelta(days=1)
    session.save(update_fields=["status", "end_datetime"])
    before = client.user_profile.wallet_balance_cents
    refund_completed_session(session, now=timezone.now())
    session.refresh_from_db()
    client.user_profile.refresh_from_db()
    if session.status != "refunded":
        raise Exception(f"Expected refunded, got {session.status}")
    if client.user_profile.wallet_balance_cents <= before:
        raise Exception("Expected client wallet credit after refund.")
    print("✓ Passed")
