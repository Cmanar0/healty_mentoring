# Financial Scenario Testing

This module provides deterministic financial lifecycle scenario testing.

## Enable testing

Set environment variable:

`ALLOW_TEST_SCENARIOS=True`

## Run all scenarios

```bash
python manage.py run_financial_scenarios
```

## Run one scenario

```bash
python manage.py run_financial_scenarios --scenario payout_transition
```

## Auto-created test users

- `test_mentor@local.test`
- `test_client@local.test`

## Notes

- Stripe test mode must be enabled (`STRIPE_SECRET_KEY` with test key).
- Scenarios abort when `ALLOW_TEST_SCENARIOS` is not enabled.
- Scenarios only operate on records tagged with `[financial_scenario]:<name>`.
