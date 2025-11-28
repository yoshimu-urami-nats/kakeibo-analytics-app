from django.db import models

# Create your models here.
class Member(models.Model):
    """家計簿の『誰の出費か』を表すメンバー"""

    name = models.CharField("名前（フル）", max_length=50)
    short_name = models.CharField("表示名（短め）", max_length=20, blank=True)
    is_active = models.BooleanField("有効フラグ", default=True)

    created_at = models.DateTimeField("作成日時", auto_now_add=True)
    updated_at = models.DateTimeField("更新日時", auto_now=True)

    def __str__(self):
        # 管理画面などでの表示用
        return self.short_name or self.name