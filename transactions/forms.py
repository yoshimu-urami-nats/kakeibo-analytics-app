from django import forms
from .models import Transaction


class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ["date", "shop", "amount", "member", "category", "memo"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
        }


class AssignMemberForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ["member"]

class CSVUploadForm(forms.Form):
    csv_file = forms.FileField(label="CSVファイル")