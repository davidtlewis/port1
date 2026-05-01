from django.shortcuts import render
from django.urls import path, reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.views.generic import DetailView
from django.core.paginator import Paginator
from django_tables2 import SingleTableView
from django_tables2.views import SingleTableMixin
from django_tables2.export.views import ExportMixin
from django_filters.views import FilterView
from .models import Stock, Price, Holding, Transaction, Account, Dividend, DailySnapshot
from .tables import StockTable, HoldingTable, TransactionTable, PriceTable, AccountTable, DividendTable, StockHoldingTable, StockListTable, HoldingTransactionsTable
from django.db.models import Sum
from .forms import TransactionForm, CommandForm
from django.shortcuts import redirect
from django.core import management
from django.contrib.auth.decorators import login_required
from .filters import HoldingByAccountFilter, HoldingByAccountFilter2, TransactionFilter, DividendByStockFilter, StockListFilter, AccountFilter
from datetime import datetime, date
import time
from django_tables2 import RequestConfig

def home(request):
    return HttpResponse("Hello, Django!")

class StockListView(SingleTableView, FilterView):
    model = Stock
    table_class = StockTable
    template_name = 'portfolio/stock.html'
    #filterset_class = StockListFilter
    queryset = Stock.objects.all().filter(active=True)
    table_pagination=False

def StockVolumesView(request):
    stock_volumes = Holding.objects.values('stock__name').annotate(share_volume=Sum('volume'))
    return render(request, 'portfolio/stock_volumes.html', {'stock_volumes': stock_volumes,}, )

class StockHoldingView(ExportMixin, SingleTableView):
    queryset  = Stock.objects.annotate(sum_value=Sum('holding__current_value')).filter(sum_value__gt=0)
    table_class = StockListTable
    template_name = "portfolio/stock_holding_summary2.html"
    table_pagination=False
    #http://127.0.0.1:8000/stockHoldingsummary2/?_export=csv to download csv of this table
        
class PriceListView(SingleTableView):
    model = Price
    table_class = PriceTable
    template_name = 'portfolio/price.html'
    paginate_by = 10

class HoldingListViewFiltered(ExportMixin,SingleTableMixin, FilterView):
    model = Holding
    table_class = HoldingTable
    template_name = 'portfolio/holding.html'
    filterset_class = HoldingByAccountFilter
    queryset  = Holding.objects.all().filter(current_value__gt=0)

class DividendListView(SingleTableMixin, FilterView):
    model = Dividend
    table_class = DividendTable
    template_name = 'portfolio/dividend.html'
    filterset_class = DividendByStockFilter

class HoldingListView(SingleTableView):
    model = Holding
    table_class = HoldingTable
    template_name = 'portfolio/holding.html'

class TransactionListView(SingleTableView):
    model = Transaction
    table_class = TransactionTable
    template_name = 'portfolio/transaction.html'
    paginate_by = 10

class TransactionListViewFiltered(SingleTableMixin, FilterView):
    model = Transaction
    table_class = TransactionTable
    template_name = 'portfolio/transaction.html'
    filterset_class = TransactionFilter

class AccountListView(SingleTableView):
    model = Account
    table_class = AccountTable
    template_name = 'portfolio/account.html'

class AccountListViewFiltered(ExportMixin,SingleTableMixin, FilterView):
    model = Account
    table_class = AccountTable
    filterset_class = AccountFilter
    # queryset  = Account.objects.all().filter(account_value__gt=0)
    template_name = 'portfolio/account.html'

def detailed_summary(request):
    totals = Account.objects.aggregate(Sum('account_value'))
    accounts = Account.objects.all()
    #accounts_by_type = Account.objects.values('account_type').annotate(total_value=Sum('account_value'))
    a = Account.objects.filter(person__name = "david") | Account.objects.filter(person__name = "henri")
    accounts_by_type = a.values('account_type').annotate(total_value=Sum('account_value'))
    accounts_by_person = Account.objects.values('person__name','person__id').annotate(total_value=Sum('account_value')).order_by('person__name')
    return render(request, 'portfolio/detailedsummary.html', {
    'totals': totals, 'accounts':accounts, 'accounts_by_type': accounts_by_type, 'accounts_by_person': accounts_by_person,
    }, )

class AccountDetailView(DetailView):
    model = Account
    template_name = 'portfolio/account_detail.html'

class TransactionDetailView(DetailView):
    model = Transaction
    template_name = 'portfolio/transaction_detail.html'

class HoldingDetailView(DetailView):
    model = Holding
    template_name = 'portfolio/holding_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        transaction_list = Transaction.objects.filter(account=self.object.account).filter(stock=self.object.stock)
        table = HoldingTransactionsTable(transaction_list)
        RequestConfig(self.request).configure(table) 
        context['table'] = table
        return context

class StockDetailView(DetailView):
    model = Stock
    template_name = 'portfolio/stock_detail.html'

def transaction_new(request):
    if request.method == "POST":
        form = TransactionForm(request.POST)
        if form.is_valid():
            transaction = form.save(commit=False)
            #transaction.account = request.account
            #transaction.transaction_type = request.transaction_type
            #transaction.date = request.date
            #transaction.stock = request.stock
            #transaction.volume = request.volume
            #transaction.tcost = request.tcost
            transaction.save()
            return redirect('transaction_detail', pk=transaction.pk)
    else:
        form = TransactionForm()
    return render(request, 'portfolio/transaction_edit.html', {'form': form})

