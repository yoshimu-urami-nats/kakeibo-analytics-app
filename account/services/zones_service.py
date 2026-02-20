from typing import Any
from statistics import median
from django.db.models import Sum
from transactions.models import Transaction
from account.utils.date_utils import yyyymm_label
from account.utils.stats_utils import percentile, zone_label


def build_zones_context(
    target_names: list[str] | None = None,
    n_base: int = 12,
) -> dict[str, Any]:

    if target_names is None:
        target_names = ["食品・日用品", "外食", "娯楽"]

    # ① source_file一覧
    sfs = list(
        Transaction.objects
        .exclude(source_file="")
        .values_list("source_file", flat=True)
        .distinct()
    )

    if not sfs:
        return {"has_data": False}

    # ② YYYYMMで束ねる
    month_to_sfs: dict[str, list[str]] = {}
    for sf in sfs:
        mo = yyyymm_label(sf)
        if mo:
            month_to_sfs.setdefault(mo, []).append(sf)

    months_sorted = sorted(
        month_to_sfs.keys(),
        key=lambda m: int(m) if m.isdigit() else -1
    )

    if not months_sorted:
        return {"has_data": False}

    # ③ 今月
    current_month = months_sorted[-1]
    current_sfs = month_to_sfs[current_month]

    # ④ ベース期間
    base_months = months_sorted[:-1][-n_base:]
    base_sfs = []
    for mo in base_months:
        base_sfs.extend(month_to_sfs.get(mo, []))

    base_qs = (
        Transaction.objects
        .exclude(source_file="")
        .exclude(category__isnull=True)
        .filter(category__name__in=target_names)
    )

    # ⑤ ベースpivot
    base_rows = (
        base_qs
        .filter(source_file__in=base_sfs)
        .values("source_file", "category__name")
        .annotate(total=Sum("amount"))
    )

    base_pivot: dict[str, dict[str, int]] = {}
    for r in base_rows:
        mo = yyyymm_label(r["source_file"])
        cat = r["category__name"]
        base_pivot.setdefault(mo, {})
        base_pivot[mo][cat] = base_pivot[mo].get(cat, 0) + int(r["total"] or 0)

    # ⑥ 今月
    cur_rows = (
        base_qs
        .filter(source_file__in=current_sfs)
        .values("category__name")
        .annotate(total=Sum("amount"))
    )
    cur_by_cat = {
        r["category__name"]: int(r["total"] or 0)
        for r in cur_rows
    }

    # ⑦ カード生成
    cards = []
    for cat in target_names:
        vals = [base_pivot.get(mo, {}).get(cat, 0) for mo in base_months]

        med = int(median(vals)) if vals else 0
        p75 = percentile(vals, 0.75) if vals else 0
        cur = cur_by_cat.get(cat, 0)

        cards.append({
            "name": cat,
            "current": cur,
            "median": med,
            "p75": p75,
            "delta": cur - med,
            "zone": zone_label(cur, med, p75),
        })

    contrib = sorted(cards, key=lambda x: x["delta"], reverse=True)

    return {
        "has_data": True,
        "current_month": current_month,
        "base_months": base_months,
        "n_base": len(base_months),
        "cards": cards,
        "contrib": contrib,
    }
