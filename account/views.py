from django.shortcuts import render

def home(request):
    # account/home.html を表示する
    return render(request, "account/home.html")
