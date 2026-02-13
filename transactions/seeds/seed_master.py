"""
NOTE:
2026-02-13 現在は使用していません。
旧seedロジック保管用。
分類ロジックの本体は transactions/rules.py にあります。
"""


from django.core.management.base import BaseCommand
from django.db import transaction

from members.models import Member
from transactions.models import Category  
from transactions.seeds.seed_data import MEMBERS, CATEGORIES

class Command(BaseCommand):
    help = "Seed master data (members, categories). Idempotent (safe to run multiple times)."

    @transaction.atomic
    def handle(self, *args, **options):
        created_members = 0
        for name in MEMBERS:
            _, created = Member.objects.get_or_create(name=name)
            created_members += int(created)

        created_categories = 0
        for name in CATEGORIES:
            _, created = Category.objects.get_or_create(name=name)
            created_categories += int(created)

        self.stdout.write(self.style.SUCCESS(
            f"done: members +{created_members}, categories +{created_categories}"
        ))
