from django.contrib import admin

from .models import Transaction, Stock, Account, Price, Holding, Person

class PersonAdmin(admin.ModelAdmin):
    list_display = ('name',)

class TransactionInline(admin.TabularInline):
    model = Transaction
    extra = 3

class HoldingInline(admin.TabularInline):
    model = Holding
    extra = 1

class AccountAdmin(admin.ModelAdmin):
    list_display = ('account_type','person','name','account_value')
    inlines = [HoldingInline,TransactionInline]

class PriceAdmin(admin.ModelAdmin):
    list_display = ('date', 'stock', 'price',)
    list_filter = ('stock', )

class TransactionAdmin(admin.ModelAdmin):
    list_display = ('transaction_type','date', 'account', 'stock','volume', 'price','tcost')
    list_filter = ( 'account', 'stock', )
    search_fields = ['stock']
    

class HoldingAdmin(admin.ModelAdmin):
    list_display = ('account', 'stock', 'volume','current_value','value_updated')
    list_filter = ('account','stock', )

class StockAdmin(admin.ModelAdmin):
    list_display = ('name', 'nickname','code', 'stock_type','current_price')
    list_filter = ('stock_type', )
    #list_editable = ('nickname',)


admin.site.register(Person, PersonAdmin)

admin.site.register(Account, AccountAdmin)
    
admin.site.register(Price, PriceAdmin)
admin.site.register(Holding, HoldingAdmin)

admin.site.register(Transaction, TransactionAdmin)
admin.site.register(Stock, StockAdmin)
