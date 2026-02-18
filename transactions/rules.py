# transactions/rules.py
import re
import unicodedata
from typing import Optional
from datetime import date

def _norm(s: str) -> str:
    """表記ゆれ吸収: 全半角統一 + 大文字化 + 空白を1個に"""
    s = s or ""
    s = unicodedata.normalize("NFKC", s)
    s = s.upper()
    s = re.sub(r"\s+", " ", s).strip()
    return s

# ここは「カテゴリ名」と「キーワード」をセットで持つ
SHOP_RULES = {
    "水道": ["東京都水道局"],
    "電気": ["LOOOP", "Loooopでんき"],  # 表記ゆれは_normで吸収される
    "ガス": ["エルピオ"],
    "インターネット": ["東京ベイネットワーク"],

    "食品・日用品": [
        "ライフ", "まいばすけっと", "オーケー",
        "NEWDAYS", "ファミリーマート", "セブン", "ローソン",
        "セリア", "アトレ亀戸", "KAMEIDO CLOCK", "コーナン",
        "ココカラファイン", "マツモトキヨシ", "スギ薬局",
        "カルディ", "シャトレーゼ", "おかしのまちおか", "ミスタードーナツ",
    ],

    "外食": [
        "雛鮨", "インド", "マクドナルド", "大戸屋", "吉野家",
        "笑縁食堂", "ママクック", "パスタママ",
    ],

    "娯楽": [
        "クックパッド", "DMM", "GOOGLE PLAY JAPAN", "ニンテンドー",
        "STEAMGAMES",
    ],

    "医療": ["亀戸駅前薬局", "錦糸町皮膚科内科クリニック"],
    "衣服・美容": ["ユニクロ"],
    "教養": ["APPLE COM BILL"],
    "その他": ["ソフトバンクM"],
}

UNCLASSIFIABLE = ["AMAZON.CO.JP", "ＡＭＡＺＯＮ．ＣＯ．ＪＰ"]

def guess_category(shop: str) -> Optional[str]:
    """店名からカテゴリ名（Category.nameと一致する文字列）を返す。見つからなければNone。"""
    shop_n = _norm(shop)

    # Amazonは“分類不可能”扱い（= Noneで返す）
    for bad in UNCLASSIFIABLE:
        if _norm(bad) in shop_n:
            return None

    for category_name, keywords in SHOP_RULES.items():
        for kw in keywords:
            if _norm(kw) in shop_n:
                return category_name

    return None


# ルール：店名に「これ」が含まれてたらこのメンバー
MEMBER_RULES = {
    "な": [
        "ＧＯＯＧＬＥ　ＰＬＡＹ　ＪＡＰＡＮ",
        "ＡＰＰＬＥ　ＣＯＭ　ＢＩＬＬ",
    ],
    "ゆ": [
        "笑縁食堂",
        "ママクック",
        "パスタママ",
        "錦糸町皮膚科内科クリニック",
        "ソフトバンクＭ",
    ],
    "共有": [
        "東京都水道局",
        "Ｌｏｏｏｐでんき",
        "エルピオ",
        "東京ベイネットワーク",
        "ライフ",
        "まいばすけっと",
        "オーケー",
        "セリア",
        "アトレ亀戸",
        "ＫＡＭＥＩＤＯ  ＣＬＯＣＫ",
        "コーナン",
        "ココカラファイン",
        "マツモトキヨシ",
        "スギ薬局",
        "カルディ",
        "シャトレーゼ",
        "おかしのまちおか",
        "ミスタードーナツ",
        "雛鮨",
        "インド",
        "マクドナルド",
        "クックパッド",
        "ＤＭＭ",
    ],
}

# 分類しない（Noneで返す）
MEMBER_UNCLASSIFIABLE = [
    "ＡＭＡＺＯＮ．ＣＯ．ＪＰ",
    "ニンテンドー",
    "STEAMGAMES",
    "ユニクロ",
]

# 条件分岐：土日なら共有、平日ならゆ（対象店）
WEEKEND_SHARED_WEEKDAY_YU = [
    "ＮｅｗＤａｙｓ",
    "ファミリーマート",
    "セブン",
    "ローソン",
    "大戸屋",
    "吉野家",
]

DERMA_CLINIC = "錦糸町皮膚科内科クリニック"
DERMA_PHARMACY = "亀戸駅前薬局"


def is_derm_clinic(shop: str) -> bool:
    """店名が皮膚科クリニックか（表記ゆれ吸収込み）"""
    return _norm(DERMA_CLINIC) in _norm(shop)

def _contains_any_norm(text: str, keywords: list[str]) -> bool:
    """text と keywords を _norm して部分一致判定"""
    t = _norm(text)
    return any(_norm(k) in t for k in keywords)


def guess_member(shop: str, d: date, derma_dates: set[date] | None = None) -> str | None:
    """
    shop: CSVの店名
    d: 日付
    derma_dates: 「皮膚科が同日にある日付」の集合（views側で作って渡す）
    """
    shop = (shop or "").strip()

    # まず「分類しない」(None)
    if _contains_any_norm(shop, MEMBER_UNCLASSIFIABLE):
        return None

    # 皮膚科ルール（薬局だけ特例）
    if _norm(DERMA_PHARMACY) in _norm(shop):
        if derma_dates and d in derma_dates:
            return "ゆ"
        return "な"

    # 土日/平日で分岐する店
    if _contains_any_norm(shop, WEEKEND_SHARED_WEEKDAY_YU):
        # weekday(): 月0 .. 日6
        is_weekend = d.weekday() >= 5
        return "共有" if is_weekend else "ゆ"

    # ふつうの固定ルール
    for member_name, keywords in MEMBER_RULES.items():
        if _contains_any_norm(shop, keywords):
            return member_name

    return None