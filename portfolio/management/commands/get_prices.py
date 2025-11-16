import logging
from django.core.management.base import BaseCommand
from portfolio.models import Stock

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Scrape current prices for all active stocks'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Enable verbose logging',
        )
    
    def handle(self, *args, **options):
        if options['verbose']:
            logging.getLogger('portfolio.scraper').setLevel(logging.DEBUG)
        
        stock_list = Stock.objects.filter(active=True)
        total_number = len(stock_list)
        
        if total_number == 0:
            self.stdout.write(self.style.WARNING("No active stocks found"))
            return
        
        counter = 0
        failed_stocks = []
        successful_count = 0
        
        for stock in stock_list:
            counter += 1
            try:
                message = f'[{counter}/{total_number}]: Scraping {stock.nickname}'
                self.stdout.write(self.style.SUCCESS(message))
                stock.refresh_value()
                successful_count += 1
            except Exception as e:
                message = f'[{counter}/{total_number}]: FAILED - {stock.nickname}: {e}'
                self.stdout.write(self.style.ERROR(message))
                failed_stocks.append((stock.nickname, str(e)))
        
        # Summary
        self.stdout.write("\n" + "="*70)
        self.stdout.write(self.style.SUCCESS(f"✓ Successfully updated: {successful_count}/{total_number}"))
        
        if failed_stocks:
            self.stdout.write(self.style.ERROR(f"✗ Failed: {len(failed_stocks)}/{total_number}"))
            for nickname, error in failed_stocks:
                self.stdout.write(f"  - {nickname}: {error}")
        
        self.stdout.write("="*70)

    
