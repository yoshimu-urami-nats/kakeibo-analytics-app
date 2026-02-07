# transactions/management/commands/import_past_csv.py
from __future__ import annotations

import csv
import re
from pathlib import Path
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from transactions.models import Transaction, Category, Member


# --- CSVの列名（日本語そのまま） ---
COL_DATE = "日付"
COL_SHOP = "店名・サービス名"
COL_AMOUNT = "金額"
COL_MEMBER = "メンバー"
COL_CATEGORY = "カテゴリ"
COL_SOURCE = "ファイル名"
COL_CLOSED = "確定済みか"


def parse_date(s: str | None):
    if not s:
        return None
    s = str(s).strip()
    for fmt in ("%Y/%m/%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    raise ValueError(f"日付が解釈できない: {s!r}")


def parse_amount(s: str | None) -> int:
    if s is None:
        raise ValueError("金額が空")
    s = str(s).strip()
    # "¥3,000" "3,000" "3000" "-120" などを許容
    m = re.search(r"-?\d[\d,]*", s)
    if not m:
        raise ValueError(f"金額が解釈できない: {s!r}")
    return int(m.group().replace(",", ""))


def parse_bool(s: str | None) -> bool:
    if s is None:
        return False
    s = str(s).strip().lower()
    return s in ("true", "1", "t", "yes", "y", "済", "確定")


class Command(BaseCommand):
    help = "過去CSV（202412-202601など）を一括インポートする（今回限り用）"

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_path",
            nargs="?",
            default="202412-202601.csv",
            help="取り込みCSVのパス（デフォルト: 202412-202601.csv）",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="DBには書かず、件数だけ確認する",
        )

    def handle(self, *args, **options):
        csv_path = Path(options["csv_path"])
        dry_run = options["dry_run"]

        if not csv_path.exists():
            raise CommandError(f"CSVが見つからない: {csv_path}")

        # Excel由来の文字コードにも耐えるため、まず utf-8-sig → ダメなら cp932
        try_encodings = ["utf-8-sig", "utf-8", "cp932"]

        text = None
        last_err = None
        for enc in try_encodings:
            try:
                text = csv_path.read_text(encoding=enc, errors="strict")
                break
            except Exception as e:
                last_err = e
        if text is None:
            raise CommandError(f"CSVが読めない（encoding試行失敗）: {last_err}")

        reader = csv.DictReader(text.splitlines())
        if not reader.fieldnames:
            raise CommandError("CSVヘッダが読めない")

        need = {COL_DATE, COL_SHOP, COL_AMOUNT, COL_MEMBER, COL_CATEGORY, COL_SOURCE, COL_CLOSED}
        missing = need - set(reader.fieldnames)
        if missing:
            raise CommandError(f"CSVに必要な列がない: {sorted(missing)} / headers={reader.fieldnames}")

        rows = list(reader)
        self.stdout.write(self.style.SUCCESS(f"CSV rows: {len(rows)}"))

        # 既存マスタをキャッシュ
        cat_map = {c.name: c for c in Category.objects.all()}
        mem_map = {m.name: m for m in Member.objects.all()}

        to_create: list[Transaction] = []

        created = 0
        skipped = 0
        errors = 0
        src_set = set()

        for idx, r in enumerate(rows, start=2):
            try:
                d = parse_date(r.get(COL_DATE))
                shop = (r.get(COL_SHOP) or "").strip()
                amt = parse_amount(r.get(COL_AMOUNT))
                mem_name = (r.get(COL_MEMBER) or "").strip()
                cat_name = (r.get(COL_CATEGORY) or "").strip()
                src = (r.get(COL_SOURCE) or "").strip()
                closed = parse_bool(r.get(COL_CLOSED))

                src_set.add(src)

                # 必須項目が欠けてる行だけスキップ（=データとして成立しない）
                # ※重複判定によるスキップはしない（同日同額は普通にありえるため）
                if not (d and shop and src):
                    skipped += 1
                    if skipped <= 20:
                        self.stdout.write(self.style.WARNING(f"SKIP(empty) line={idx}: {r!r}"))
                    continue

                # Category / Member はなければ作る
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
                        memo="",  # CSVに無いので空
                    )
                )
                created += 1

            except Exception as e:
                errors += 1
                # 文字化けしても落ちないように repr で出す
                self.stdout.write(self.style.WARNING(f"ROW ERROR line={idx}: {e!r}"))
                continue

        self.stdout.write(f"作成予定: {created} / スキップ: {skipped} / エラー: {errors}")
        self.stdout.write(f"source_file一覧: {sorted(src_set)}")

        if dry_run:
            self.stdout.write(self.style.WARNING("dry-run のためDBへは書き込みません"))
            return

        with transaction.atomic():
            Transaction.objects.bulk_create(to_create, batch_size=1000)

        self.stdout.write(self.style.SUCCESS(f"INSERT完了: {len(to_create)} 件"))
