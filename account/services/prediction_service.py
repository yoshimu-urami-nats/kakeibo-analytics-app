# account/services/prediction_service.py
"""
service：集計・予測の処理（DBアクセス含む）をするところ
- views から呼ばれて、計算結果（dict）を返す
- 画面(render)やrequestの扱いはしない（viewsの仕事）
"""

from django.db.models import Sum, Q
from transactions.models import Transaction

from account.utils.date_utils import yyyymm_add1
from account.utils.stats_utils import linear_regression

def build_monthly_series(exclude_keywords: list[str]) -> tuple[list[dict], dict[str, int]]:
    """
    prediction と breakdown で共通の「月次系列」を作る
    return:
      - series: [{"i":0,"billing_month":"202601","total":123}, ...]
      - month_totals: {"202601":123, ...}  （内訳側で使える）
    """
    exclude_q = Q()
    for kw in exclude_keywords:
        exclude_q |= Q(category__name__icontains=kw)

    base = (
        Transaction.objects
        .exclude(source_file="")
        .exclude(category__isnull=True)
        .exclude(exclude_q)
    )

    rows = base.values("source_file").annotate(total_amount=Sum("amount"))

    month_totals: dict[str, int] = {}
    for r in rows:
        sf = (r["source_file"] or "").strip()
        # 前提：gold配下CSVは "YYYYMM.csv" 形式（先頭6桁が請求月）
        mo = sf[:6]  # ★ファイル名先頭がYYYYMM前提
        if len(mo) != 6 or not mo.isdigit():
            continue    
        month_totals[mo] = month_totals.get(mo, 0) + int(r["total_amount"] or 0)

    months_sorted = sorted(month_totals.keys(), key=lambda m: int(m) if (m and m.isdigit()) else -1)

    series = []
    for i, mo in enumerate(months_sorted):
        series.append({"i": i, "billing_month": mo, "total": int(month_totals[mo] or 0)})

    return series, month_totals

def run_prediction(exclude_keywords: list[str], min_train: int) -> dict:
    """
    予測（全期間1本）＋ walk-forward バックテスト
    """
    series, month_totals = build_monthly_series(exclude_keywords)

    # 予測（全期間1本）
    slope = intercept = pred_next = None
    next_month = ""
    if len(series) >= 2:
        points = [(d["i"], d["total"]) for d in series]
        slope, intercept = linear_regression(points)
        if slope is not None:
            next_i = series[-1]["i"] + 1
            pred_next = int(round(slope * next_i + intercept))
            next_month = yyyymm_add1(series[-1]["billing_month"])

    # walk-forward
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
            s, b = linear_regression(pts)
            if s is None:
                continue

            pred = int(round(s * test["i"] + b))
            actual = int(test["total"])

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
        "month_totals": month_totals,
        "slope": slope,
        "intercept": intercept,
        "pred_next": pred_next,
        "next_month": next_month,
        "backtests": backtests,
        "metrics": metrics,
        "worst_months": worst_months,
    }
