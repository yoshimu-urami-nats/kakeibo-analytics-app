# demo_generate.py
from __future__ import annotations

import csv
import random
from dataclasses import dataclass
from datetime import date
from pathlib import Path


# =========================
# 設定（ここだけ触ればOK）
# =========================
MONTHS = 6              # 何か月分作る？
ROWS_PER_MONTH = 100    # 1か月あたり何行？
START_YEAR = 2025
START_MONTH = 4         # 2025-04 から6か月分 → 2025-04..2025-09
SEED = 42               # 生成を再現可能にする（同じデータが出る）

OUT_PATH = Path("data_demo") / "demo_transactions.csv"


# =========================
# データ定義
# =========================
MEMBERS = ["Aさん", "Bさん", "共有"]


@dataclass(frozen=True)
class CategorySpec:
    name: str
    # そのカテゴリの出現割合（全体の比率）
    weight: float
    # 金額レンジ（円）
    amount_min: int
    amount_max: int
    # 店名候補
    merchants: list[str]
    # メンバー割合（A/B/共有）
    member_weights: dict[str, float]
    # memo候補（空多め）
    memos: list[str]


CATEGORIES: list[CategorySpec] = [
    CategorySpec(
        name="食費（スーパー）",
        weight=0.22,
        amount_min=1200,
        amount_max=9000,
        merchants=["オーケー", "ライフ", "まいばすけっと", "西友", "業務スーパー"],
        member_weights={"Aさん": 0.35, "Bさん": 0.35, "共有": 0.30},
        memos=["", "", "", "まとめ買い", "食品・日用品"],
    ),
    CategorySpec(
        name="食費（コンビニ）",
        weight=0.18,
        amount_min=110,
        amount_max=1600,
        merchants=["セブン-イレブン", "ローソン", "ファミリーマート", "NewDays"],
        member_weights={"Aさん": 0.42, "Bさん": 0.42, "共有": 0.16},
        memos=["", "", "", "おやつ", "飲み物"],
    ),
    CategorySpec(
        name="外食",
        weight=0.10,
        amount_min=600,
        amount_max=6000,
        merchants=["マクドナルド", "吉野家", "ミスタードーナツ", "サイゼリヤ", "コメダ珈琲店"],
        member_weights={"Aさん": 0.45, "Bさん": 0.45, "共有": 0.10},
        memos=["", "", "ランチ", "夕食", "カフェ"],
    ),
    CategorySpec(
        name="日用品",
        weight=0.12,
        amount_min=300,
        amount_max=7000,
        merchants=["マツモトキヨシ", "ウエルシア", "ダイソー", "無印良品", "アトレ"],
        member_weights={"Aさん": 0.30, "Bさん": 0.30, "共有": 0.40},
        memos=["", "", "洗剤など", "消耗品", "日用品まとめ"],
    ),
    CategorySpec(
        name="光熱費",
        weight=0.06,
        amount_min=1800,
        amount_max=15000,
        merchants=["東京都水道局", "Looopでんき", "東京ガス"],
        member_weights={"Aさん": 0.05, "Bさん": 0.05, "共有": 0.90},
        memos=["水道料金", "電気料金", "ガス料金", ""],
    ),
    CategorySpec(
        name="通信",
        weight=0.05,
        amount_min=500,
        amount_max=12000,
        merchants=["ソフトバンク", "楽天モバイル", "APPLE.COM BILL", "GOOGLE PLAY JAPAN"],
        member_weights={"Aさん": 0.10, "Bさん": 0.10, "共有": 0.80},
        memos=["月額", "サブスク", "", ""],
    ),
    CategorySpec(
        name="医療・薬",
        weight=0.05,
        amount_min=300,
        amount_max=6000,
        merchants=["亀戸駅前薬局", "皮膚科クリニック", "内科クリニック", "ドラッグストア"],
        member_weights={"Aさん": 0.48, "Bさん": 0.48, "共有": 0.04},
        memos=["", "", "処方", "診察", ""],
    ),
    CategorySpec(
        name="交通",
        weight=0.06,
        amount_min=150,
        amount_max=2500,
        merchants=["PASMO", "JR東日本", "都営交通", "タクシー"],
        member_weights={"Aさん": 0.45, "Bさん": 0.45, "共有": 0.10},
        memos=["", "", "移動", ""],
    ),
    CategorySpec(
        name="趣味・娯楽",
        weight=0.10,
        amount_min=300,
        amount_max=9000,
        merchants=["アニメイト", "DMM", "Steam", "書泉ブックタワー", "TOHOシネマズ"],
        member_weights={"Aさん": 0.48, "Bさん": 0.48, "共有": 0.04},
        memos=["", "", "映画", "書籍", "ゲーム"],
    ),
    CategorySpec(
        name="その他",
        weight=0.06,
        amount_min=200,
        amount_max=12000,
        merchants=["Amazon.co.jp", "楽天市場", "メルカリ", "ヤフーショッピング"],
        member_weights={"Aさん": 0.40, "Bさん": 0.40, "共有": 0.20},
        memos=["", "", "通販", "備品", ""],
    ),
]


