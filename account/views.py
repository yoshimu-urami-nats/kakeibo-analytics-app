# account/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.template.loader import render_to_string
from account.services.prediction_service import run_prediction
from account.services.prediction_service import build_monthly_series
from account.services.eda_service import build_eda_context
from account.services.zones_service import build_zones_context
from account.services.prediction_breakdown_service import build_prediction_breakdown_data


def home(request):
    return render(request, "account/home.html")

@login_required
def csv_import(request):
    return render(request, "account/csv_import.html")

@login_required
def eda(request):
    context = build_eda_context(top_n_categories=8)
    return render(request, "account/eda.html", context)

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
    # 2) 比較：交際「含む」vs「除外」
    # -----------------------------
    result_include = run_prediction(base_exclude_keywords, min_train)

    # 「交際」を除外に足した版（すでに入ってたら二重にしない）
    exclude_plus_social = list(base_exclude_keywords)
    if not any("交際" in x for x in exclude_plus_social):
        exclude_plus_social.append("交際")
    result_exclude = run_prediction(exclude_plus_social, min_train)

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
        "z_scores": result_include["z_scores"],
        "anomaly_top_months": result_include["anomaly_top_months"],
        "cross_top": result_include["cross_top"],

        # 追加：比較用（2本）
        "compare_include": result_include,
        "compare_exclude": result_exclude,
    })


@login_required
def zones(request):
    context = build_zones_context()
    return render(request, "account/zones.html", context)


@login_required
def prediction_breakdown(request, yyyymm: str):

    exclude_param = (request.GET.get("exclude") or "").strip()
    if exclude_param:
        exclude_keywords = [x.strip() for x in exclude_param.split(",") if x.strip()]
    else:
        exclude_keywords = ["家具・家電"]

    # 月次系列は既存service
    series, month_totals = build_monthly_series(exclude_keywords)
    months_sorted = [d["billing_month"] for d in series]

    data = build_prediction_breakdown_data(
        yyyymm=yyyymm,
        exclude_keywords=exclude_keywords,
        months_sorted=months_sorted,
        month_totals=month_totals,
    )

    if data["not_found"]:
        html = render_to_string(
            "account/_prediction_breakdown.html",
            {**data},
            request=request
        )
        return HttpResponse(html)

    html = render_to_string(
        "account/_prediction_breakdown.html",
        data,
        request=request
    )
    return HttpResponse(html)

