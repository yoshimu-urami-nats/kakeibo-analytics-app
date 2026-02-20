# account/services/eda_service.py
"""
service: EDAの集計・整形（DBアクセス含む）をするところ
- views.py は「入力取得 → service呼び出し → render」だけにする
"""

import re
from typing import Any

from django.db.models import Count, Sum, Q
from transactions.models import Transaction

from account.utils.date_utils import yyyymm_key


def build_eda_context(*, top_n_categories: int = 8) -> dict[str, Any]:
    """
    EDA画面用のcontext一式を返す
    返すキーは views.py の従来と同じ：
      billing_stats, member_cols, member_table, cat_cols, category_table
    """
    billing_stats = _build_billing_stats()
    months = [x["billing_month"] for x in billing_stats]

    member_cols, member_table = _build_member_table(months)
    cat_cols, category_table = _build_category_table(months, top_n_categories)

    return {
        "billing_stats": billing_stats,
        "member_cols": member_cols,
        "member_table": member_table,
        "cat_cols": cat_cols,
        "category_table": category_table,
    }


def _build_billing_stats() -> list[dict[str, Any]]:
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

    rows_sorted = sorted(list(rows), key=lambda r: yyyymm_key(r["source_file"]))

    billing_stats: list[dict[str, Any]] = []
    for r in rows_sorted:
        total = int(r["total_count"] or 0)
        unclosed = int(r["unclosed_count"] or 0)
        rate = round((unclosed / total) * 100, 1) if total else 0.0

        sf = r["source_file"] or ""
        m = re.search(r"(\d{6})", sf)
        label = m.group(1) if m else sf  # 表示は 202601 に寄せる

        billing_stats.append({
            "billing_month": label,     # "YYYYMM"
            "source_file": sf,          # 生のファイル名も必要なら使える
            "count": total,
            "total": int(r["total_amount"] or 0),
            "unclosed": unclosed,
            "unclosed_rate": rate,
        })

    return billing_stats


def _build_member_table(months: list[str]) -> tuple[list[str], list[dict[str, Any]]]:
    # ① 請求月 × メンバー 合計（memberがNULLも拾って「未割当」に寄せる）
    member_rows = (
        Transaction.objects
        .exclude(source_file="")
        .values("source_file", "member__name")
        .annotate(total=Sum("amount"), count=Count("id"))
    )

    member_order = ["な", "ゆ", "共有", "未割当"]
    member_set = set(member_order)

    member_pivot: dict[str, dict[str, int]] = {}
    for r in member_rows:
        sf = r["source_file"] or ""
        m = re.search(r"(\d{6})", sf)
        month = m.group(1) if m else sf

        name = r["member__name"] or "未割当"
        member_set.add(name)

        member_pivot.setdefault(month, {})
        member_pivot[month][name] = int(r["total"] or 0)

    member_cols = member_order + sorted([x for x in member_set if x not in member_order])

    member_table: list[dict[str, Any]] = []
    for mo in months:
        row = {"billing_month": mo, "cells": []}
        for name in member_cols:
            row["cells"].append({
                "name": name,
                "total": member_pivot.get(mo, {}).get(name, 0),
            })
        member_table.append(row)

    return member_cols, member_table


def _build_category_table(
    months: list[str],
    top_n: int,
) -> tuple[list[str], list[dict[str, Any]]]:
    # ② 請求月 × カテゴリ 合計（上位Nカテゴリだけ表示）
    top_categories = list(
        Transaction.objects
        .exclude(source_file="")
        .exclude(category__isnull=True)
        .values("category__name")
        .annotate(total=Sum("amount"))
        .order_by("-total")[:top_n]
    )
    cat_cols = [r["category__name"] for r in top_categories]

    cat_rows = (
        Transaction.objects
        .exclude(source_file="")
        .exclude(category__isnull=True)
        .values("source_file", "category__name")
        .annotate(total=Sum("amount"))
    )

    cat_pivot: dict[str, dict[str, int]] = {}
    for r in cat_rows:
        sf = r["source_file"] or ""
        m = re.search(r"(\d{6})", sf)
        month = m.group(1) if m else sf

        cname = r["category__name"]
        if cname not in cat_cols:
            continue

        cat_pivot.setdefault(month, {})
        cat_pivot[month][cname] = int(r["total"] or 0)

    category_table: list[dict[str, Any]] = []
    for mo in months:
        row = {"billing_month": mo, "cells": []}
        for cname in cat_cols:
            row["cells"].append({
                "name": cname,
                "total": cat_pivot.get(mo, {}).get(cname, 0),
            })
        category_table.append(row)

    return cat_cols, category_table
