from django.urls import path
from . import views

app_name = "transactions"

urlpatterns = [
    path("", views.transaction_list, name="list"),
    path("new/", views.transaction_create, name="create"),
    path("unassigned/", views.unassigned_list, name="unassigned"),
    path("assign/<int:pk>/", views.assign_member, name="assign_member"),
]
