# transactions/rules.py
from datetime import date
from typing import Literal, Optional

OwnerKey = Literal["nacchan", "yuhei", "shared"]


def guess_owner(shop: str, dt: Optional[date] = None) -> Optional[OwnerKey]:
    """
    店名(＋必要なら日付)から、だいたい誰の出費かを推定する。
    - 戻り値:
        "nacchan" / "yuhei" / "shared" / None(判定不能)
    """
    if not shop:
        return None

    # 大文字に揃えたもの（英字用）
    shop_upper = shop.upper()

    # ------------- 食費・スーパー関係＝共有 -------------
    supermarket_keywords = [
        "まいばすけっと",
        "ライフ",
        "オーケー",
        "ｵｰｹｰ",  # 半角対策
        "カルディ",
        "KALDI",
        "ミスタードーナツ",
        "ﾐｽﾀｰﾄﾞｰﾅﾂ",
        "シャトレーゼ",
    ]
    if any(k in shop for k in supermarket_keywords):
        return "shared"

    # ------------- 日用品関係＝共有 -------------
    daily_keywords = [
        "アトレ",
        "ｱﾄﾚ",
        "マツモトキヨシ",
        "ﾏﾂﾓﾄｷﾖｼ",
    ]
    if any(k in shop for k in daily_keywords):
        return "shared"

    # ------------- 昼食／コンビニ系 -------------
    # コンビニ全般＝ゆーへー
    convenience_keywords = [
        "セブン",
        "SEVEN",
        "ファミリーマート",
        "ﾌｧﾐﾘｰﾏｰﾄ",
        "ファミマ",
        "ﾌｧﾐﾏ",
        "ローソン",
        "LAWSON",
        "ニューデイズ",
        "NEWDAYS",
    ]
    
    # コンビニ系
    if any(k in shop for k in convenience_keywords):
        # dt が渡ってきている前提で曜日判定
        # weekday(): 0=月 … 6=日
        if dt is not None and dt.weekday() >= 5:
            return "shared"   # 土日なら「共有」
        return "yuhei"        # 平日は「ゆーへー」

    # 笑縁食堂＝ゆーへー
    if "笑縁食堂" in shop:
        return "yuhei"

    # 吉野家とかの飲食店＝平日だったら、だいたい、ゆーへー
    if "吉野家" in shop:
        if dt is not None and dt.weekday() < 5:  # 0〜4 が平日
            return "yuhei"
        # 休日や日付不明のときは判定保留
        return None

    # ------------- 病院関係 -------------
    # 皮膚科＝ゆーへー（病院名は実データに合わせて増やす）
    if "皮膚科" in shop:
        return "yuhei"

    # 亀戸駅前薬局
    if "亀戸駅前薬局" in shop:
        # TODO: 本当は「同じ日の皮膚科があるか」を見たいが、
        # そこまでやるとややこしいので、まずはゆーへー寄りに判定。
        return "yuhei"

    # ------------- 光熱費＝共有 -------------
    utility_keywords = [
        "東京ベイネットワーク",
        "東京都水道局",
    ]
    if any(k in shop for k in utility_keywords):
        return "shared"

    # ------------- 雑費 -------------
    if "GOOGLE PLAY JAPAN" in shop_upper or "ＧＯＯＧＬＥ　ＰＬＡＹ　ＪＡＰＡＮ" in shop:
        return "nacchan"

    if "クックパッド" in shop or "COOKPAD" in shop_upper:
        return "shared"

    if "ソフトバンク" in shop or "SOFTBANK" in shop_upper:
        return "yuhei"

    # ------------- 娯楽等 -------------
    # Amazon / ユニクロは「どちらか不明（人間判断）」なので None を返す
    if "AMAZON" in shop_upper or "ＡＭＡＺＯＮ" in shop:
        return None

    if "ユニクロ" in shop or "UNIQLO" in shop_upper:
        return None

    if "ＴＯＨＯシネマズ" in shop or "TOHOシネマズ" in shop or "TOHO CINEMAS" in shop_upper:
        return "shared"

    if "大丸" in shop:
        return "shared"

    if "APPLE" in shop_upper or "ＡＰＰＬＥ" in shop:
        return "nacchan"

    # ------------- ペット出費系（TODO） -------------
    # ここはこれから詰める。とりあえず判定保留。
    # if "ペット" in shop or "動物病院" in shop: ...
    #     return "shared"

    # どれにも当てはまらなかったら人間判断
    return None
