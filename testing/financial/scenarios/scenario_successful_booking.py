from testing.financial.base import cleanup_scenario_data, create_paid_confirmed_session, ensure_test_users


def run():
    print("Running: scenario_successful_booking")
    cleanup_scenario_data("scenario_successful_booking")
    session = create_paid_confirmed_session(scenario_name="scenario_successful_booking")
    _, client = ensure_test_users()
    client_profile = client.user_profile
    client_profile.refresh_from_db()
    if session.status != "confirmed":
        raise Exception(f"Expected confirmed, got {session.status}")
    if not session.payment_id:
        raise Exception("Expected payment to exist.")
    if client_profile.wallet_balance_cents != 0:
        raise Exception("Client wallet should remain unchanged for card payment.")
    print("✓ Passed")
