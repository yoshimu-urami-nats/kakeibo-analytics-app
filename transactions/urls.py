# transactions/urls.py
from django.urls import path
from . import views

app_name = "transactions"

urlpatterns = [
    path("", views.transaction_list, name="list"),
    path("summary/", views.summary, name="summary"),
]

