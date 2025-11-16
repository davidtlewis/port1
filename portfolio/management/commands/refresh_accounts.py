import logging
from django.core.management.base import BaseCommand
from portfolio.models import Account

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Refresh account values by summing all holdings'
    
    def handle(self, *args, **options):
        accounts = Account.objects.all()
        total_number = len(accounts)
        
        if total_number == 0:
            self.stdout.write(self.style.WARNING("No accounts found"))
            return
        
        counter = 0
        failed_accounts = []
        
        for account in accounts:
            counter += 1
            try:
                message = f'[{counter}/{total_number}]: Refreshing {account.name}'
                self.stdout.write(self.style.SUCCESS(message))
                account.refresh_value()
                message = f'         Value: £{account.account_value:,.2f}'
                self.stdout.write(self.style.SUCCESS(message))
            except Exception as e:
                message = f'[{counter}/{total_number}]: FAILED - {account.name}: {e}'
                self.stdout.write(self.style.ERROR(message))
                failed_accounts.append((account.name, str(e)))
                logger.error(f"Error refreshing account {account.name}: {e}", exc_info=True)
        
        # Summary
        self.stdout.write("\n" + "="*70)
        successful_count = total_number - len(failed_accounts)
        self.stdout.write(self.style.SUCCESS(f"✓ Successfully updated: {successful_count}/{total_number}"))
        
        if failed_accounts:
            self.stdout.write(self.style.ERROR(f"✗ Failed: {len(failed_accounts)}/{total_number}"))
            for name, error in failed_accounts:
                self.stdout.write(f"  - {name}: {error}")
        
        self.stdout.write("="*70)
