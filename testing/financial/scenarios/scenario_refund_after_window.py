from datetime import timedelta

from django.utils import timezone

from billing import config
from billing.services.session_finance_service import RefundError, refund_completed_session
from testing.financial.base import cleanup_scenario_data, create_paid_confirmed_session


def run():
    print("Running: scenario_refund_after_window")
    cleanup_scenario_data("scenario_refund_after_window")
    session = create_paid_confirmed_session(
        scenario_name="scenario_refund_after_window",
        hours_from_now=-(24 * (config.SESSION_REFUND_WINDOW_DAYS + 2)),
        amount_cents=10000,
    )
    session.status = "completed"
    session.end_datetime = timezone.now() - timedelta(days=config.SESSION_REFUND_WINDOW_DAYS + 1)
    session.save(update_fields=["status", "end_datetime"])
    try:
        refund_completed_session(session, now=timezone.now())
    except RefundError:
        print("✓ Passed")
        return
    raise Exception("Expected RefundError for refund after refund window.")
