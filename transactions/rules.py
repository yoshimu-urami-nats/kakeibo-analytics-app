# transactions/rules.py
import re
import unicodedata
from typing import Optional

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
