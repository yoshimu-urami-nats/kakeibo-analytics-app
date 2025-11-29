from django import forms
from .models import Transaction


class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ["date", "shop", "amount", "member", "memo"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
        }


class AssignMemberForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ["member"]