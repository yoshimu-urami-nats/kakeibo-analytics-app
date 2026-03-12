# transactions/forms.py
from django import forms

class CSVUploadForm(forms.Form):
    csv_file = forms.FileField(label="CSVファイル")