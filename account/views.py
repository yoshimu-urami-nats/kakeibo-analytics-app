# account/views.py
import re
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum, Q

from transactions.models import Transaction

def home(request):
    return render(request, "account/home.html")

@login_required
def csv_import(request):
    return render(request, "account/csv_import.html")

@login_required
def eda(request):
    # 請求月（CSVファイル単位）で集計
    rows = (
        Transaction.objects
        .exclude(source_file="")  # 念のため
        .values("source_file")
        .annotate(
            total_count=Count("id"),
            total_amount=Sum("amount"),
            unclosed_count=Count("id", filter=Q(is_closed=False)),
        )
    )

    # source_file から YYYYMM を抜いて並び替え（例: "202601.csv" / "202601" 両対応）
    def yyyymm_key(s: str) -> int:
        m = re.search(r"(\d{6})", s or "")
        return int(m.group(1)) if m else -1

    rows_sorted = sorted(list(rows), key=lambda r: yyyymm_key(r["source_file"]))

    billing_stats = []
    for r in rows_sorted:
        total = int(r["total_count"] or 0)
        unclosed = int(r["unclosed_count"] or 0)
        rate = round((unclosed / total) * 100, 1) if total else 0.0

        sf = r["source_file"] or ""
        m = re.search(r"(\d{6})", sf)
        label = m.group(1) if m else sf  # 表示は 202601 に寄せる

        billing_stats.append({
            "billing_month": label,              # "YYYYMM"
            "source_file": sf,                  # 生のファイル名も必要なら使える
            "count": total,
            "total": int(r["total_amount"] or 0),
            "unclosed": unclosed,
            "unclosed_rate": rate,
        })

    return render(request, "account/eda.html", {"billing_stats": billing_stats})

@login_required
def prediction(request):
    return render(request, "account/prediction.html")
