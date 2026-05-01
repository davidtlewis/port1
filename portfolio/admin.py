from datetime import datetime
from django.contrib import admin
from .models import Transaction, Stock, Account, Price, Holding, Person, Dividend, DailySnapshot


class TransactionInline(admin.TabularInline):
    model = Transaction
    extra = 3


class HoldingInline(admin.TabularInline):
    model = Holding
    extra = 1


class AccountAdmin(admin.ModelAdmin):
    list_display = ('person', 'account_type', 'name', 'account_value')
    inlines = [HoldingInline, TransactionInline]


class PriceAdmin(admin.ModelAdmin):
    list_display = ('date', 'stock', 'price',)
    list_filter = ('stock', )


class DividendAdmin(admin.ModelAdmin):
    list_display = ('date', 'stock', 'amount',)
    list_filter = ('stock', )


class TransactionAdmin(admin.ModelAdmin):
    list_display = ('transaction_type', 'date', 'account',
                    'stock', 'volume', 'price', 'tcost')
    list_filter = ('account', 'stock')
    search_fields = ['stock']


class HoldingAdmin(admin.ModelAdmin):
    list_display = ('account', 'stock', 'volume',
                    'current_value', 'book_cost', 'value_updated')
    list_filter = ('account', 'stock', )


class StockAdmin(admin.ModelAdmin):
    list_display = ('name', 'active', 'nickname', 'code', 'yahoo_code',
                    'stock_type', 'stock_region', 'current_price', 'price_updated')
    list_filter = ('stock_type', )


class PersonAdmin(admin.ModelAdmin):
    list_display = ('name', )


class DailySnapshotAdmin(admin.ModelAdmin):
    list_display = ('date', 'total_value_gbp', 'total_value_usd', 'total_value_currency_index',
                    'hd_value_gbp', 'hd_value_usd', 'hd_value_currency_index',
                    'gbp_usd_rate', 'currency_index_rate', 'snapshot_time')
    list_filter = ('date', )
    readonly_fields = ('snapshot_time',)
    ordering = ('-date',)


admin.site.register(Account, AccountAdmin)
admin.site.register(Person, PersonAdmin)
admin.site.register(Price, PriceAdmin)
admin.site.register(Dividend, DividendAdmin)
admin.site.register(Holding, HoldingAdmin)
admin.site.register(Transaction, TransactionAdmin)
admin.site.register(Stock, StockAdmin)
admin.site.register(DailySnapshot, DailySnapshotAdmin)
