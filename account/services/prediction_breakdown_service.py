from typing import Any
from django.db.models import Count, Sum, Q
from transactions.models import Transaction


def build_prediction_breakdown_data(
    *,
    yyyymm: str,
    exclude_keywords: list[str],
    months_sorted: list[str],
    month_totals: dict[str, int],
) -> dict[str, Any]:

    # 除外Q
    exclude_q = Q()
    for kw in exclude_keywords:
        exclude_q |= Q(category__name__icontains=kw)

    if yyyymm not in months_sorted:
        return {"not_found": True}

    target_idx = months_sorted.index(yyyymm)
    train_months = months_sorted[:target_idx]

    # --- 対象月 ---
    target_qs = (
        Transaction.objects
        .exclude(source_file="")
        .exclude(category__isnull=True)
        .exclude(exclude_q)
        .filter(source_file__startswith=yyyymm)
    )

    total_all = int(target_qs.aggregate(s=Sum("amount"))["s"] or 0)

    cat_rows = (
        target_qs
        .values("category__name")
        .annotate(total=Sum("amount"), count=Count("id"))
        .order_by("-total")
    )

    shop_rows = (
        target_qs
        .values("shop")
        .annotate(total=Sum("amount"), count=Count("id"))
        .order_by("-total")[:8]
    )

    # --- 学習期間 ---
    train_cat_rows = []
    train_shop_rows = []
    train_total_all = 0
    train_month_totals = []

    if train_months:
        train_q = Q()
        for mo in train_months:
            train_q |= Q(source_file__startswith=mo)

        train_qs = (
            Transaction.objects
            .exclude(source_file="")
            .exclude(category__isnull=True)
            .exclude(exclude_q)
            .filter(train_q)
        )

        train_total_all = int(train_qs.aggregate(s=Sum("amount"))["s"] or 0)

        train_cat_rows = (
            train_qs
            .values("category__name")
            .annotate(total=Sum("amount"), count=Count("id"))
            .order_by("-total")
        )

        train_shop_rows = (
            train_qs
            .values("shop")
            .annotate(total=Sum("amount"), count=Count("id"))
            .order_by("-total")[:8]
        )

        for mo in train_months:
            train_month_totals.append({
                "month": mo,
                "total": int(month_totals.get(mo, 0)),
            })

    return {
        "not_found": False,
        "yyyymm": yyyymm,
        "exclude_keywords": exclude_keywords,
        "total_all": total_all,
        "cat_rows": cat_rows,
        "shop_rows": shop_rows,
        "train_months": train_months,
        "train_total_all": train_total_all,
        "train_cat_rows": train_cat_rows,
        "train_shop_rows": train_shop_rows,
        "train_month_totals": train_month_totals,
    }
