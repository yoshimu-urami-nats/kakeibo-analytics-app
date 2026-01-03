from django.db import models

class Member(models.Model):
    name = models.CharField("メンバー名", max_length=50, unique=True)

    class Meta:
        ordering = ["id"]
        verbose_name = "メンバー"
        verbose_name_plural = "メンバー"

    def __str__(self):
        return self.name
