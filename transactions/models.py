from django.db import models
from members.models import Member


class Category(models.Model):
    name = models.CharField("カテゴリ名", max_length=50, unique=True)
    # 必要なら「種別（例: 支出/収入）」を後で追加できるように残すのはアリ
    # type = models.CharField("種別", max_length=20, blank=True, default="")

    class Meta:
        ordering = ["id"]
        verbose_name = "カテゴリ"
        verbose_name_plural = "カテゴリ"

    def __str__(self):
        return self.name


class Transaction(models.Model):
    date = models.DateField("日付")
    shop = models.CharField("店名", max_length=200)
    amount = models.IntegerField("金額")

    member = models.ForeignKey(
        Member,
        on_delete=models.PROTECT,
        related_name="transactions",
        verbose_name="使用メンバー",
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="transactions",
        verbose_name="カテゴリ",
    )

    memo = models.TextField("メモ", blank=True, default="")

    # 「yyyy/mm」表示したいけど、DBはDateFieldが扱いやすいので
    # “その月の1日” を入れる運用にするのが一番ラク（例: 2026-01-01）
    import_month = models.DateField("インポート月")

    is_closed = models.BooleanField("確定済み", default=False)

    class Meta:
        ordering = ["-date", "-id"]
        verbose_name = "明細"
        verbose_name_plural = "明細"

    def __str__(self):
        return f"{self.date} {self.shop} {self.amount}円"

    # 画面表示用（テンプレで使える）
    @property
    def date_label(self) -> str:
        # 曜日つき表示：yyyy/mm/dd(曜)
        youbi = ["月", "火", "水", "木", "金", "土", "日"]
        w = youbi[self.date.weekday()]
        return self.date.strftime(f"%Y/%m/%d({w})")

    @property
    def import_month_label(self) -> str:
        return self.import_month.strftime("%Y/%m")
