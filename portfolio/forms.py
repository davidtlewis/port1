from django import forms

from .models import Stock, Transaction

class TransactionForm(forms.ModelForm):

    class Meta:
        model = Transaction
        fields = ('account', 'transaction_type', 'date', 'stock', 'volume', 'price', 'tcost')

class HoldingTransactionForm(forms.ModelForm):
    """Buy/sell form for a transaction against a single, already-known account."""

    class Meta:
        model = Transaction
        fields = ('transaction_type', 'date', 'stock', 'volume', 'price', 'tcost')
        widgets = {'date': forms.DateInput(attrs={'type': 'date'})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['stock'].queryset = Stock.objects.filter(
            active=True, is_cash=False
        ).exclude(stock_type='curr').order_by('nickname')
        default_stock = self.fields['stock'].queryset.filter(code='VWRL:LSE:GBP').first()
        if default_stock:
            self.fields['stock'].initial = default_stock.pk

class CommandForm(forms.Form):
    do_get_prices  = forms.BooleanField(required=False, initial=True )
    do_refresh_accounts  = forms.BooleanField(required=False, initial=True)
    do_refresh_holdings  = forms.BooleanField(required=False)
    do_get_perf  = forms.BooleanField(required=False)
    #do_clear_history = forms.BooleanField(required=False)
    #do_clear_history = forms.BooleanField(required=False)