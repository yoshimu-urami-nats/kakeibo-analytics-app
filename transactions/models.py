from django.db import models
from members.models import Member


class Category(models.Model):
    name = models.CharField("カテゴリ名", max_length=50)

    def __str__(self):
        return self.name


class Transaction(models.Model):
    date = models.DateField("日付")
    shop = models.CharField("店名・サービス名", max_length=255)
    amount = models.IntegerField("金額")

    member = models.ForeignKey(
        Member,
        on_delete=models.PROTECT,
        related_name="transactions",
        verbose_name="メンバー",
        null=True,
        blank=True,
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="transactions",
        verbose_name="カテゴリ",
        null=True,
        blank=True,
    )

    memo = models.TextField("メモ", blank=True, default="")
    import_month = models.DateField("インポート月")
    is_closed = models.BooleanField("確定済みか", default=False)

    class Meta:
        ordering = ["-date", "-id"]
        verbose_name = "明細"
        verbose_name_plural = "明細"

    def __str__(self):
        return f"{self.date} {self.shop} {self.amount}円"
