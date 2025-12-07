from django.contrib import admin
from .models import Transaction, Category


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("id", "date", "shop", "amount", "member", "category")
    list_filter = ("member", "date")
    search_fields = ("shop", "memo")
    list_select_related = ("member",)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "type")
    list_filter = ("type",)
    search_fields = ("name",)
