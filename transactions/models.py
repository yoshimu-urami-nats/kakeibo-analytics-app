from django.db import models
from members.models import Member


class Transaction(models.Model):
    """クレカ明細1件分"""

    date = models.DateField("日付")
    shop = models.CharField("店名・サービス名", max_length=100)
    amount = models.IntegerField("金額（円）")
    memo = models.CharField("メモ", max_length=200, blank=True)

    member = models.ForeignKey(
        Member,
        verbose_name="誰の出費か",
        on_delete=models.PROTECT,  # 間違ってMember消しても明細は残す方針
        related_name="transactions",
        null=True,
        blank=True,
    )

    # ★追加：仕分け確定フラグ
    is_confirmed = models.BooleanField("仕分け確定フラグ", default=False)

    # ★追加：どうやって決めたか
    decided_by = models.CharField(
        "判定方法",
        max_length=20,
        choices=(
            ("none", "未判定"),
            ("rule", "ルール自動判定"),   # なんちゃってAI
            ("manual", "人間が手動で確定"),
        ),
        default="none",
    )

    created_at = models.DateTimeField("作成日時", auto_now_add=True)
    updated_at = models.DateTimeField("更新日時", auto_now=True)

    class Meta:
        ordering = ["-date", "-id"]
        verbose_name = "明細"
        verbose_name_plural = "明細"

    def __str__(self):
        return f"{self.date} {self.shop} {self.amount}円 ({self.member})"

    def formatted_date(self):
        """yyyy/mm/dd (曜日) の形式で日付を返す"""
        youbi = ["月", "火", "水", "木", "金", "土", "日"]
        weekday = youbi[self.date.weekday()]  # 0=月曜〜6=日曜
        return self.date.strftime(f"%Y/%m/%d ({weekday})")