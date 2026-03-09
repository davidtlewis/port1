import logging
from django.core.management.base import BaseCommand
from django.core import management
from portfolio.models import DailySnapshot
from datetime import date

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Create end-of-day portfolio snapshot at market close (5pm)'
    
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
    
    def handle(self, *args, **options):
        if options['verbose']:
            logging.getLogger('portfolio').setLevel(logging.DEBUG)
        
        # Parse snapshot date
        if options['date']:
            try:
                snapshot_date = date.fromisoformat(options['date'])
            except ValueError:
                self.stdout.write(self.style.ERROR(f"Invalid date format: {options['date']}. Use YYYY-MM-DD"))
                return
        else:
            snapshot_date = date.today()
        
        self.stdout.write(self.style.SUCCESS(f"=== End of Day Snapshot for {snapshot_date} ==="))
        
        # Step 1: Refresh prices (unless skipped)
        if not options['skip_refresh']:
            self.stdout.write(self.style.SUCCESS("\n[1/3] Refreshing stock prices..."))
            try:
                management.call_command('get_prices')
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
                self.stdout.write("\n" + "="*70)
                self.stdout.write(f"Date: {snapshot.date}")
                self.stdout.write(f"Total Portfolio (GBP): £{snapshot.total_value_gbp:,.2f}")
                self.stdout.write(f"Total Portfolio (USD): ${snapshot.total_value_usd:,.2f}")
                self.stdout.write(f"Total Portfolio (Idx): {snapshot.total_value_currency_index:,.2f}")
                self.stdout.write(f"\nH&D Portfolio (GBP): £{snapshot.hd_value_gbp:,.2f}")
                self.stdout.write(f"H&D Portfolio (USD): ${snapshot.hd_value_usd:,.2f}")
                self.stdout.write(f"H&D Portfolio (Idx): {snapshot.hd_value_currency_index:,.2f}")
                self.stdout.write(f"\nExchange Rates:")
                self.stdout.write(f"  GBP/USD: {snapshot.gbp_usd_rate}")
                self.stdout.write(f"  Currency Index: {snapshot.currency_index_rate}")
                self.stdout.write("="*70)
            else:
                self.stdout.write(self.style.WARNING(f"Snapshot for {snapshot_date} already exists"))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ Failed to create snapshot: {e}"))
            logger.error(f"Failed to create snapshot: {e}", exc_info=True)
            return
        
        self.stdout.write(self.style.SUCCESS("\n✓ End of day process complete!"))

