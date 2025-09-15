import locale
import time
from datetime import datetime, date, timedelta
from django.db import models
from django.db.models import Sum
#import requests
from requests_html import HTMLSession

from bs4 import BeautifulSoup
from django.utils import timezone
from django.urls import reverse

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
        locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
        # locale.setlocale(locale.LC_ALL, 'en_GB.utf8')
        # locale.setlocale(locale.LC_ALL, '')
        # self.current_price = 0
        if self.active==True and self.code != 'none':
            print(f"Refreshing  {self.nickname}.")
            if self.scraper_source == 'ft':
                baseurl1 = "https://markets.ft.com/data/"
                baseurl2 = {
                    "etfs":"etfs/tearsheet/summary?s=",
                    "fund":"funds/tearsheet/performance?s=",
                    "equity":"equities/tearsheet/summary?s=",
                    "curr":"currencies/tearsheet/summary?s="
                }
                url = baseurl1 + baseurl2[self.stock_type] + self.code
                session = HTMLSession() # trying new library to get more reliable scrapes
                print(f"Calling URL: {url}")
                page = session.get(url)
                contents = page.content
                soup = BeautifulSoup(contents, 'html.parser')
                scrapped_element = soup.find_all("span", class_='mod-ui-data-list__value')[0].string
                if scrapped_element is not None:
                        scrapped_current_price = scrapped_element.string
                        current_price = locale.atof(scrapped_current_price)
                else:
                    print(soup)
                    print("!!!WARNING: Scrape fail")
                    scrapped_current_price = ""
                    current_price = self.current_price
                  

            else:
                #the yahoo scraper is not working ; the shows unavailable to this scaper
                # # if self.stock_type == 'etfs' or self.stock_type =='curr':
                url = "https://finance.yahoo.com/quote/" + self.yahoo_code
                session = HTMLSession() # trying new library to get more reliable scrapes
                print(f"Calling URL: {url}")
                page = session.get(url)
                contents = page.content
                soup = BeautifulSoup(contents, 'html.parser')
                #scrapped_element =  soup.find("fin-streamer", attrs={"data-reactid": "29"})
                #scrapped_element =  soup.find("fin-streamer", attrs={"data-symbol": self.yahoo_code, "data-field": 'regularMarketPrice'})
                scrapped_element =  soup.find("span", attrs={"data-testid": "qsp-price"})
                if scrapped_element is not None:
                        scrapped_current_price = scrapped_element.string
                        current_price = locale.atof(scrapped_current_price)
                else:
                    print(soup)
                    print("!!!WARNING: Scrape fail")
                    scrapped_current_price = ""
                    current_price = self.current_price
            print(f"Calling URL: {url}. Returned string value {scrapped_current_price}.")
            if self.currency == 'gbx':
                current_price = current_price / 100
            self.current_price = current_price
            self.price_updated = timezone.now()
            self.save()
        #now to refresh  holdings which contain this stock
        related_holdings = Holding.objects.filter(stock=self)
        for h in related_holdings:
            h.refresh_value()

    def refresh_perf(self):
        locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
        baseurl1 = "https://markets.ft.com/data/"
        baseurl2 = {
            "etfs":"etfs/tearsheet/performance?s=",
            "fund":"funds/tearsheet/performance?s=",
            "equity":"equities/tearsheet/summary?s="
        }
        if self.stock_type != 'equity' and self.stock_type != 'curr':
            url = baseurl1 + baseurl2[self.stock_type] + self.code
            session = HTMLSession() # trying new library to get more reliable scrapes
            page = session.get(url)
            #page = requests.get(url)
            contents = page.content
            soup = BeautifulSoup(contents, 'html.parser')
            scrapped_5y_perf = soup.find("div", class_='mod-ui-table--freeze-pane__scroll-container').find_all("tr")[1].find_all("td")[1].string
            if scrapped_5y_perf != '--': self.perf_5y = locale.atof(scrapped_5y_perf[:-1])
            scrapped_3y_perf = soup.find("div", class_='mod-ui-table--freeze-pane__scroll-container').find_all("tr")[1].find_all("td")[2].string
            if scrapped_3y_perf != '--': self.perf_3y = locale.atof(scrapped_3y_perf[:-1])
            scrapped_1y_perf = soup.find("div", class_='mod-ui-table--freeze-pane__scroll-container').find_all("tr")[1].find_all("td")[3].string
            if scrapped_1y_perf != '--': self.perf_1y = locale.atof(scrapped_1y_perf[:-1])
            scrapped_6m_perf = soup.find("div", class_='mod-ui-table--freeze-pane__scroll-container').find_all("tr")[1].find_all("td")[4].string
            if scrapped_6m_perf != '--': self.perf_6m = locale.atof(scrapped_6m_perf[:-1])
            scrapped_3m_perf = soup.find("div", class_='mod-ui-table--freeze-pane__scroll-container').find_all("tr")[1].find_all("td")[5].string
            if scrapped_3m_perf != '--': self.perf_3m = locale.atof(scrapped_3m_perf[:-1])
            scrapped_1m_perf = soup.find("div", class_='mod-ui-table--freeze-pane__scroll-container').find_all("tr")[1].find_all("td")[6].string
            if scrapped_1m_perf != '--': self.perf_1m = locale.atof(scrapped_1m_perf[:-1])
            self.save()
               
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
        #sum up all relevant tranaction to get current number of shares
        transactions = Transaction.objects.filter(stock=self.stock).filter(account=self.account)
        nett_volume_bought = transactions.filter(transaction_type='buy').aggregate(Sum('volume'))['volume__sum']
        if nett_volume_bought is None:
            nett_volume_bought = 0

        nett_volume_sold = transactions.filter(transaction_type='sell').aggregate(Sum('volume'))['volume__sum']
        if nett_volume_sold is None:
            nett_volume_sold = 0

        self.volume = nett_volume_bought - nett_volume_sold
        #self.current_value = Price.objects.filter(stock=self.stock).latest('date').price * self.volume
        self.current_value = Stock.objects.get(pk=self.stock.id).current_price * self.volume
        self.value_updated = timezone.now()
        self.save()
