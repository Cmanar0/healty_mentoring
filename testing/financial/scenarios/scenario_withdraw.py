from datetime import timedelta

from django.utils import timezone

from billing import config
from billing.services.session_finance_service import mark_session_payout_available, withdraw_session_payout
from testing.financial.base import cleanup_scenario_data, create_paid_confirmed_session, ensure_test_users


def run():
    print("Running: scenario_withdraw")
    cleanup_scenario_data("scenario_withdraw")
    mentor, _ = ensure_test_users()
    session = create_paid_confirmed_session(
        scenario_name="scenario_withdraw",
        hours_from_now=-(24 * (config.SESSION_REFUND_WINDOW_DAYS + 2)),
        amount_cents=16000,
    )
    session.status = "completed"
    session.end_datetime = timezone.now() - timedelta(days=config.SESSION_REFUND_WINDOW_DAYS + 1)
    session.save(update_fields=["status", "end_datetime"])
    mark_session_payout_available(session, now=timezone.now())
    mentor.mentor_profile.refresh_from_db()
    before_withdraw = mentor.mentor_profile.wallet_balance_cents
    withdraw_session_payout(session, mentor.mentor_profile, now=timezone.now())
    session.refresh_from_db()
    mentor.mentor_profile.refresh_from_db()
    if session.status != "paid_out":
        raise Exception(f"Expected paid_out, got {session.status}")
    if mentor.mentor_profile.wallet_balance_cents >= before_withdraw:
        raise Exception("Expected mentor wallet deduction after withdrawal.")
    print("✓ Passed")
