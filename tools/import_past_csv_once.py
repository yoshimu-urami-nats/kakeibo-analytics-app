# tools/import_past_csv_once.py
import csv
import re
from pathlib import Path
from datetime import datetime

from django.db import transaction
from transactions.models import Transaction, Category, Member


CSV_PATH = Path("202412-202601.csv")  # プロジェクト直下に置いてる想定
# CSV_PATH = Path(r"C:\GitHub_Nats\kakeibo-analytics-app\202412-202601.csv")


def normalize_key(s: str) -> str:
    # 余計な空白と中黒の揺れを吸収（例: 店名・サービス名 / 店名サービス名 どっちでもOK）
    return (s or "").strip().replace(" ", "").replace("　", "").replace("・", "")


def decode_csv_bytes(b: bytes) -> str:
    for enc in ("utf-8-sig", "utf-8", "cp932", "shift_jis"):
        try:
            return b.decode(enc)
        except UnicodeDecodeError:
            continue
    return b.decode("cp932", errors="replace")


def parse_date(s: str):
    s = (s or "").strip()
    for fmt in ("%Y/%m/%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    raise ValueError(f"日付形式が不正: {s}")


def parse_amount(s: str) -> int:
    s = (s or "").strip()
    s = s.replace(",", "").replace("¥", "").replace("￥", "").replace("円", "").strip()
    m = re.search(r"-?\d+", s)
    if not m:
        raise ValueError(f"金額が不正: {s}")
    return int(m.group())


def parse_bool(s: str) -> bool:
    s = (s or "").strip().lower()
    return s in ("true", "1", "yes", "y", "t", "済", "確定")


def main():
    raw = CSV_PATH.read_bytes()
    text = decode_csv_bytes(raw)

    reader = csv.DictReader(text.splitlines())
    print("CSV headers:", reader.fieldnames)

    rows = list(reader)
    print("rows:", len(rows))
    if not rows:
        print("CSVが空っぽっぽい")
        return

    # ヘッダ正規化マップ
    header_map = {normalize_key(h): h for h in (reader.fieldnames or [])}

    def get(row, want_norm_key: str):
        real_key = header_map.get(want_norm_key)
        return row.get(real_key) if real_key else None

    # 欲しいキー（正規化済み）
    K_DATE   = normalize_key("日付")
    K_SHOP   = normalize_key("店名・サービス名")
    K_AMOUNT = normalize_key("金額")
    K_MEMBER = normalize_key("メンバー")
    K_CAT    = normalize_key("カテゴリ")
    K_SRC    = normalize_key("ファイル名")
    K_CLOSED = normalize_key("確定済みか")

    # まず1行目を見せる（ここで店名がNoneなら列名ズレ確定）
    print("sample row:", {
        "日付": get(rows[0], K_DATE),
        "店名": get(rows[0], K_SHOP),
        "金額": get(rows[0], K_AMOUNT),
        "ファイル名": get(rows[0], K_SRC),
    })

    cat_map = {c.name: c for c in Category.objects.all()}
    mem_map = {m.name: m for m in Member.objects.all()}

    to_create = []
    seen = set()  # CSV内重複だけ弾く
    errors = 0
    skipped = 0

    for i, r in enumerate(rows, start=2):
        try:
            d = parse_date(get(r, K_DATE))
            shop = (get(r, K_SHOP) or "").strip()
            amt = parse_amount(get(r, K_AMOUNT))
            mem_name = (get(r, K_MEMBER) or "").strip()
            cat_name = (get(r, K_CAT) or "").strip()
            src = (get(r, K_SRC) or "").strip()
            closed = parse_bool(get(r, K_CLOSED))

            if not (d and shop and src):
                skipped += 1
                continue

            key = (d, shop, amt, src)
            if key in seen:
                skipped += 1
                continue
            seen.add(key)

            cat_obj = None
            if cat_name:
                cat_obj = cat_map.get(cat_name)
                if not cat_obj:
                    cat_obj = Category.objects.create(name=cat_name)
                    cat_map[cat_name] = cat_obj

            mem_obj = None
            if mem_name:
                mem_obj = mem_map.get(mem_name)
                if not mem_obj:
                    mem_obj = Member.objects.create(name=mem_name)
                    mem_map[mem_name] = mem_obj

            to_create.append(
                Transaction(
                    date=d,
                    shop=shop,
                    amount=amt,
                    member=mem_obj,
                    category=cat_obj,
                    source_file=src,
                    is_closed=closed,
                    memo="",
                )
            )

        except Exception as e:
            errors += 1
            print("ROW ERROR:", i, e)

    with transaction.atomic():
        Transaction.objects.bulk_create(to_create, batch_size=1000)

    print(f"追加 {len(to_create)} / スキップ {skipped} / エラー {errors}")


main()
