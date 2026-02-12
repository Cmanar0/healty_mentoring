from datetime import timedelta

from django.utils import timezone

from billing.services.session_finance_service import CancellationError, cancel_session_with_refund
from testing.financial.base import cleanup_scenario_data, create_paid_confirmed_session


def run():
    print("Running: scenario_cancel_after_window")
    cleanup_scenario_data("scenario_cancel_after_window")
    session = create_paid_confirmed_session(
        scenario_name="scenario_cancel_after_window",
        hours_from_now=12,
        amount_cents=10000,
    )
    try:
        cancel_session_with_refund(session, now=timezone.now())
    except CancellationError:
        print("✓ Passed")
        return
    raise Exception("Expected CancellationError for cancellation after window.")
