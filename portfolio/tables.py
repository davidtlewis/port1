import django_tables2 as tables
from django.urls import reverse
from django.utils.html import format_html
from .models import Stock, Price, Holding, Transaction, Account, HistoricPrice, Dividend
from django_tables2 import A
from django.db.models import Sum

class StockTable(tables.Table):
    class Meta:
        model = Stock
        template_name = "django_tables2/bootstrap.html"
        fields = ('nickname','name', 'stock_type', 'current_price','price_updated','perf_5y','perf_3y','perf_1y','perf_6m','perf_3m','perf_1m')
    nickname = tables.LinkColumn("stock_detail", args=[A("pk")])

class StockHoldingTable(tables.Table):
    nickname = tables.Column(orderable=True)
    sum_value = tables.Column(orderable=True)
    perf_1y = tables.Column(orderable=True)
    perf_3y = tables.Column(orderable=True)
    perf_5y = tables.Column(orderable=True)
    class Meta:
        order_by = '-sum_value'
        template_name = "django_tables2/bootstrap.html"
 
class StockListTable(tables.Table):
    #nickname = tables.Column(orderable=True)
    name = tables.LinkColumn("holdingsfiltered")
    stock_region = tables.Column(orderable=True)
    sum_value = tables.Column(orderable=True)
    perf_1y = tables.Column(orderable=True)
    perf_3y = tables.Column(orderable=True)
    perf_5y = tables.Column(orderable=True)
    class Meta:
        order_by = '-sum_value'
        template_name = "django_tables2/bootstrap.html"
    def render_name(self, record):
        url = reverse('holdingsfiltered')
        return format_html('<a href="{}?stock={}">{}</a>', url, record.id, record.nickname)

class PriceTable(tables.Table):
    class Meta:
        model = Price
        template_name = "django_tables2/bootstrap.html"
        #fields = ('price' ,)
        fields = ('stock','date', 'price')

class HistoricPriceTable(tables.Table):
    class Meta:
        model = HistoricPrice
        template_name = "django_tables2/bootstrap.html"
        fields = ('date', 'stock', 'open', 'high', 'low', 'close', 'adjclose',  )

class DividendTable(tables.Table):
    class Meta:
        model = Dividend
        template_name = "django_tables2/bootstrap.html"
        fields = ('date','stock', 'amount',  )
       
class HoldingTable(tables.Table):
    class Meta:
        model = Holding
        template_name = "django_tables2/bootstrap.html"
        fields = ('account','stock', 'volume', 'book_cost')
    account = tables.LinkColumn("holding_detail", args=[A("pk")])
    current_value = tables.Column(footer=lambda table: sum(x.current_value for x in table.data))
    volume = tables.Column(footer=lambda table: sum(x.volume for x in table.data))

class TransactionTable(tables.Table):
    class Meta:
        model = Transaction
        template_name = "django_tables2/bootstrap.html"
        fields = ('stock','account','transaction_type', 'date', 'volume','price','tcost')
    stock = tables.LinkColumn("transaction_detail", args=[A("pk")])

class AccountTable(tables.Table):
    class Meta:
        model = Account
        template_name = "django_tables2/bootstrap.html"
        fields = ('name', 'person','account_type','account_value')
        order_by = '-person'
    name = tables.LinkColumn("holdingsfiltered")
    def render_name(self, record):
        url = reverse('holdingsfiltered')
        return format_html('<a href="{}?account={}">{}</a>', url, record.id, record.name)