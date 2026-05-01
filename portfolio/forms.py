from django import forms

from .models import Transaction

class TransactionForm(forms.ModelForm):

    class Meta:
        model = Transaction
        fields = ('account', 'transaction_type', 'date', 'stock', 'volume', 'price', 'tcost')

class CommandForm(forms.Form):
    do_get_prices  = forms.BooleanField(required=False, initial=True )
    do_refresh_accounts  = forms.BooleanField(required=False, initial=True)
    do_refresh_holdings  = forms.BooleanField(required=False)
    do_get_perf  = forms.BooleanField(required=False)
    #do_clear_history = forms.BooleanField(required=False)
    #do_clear_history = forms.BooleanField(required=False)