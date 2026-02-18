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
    source_file = models.CharField("ファイル名", max_length=255, blank=True, default="")
    is_closed = models.BooleanField("確定済みか", default=False)

    class Meta:
        ordering = ["-date", "-id"]
        verbose_name = "明細"
        verbose_name_plural = "明細"

    def __str__(self):
        return f"{self.date} {self.shop} {self.amount}円"
    
    @property
    def date_label(self):
        youbi = ["月", "火", "水", "木", "金", "土", "日"]
        w = youbi[self.date.weekday()]
        return self.date.strftime(f"%Y/%m/%d({w})")

    @property
    def import_month_label(self):
        return self.import_month.strftime("%Y/%m")
