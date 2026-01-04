from django.contrib import admin
from .models import Category, Transaction

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("id", "date", "shop", "amount", "member", "category", "source_file", "is_closed")
    list_filter = ("member", "category", "is_closed", "source_file")
    search_fields = ("shop", "memo")
