# transactions/management/commands/seed_transactions.py

import csv
from pathlib import Path
from datetime import datetime

from django.core.management.base import BaseCommand
from django.db import transaction

from transactions.models import Transaction, Category
from members.models import Member


def _open_text_auto(path: Path):
    """
    Excel保存のANSI(=cp932)やUTF-8-SIGなど、ありがちな文字コードを順に試す。
    """
    encodings = ["cp932", "utf-8-sig", "utf-8", "shift_jis"]
    last_err = None
    for enc in encodings:
        try:
            return path.open(mode="r", encoding=enc, newline=""), enc
        except UnicodeDecodeError as e:
            last_err = e
            continue
    raise last_err or UnicodeDecodeError("unknown", b"", 0, 1, "decode failed")


class Command(BaseCommand):
    help = "初期データCSVをTransactionにインポートする（cp932/utf-8自動対応）"

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=str, help="インポートするCSVファイルのパス")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="DBに保存せず、読み取りと変換だけ行う",
        )
        parser.add_argument(
            "--replace",
            action="store_true",
            help="CSV内のファイル名(source_file)が一致する既存データを削除してから入れ直す",
        )
        parser.add_argument(
            "--skip-errors",
            action="store_true",
            help="行エラーがあっても止めずにスキップして続行する（デフォルトは全取り消し）",
        )

    def handle(self, *args, **options):
        csv_path = Path(options["csv_path"])
        dry_run = options["dry_run"]
        replace = options["replace"]
        skip_errors = options["skip_errors"]

        if not csv_path.exists():
            self.stderr.write(self.style.ERROR(f"CSVが見つかりません: {csv_path}"))
            return

        f, used_enc = _open_text_auto(csv_path)
        self.stdout.write(f"CSVを読み込みます（encoding={used_enc}）: {csv_path}")

        # ここからDB操作：デフォルトは「1件でも失敗したら全部ロールバック」
        ctx = transaction.atomic()
        ctx.__enter__()

        created = 0
        skipped = 0
        deleted = 0

        try:
            with f:
                reader = csv.DictReader(f)

                required_cols = ["日付", "店名・サービス名", "金額", "メンバー", "カテゴリ", "ファイル名", "確定済みか"]
                missing = [c for c in required_cols if c not in (reader.fieldnames or [])]
                if missing:
                    raise ValueError(f"CSVヘッダ不足: {missing} / あるヘッダ={reader.fieldnames}")

                # replace: CSVに出てくるファイル名単位で削除→入れ直し
                if replace:
                    # まずCSV全体の source_file を収集（読み取り直すのが面倒なので一旦全行をリスト化）
                    rows = list(reader)
                    source_files = sorted({(r.get("ファイル名") or "").strip() for r in rows if (r.get("ファイル名") or "").strip()})
                    if source_files:
                        deleted = Transaction.objects.filter(source_file__in=source_files).delete()[0]

                    # 収集したrowsで処理続行
                    iterable = rows
                else:
                    iterable = reader

                for idx, row in enumerate(iterable, start=2):  # ヘッダが1行目なのでデータは2行目スタート
                    try:
                        date = datetime.strptime(row["日付"].strip(), "%Y/%m/%d").date()
                        shop = (row["店名・サービス名"] or "").strip()

                        # 金額：カンマや¥があってもOKにする
                        amount_str = (row["金額"] or "").strip().replace(",", "").replace("¥", "").replace("￥", "")
                        amount = int(amount_str)

                        member_name = (row["メンバー"] or "").strip()
                        category_name = (row["カテゴリ"] or "").strip()
                        source_file = (row["ファイル名"] or "").strip()
                        is_closed = (row["確定済みか"] or "").strip().upper() == "TRUE"

                        member = None
                        if member_name:
                            member, _ = Member.objects.get_or_create(name=member_name)

                        category = None
                        if category_name:
                            category, _ = Category.objects.get_or_create(name=category_name)

                        if dry_run:
                            continue

                        Transaction.objects.create(
                            date=date,
                            shop=shop,
                            amount=amount,
                            member=member,
                            category=category,
                            source_file=source_file,
                            is_closed=is_closed,
                        )
                        created += 1

                    except Exception as e:
                        if skip_errors:
                            skipped += 1
                            self.stderr.write(self.style.WARNING(f"[SKIP] {idx}行目: {e} / row={row}"))
                            continue
                        raise  # 1件でもエラーなら全部ロールバック（安全）

            if dry_run:
                self.stdout.write(self.style.SUCCESS("dry-run完了（DB保存なし）"))
            else:
                self.stdout.write(self.style.SUCCESS(f"インポート完了：作成 {created}件 / 削除 {deleted}件 / スキップ {skipped}件"))

            # dry-runならロールバックして終わり（DB汚さない）
            if dry_run:
                raise RuntimeError("DRY_RUN_ROLLBACK")

            ctx.__exit__(None, None, None)

        except RuntimeError as e:
            if str(e) == "DRY_RUN_ROLLBACK":
                ctx.__exit__(Exception, e, None)  # ロールバック
                return
            ctx.__exit__(type(e), e, e.__traceback__)
            raise
        except Exception as e:
            ctx.__exit__(type(e), e, e.__traceback__)
            self.stderr.write(self.style.ERROR(f"インポート失敗（全取り消し）: {e}"))
            self.stderr.write("原因行を直してから、再実行してね。")
            return
