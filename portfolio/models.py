from django.db import models
from django.db.models import Sum
import requests
from bs4 import BeautifulSoup
import locale
from django.utils import timezone
from django.urls import reverse

class Person(models.Model):
    name = models.CharField(max_length=50)
    def __str__(self):
        return self.name
    
class Account(models.Model):
    name = models.CharField(max_length=50)
    person = models.ForeignKey(Person, on_delete=models.CASCADE, null=True)
    ACCOUNT_TYPE = (
        ('ISA','ISA'),
        ('pension', 'PENSION'),
        ('standard','STANDARD'),
    )
    account_type = models.CharField(max_length=8, choices=ACCOUNT_TYPE, default='buy')
    account_value = models.DecimalField(max_digits=9, decimal_places=2, default = 0)
    
    def __str__(self):
        return self.name

    def get_absolute_url(self):
        """Returns the url to access a particular  instance."""
        return reverse('account_detail', args=[str(self.id)])

    def refresh_value(self):
        holdings = Holding.objects.filter(account=self)
        account_value = holdings.aggregate(Sum('current_value'))['current_value__sum']
        if account_value is None: account_value = 0
        self.account_value = account_value
        self.save()

class Stock(models.Model):
    name = models.CharField(max_length=50)
    code = models.CharField(max_length=20)
    nickname = models.CharField(max_length=40)
    CURRENCY_TYPE = (
        ('gbp','GBP'),
        ('gbx','GBX'),
        ('usd','USD'),
    )
    currency = models.CharField(max_length=6, choices=CURRENCY_TYPE, default='equity')
    STOCK_TYPE = (
        ('fund','FUND'),
        ('equity','EQUITY'),
        ('etfs','ETFS'),
    )
    stock_type = models.CharField(max_length=6, choices=STOCK_TYPE, default='equity')
    current_price = models.DecimalField(max_digits=7, decimal_places=2)
    price_updated = models.DateTimeField(null=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.nickname

    def get_absolute_url(self):
        return reverse('stock_detail', args=[str(self.id)])

    def refresh_value(self):
        locale.setlocale(locale.LC_ALL,'en_US.UTF-8')
        baseurl1 = "https://markets.ft.com/data/"
        baseurl2 = {
            "etfs":"etfs/tearsheet/performance?s=",
            "fund":"funds/tearsheet/performance?s=",
            "equity":"equities/tearsheet/summary?s="
        }
        url = baseurl1 + baseurl2[self.stock_type] + self.code
        page = requests.get(url)
        contents = page.content
        soup = BeautifulSoup(contents, 'html.parser')
        scrapped_current_price = soup.find_all("span",class_='mod-ui-data-list__value')[0].string
        current_price = locale.atof(scrapped_current_price)
        if (self.currency == 'gbx'): current_price = current_price / 100
        #p = Price(stock = s, price= current_price)
        #p.save()
        self.current_price = current_price
        self.price_updated = timezone.now()
        self.save()
        #now to refresh  price !
        p = Price(stock = self, price= current_price)
        p.save()
        #now to refresh related holdings !
        related_holdings = Holding.objects.filter(stock=self) 
        for h in related_holdings:
            h.refresh_value()
    
class Transaction(models.Model):
    account = models.ForeignKey(Account, on_delete=models.CASCADE, null=True)
    TRANSACTION_TYPE = (
        ('buy','BUY'),
        ('sell', 'SELL'),
    )
    transaction_type = models.CharField(max_length=4, choices=TRANSACTION_TYPE, default='buy')
    date = models.DateField()
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, null=True)
    volume = models.IntegerField()
    price = models.DecimalField(max_digits=5, decimal_places=2,default=0)
    tcost = models.DecimalField(max_digits=5, decimal_places=2,default=0)

    class Meta:
        ordering = ['-date']
    def __str__(self):
        return (self.transaction_type + " " + str(self.volume) + " " + self.stock.code)
    def get_absolute_url(self):
        return reverse('transaction_detail', args=[str(self.id)])

class Price(models.Model):
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, null=True)
    date =  models.DateTimeField(auto_now_add=True, blank=True)
    price = models.DecimalField(max_digits=7, decimal_places=2)

    class Meta:
        ordering = ['-date','stock']

    def __str__(self):
        return (self.stock.name + " at " + str(self.date) )

class Holding(models.Model):
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, null=True)
    account = models.ForeignKey(Account, on_delete=models.CASCADE, null=True)
    volume = models.IntegerField()
    book_cost = models.DecimalField(max_digits = 10, decimal_places=2)
    current_value = models.DecimalField(max_digits = 10, decimal_places=2)
    value_updated = models.DateTimeField(null=True)

    class Meta:
        ordering = ['stock']

    def __str__(self):
        return (self.stock.name + " in " + str(self.account.name) )

    def get_absolute_url(self):
        return reverse('holding_detail', args=[str(self.id)])

    def refresh_value(self):
        #counter =  Transaction.objects.filter(stock__name=self.stock).count()
        transactions = Transaction.objects.filter(stock=self.stock).filter(account=self.account)
        nett_volume_bought = transactions.filter(transaction_type= 'buy').aggregate(Sum('volume'))['volume__sum']
        if nett_volume_bought is None: nett_volume_bought = 0
        
        nett_volume_sold = transactions.filter(transaction_type= 'sell').aggregate(Sum('volume'))['volume__sum']
        if nett_volume_sold is None: nett_volume_sold = 0
         
        self.volume = nett_volume_bought - nett_volume_sold
        self.current_value = Price.objects.filter(stock=self.stock).latest('date').price * self.volume
        self.value_updated = timezone.now()
        self.save()