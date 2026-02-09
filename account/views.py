# account/views.py
import re
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum, Q, F
from transactions.models import Transaction
from datetime import datetime
from statistics import median

def _yyyymm_key(s: str) -> int:
    """source_file から YYYYMM を抜いて、ソート用の数値にする"""
    m = re.search(r"(\d{6})", s or "")
    return int(m.group(1)) if m else -1

def _yyyymm_label(s: str) -> str:
    """表示用に YYYYMM を返す（取れなければ元文字列）"""
    m = re.search(r"(\d{6})", s or "")
    return m.group(1) if m else (s or "")

def _yyyymm_add1(yyyymm: str) -> str:
    """YYYYMM を 1か月進めた YYYYMM を返す"""
    dt = datetime.strptime(yyyymm, "%Y%m")
    y = dt.year + (1 if dt.month == 12 else 0)
    m = 1 if dt.month == 12 else dt.month + 1
    return f"{y:04d}{m:02d}"

def _linear_regression(points: list[tuple[float, float]]):
    """
    points: [(x, y), ...]
    return: (slope, intercept)
    """
    n = len(points)
    if n < 2:
        return None, None

    xs = [p[0] for p in points]
    ys = [p[1] for p in points]

    x_mean = sum(xs) / n
    y_mean = sum(ys) / n

    denom = sum((x - x_mean) ** 2 for x in xs)
    if denom == 0:
        return None, None

    num = sum((x - x_mean) * (y - y_mean) for x, y in points)
    slope = num / denom
    intercept = y_mean - slope * x_mean
    return slope, intercept

def _percentile(values: list[int], p: float) -> int:
    """
    p: 0.0〜1.0
    線形補間のパーセンタイル（ざっくりで十分）
    """
    if not values:
        return 0
    xs = sorted(values)
    if len(xs) == 1:
        return xs[0]
    k = (len(xs) - 1) * p
    f = int(k)
    c = min(f + 1, len(xs) - 1)
    if f == c:
        return xs[f]
    d = k - f
    return int(round(xs[f] + (xs[c] - xs[f]) * d))

def _zone_label(cur: int, med: int, p75: int) -> str:
    if cur <= med:
        return "安定ゾーン"
    if cur <= p75:
        return "高めゾーン"
    return "負担感あり"

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

    rows_sorted = sorted(list(rows), key=lambda r: _yyyymm_key(r["source_file"]))

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
    # --- 除外カテゴリ（まずは“名前に含まれる語”で除外） ---
    # 実データのカテゴリ名に合わせて、後で増減OK
    exclude_keywords = ["家具", "家電"]

    exclude_q = Q()
    for kw in exclude_keywords:
        exclude_q |= Q(category__name__icontains=kw)

    # --- ① 請求月（source_file）単位で合計を作る ---
    base = (
        Transaction.objects
        .exclude(source_file="")
        .exclude(category__isnull=True)  # NULLカテゴリは一旦除外（必要なら外してもOK）
        .exclude(exclude_q)              # 家具・家電を除外
    )

    rows = (
        base
        .values("source_file")
        .annotate(total_amount=Sum("amount"))
    )

    # --- ② 月順にソートして、時系列（index付き）に整形 ---
    rows_sorted = sorted(list(rows), key=lambda r: _yyyymm_key(r["source_file"]))

    series = []
    for i, r in enumerate(rows_sorted):
        label = _yyyymm_label(r["source_file"])
        total = int(r["total_amount"] or 0)
        series.append({
            "i": i,             # 回帰用のx
            "billing_month": label,
            "total": total,
        })

    # --- ③ 線形回帰（最初は“全期間”で一本） ---
    slope = intercept = pred_next = None
    next_month = ""

    if len(series) >= 2:
        points = [(d["i"], d["total"]) for d in series]
        slope, intercept = _linear_regression(points)

        if slope is not None:
            next_i = series[-1]["i"] + 1
            pred_next = int(round(slope * next_i + intercept))

            # 表示用の「来月YYYYMM」も作る
            next_month = _yyyymm_add1(series[-1]["billing_month"])

    # --- render ---
    return render(request, "account/prediction.html", {
        "exclude_keywords": exclude_keywords,
        "series": series,                 # 時系列テーブル用
        "slope": slope,                   # 増減傾向（円/月）
        "intercept": intercept,
        "pred_next": pred_next,           # 来月予測（円）
        "next_month": next_month,         # 表示用ラベル
    })

