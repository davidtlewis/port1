import django_filters
from .models import Stock, Transaction, Holding, HistoricPrice, Dividend, Account

class TransactionFilter(django_filters.FilterSet):
    class Meta:
        model = Transaction
        fields = ['account','stock']

class HoldingByAccountFilter(django_filters.FilterSet):
    class Meta:
        model = Holding
        fields = ['account','stock','account__person']

class HoldingByAccountFilter2(django_filters.FilterSet):
    class Meta:
        model = Holding
        fields = ['account']

class HistoricPriceByStockFilter(django_filters.FilterSet):
    class Meta:
        model = HistoricPrice
        fields = ['stock',]

class DividendByStockFilter(django_filters.FilterSet):
    class Meta:
        model = Dividend
        fields = ['stock',]

class StockListFilter(django_filters.FilterSet):
    class Meta:
        model = Stock
        fields = ['active','stock_type',]

class AccountFilter(django_filters.FilterSet):
    class Meta:
        model = Account
        fields = ['account_type','person',]