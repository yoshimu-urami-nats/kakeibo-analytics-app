from django.contrib import admin
from .models import Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("id", "date", "shop", "amount", "member")
    list_filter = ("member", "date")
    search_fields = ("shop", "memo")
    list_select_related = ("member",)