@login_required
def zones(request):
    target_names = ["食品・日用品", "外食", "娯楽"]
    N = 12

    # まず存在する source_file 一覧
    sfs = list(
        Transaction.objects
        .exclude(source_file="")
        .values_list("source_file", flat=True)
        .distinct()
    )
    if not sfs:
        return render(request, "account/zones.html", {"has_data": False})

    # ★ YYYYMM ラベルごとに source_file を束ねる（同月に複数ファイルがあってもOK）
    month_to_sfs: dict[str, list[str]] = {}
    for sf in sfs:
        mo = _yyyymm_label(sf)   # "202602" みたいな表示用YYYYMM
        if mo:
            month_to_sfs.setdefault(mo, []).append(sf)

    months_sorted = sorted(month_to_sfs.keys(), key=lambda m: int(m) if m.isdigit() else -1)
    if not months_sorted:
        return render(request, "account/zones.html", {"has_data": False})

    # 今月（最新YYYYMM）
    current_month = months_sorted[-1]
    current_sfs = month_to_sfs[current_month]  # ★同月ファイルを全部今月扱い

    # ベース（月ラベルのリスト：最新を除いた直近N）
    base_months = months_sorted[:-1][-N:]
    base_sfs = []
    for mo in base_months:
        base_sfs.extend(month_to_sfs.get(mo, []))

    # 対象データ
    base_qs = (
        Transaction.objects
        .exclude(source_file="")
        .exclude(category__isnull=True)
        .filter(category__name__in=target_names)
    )

    # ① ベース期間：月×カテゴリ 合計（source_fileはbase_sfsに寄せる）
    base_rows = (
        base_qs
        .filter(source_file__in=base_sfs)
        .values("source_file", "category__name")
        .annotate(total=Sum("amount"))
    )

    # month(YYYYMM) -> cat -> total
    base_pivot: dict[str, dict[str, int]] = {}
    for r in base_rows:
        mo = _yyyymm_label(r["source_file"])
        cat = r["category__name"]
        base_pivot.setdefault(mo, {})
        base_pivot[mo][cat] = base_pivot[mo].get(cat, 0) + int(r["total"] or 0)  # ★同月を足し込む

    # ② 今月：カテゴリ合計（同月ファイル全部）
    cur_rows = (
        base_qs
        .filter(source_file__in=current_sfs)
        .values("category__name")
        .annotate(total=Sum("amount"))
    )
    cur_by_cat = {r["category__name"]: int(r["total"] or 0) for r in cur_rows}

    # ③ カテゴリごとに「中央値 / 75% / 今月 / ゾーン」
    cards = []
    for cat in target_names:
        vals = [base_pivot.get(mo, {}).get(cat, 0) for mo in base_months]

        med = int(median(vals)) if vals else 0
        p75 = _percentile(vals, 0.75) if vals else 0
        cur = cur_by_cat.get(cat, 0)

        cards.append({
            "name": cat,
            "current": cur,
            "median": med,
            "p75": p75,
            "delta": cur - med,
            "zone": _zone_label(cur, med, p75),
        })

    contrib = sorted(cards, key=lambda x: x["delta"], reverse=True)

    return render(request, "account/zones.html", {
        "has_data": True,
        "current_month": current_month,
        "base_months": base_months,
        "n_base": len(base_months),
        "cards": cards,
        "contrib": contrib,
    })

