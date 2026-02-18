# account/views.py
import re
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum, Q, F
from transactions.models import Transaction
from datetime import datetime
from statistics import median
from django.http import HttpResponse
from django.template.loader import render_to_string
from account.utils.date_utils import yyyymm_key, yyyymm_label, yyyymm_add1

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
    # -----------------------------
    # 0) GET params
    # -----------------------------
    try:
        min_train = int(request.GET.get("min_train", "3"))
    except ValueError:
        min_train = 3
    min_train = max(2, min_train)

    exclude_param = (request.GET.get("exclude") or "").strip()
    if exclude_param:
        base_exclude_keywords = [x.strip() for x in exclude_param.split(",") if x.strip()]
    else:
        base_exclude_keywords = ["家具・家電"]

    # -----------------------------
    # 1) 共通：計算ロジックを関数化
    # -----------------------------
    def _run_prediction(exclude_keywords: list[str], min_train: int):
        # 除外Q
        exclude_q = Q()
        for kw in exclude_keywords:
            exclude_q |= Q(category__name__icontains=kw)

        # 対象データ
        base = (
            Transaction.objects
            .exclude(source_file="")
            .exclude(category__isnull=True)
            .exclude(exclude_q)
        )

        # source_file ごとの合計
        rows = (
            base
            .values("source_file")
            .annotate(total_amount=Sum("amount"))
        )

        # YYYYMM（月）へ寄せて集計（同月に複数CSVがあっても足し込む）
        month_totals: dict[str, int] = {}
        for r in rows:
            sf = r["source_file"] or ""
            mo = yyyymm_label(sf)  # "202602"
            if not mo:
                continue
            month_totals[mo] = month_totals.get(mo, 0) + int(r["total_amount"] or 0)

        months_sorted = sorted(
            month_totals.keys(),
            key=lambda m: int(m) if (m and m.isdigit()) else -1
        )

        series = []
        for i, mo in enumerate(months_sorted):
            series.append({
                "i": i,
                "billing_month": mo,
                "total": int(month_totals[mo] or 0),
            })

        # 予測（全期間1本）
        slope = intercept = pred_next = None
        next_month = ""
        if len(series) >= 2:
            points = [(d["i"], d["total"]) for d in series]
            slope, intercept = _linear_regression(points)
            if slope is not None:
                next_i = series[-1]["i"] + 1
                pred_next = int(round(slope * next_i + intercept))
                next_month = yyyymm_add1(series[-1]["billing_month"])

        # バックテスト（walk-forward）
        backtests = []
        errors_abs = []
        errors_sq = []
        errors_pct = []

        naive_abs = []
        naive_sq = []
        naive_pct = []

        if len(series) >= (min_train + 1):
            for t in range(min_train, len(series)):
                train = series[:t]
                test = series[t]

                pts = [(d["i"], d["total"]) for d in train]
                s, b = _linear_regression(pts)
                if s is None:
                    continue

                pred = int(round(s * test["i"] + b))
                actual = int(test["total"])

                # ベースライン：直前月
                naive_pred = int(train[-1]["total"]) if train else 0

                err = pred - actual
                ae = abs(err)
                se = err * err

                n_err = naive_pred - actual
                n_ae = abs(n_err)
                n_se = n_err * n_err

                ape = None
                n_ape = None
                if actual != 0:
                    ape = abs(err) / abs(actual) * 100.0
                    errors_pct.append(ape)

                    n_ape = abs(n_err) / abs(actual) * 100.0
                    naive_pct.append(n_ape)

                errors_abs.append(ae)
                errors_sq.append(se)

                naive_abs.append(n_ae)
                naive_sq.append(n_se)

                backtests.append({
                    "month": test["billing_month"],
                    "train_months": len(train),
                    "pred": pred,
                    "actual": actual,
                    "error": err,
                    "abs_error": ae,
                    "ape": ape,

                    "naive_pred": naive_pred,
                    "naive_error": n_err,
                    "naive_abs_error": n_ae,
                    "naive_ape": n_ape,
                })

        metrics = {
            "n": len(backtests),
            "mae": None,
            "rmse": None,
            "mape": None,
            "naive_mae": None,
            "naive_rmse": None,
            "naive_mape": None,
            "mae_improve_pct": None,
        }

        worst_months = []
        if backtests:
            metrics["mae"] = int(round(sum(errors_abs) / len(errors_abs)))
            metrics["rmse"] = int(round((sum(errors_sq) / len(errors_sq)) ** 0.5))
            metrics["mape"] = round(sum(errors_pct) / len(errors_pct), 1) if errors_pct else None

            metrics["naive_mae"] = int(round(sum(naive_abs) / len(naive_abs)))
            metrics["naive_rmse"] = int(round((sum(naive_sq) / len(naive_sq)) ** 0.5))
            metrics["naive_mape"] = round(sum(naive_pct) / len(naive_pct), 1) if naive_pct else None

            if metrics["naive_mae"] and metrics["naive_mae"] != 0:
                metrics["mae_improve_pct"] = round(
                    (metrics["naive_mae"] - metrics["mae"]) / metrics["naive_mae"] * 100.0, 1
                )

            worst_months = sorted(
                [r for r in backtests if r["ape"] is not None],
                key=lambda r: r["ape"],
                reverse=True
            )[:3]

        return {
            "exclude_keywords": exclude_keywords,
            "series": series,
            "slope": slope,
            "intercept": intercept,
            "pred_next": pred_next,
            "next_month": next_month,
            "backtests": backtests,
            "metrics": metrics,
            "worst_months": worst_months,
        }

    # -----------------------------
    # 2) 比較：交際「含む」vs「除外」
    # -----------------------------
    result_include = _run_prediction(base_exclude_keywords, min_train)

    # 「交際」を除外に足した版（すでに入ってたら二重にしない）
    exclude_plus_social = list(base_exclude_keywords)
    if not any("交際" in x for x in exclude_plus_social):
        exclude_plus_social.append("交際")
    result_exclude = _run_prediction(exclude_plus_social, min_train)

    # -----------------------------
    # 3) 画面表示用：メイン表示は「含む」側を従来通り出す
    # -----------------------------
    return render(request, "account/prediction.html", {
        # 入力欄用
        "exclude_keywords": base_exclude_keywords,
        "exclude_param": ",".join(base_exclude_keywords),
        "min_train": min_train,

        # 従来表示（交際“含む”）
        "series": result_include["series"],
        "slope": result_include["slope"],
        "intercept": result_include["intercept"],
        "pred_next": result_include["pred_next"],
        "next_month": result_include["next_month"],
        "backtests": result_include["backtests"],
        "metrics": result_include["metrics"],
        "worst_months": result_include["worst_months"],

        # 追加：比較用（2本）
        "compare_include": result_include,
        "compare_exclude": result_exclude,
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
        mo = yyyymm_label(sf)   # "202602" みたいな表示用YYYYMM
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
        mo = yyyymm_label(r["source_file"])
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

@login_required
def prediction_breakdown(request, yyyymm: str):
    """
    Predictionページの「ズレ月クリック」用：
    指定した請求月(YYYYMM)のカテゴリ内訳（除外カテゴリ適用後）をHTML断片で返す

    ★追加：その月を予測する時に使われる「学習期間（過去月）」の内訳も返す
    """

    # --- ① prediction() と同じく GET パラメータを解釈 ---
    exclude_param = (request.GET.get("exclude") or "").strip()
    if exclude_param:
        exclude_keywords = [x.strip() for x in exclude_param.split(",") if x.strip()]
    else:
        # prediction() 側のデフォルトに合わせる（ここは好みでOK）
        exclude_keywords = ["家具・家電"]

    # 除外Q（部分一致）
    exclude_q = Q()
    for kw in exclude_keywords:
        exclude_q |= Q(category__name__icontains=kw)

    # --- ② まず「Predictionで使ってる月次系列」を同条件で作る（重要） ---
    # 同月に複数CSVがあっても足し込む（prediction() と同じ方針）
    base_for_series = (
        Transaction.objects
        .exclude(source_file="")
        .exclude(category__isnull=True)
        .exclude(exclude_q)
    )

    rows = (
        base_for_series
        .values("source_file")
        .annotate(total_amount=Sum("amount"))
    )

    month_totals: dict[str, int] = {}
    for r in rows:
        sf = r["source_file"] or ""
        mo = yyyymm_label(sf)  # "202602" みたいなYYYYMMに寄せる
        if not mo:
            continue
        month_totals[mo] = month_totals.get(mo, 0) + int(r["total_amount"] or 0)

    months_sorted = sorted(
        month_totals.keys(),
        key=lambda m: int(m) if (m and m.isdigit()) else -1
    )

    # 対象月が series に存在するか確認
    if yyyymm not in months_sorted:
        html = render_to_string(
            "account/_prediction_breakdown.html",
            {
                "yyyymm": yyyymm,
                "exclude_keywords": exclude_keywords,
                "total_all": 0,
                "cat_rows": [],
                "shop_rows": [],
                # 学習期間側（空）
                "train_months": [],
                "train_total_all": 0,
                "train_cat_rows": [],
                "train_shop_rows": [],
                "train_month_totals": [],
                "not_found": True,
            },
            request=request
        )
        return HttpResponse(html)

    # クリックされた月＝テスト月、その前が学習期間（walk-forward想定）
    target_idx = months_sorted.index(yyyymm)
    train_months = months_sorted[:target_idx]  # その月より前を全部

    # --- ③ 対象月（テスト月）の内訳 ---
    target_qs = (
        Transaction.objects
        .exclude(source_file="")
        .exclude(category__isnull=True)
        .exclude(exclude_q)
        .filter(source_file__startswith=yyyymm)  # 同月ファイル全部拾う
    )

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

    total_all = int(target_qs.aggregate(s=Sum("amount"))["s"] or 0)

    # --- ④ 学習期間（過去月）の内訳（★追加） ---
    train_cat_rows = []
    train_shop_rows = []
    train_total_all = 0
    train_month_totals = []

    if train_months:
        # 学習期間に該当する source_file を拾う（startswith で "YYYYMM" をまとめて拾う）
        # OR が多くなりすぎるのを避けたいなら、件数が増えた時に別アプローチにする
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

        # 学習期間：月ごとの合計（seriesと同じ値を並べる）
        for mo in train_months:
            train_month_totals.append({
                "month": mo,
                "total": int(month_totals.get(mo, 0)),
            })

    # --- ⑤ render ---
    html = render_to_string(
        "account/_prediction_breakdown.html",
        {
            "yyyymm": yyyymm,
            "exclude_keywords": exclude_keywords,

            # 対象月（テスト月）
            "total_all": total_all,
            "cat_rows": cat_rows,
            "shop_rows": shop_rows,

            # 学習期間（過去月）
            "train_months": train_months,
            "train_total_all": train_total_all,
            "train_cat_rows": train_cat_rows,
            "train_shop_rows": train_shop_rows,
            "train_month_totals": train_month_totals,

            "not_found": False,
        },
        request=request
    )
    return HttpResponse(html)
