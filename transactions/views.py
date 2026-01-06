# transactions/views.py
import csv
import io
from datetime import datetime, date

from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .forms import CSVUploadForm
from .models import Transaction,Category
from .rules import guess_category


def _parse_date(s: str) -> date:
    s = (s or "").strip()
    # 例: 2025-11-30 / 2025/11/30 どっちでもOKにする
    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    raise ValueError(f"日付形式が不正: {s}")


def _parse_amount(s: str) -> int:
    s = (s or "").strip()
    s = s.replace(",", "").replace("円", "")
    return int(s)


def _first_day_of_month(d: date) -> date:
    return d.replace(day=1)

def _decode_csv_bytes(b: bytes) -> str:
    """
    CSVの文字コードが UTF-8 / UTF-8(BOM付き) / CP932(Shift_JIS系) どれでも読めるようにする
    """
    for enc in ("utf-8-sig", "utf-8", "cp932", "shift_jis"):
        try:
            return b.decode(enc)
        except UnicodeDecodeError:
            continue
    # 最後の手段：読めない文字は落として読み進める（ログ用途）
    return b.decode("cp932", errors="replace")


@require_http_methods(["GET", "POST"])
def transaction_list(request):
    if request.method == "POST":
        form = CSVUploadForm(request.POST, request.FILES)
        if not form.is_valid():
            messages.error(request, "CSVファイルが選択されてないか、形式が不正っぽい…")
            return redirect("transactions:list")

        f = form.cleaned_data["csv_file"]
        source_file = getattr(f, "name", "")  # 例: 202601.csv

        created = 0
        skipped = 0
        errors = 0

        # 先にカテゴリを全部辞書にしておく（name -> Category）
        category_map = {c.name: c for c in Category.objects.all()}

        # まとめて作る用
        to_create = []

        try:
            f.seek(0)
            raw = f.read()

            text = _decode_csv_bytes(raw)
            reader = csv.reader(io.StringIO(text))

            for row_index, row in enumerate(reader, start=1):
                # 本番仕様：1行目不要 → 無条件で飛ばす
                if row_index == 1:
                    continue

                # 空行はスキップ
                if not row or all((c or "").strip() == "" for c in row):
                    skipped += 1
                    continue

                # 左から3列だけ使う（足りなければスキップ）
                if len(row) < 3:
                    skipped += 1
                    continue

                date_str = row[0].strip()
                shop = row[1].strip()
                amount_str = row[2].strip()

                if not date_str or not shop or not amount_str:
                    skipped += 1
                    continue

                try:
                    d = _parse_date(date_str)
                    amount = _parse_amount(amount_str)

                    # カテゴリ自動推定（店名から）
                    category_name = guess_category(shop)  # ← ここ重要
                    category_obj = category_map.get(category_name) if category_name else None

                    to_create.append(
                        Transaction(
                            date=d,
                            shop=shop,
                            amount=amount,
                            memo="",
                            source_file=source_file,
                            category=category_obj,
                            member=None,
                            is_closed=False,
                        )
                    )
                    

                except Exception as e:
                    errors += 1
                    print("IMPORT ERROR:", row_index, row, repr(e))

        except Exception as e:
            messages.error(request, f"CSVの読み込みに失敗した: {e}")
            return redirect("transactions:list")

        # まとめてINSERT
        if to_create:
            Transaction.objects.bulk_create(to_create, batch_size=1000)

        created = len(to_create)

    
        messages.success(
            request,
            f"CSV取り込み完了！ 追加 {created} / スキップ {skipped} / エラー {errors}"
        )
        return redirect("transactions:list")

    # GET
    form = CSVUploadForm()
    transactions = Transaction.objects.all()
    return render(
        request,
        "transactions/transaction_list.html",
        {"transactions": transactions, "upload_form": form},
    )
