# account/utils/date_utils.py
"""
utils：汎用関数置き場（views/servicesのどこからでも使える）
- date_utils：日付/年月(YYYYMM)の小物関数
"""

import re
from datetime import datetime

def yyyymm_key(s: str) -> int:
    """source_file から YYYYMM を抜いて、ソート用の数値にする"""
    m = re.search(r"(\d{6})", s or "")
    return int(m.group(1)) if m else -1

def yyyymm_label(s: str) -> str:
    """表示用に YYYYMM を返す（取れなければ元文字列）"""
    m = re.search(r"(\d{6})", s or "")
    return m.group(1) if m else (s or "")

def yyyymm_add1(yyyymm: str) -> str:
    """YYYYMM を 1か月進めた YYYYMM を返す"""
    dt = datetime.strptime(yyyymm, "%Y%m")
    y = dt.year + (1 if dt.month == 12 else 0)
    m = 1 if dt.month == 12 else dt.month + 1
    return f"{y:04d}{m:02d}"