# =========================
# ユーティリティ
# =========================
def month_range(start_year: int, start_month: int, months: int) -> list[tuple[int, int]]:
    y, m = start_year, start_month
    out = []
    for _ in range(months):
        out.append((y, m))
        m += 1
        if m == 13:
            y += 1
            m = 1
    return out


def weighted_choice(items: list, weights: list[float]):
    return random.choices(items, weights=weights, k=1)[0]


def pick_member(member_weights: dict[str, float]) -> str:
    names = list(member_weights.keys())
    w = list(member_weights.values())
    return weighted_choice(names, w)


def clamp_amount(x: int) -> int:
    return max(0, x)


def maybe_refund(amount: int) -> int:
    """
    返品（マイナス）を少し混ぜる。
    全体の約1%程度で、-amount にする。
    """
    if random.random() < 0.01 and amount > 0:
        return -amount
    return amount


# =========================
# 生成本体
# =========================
def generate_demo_csv(out_path: Path) -> Path:
    random.seed(SEED)

    out_path.parent.mkdir(parents=True, exist_ok=True)

    # カテゴリ選択のためのweights
    cat_weights = [c.weight for c in CATEGORIES]

    rows = []
    current_id = 1

    for (y, m) in month_range(START_YEAR, START_MONTH, MONTHS):
        for _ in range(ROWS_PER_MONTH):
            cat = weighted_choice(CATEGORIES, cat_weights)

            # 日付：1〜28日に散らす（クレカ明細っぽく）
            day = random.randint(1, 28)
            d = date(y, m, day).isoformat()

            merchant = random.choice(cat.merchants)

            amount = random.randint(cat.amount_min, cat.amount_max)
            # 端数っぽさ（10円単位に寄せる）
            amount = int(round(amount / 10.0) * 10)
            amount = maybe_refund(amount)

            memo = random.choice(cat.memos)
            if amount < 0:
                memo = "返品" if memo == "" else f"{memo}（返品）"

            member_name = pick_member(cat.member_weights)

            rows.append(
                {
                    "id": current_id,
                    "date": d,
                    "merchant": merchant,
                    "amount": amount,
                    "memo": memo,
                    "member_name": member_name,
                    "category_name": cat.name,
                }
            )
            current_id += 1

    # 日付順に並べ替え（見やすい）
    rows.sort(key=lambda r: (r["date"], r["id"]))

    # id振り直し（並べ替え後に連番）
    for i, r in enumerate(rows, start=1):
        r["id"] = i

    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["id", "date", "merchant", "amount", "memo", "member_name", "category_name"],
        )
        writer.writeheader()
        writer.writerows(rows)

    return out_path


if __name__ == "__main__":
    path = generate_demo_csv(OUT_PATH)
    print(f"Generated: {path} (months={MONTHS}, rows_per_month={ROWS_PER_MONTH}, total={MONTHS * ROWS_PER_MONTH})")
