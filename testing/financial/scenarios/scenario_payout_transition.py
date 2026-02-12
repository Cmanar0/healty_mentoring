from datetime import timedelta

from django.utils import timezone

from billing import config
from billing.services.session_finance_service import mark_session_payout_available
from testing.financial.base import cleanup_scenario_data, create_paid_confirmed_session, ensure_test_users


def run():
    print("Running: scenario_payout_transition")
    cleanup_scenario_data("scenario_payout_transition")
    mentor, _ = ensure_test_users()
    session = create_paid_confirmed_session(
        scenario_name="scenario_payout_transition",
        hours_from_now=-(24 * (config.SESSION_REFUND_WINDOW_DAYS + 2)),
        amount_cents=14000,
    )
    session.status = "completed"
    session.end_datetime = timezone.now() - timedelta(days=config.SESSION_REFUND_WINDOW_DAYS + 1)
    session.save(update_fields=["status", "end_datetime"])
    before = mentor.mentor_profile.wallet_balance_cents
    mark_session_payout_available(session, now=timezone.now())
    session.refresh_from_db()
    mentor.mentor_profile.refresh_from_db()
    if session.status != "payout_available":
        raise Exception(f"Expected payout_available, got {session.status}")
    if mentor.mentor_profile.wallet_balance_cents <= before:
        raise Exception("Expected mentor wallet to be credited for payout_available transition.")
    print("✓ Passed")
