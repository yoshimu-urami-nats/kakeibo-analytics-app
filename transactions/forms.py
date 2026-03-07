# transactions/forms.py
from django import forms

from transactions.models import Transaction

class CSVUploadForm(forms.Form):
    csv_file = forms.FileField(label="CSVファイル")

class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['date', 'shop', 'amount', 'member', 'category', 'memo'] # memoを追加
        widgets = {
            'memo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'メモを入力'}),
        }