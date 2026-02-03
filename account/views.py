from django.shortcuts import render

def home(request):
    return render(request, "account/home.html")

def csv_import(request):
    return render(request, "account/csv_import.html")

def eda(request):
    return render(request, "account/eda.html")

def prediction(request):
    return render(request, "account/prediction.html")