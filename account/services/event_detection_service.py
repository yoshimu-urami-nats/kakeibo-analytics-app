# account/services/event_detection_service.py
"""
Phase1: イベント判定（ルールベース）→ 月タグ付け → 最新月カード

- 既存の要素（z_scores / backtests）を使って、まずは「月次イベントっぽさ」をタグ化する
- APE（予測誤差）は backtest が存在する月だけ計算できる
  → 最新月など、まだ検証できない月は「未検証」として扱う

ロードマップ Phase1（高額単発/上振れ/カテゴリ偏り…）のうち、
まずは「月次上振れ（Z）」と「誤差（APE）」のクロス分類をタグの土台にする。
（高額単発/カテゴリ偏りは Phase1.5〜2 で拡張しやすい形にしておく）
"""

from __future__ import annotations

from typing import Any
from django.db.models import Q
from django.db.models import Max
from transactions.models import Transaction

def _detect_high_single_spike(
    *,
    yyyymm: str,
    month_total: int,
    exclude_keywords: list[str],
    # 単一明細（1件）向け
    single_amount_th: int = 40000,
    single_ratio_th: float = 0.15,
) -> dict[str, Any]:
    """
    高額単発判定（Phase1.5）：
      ・単一明細（1件）が
          single_amount_th 円以上
          かつ 月合計の single_ratio_th 以上
    """
    if month_total <= 0:
        return {"is_spike": False, "amount": None, "shop": None}

    exclude_q = Q()
    for kw in exclude_keywords:
        exclude_q |= Q(category__name__icontains=kw)

    base_qs = (
        Transaction.objects
        .exclude(source_file="")
        .exclude(category__isnull=True)
        .exclude(exclude_q)
        .filter(source_file__startswith=yyyymm)
    )

    # 単一明細（1件）の最大額（同時にshopも取る）
    max_row = (
        base_qs
        .order_by("-amount")
        .values("amount", "shop")
        .first()
    )

    if not max_row:
        return {"is_spike": False, "amount": None, "shop": None}

    max_amount = int(max_row["amount"] or 0)
    max_shop = (max_row.get("shop") or "").strip() or "（不明）"

    if max_amount >= single_amount_th and (max_amount / month_total) >= single_ratio_th:
        return {"is_spike": True, "amount": max_amount, "shop": max_shop}
    
    return {"is_spike": False, "amount": max_amount, "shop": max_shop}

def _label_cross(
    *,
    z: float,
    ape_percent: float | None,
    z_th: float = 2.0,
    ape_th: float = 50.0,
) -> str:
    """
    既存のクロス分類（Z × %誤差）を踏襲。
    - ape_percent が None の月（未検証）は、Zだけで暫定タグを返す。
    """
    if ape_percent is None:
        # まだ予測誤差を評価できない月（例：最新月）
        if abs(z) >= z_th:
            return "月次上振れ/下振れ（未検証）"
        return "通常（未検証）"

    # 検証できる月は、4象限でラベリング
    if abs(z) >= z_th and ape_percent >= ape_th:
        return "強イベント"
    if abs(z) >= z_th and ape_percent < ape_th:
        return "イベント（予測成功）"
    if abs(z) < z_th and ape_percent >= ape_th:
        return "予測課題"
    return "通常"


def build_event_detection_data(
    *,
    series: list[dict[str, Any]],
    backtests: list[dict[str, Any]],
    z_scores: list[dict[str, Any]],
    exclude_keywords: list[str],
    month_totals: dict[str, int],
    z_th: float = 2.0,
    ape_th: float = 50.0,
    cross_top_n: int = 6,
) -> dict[str, Any]:
    """
    return:
      - cross_rows: 既存の「Z×誤差」テーブル用（全月分）
      - cross_top: 優先順で上位N件（表示用）
      - month_tags: { "YYYYMM": "タグ" }（全月分）
      - latest_judgement: 最新月カード表示用 dict
    """

    # --- APE（誤差）を月→ape% にマップ（Noneは Noneのまま保持） ---
    ape_map: dict[str, float | None] = {}
    for b in backtests:
        m = b.get("month")
        if not m:
            continue
        ape_val = b.get("ape")
        ape_map[m] = float(ape_val) if ape_val is not None else None

    # --- cross_rows（全月） ---
    cross_rows: list[dict[str, Any]] = []
    for r in z_scores:
        m = str(r["month"])
        z = float(r["z"])
        ape_p = ape_map.get(m)  # None なら未検証（月 or 実績0など）
        label = _label_cross(z=z, ape_percent=ape_p, z_th=z_th, ape_th=ape_th)

        # --- 高額単発チェック ---
        spike = _detect_high_single_spike(
            yyyymm=m,
            month_total=month_totals.get(m, 0),
            exclude_keywords=exclude_keywords,
        )

        is_spike = bool(spike.get("is_spike"))
        if is_spike:
            amt = spike.get("amount")
            shop = spike.get("shop")
            if amt is not None:
                label = f"{label} + 高額単発（¥{amt:,} / {shop}）"
            else:
                label = f"{label} + 高額単発（{shop}）"

        cross_rows.append(
            {
                "month": m,
                "total": int(r["total"]),
                "z": round(z, 2),
                "ape": (round(float(ape_p), 1) if ape_p is not None else None),
                "label": label,
                "has_ape": (ape_p is not None),
                "is_spike": is_spike,
                "spike_amount": spike.get("amount"),
                "spike_shop": spike.get("shop"),
            }
        )

    # 優先度（現行メモの並びを踏襲しつつ、未検証は最後寄せ）
    priority = {
        "強イベント": 0,
        "予測課題": 1,
        "イベント（予測成功）": 2,
        "月次上振れ/下振れ（未検証）": 3,
        "通常": 4,
        "通常（未検証）": 5,
    }

    def _base_label(label: str) -> str:
        # "イベント（予測成功） + 高額単発" -> "イベント（予測成功）"
        return label.split(" + ")[0].strip() if label else ""

    cross_rows_sorted = sorted(
        cross_rows,
        key=lambda x: (
            priority.get(_base_label(x["label"]), 9),
            -abs(float(x["z"])),
            -(float(x["ape"]) if x["ape"] is not None else -1.0),
        ),
    )
    cross_top = cross_rows_sorted[:cross_top_n]

    # --- 全月分タグ（要求：全月分タグ付け） ---
    # ひとまず label をそのままタグにする（後で Phase1 の詳細タグへ置き換えしやすい）
    month_tags: dict[str, str] = {row["month"]: row["label"] for row in cross_rows}

    # --- 最新月カード（要求：最新月カード表示） ---
    latest_month = None
    if series:
        latest_month = str(series[-1].get("billing_month") or "")

    latest_row = None
    if latest_month:
        latest_row = next((x for x in cross_rows if x["month"] == latest_month), None)

    latest_judgement = {
        "month": latest_month,
        "tag": (latest_row["label"] if latest_row else "—"),
        "total": (latest_row["total"] if latest_row else None),
        "z": (latest_row["z"] if latest_row else None),
        "ape": (latest_row["ape"] if latest_row else None),
        "note": (
            "当月の予測誤差(APE)は、翌月以降の検証で確定します。"
            if (latest_row and latest_row["ape"] is None)
            else None
        ),
    }

    return {
        "cross_rows": cross_rows,
        "cross_top": cross_top,
        "month_tags": month_tags,
        "latest_judgement": latest_judgement,
    }