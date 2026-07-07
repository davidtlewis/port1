import logging
import time
from django.core.management.base import BaseCommand
from django.core import management
from portfolio.models import DailySnapshot, Stock
from datetime import date

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Create or update the end-of-day portfolio snapshot'

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            help='Snapshot date in YYYY-MM-DD format (defaults to today)',
        )
        parser.add_argument(
            '--skip-refresh',
            action='store_true',
            help='Skip refreshing prices and accounts before snapshot',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Enable verbose logging',
        )

        mode = parser.add_mutually_exclusive_group()
        mode.add_argument(
            '--fx-only',
            action='store_true',
            help='Only refresh FX/currency stocks. Intended to run just before market close '
                 '(e.g. 16:30) so the real-time FX rate lines up with the close, rather than '
                 'drifting for the 15 minutes until the main refresh.',
        )
        mode.add_argument(
            '--late-only',
            action='store_true',
            help="Only refresh stocks flagged as late-pricing, then update today's snapshot "
                 "in place. Intended to run after the main 16:45 snapshot, once those funds "
                 "have actually published their NAV for the day.",
        )

        parser.add_argument(
            '--attempts',
            type=int,
            default=3,
            help='(--late-only) number of times to check for an updated price before giving up',
        )
        parser.add_argument(
            '--wait-minutes',
            type=int,
            default=15,
            help='(--late-only) minutes to wait between price checks',
        )

    def handle(self, *args, **options):
        if options['verbose']:
            logging.getLogger('portfolio').setLevel(logging.DEBUG)

        if options['date']:
            try:
                snapshot_date = date.fromisoformat(options['date'])
            except ValueError:
                self.stdout.write(self.style.ERROR(f"Invalid date format: {options['date']}. Use YYYY-MM-DD"))
                return
        else:
            snapshot_date = date.today()

        if options['fx_only']:
            self.handle_fx_only()
        elif options['late_only']:
            self.handle_late_only(snapshot_date, options['attempts'], options['wait_minutes'])
        else:
            self.handle_full(snapshot_date, options['skip_refresh'])

    def handle_fx_only(self):
        self.stdout.write(self.style.SUCCESS("=== Refreshing FX rates ==="))
        try:
            management.call_command('get_prices', stock_type='curr')
            self.stdout.write(self.style.SUCCESS("✓ FX rates refreshed"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ Failed to refresh FX rates: {e}"))
            logger.error(f"Failed to refresh FX rates: {e}", exc_info=True)

    def handle_late_only(self, snapshot_date, attempts, wait_minutes):
        self.stdout.write(self.style.SUCCESS(f"=== Late-pricing fund check for {snapshot_date} ==="))

        late_stocks = list(Stock.objects.filter(active=True, late_pricing=True))
        if not late_stocks:
            self.stdout.write(self.style.WARNING("No stocks flagged as late-pricing - nothing to do"))
            return

        before_prices = {stock.pk: stock.current_price for stock in late_stocks}
        changed = False

        for attempt in range(1, attempts + 1):
            self.stdout.write(f"[{attempt}/{attempts}] Checking late-pricing funds...")
            management.call_command('get_prices', late_only=True)

            changed = any(
                Stock.objects.get(pk=pk).current_price != before
                for pk, before in before_prices.items()
            )
            if changed:
                self.stdout.write(self.style.SUCCESS("✓ Price change detected"))
                break

            if attempt < attempts:
                self.stdout.write(self.style.WARNING(
                    f"No change yet - waiting {wait_minutes} minutes before retrying"
                ))
                time.sleep(wait_minutes * 60)

        if not changed:
            self.stdout.write(self.style.WARNING(
                f"Prices unchanged after {attempts} attempts - proceeding with latest available values anyway"
            ))

        self.stdout.write(self.style.SUCCESS("Refreshing holdings and accounts..."))
        management.call_command('refresh_holdings')
        management.call_command('refresh_accounts')

        snapshot = DailySnapshot.update_snapshot(snapshot_date)
        self.stdout.write(self.style.SUCCESS("✓ Snapshot updated"))
        self.print_snapshot(snapshot)

    def handle_full(self, snapshot_date, skip_refresh):
        self.stdout.write(self.style.SUCCESS(f"=== End of Day Snapshot for {snapshot_date} ==="))

        # Step 1: Refresh prices (unless skipped)
        if not skip_refresh:
            self.stdout.write(self.style.SUCCESS("\n[1/3] Refreshing stock prices..."))
            try:
                # Currency stocks are refreshed separately (--fx-only, near market close) and
                # late-pricing funds aren't published yet - both are left alone here and
                # picked up by their own passes.
                management.call_command('get_prices', exclude_type='curr', exclude_late=True)
                self.stdout.write(self.style.SUCCESS("✓ Prices refreshed"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"✗ Failed to refresh prices: {e}"))
                self.stdout.write(self.style.WARNING("Continuing with existing prices..."))

            # Step 2: Refresh holdings
            self.stdout.write(self.style.SUCCESS("\n[2/3] Refreshing holdings..."))
            try:
                management.call_command('refresh_holdings')
                self.stdout.write(self.style.SUCCESS("✓ Holdings refreshed"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"✗ Failed to refresh holdings: {e}"))
                self.stdout.write(self.style.WARNING("Continuing with existing holdings..."))

            # Step 3: Refresh account values
            self.stdout.write(self.style.SUCCESS("\n[3/3] Refreshing account values..."))
            try:
                management.call_command('refresh_accounts')
                self.stdout.write(self.style.SUCCESS("✓ Account values refreshed"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"✗ Failed to refresh accounts: {e}"))
                return
        else:
            self.stdout.write(self.style.WARNING("Skipping refresh (--skip-refresh flag set)"))

        # Step 4: Create snapshot
        self.stdout.write(self.style.SUCCESS("\n[4/4] Creating daily snapshot..."))
        try:
            snapshot = DailySnapshot.create_snapshot(snapshot_date)

            if snapshot:
                self.stdout.write(self.style.SUCCESS("✓ Snapshot created successfully!"))
                self.print_snapshot(snapshot)
            else:
                self.stdout.write(self.style.WARNING(f"Snapshot for {snapshot_date} already exists"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ Failed to create snapshot: {e}"))
            logger.error(f"Failed to create snapshot: {e}", exc_info=True)
            return

        self.stdout.write(self.style.SUCCESS("\n✓ End of day process complete!"))

    def print_snapshot(self, snapshot):
        self.stdout.write("\n" + "=" * 70)
        self.stdout.write(f"Date: {snapshot.date}")
        self.stdout.write(f"Total Portfolio (GBP): £{snapshot.total_value_gbp:,.2f}")
        self.stdout.write(f"Total Portfolio (USD): ${snapshot.total_value_usd:,.2f}")
        self.stdout.write(f"Total Portfolio (Idx): {snapshot.total_value_currency_index:,.2f}")
        self.stdout.write(f"\nH&D Portfolio (GBP): £{snapshot.hd_value_gbp:,.2f}")
        self.stdout.write(f"H&D Portfolio (USD): ${snapshot.hd_value_usd:,.2f}")
        self.stdout.write(f"H&D Portfolio (Idx): {snapshot.hd_value_currency_index:,.2f}")
        self.stdout.write("\nExchange Rates:")
        self.stdout.write(f"  GBP/USD: {snapshot.gbp_usd_rate}")
        self.stdout.write(f"  Currency Index: {snapshot.currency_index_rate}")
        self.stdout.write("=" * 70)
