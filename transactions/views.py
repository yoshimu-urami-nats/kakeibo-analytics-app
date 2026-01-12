# transactions/views.py
import csv
import io
from datetime import datetime, date

from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .forms import CSVUploadForm
from .models import Transaction,Category,Member
from .rules import guess_category, guess_member, is_derm_clinic
from django.db.models import Q

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

    edit_mode = request.GET.get("edit") == "1"

    latest_source = (
        Transaction.objects
        .exclude(source_file="")
        .order_by("-id")
        .values_list("source_file", flat=True)
        .first()
    )

    # 一括更新（POST）
    if request.method == "POST" and request.POST.get("bulk_action"):
        action = request.POST.get("bulk_action")  # "category" or "member"
        selected_ids = request.POST.get("selected_ids", "")
        ids = [int(x) for x in selected_ids.split(",") if x.strip().isdigit()]

        if not ids:
          messages.error(request, "チェックされた行がないよ")
          return redirect(request.path + ("?edit=1" if edit_mode else ""))

        qs = Transaction.objects.filter(id__in=ids)
        if latest_source:
            qs = qs.filter(source_file=latest_source)

        if action == "category":
            category_id = request.POST.get("category_id")
            if not category_id:
                messages.error(request, "カテゴリが未選択だよ")
            else:
                n = qs.update(category_id=category_id)
                messages.success(request, f"カテゴリを {n} 件に適用したよ")
        elif action == "member":
            member_id = request.POST.get("member_id")
            if not member_id:
                messages.error(request, "メンバーが未選択だよ")
            else:
                n = qs.update(member_id=member_id)
                messages.success(request, f"メンバーを {n} 件に適用したよ")

        return redirect(request.path + ("?edit=1" if edit_mode else ""))

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

        # 先にカテゴリ/メンバーを全件辞書にしておく（DBアクセスを減らす）
        category_map = {c.name: c for c in Category.objects.all()}
        member_map = {m.name: m for m in Member.objects.all()}

        # 1) CSVを一旦パースして溜める + 皮膚科の「同日判定」用に日付を集める
        parsed_rows = []
        derm_dates = set()

        try:
            f.seek(0)
            raw = f.read()
            text = _decode_csv_bytes(raw)
            reader = csv.reader(io.StringIO(text))

            for row_index, row in enumerate(reader, start=1):
                # 1行目はヘッダ想定（不要なら削除OK）
                if row_index == 1:
                    continue

                # 空行スキップ
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

                    parsed_rows.append((d, shop, amount))

                    # 皮膚科が同日にあるか判定するため、日付を覚える
                    if is_derm_clinic(shop):
                        derm_dates.add(d)

                except Exception as e:
                    errors += 1
                    print("IMPORT ERROR:", row_index, row, repr(e))

        except Exception as e:
            messages.error(request, f"CSVの読み込みで落ちた: {e}")
            return redirect("transactions:list")


        # 2) ルールでカテゴリ/メンバーを割り当てて一括INSERT
        to_create = []

        for d, shop, amount in parsed_rows:
            category_name = guess_category(shop)
            category_obj = category_map.get(category_name) if category_name else None

            member_name = guess_member(shop, d, derm_dates)
            member_obj = member_map.get(member_name) if member_name else None

            to_create.append(
                Transaction(
                    date=d,
                    shop=shop,
                    amount=amount,
                    memo="",
                    source_file=source_file,
                    category=category_obj,
                    member=member_obj,
                    is_closed=False,
                )
            )

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

    edit_mode = request.GET.get("edit") == "1"

    qs = (
        Transaction.objects
        .select_related("category", "member")
    )

    if latest_source:
        qs = qs.filter(source_file=latest_source)
    else:
        qs = Transaction.objects.none()

    # 編集モードONなら、未割当てだけ（カテゴリ or メンバーがNULL）
    if edit_mode:
        qs = qs.filter(Q(category__isnull=True) | Q(member__isnull=True))

    transactions = qs

    categories = Category.objects.all().order_by("id")
    members = Member.objects.all().order_by("id")

    return render(
        request,
        "transactions/transaction_list.html",
        {
            "transactions": transactions,
            "upload_form": form,
            "edit_mode": edit_mode,
            "latest_source": latest_source,
            "categories": categories,
            "members": members,
        },
    )
