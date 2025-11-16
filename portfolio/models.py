import logging
import locale
import time
from datetime import datetime, date, timedelta
from decimal import Decimal
from django.db import models
from django.db.models import Sum, Q
from django.utils import timezone
from django.urls import reverse
from requests_html import HTMLSession
from bs4 import BeautifulSoup
from .scraper import PriceScraper, PerformanceScraper, ScraperException

logger = logging.getLogger(__name__)

class Account(models.Model):
    """ this holds the accounts"""
    name = models.CharField(max_length=50)
    ACCOUNT_TYPE = (
        ('ISA', 'ISA'),
        ('pension', 'PENSION'),
        ('standard', 'STANDARD'),
        ('VCT', 'VCT'),
        ('cash','CASH')
    )
    account_type = models.CharField(max_length=8, choices=ACCOUNT_TYPE, default='buy')
    account_value = models.DecimalField(max_digits=9, decimal_places=2, default=0)
    person = models.ForeignKey('Person', on_delete=models.CASCADE, null=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        """Returns the url to access a particular  instance."""
        return reverse('account_detail', args=[str(self.id)])

    def refresh_value(self):
        holdings = Holding.objects.filter(account=self)
        account_value = holdings.aggregate(Sum('current_value'))['current_value__sum']
        if account_value is None:
            account_value = 0
        self.account_value = account_value
        self.save()

class Person(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        """Returns the url to access a particular  instance."""
        return reverse('account_detail', args=[str(self.id)])

class Stock(models.Model):
    name = models.CharField(max_length=50)
    code = models.CharField(max_length=20)
    yahoo_code = models.CharField(max_length=20, null=True)
    nickname = models.CharField(max_length=40)
    CURRENCY_TYPE = (
        ('gbp', 'GBP'),
        ('gbx', 'GBX'),
        ('usd', 'USD'),
    )
    currency = models.CharField(max_length=6, choices=CURRENCY_TYPE, default='equity')
    STOCK_TYPE = (
        ('fund', 'FUND'),
        ('equity', 'EQUITY'),
        ('etfs', 'ETFS'),
        ('curr','CURR'),
    )
    stock_type = models.CharField(max_length=6, choices=STOCK_TYPE, default='equity')
    STOCK_REGION = (
        ('world', 'WORLD'),
        ('us', 'US'),
        ('uk', 'UK'),
        ('europe', 'EUROPE'),
    )
    stock_region = models.CharField(max_length=6, choices=STOCK_REGION, default='world')
    SCRAPER_SOURCE = (
        ('ft', 'ft'),
        ('yahoo', 'yahoo'),
    )
    scraper_source = models.CharField(max_length=5, choices=SCRAPER_SOURCE, default='ft')
    
    active = models.BooleanField(default=True)
    current_price = models.DecimalField(max_digits=8, decimal_places=4)
    price_updated = models.DateTimeField(null=True)
    perf_5y = models.DecimalField(max_digits=7, decimal_places=2, null=True)
    perf_3y = models.DecimalField(max_digits=7, decimal_places=2, null=True)
    perf_1y = models.DecimalField(max_digits=7, decimal_places=2, null=True)
    perf_6m = models.DecimalField(max_digits=7, decimal_places=2, null=True)
    perf_3m = models.DecimalField(max_digits=7, decimal_places=2, null=True)
    perf_1m = models.DecimalField(max_digits=7, decimal_places=2, null=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.nickname

    def get_absolute_url(self):
        return reverse('stock_detail', args=[str(self.id)])

    def refresh_value(self):
        """
        Refresh the current price of the stock from external source.
        Updates current_price and price_updated timestamp.
        Falls back to previous price if scraping fails.
        Also refreshes related holding values.
        """
        if not self.active or self.code == 'none':
            logger.debug(f"Skipping refresh for {self.nickname} - not active or code is 'none'")
            return
        
        logger.info(f"Refreshing price for {self.nickname}")
        
        try:
            locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
        except locale.Error:
            logger.warning("Failed to set locale, using default")
        
        current_price = None
        
        try:
            scraper = PriceScraper()
            
            if self.scraper_source == 'ft':
                current_price = scraper.scrape_ft_price(self.code, self.stock_type)
            elif self.scraper_source == 'yahoo':
                if not self.yahoo_code:
                    logger.warning(f"No Yahoo code set for {self.nickname}")
                    return
                current_price = scraper.scrape_yahoo_price(self.yahoo_code)
            else:
                logger.error(f"Unknown scraper source: {self.scraper_source}")
                return
            
            if current_price is None:
                logger.warning(f"Scraper returned None for {self.nickname}")
                return
            
            # Handle GBX (pence) to GBP (pounds) conversion
            if self.currency == 'gbx':
                current_price = current_price / Decimal('100')
            
            # Only update if price is valid
            if current_price > 0:
                self.current_price = current_price
                self.price_updated = timezone.now()
                self.save()
                logger.info(f"Updated {self.nickname}: {current_price} (updated at {self.price_updated})")
            else:
                logger.warning(f"Invalid price {current_price} for {self.nickname}")
        
        except ScraperException as e:
            logger.error(f"Failed to refresh price for {self.nickname}: {e}")
            # Keep existing price rather than crashing
        
        except Exception as e:
            logger.error(f"Unexpected error refreshing {self.nickname}: {e}", exc_info=True)
        
        finally:
            # Always refresh holdings that contain this stock
            self._refresh_related_holdings()
    
    def _refresh_related_holdings(self):
        """Refresh values of all holdings that contain this stock"""
        try:
            related_holdings = Holding.objects.filter(stock=self)
            for holding in related_holdings:
                holding.refresh_value()
        except Exception as e:
            logger.error(f"Error refreshing holdings for {self.nickname}: {e}")


    def refresh_perf(self):
        """
        Refresh performance data (5y, 3y, 1y, 6m, 3m, 1m returns) from Financial Times.
        Only available for funds and ETFs, not for equities or currencies.
        """
        if self.stock_type not in ('fund', 'etfs'):
            logger.debug(f"Performance data not available for {self.stock_type}")
            return
        
        logger.info(f"Refreshing performance for {self.nickname}")
        
        try:
            locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
        except locale.Error:
            logger.warning("Failed to set locale, using default")
        
        try:
            scraper = PerformanceScraper()
            perf_data = scraper.scrape_performance(self.code, self.stock_type)
            
            # Update each performance field
            for field_name, value in perf_data.items():
                setattr(self, field_name, value)
            
            self.save()
            logger.info(f"Updated performance for {self.nickname}: {perf_data}")
        
        except ScraperException as e:
            logger.error(f"Failed to refresh performance for {self.nickname}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error refreshing performance for {self.nickname}: {e}", exc_info=True)

               
    def get_historic_prices(self):
        #broken - might need to implement all this cookie stuff to fix access to yahoo - https://maikros.github.io/yahoo-finance-python/
        if not self.yahoo_code:
            return
        if self.yahoo_code == "none":
            return
        if self.active == False:
            return
        batch = 135
        locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
        def converttonumber(textin):
            try:
                return locale.atof(textin)
            except ValueError:
                return 0
        today = date.today()
        #find last date in historicPrices
        last_date_record = HistoricPrice.objects.filter(stock=self).first()
        if last_date_record is None:
            #set default to 1 jan 2017
            last_date = date(2017, 1, 1)
        else:
            last_date = last_date_record.date
        print("Stock:", self.name, " Getting history from ", last_date, "to ", today,)
        from_date = last_date + timedelta(days=1)
        while from_date < today:
            to_date = min((from_date + timedelta(days=batch)), today)
            endunix = int(time.mktime(to_date.timetuple()))
            startunix = int(time.mktime(from_date.timetuple()))
            url = "https://uk.finance.yahoo.com/quote/" + self.yahoo_code + "/history?period1=" + str(startunix) + "&period2=" + str(endunix) + "&interval=1d&filter=history&frequency=1d"
            
            #page = requests.get(url)
            session = HTMLSession()
            page = session.get(url)
            contents = page.content
            soup = BeautifulSoup(contents, 'html.parser')
            rows = soup.table.tbody.find_all("tr")
            print("Stock:", self.name,"from:", from_date, " to :", to_date, ". Records returned: ", len(rows), ". ", url)
            print ("rows", len(rows))
            for table_row in rows:
                columns = table_row.find_all("td")
                print ("Columns: ", len(columns))
                if len(columns) == 7:
                    #save price record
                    hp = HistoricPrice(stock=self, date=datetime.strptime(columns[0].text.upper().replace("SEPT", "SEP"), '%d %b %Y'), open=converttonumber(columns[1].text), high=converttonumber(columns[2].text), low=converttonumber(columns[3].text), close=converttonumber(columns[4].text), adjclose=converttonumber(columns[5].text))
                    hp.save()
                    #maybe use uniqueness of data to stop duplicate being added.
                if len(columns) == 2:
                    #save div record
                    #amount_text = columns[1].strong.text
                    amount_text = columns[1].span.text
                    div = Dividend(stock=self, date=datetime.strptime(columns[0].text.upper().replace("SEPT", "SEP"), '%d %b %Y'), amount=converttonumber(amount_text))
                    div.save()
            #get ready for next loop
            from_date = to_date + + timedelta(days=1)


    def clear_historic_prices(self):
        HistoricPrice.objects.filter(stock=self).delete()
        Dividend.objects.filter(stock=self).delete()

class Dividend(models.Model):
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, null=True)
    date = models.DateField(blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=8)
    class Meta:
        ordering = ['-date',]

class Transaction(models.Model):
    account = models.ForeignKey(Account, on_delete=models.CASCADE, null=True)
    TRANSACTION_TYPE = (
        ('buy', 'BUY'),
        ('sell', 'SELL'),
    )
    transaction_type = models.CharField(max_length=4, choices=TRANSACTION_TYPE, default='buy')
    date = models.DateField()
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, null=True)
    volume = models.IntegerField()
    price = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    tcost = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    class Meta:
        ordering = ['-date']
    def __str__(self):
        return self.transaction_type + " " + str(self.volume) + " " + self.stock.code
    def get_absolute_url(self):
        return reverse('transaction_detail', args=[str(self.id)])

class Price(models.Model):
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, null=True)
    date = models.DateTimeField(auto_now_add=True, blank=True)
    price = models.DecimalField(max_digits=7, decimal_places=2)

    class Meta:
        ordering = ['-date', 'stock']

    def __str__(self):
        return self.stock.name + " at " + str(self.date)

