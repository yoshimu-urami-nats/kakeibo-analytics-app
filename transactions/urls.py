from django.urls import path
from . import views

app_name = "transactions"

urlpatterns = [
    path("", views.transaction_list, name="list"),
    path("new/", views.transaction_create, name="create"),
    path("unassigned/", views.unassigned_list, name="unassigned"),
    path("assign/<int:pk>/", views.assign_member, name="assign_member"),
    path("upload/", views.upload_csv, name="upload_csv"),
    path("auto_assign/", views.auto_assign, name="auto_assign"),
    path("to_confirm/", views.to_confirm_list, name="to_confirm"),
    path("confirm_bulk/", views.confirm_bulk, name="confirm_bulk"),
]
