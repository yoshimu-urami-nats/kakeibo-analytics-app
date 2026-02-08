# account/views.py
import re
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum, Q, F

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

    # --- ① 請求月 × メンバー 合計（memberがNULLも拾って「未割当」に寄せる） ---
    member_rows = (
        Transaction.objects
        .exclude(source_file="")
        .values("source_file", "member__name")
        .annotate(total=Sum("amount"), count=Count("id"))
    )

    # メンバー表示順（必要なら増やせる）
    member_order = ["な", "ゆ", "共有", "未割当"]
    member_set = set(member_order)

    # month -> member -> total の辞書にする
    member_pivot = {}
    for r in member_rows:
        sf = r["source_file"] or ""
        m = re.search(r"(\d{6})", sf)
        month = m.group(1) if m else sf

        name = r["member__name"] or "未割当"
        member_set.add(name)

        member_pivot.setdefault(month, {})
        member_pivot[month][name] = int(r["total"] or 0)

    # 実データに合わせてメンバー列を確定（order優先、残りは後ろに追加）
    member_cols = member_order + sorted([x for x in member_set if x not in member_order])

    # テンプレで回しやすい行リストに変換（billing_statsの月順に揃える）
    months = [x["billing_month"] for x in billing_stats]

    member_table = []
    for mo in months:
        row = {"billing_month": mo, "cells": []}
        for name in member_cols:
            row["cells"].append({
                "name": name,
                "total": member_pivot.get(mo, {}).get(name, 0),
            })
        member_table.append(row)


    # --- ② 請求月 × カテゴリ 合計（上位Nカテゴリだけ表示） ---
    # まず全期間で「金額が大きいカテゴリ上位」を決める（NULL除外）
    TOP_N = 8
    top_categories = list(
        Transaction.objects
        .exclude(source_file="")
        .exclude(category__isnull=True)
        .values("category__name")
        .annotate(total=Sum("amount"))
        .order_by("-total")[:TOP_N]
    )
    cat_cols = [r["category__name"] for r in top_categories]

    cat_rows = (
        Transaction.objects
        .exclude(source_file="")
        .exclude(category__isnull=True)
        .values("source_file", "category__name")
        .annotate(total=Sum("amount"))
    )

    cat_pivot = {}
    for r in cat_rows:
        sf = r["source_file"] or ""
        m = re.search(r"(\d{6})", sf)
        month = m.group(1) if m else sf

        cname = r["category__name"]
        if cname not in cat_cols:
            continue

        cat_pivot.setdefault(month, {})
        cat_pivot[month][cname] = int(r["total"] or 0)

    category_table = []
    for mo in months:
        row = {"billing_month": mo, "cells": []}
        for cname in cat_cols:
            row["cells"].append({
                "name": cname,
                "total": cat_pivot.get(mo, {}).get(cname, 0),
            })
        category_table.append(row)

    # --- render context を増やす（最後の render をこれに） ---
    return render(request, "account/eda.html", {
        "billing_stats": billing_stats,
        "member_cols": member_cols,
        "member_table": member_table,
        "cat_cols": cat_cols,
        "category_table": category_table,
    })

@login_required
def prediction(request):
    return render(request, "account/prediction.html")
