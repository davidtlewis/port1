import logging
from django.core.management.base import BaseCommand
from portfolio.models import Holding

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Refresh holding values based on current stock prices'
    
    def handle(self, *args, **options):
        holdings = Holding.objects.all()
        total_number = len(holdings)
        
        if total_number == 0:
            self.stdout.write(self.style.WARNING("No holdings found"))
            return
        
        counter = 0
        failed_holdings = []
        
        for holding in holdings:
            counter += 1
            try:
                message = f'[{counter}/{total_number}]: {holding.stock.name} / {holding.account.name}'
                self.stdout.write(self.style.SUCCESS(message))
                holding.refresh_value()
                message = f'         Volume: {holding.volume}, Value: £{holding.current_value:,.2f}'
                self.stdout.write(self.style.SUCCESS(message))
            except Exception as e:
                message = f'[{counter}/{total_number}]: FAILED - {holding.stock.name} / {holding.account.name}: {e}'
                self.stdout.write(self.style.ERROR(message))
                failed_holdings.append((f"{holding.stock.name} / {holding.account.name}", str(e)))
                logger.error(f"Error refreshing holding {holding.id}: {e}", exc_info=True)
        
        # Summary
        self.stdout.write("\n" + "="*70)
        successful_count = total_number - len(failed_holdings)
        self.stdout.write(self.style.SUCCESS(f"✓ Successfully updated: {successful_count}/{total_number}"))
        
        if failed_holdings:
            self.stdout.write(self.style.ERROR(f"✗ Failed: {len(failed_holdings)}/{total_number}"))
            for name, error in failed_holdings:
                self.stdout.write(f"  - {name}: {error}")
        
        self.stdout.write("="*70)

            