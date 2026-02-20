# account/views.py
import re
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum, Q
from transactions.models import Transaction
from statistics import median
from django.http import HttpResponse
from django.template.loader import render_to_string
from account.utils.date_utils import yyyymm_key, yyyymm_label
from account.utils.stats_utils import percentile, zone_label
from account.services.prediction_service import run_prediction
from account.services.prediction_service import build_monthly_series
from account.services.eda_service import build_eda_context
from account.services.zones_service import build_zones_context


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

    # --- ② まず「Predictionで使ってる月次系列」を同条件で作る（service版） ---
    series, month_totals = build_monthly_series(exclude_keywords)
    months_sorted = [d["billing_month"] for d in series]

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
        .filter(source_file__startswith=yyyymm)
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

    # --- ④ 学習期間（過去月）の内訳 ---
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
