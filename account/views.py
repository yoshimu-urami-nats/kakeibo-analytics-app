# account/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from django.db.models import Count, Sum, Q
from django.db.models.functions import TruncMonth

from transactions.models import Transaction  # ★追加

def home(request):
    return render(request, "account/home.html")

@login_required
def csv_import(request):
    return render(request, "account/csv_import.html")

@login_required
def eda(request):
    # 月次：件数 / 合計 / 未確定率
    rows = (
        Transaction.objects
        .annotate(month=TruncMonth("date"))
        .values("month")
        .annotate(
            total_count=Count("id"),
            total_amount=Sum("amount"),
            unclosed_count=Count("id", filter=Q(is_closed=False)),
        )
        .order_by("month")
    )

    monthly_stats = []
    for r in rows:
        total = int(r["total_count"] or 0)
        unclosed = int(r["unclosed_count"] or 0)
        rate = round((unclosed / total) * 100, 1) if total else 0.0

        monthly_stats.append({
            "month": r["month"],
            "count": total,
            "total": int(r["total_amount"] or 0),
            "unclosed": unclosed,
            "unclosed_rate": rate,  # %
        })

    return render(request, "account/eda.html", {"monthly_stats": monthly_stats})

@login_required
def prediction(request):
    return render(request, "account/prediction.html")
