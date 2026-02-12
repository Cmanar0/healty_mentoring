from django.core.management.base import BaseCommand, CommandError

from testing.financial.runner import AVAILABLE_SCENARIOS, run_all, run_scenario


class Command(BaseCommand):
    help = "Run financial lifecycle scenarios (guarded by ALLOW_TEST_SCENARIOS)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--scenario",
            type=str,
            help=f"Run only one scenario. Available: {', '.join(AVAILABLE_SCENARIOS.keys())}",
        )

    def handle(self, *args, **options):
        scenario = options.get("scenario")
        self.stdout.write(self.style.WARNING("=== Financial Scenario Runner ==="))
        try:
            if scenario:
                self.stdout.write(f"Running one scenario: {scenario}")
                run_scenario(scenario)
            else:
                self.stdout.write("Running all scenarios...")
                run_all()
        except Exception as exc:
            raise CommandError(f"Scenario run failed: {exc}")
        self.stdout.write(self.style.SUCCESS("All requested scenarios passed."))
