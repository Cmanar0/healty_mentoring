from testing.financial.base import assert_scenarios_enabled
from testing.financial.scenarios import (
    scenario_cancel_after_window,
    scenario_cancel_before_window,
    scenario_double_payout_guard,
    scenario_illegal_refund_after_payout,
    scenario_payout_transition,
    scenario_refund_after_window,
    scenario_refund_within_window,
    scenario_successful_booking,
    scenario_withdraw,
)

AVAILABLE_SCENARIOS = {
    "booking": scenario_successful_booking,
    "cancel_before": scenario_cancel_before_window,
    "cancel_after": scenario_cancel_after_window,
    "refund_within": scenario_refund_within_window,
    "refund_after": scenario_refund_after_window,
    "payout_transition": scenario_payout_transition,
    "double_payout_guard": scenario_double_payout_guard,
    "withdraw": scenario_withdraw,
    "illegal_refund_after_payout": scenario_illegal_refund_after_payout,
}


def run_scenario(name):
    assert_scenarios_enabled()
    if name not in AVAILABLE_SCENARIOS:
        raise Exception(f"Unknown scenario '{name}'. Available: {', '.join(AVAILABLE_SCENARIOS.keys())}")
    AVAILABLE_SCENARIOS[name].run()


def run_all():
    assert_scenarios_enabled()
    for _, scenario in AVAILABLE_SCENARIOS.items():
        scenario.run()
