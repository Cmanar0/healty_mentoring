from datetime import timedelta

from django.utils import timezone

from billing.services.session_finance_service import cancel_session_with_refund
from testing.financial.base import cleanup_scenario_data, create_paid_confirmed_session, ensure_test_users


def run():
    print("Running: scenario_cancel_before_window")
    cleanup_scenario_data("scenario_cancel_before_window")
    _, client = ensure_test_users()
    session = create_paid_confirmed_session(
        scenario_name="scenario_cancel_before_window",
        hours_from_now=48,
        amount_cents=12000,
    )
    before = client.user_profile.wallet_balance_cents
    cancel_session_with_refund(session, now=timezone.now())
    session.refresh_from_db()
    client.user_profile.refresh_from_db()
    if session.status != "cancelled":
        raise Exception(f"Expected cancelled, got {session.status}")
    if client.user_profile.wallet_balance_cents <= before:
        raise Exception("Expected client wallet to be credited on cancellation refund.")
    print("✓ Passed")
