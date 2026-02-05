from django.urls import path
from portfolio import views
from portfolio.views import StockListView, PriceListView, TransactionListView, TransactionListViewFiltered, HoldingListView, HoldingListViewFiltered, AccountListView, AccountDetailView, HoldingDetailView, HistoricPriceListView, DividendListView, StockHoldingView, AccountListViewFiltered

urlpatterns = [
    path("", views.summary, name="index"),
    path("summaryold", views.summary_old, name="index_old"),
    path("report", views.detailed_summary, name="detail"),
    path("stocks/", StockListView.as_view(), name='stocks'),
    path("stockvolumes/", views.StockVolumesView, name='stockvolumes'),
    path("prices/", PriceListView.as_view(), name='prices'),
    path("historicprices/", HistoricPriceListView.as_view(), name='historicprices'),
    path("dividends/", DividendListView.as_view(), name='dividends'),
    path("transactions/", TransactionListView.as_view(), name='transactions'),
    path("transactionsfiltered/", TransactionListViewFiltered.as_view(), name='transactionsfiltered'),
    path("holdings/", HoldingListView.as_view(), name='holdings'),
    path("holdingsfiltered/", HoldingListViewFiltered.as_view(), name='holdingsfiltered'),
    path("accounts/", AccountListView.as_view(), name='accounts'),
    path("accountsfiltered/", AccountListViewFiltered.as_view(), name='accountsfiltered'),
    path('account/<int:pk>', AccountDetailView.as_view(), name='account_detail'),
    path('holding/<int:pk>', HoldingDetailView.as_view(), name='holding_detail'),
    path('transaction/<int:pk>', views.TransactionDetailView.as_view(), name='transaction_detail'),
    path('stock/<int:pk>', views.StockDetailView.as_view(), name='stock_detail'),
    path('transaction/new/', views.transaction_new, name='transaction_new'),
    path('commands/', views.command, name='commandform'),
    path("stockholdingsummary/", views.StockHoldingView.as_view(), name='stockholdingsummary'),
    path("refresh/", views.recalc, name='refresh'),
]
