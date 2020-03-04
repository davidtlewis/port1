import django_tables2 as tables
from .models import Stock, Price, Holding, Transaction, Account
from django_tables2 import A


class StockTable(tables.Table):
    class Meta:
        model = Stock
        template_name = "django_tables2/bootstrap.html"
        fields = ('nickname','code','name', 'stock_type', 'current_price','price_updated')
    nickname = tables.LinkColumn("stock_detail", args=[A("pk")])

class PriceTable(tables.Table):
    class Meta:
        model = Price
        template_name = "django_tables2/bootstrap.html"
        #fields = ('price' ,)
        fields = ('stock','date', 'price')
       
class HoldingTable(tables.Table):
    class Meta:
        model = Holding
        template_name = "django_tables2/bootstrap.html"
        fields = ('account','stock', 'volume', 'book_cost','current_value')
    account = tables.LinkColumn("holding_detail", args=[A("pk")])

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
        fields = ('name','person','account_type','account_value')
    name = tables.LinkColumn("account_detail", args=[A("pk")])