class HistoricPrice(models.Model):
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, null=True)
    date = models.DateField(blank=True)
    open = models.DecimalField(max_digits=7, decimal_places=2)
    high = models.DecimalField(max_digits=7, decimal_places=2)
    low = models.DecimalField(max_digits=7, decimal_places=2)
    close = models.DecimalField(max_digits=7, decimal_places=2)
    adjclose = models.DecimalField(max_digits=7, decimal_places=2)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return self.stock.name + " at " + str(self.date)

class Holding(models.Model):
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, null=True)
    account = models.ForeignKey(Account, on_delete=models.CASCADE, null=True)
    volume = models.IntegerField()
    book_cost = models.DecimalField(max_digits=10, decimal_places=2)
    current_value = models.DecimalField(max_digits=10, decimal_places=2)
    value_updated = models.DateTimeField(null=True)

    class Meta:
        ordering = ['stock']

    def __str__(self):
        return self.stock.name + " in " + str(self.account.name)

    def get_absolute_url(self):
        return reverse('holding_detail', args=[str(self.id)])

    def refresh_value(self):
        """
        Refresh holding value based on:
        1. Current transaction history (bought - sold)
        2. Current stock price
        
        Optimized to use single aggregation query instead of N+1 queries.
        """
        try:
            # Single efficient query to get buy/sell volumes
            transactions = Transaction.objects.filter(
                stock=self.stock,
                account=self.account
            ).aggregate(
                bought=Sum('volume', filter=Q(transaction_type='buy')),
                sold=Sum('volume', filter=Q(transaction_type='sell'))
            )
            
            nett_volume_bought = transactions['bought'] or 0
            nett_volume_sold = transactions['sold'] or 0
            self.volume = nett_volume_bought - nett_volume_sold
            
            # Get fresh stock price from database
            stock = Stock.objects.get(pk=self.stock.id)
            self.current_value = Decimal(str(stock.current_price)) * Decimal(str(self.volume))
            self.value_updated = timezone.now()
            self.save()
            
            logger.debug(f"Updated holding {self.id}: volume={self.volume}, value={self.current_value}")
        
        except Stock.DoesNotExist:
            logger.error(f"Stock {self.stock.id} not found for holding {self.id}")
            raise
        except Exception as e:
            logger.error(f"Error refreshing holding {self.id}: {e}", exc_info=True)
            raise

