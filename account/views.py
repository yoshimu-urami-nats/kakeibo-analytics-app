from django.shortcuts import render
from django.contrib.auth.decorators import login_required

def home(request):
    return render(request, "account/home.html")

@login_required
def csv_import(request):
    return render(request, "account/csv_import.html")

@login_required
def eda(request):
    return render(request, "account/eda.html")

@login_required
def prediction(request):
    return render(request, "account/prediction.html")