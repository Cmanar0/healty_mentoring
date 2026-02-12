from datetime import timedelta

from django.utils import timezone

from billing import config
from billing.services.session_finance_service import mark_session_payout_available
from testing.financial.base import cleanup_scenario_data, create_paid_confirmed_session, ensure_test_users


def run():
    print("Running: scenario_double_payout_guard")
    cleanup_scenario_data("scenario_double_payout_guard")
    mentor, _ = ensure_test_users()
    session = create_paid_confirmed_session(
        scenario_name="scenario_double_payout_guard",
        hours_from_now=-(24 * (config.SESSION_REFUND_WINDOW_DAYS + 2)),
        amount_cents=15000,
    )
    session.status = "completed"
    session.end_datetime = timezone.now() - timedelta(days=config.SESSION_REFUND_WINDOW_DAYS + 1)
    session.save(update_fields=["status", "end_datetime"])
    before = mentor.mentor_profile.wallet_balance_cents
    mark_session_payout_available(session, now=timezone.now())
    mentor.mentor_profile.refresh_from_db()
    once = mentor.mentor_profile.wallet_balance_cents
    mark_session_payout_available(session, now=timezone.now())
    mentor.mentor_profile.refresh_from_db()
    twice = mentor.mentor_profile.wallet_balance_cents
    if not (once > before):
        raise Exception("Expected first payout transition to credit mentor wallet.")
    if twice != once:
        raise Exception("Expected second payout transition to not credit again.")
    print("✓ Passed")