@login_required(login_url='/account/login/')
def command(request):
    if request.method =='POST':
        form = CommandForm(request.POST)
        if form.is_valid():
            do_get_prices = form.cleaned_data['do_get_prices']
            do_refresh_accounts = form.cleaned_data['do_refresh_accounts']
            do_refresh_holdings = form.cleaned_data['do_refresh_holdings']
            do_get_perf = form.cleaned_data['do_get_perf']

            if do_get_prices:
                management.call_command('get_prices')
            if do_refresh_holdings:
                management.call_command('refresh_holdings')
            if do_refresh_accounts:
                management.call_command('refresh_accounts')
            if do_get_perf:
                management.call_command('get_perf')
        return HttpResponseRedirect(reverse('index') )
    else:
        form = CommandForm()
        context = {
            'form': form
        }
    return render(request, 'portfolio/commands.html', context)

@login_required(login_url='/account/login/')
def recalc(request):
    management.call_command('get_prices')
    management.call_command('refresh_accounts')
    return HttpResponseRedirect(reverse('index') )

def summary_old(request):
    a = Account.objects.filter(person__name = "david") | Account.objects.filter(person__name = "henri")
    total = a.aggregate(Sum('account_value'))
    pensions = Account.objects.filter(account_type = "pension") 
    #a = Account.objects.filter(person__name = "david").exclude(account_type = "pension") | Account.objects.filter(person__name = "henri").exclude(account_type = "pension")
    accounts_by_type = a.values('account_type').annotate(total_value=Sum('account_value'))
    stock_currencies = Stock.objects.filter(stock_type = "curr")
    return render(request, 'portfolio/custom_report.html', {
    'total': total, 'pensions':pensions, 'accounts_by_type': accounts_by_type, 'stock_currencies': stock_currencies,
    }, )

def summary(request):
    # Get the primary GBP/USD exchange rate currency stock
    try:
        # Get the GBPUSD currency stock
        usd_gbp_stock = Stock.objects.get(stock_type="curr", nickname="GBPUSD")
        USDGBP = usd_gbp_stock.current_price if usd_gbp_stock else 1
        updateTime = usd_gbp_stock.price_updated if usd_gbp_stock else None
    except Stock.DoesNotExist:
        # Fallback if no currency stocks exist
        USDGBP = 1
        updateTime = None

    # Get the GBP Currency Index for global value perspective
    try:
        currency_index_stock = Stock.objects.get(stock_type="curr", nickname="GBP Currency Index")
        currencyIndex = currency_index_stock.current_price if currency_index_stock else 1
        currencyIndexUpdateTime = currency_index_stock.price_updated if currency_index_stock else None
    except Stock.DoesNotExist:
        # Fallback if currency index doesn't exist
        currencyIndex = 1
        currencyIndexUpdateTime = None

    a = Account.objects.filter(person__name = "david") | Account.objects.filter(person__name = "henri")
    HDaccounts_by_type = a.values('account_type').annotate(total_value=Sum('account_value'))
    HDtotal = a.aggregate(Sum('account_value'))
    HDtotalvalue = HDtotal['account_value__sum']

    pensions = Account.objects.filter(account_type = "pension")


    totals = Account.objects.aggregate(Sum('account_value'))
    totalUSD = totals['account_value__sum'] * USDGBP
    totalCurrencyIndex = totals['account_value__sum'] * currencyIndex

    previous_snapshot = DailySnapshot.objects.filter(date__lt=date.today()).first()

    hd_value_gbp_change = None
    hd_value_usd_change = None
    hd_value_currency_index_change = None
    total_value_gbp_change = None
    total_value_usd_change = None
    total_value_currency_index_change = None

    if previous_snapshot:
        hd_value_gbp_change = HDtotalvalue - previous_snapshot.hd_value_gbp
        hd_value_usd_change = (HDtotalvalue * USDGBP) - previous_snapshot.hd_value_usd
        hd_value_currency_index_change = (HDtotalvalue * currencyIndex) - previous_snapshot.hd_value_currency_index
        total_value_gbp_change = totals['account_value__sum'] - previous_snapshot.total_value_gbp
        total_value_usd_change = totalUSD - previous_snapshot.total_value_usd
        total_value_currency_index_change = totalCurrencyIndex - previous_snapshot.total_value_currency_index


    accounts_by_person = Account.objects.values('person__name','person__id').annotate(total_value=Sum('account_value')).order_by('person__name')


# accounts_by_type = a.values('account_type').annotate(total_value=Sum('account_value'))
    # accounts = Account.objects.all()
    #accounts_by_type = Account.objects.values('account_type').annotate(total_value=Sum('account_value'))


    return render(request, 'portfolio/summary.html', {
      'HDtotalvalue': HDtotalvalue,
      'HDtotalvalueUSD': (HDtotalvalue * USDGBP),
      'HDtotalvalueCurrencyIndex': (HDtotalvalue * currencyIndex),
      'USDGBP': USDGBP,
      'currencyIndex': currencyIndex,
      'totals': totals,
      'totalvalueUSD': totalUSD,
      'totalvalueCurrencyIndex': totalCurrencyIndex,
      'previous_snapshot': previous_snapshot,
      'HDtotalvalueChange': hd_value_gbp_change,
      'HDtotalvalueUSDChange': hd_value_usd_change,
      'HDtotalvalueCurrencyIndexChange': hd_value_currency_index_change,
      'totalvalueChange': total_value_gbp_change,
      'totalvalueUSDChange': total_value_usd_change,
      'totalvalueCurrencyIndexChange': total_value_currency_index_change,
      'pensions':pensions,
      'HDaccounts_by_type': HDaccounts_by_type,
      'updateTime': updateTime,
      'currencyIndexUpdateTime': currencyIndexUpdateTime,
      'accounts_by_person': accounts_by_person,
    }, )


def daily_snapshots(request):
    snapshots = DailySnapshot.objects.all()
    paginator = Paginator(snapshots, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'portfolio/daily_snapshots.html', {
        'snapshots': page_obj.object_list,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
    })