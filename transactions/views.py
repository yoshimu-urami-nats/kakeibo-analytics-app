# tr
from django.contrib import messages  # フラッシュメッセージ

from members.models import Member    # 出費者
from .rules import guess_owner, guess_category       # ルール関数

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required

import csv
import io
import datetime

from .models import Transaction, Category
from .forms import TransactionForm, AssignMemberForm, CSVUploadForm


# 日付文字列 "2025/10/01" → date型 に変換する小さいヘルパー
def parse_date_from_string(date_str: str) -> datetime.date:
    # クレカCSVが「2025/10/01」形式前提
    return datetime.datetime.strptime(date_str, "%Y/%m/%d").date()


@login_required
def monthly_summary(request):
    """人間CK済みの明細を、月ごと・カテゴリごと・人ごとに集計した表"""

    # デフォルトの対象年月：一番新しい明細の日付
    latest = Transaction.objects.order_by("-date").first()
    if latest is None:
        context = {
            "year": None,
            "month": None,
            "members": [],
            "rows": [],
            "grand_per_member_list": [],
            "grand_total": 0,
        }
        return render(request, "transactions/monthly_summary.html", context)

    # URLパラメータ ?year=2025&month=11 があればそれを使う
    year = int(request.GET.get("year", latest.date.year))
    month = int(request.GET.get("month", latest.date.month))

    # 対象月の「人間CK済み」明細だけ拾う
    qs = (
        Transaction.objects
        .filter(is_confirmed=True, date__year=year, date__month=month)
        .select_related("member", "category")
    )

    # 列に並べるメンバー（順番はID順で固定）
    members = list(Member.objects.all().order_by("id"))

    # rows_dict[category_id] = {"category": Category or None,
    #                           "per_member": {member.id: amount, ...},
    #                           "total": amount}
    rows_dict = {}
    grand_per_member = {m.id: 0 for m in members}
    grand_total = 0

    for t in qs:
        cat = t.category      # None の可能性あり
        cat_key = cat.id if cat is not None else None

        if cat_key not in rows_dict:
            rows_dict[cat_key] = {
                "category": cat,
                "per_member": {m.id: 0 for m in members},
                "total": 0,
            }

        row = rows_dict[cat_key]

        # カテゴリ合計
        row["total"] += t.amount
        grand_total += t.amount

        # メンバー別合計
        if t.member_id is not None:
            row["per_member"][t.member_id] += t.amount
            grand_per_member[t.member_id] += t.amount

    # 表示順はカテゴリ名（なければ「未分類」として最後に）
    def sort_key(row):
        if row["category"] is None:
            return "zzz 未分類"
        return row["category"].name

    # テンプレートで扱いやすい形に整形
    rows = []
    for r in sorted(rows_dict.values(), key=sort_key):
        per_member_list = [r["per_member"][m.id] for m in members]
        rows.append(
            {
                "category": r["category"],
                "per_member_list": per_member_list,
                "total": r["total"],
            }
        )

    grand_per_member_list = [grand_per_member[m.id] for m in members]

    context = {
        "year": year,
        "month": month,
        "members": members,
        "rows": rows,
        "grand_per_member_list": grand_per_member_list,
        "grand_total": grand_total,
    }
    return render(request, "transactions/monthly_summary.html", context)




@login_required
def transaction_list(request):
    """明細の一覧（全部）"""
    transactions = Transaction.objects.all().order_by("-date", "-id")
    return render(
        request,
        "transactions/transaction_list.html",
        {"transactions": transactions},
    )


@login_required
def transaction_create(request):
    """明細を1件手入力で登録"""
    if request.method == "POST":
        form = TransactionForm(request.POST)
        if form.is_valid():
            t = form.save(commit=False)
            t.decided_by = "manual"   # 手入力 = manual
            t.is_confirmed = True
            t.save()
            return redirect("transactions:list")
    else:
        form = TransactionForm()

    return render(
        request,
        "transactions/transaction_form.html",
        {"form": form},
    )



@login_required
def unassigned_list(request):
    """まだ「誰の出費か」が決まっていない明細の一覧＆一括登録"""

    # まず未仕分けの一覧を取得
    transactions = (
        Transaction.objects.filter(member__isnull=True)
        .order_by("-date", "-id")
    )

    # プルダウン用にメンバー一覧も取得（表示順はお好みで）
    members = Member.objects.all().order_by("id")

    if request.method == "POST":
        # フォームから送られてきた値を使って一括で登録
        updated = 0

        for t in transactions:
            # 各行の <select name="member_{{ t.id }}"> に対応
            member_id = request.POST.get(f"member_{t.id}")
            if not member_id:
                # 何も選ばれていない行はスキップ
                continue

            try:
                member = Member.objects.get(pk=member_id)
            except Member.DoesNotExist:
                continue

            t.member = member
            t.decided_by = "manual"   # 人間が決めた
            t.is_confirmed = True     # 確定済み
            t.save()
            updated += 1

        # 終わったら同じ画面に戻る（F5で二重送信しないように）
        return redirect("transactions:unassigned")

    # GET のときは画面表示だけ
    return render(
        request,
        "transactions/unassigned_list.html",
        {
            "transactions": transactions,
            "members": members,
        },
    )



@login_required
def assign_member(request, pk):
    """1件の明細について「誰の出費か」を登録する画面"""
    transaction = get_object_or_404(Transaction, pk=pk)

    if request.method == "POST":
        form = AssignMemberForm(request.POST, instance=transaction)
        if form.is_valid():
            t = form.save(commit=False)
            t.decided_by = "manual"   # 人が手で確定
            t.is_confirmed = True     # 確定済みにする
            t.save()
            return redirect("transactions:unassigned")
    else:
        form = AssignMemberForm(instance=transaction)

    return render(
        request,
        "transactions/assign_member.html",
        {
            "transaction": transaction,
            "form": form,
        },
    )



@login_required
def upload_csv(request):
    """クレカCSVを取り込んで、未仕分け明細として登録"""

    if request.method == "POST":
        form = CSVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES["file"]

            # 文字コードUTF-8前提（SJISならencoding変える）
            wrapper = io.TextIOWrapper(csv_file, encoding="utf-8")
            reader = csv.reader(wrapper)

            for i, row in enumerate(reader):
                # 1行目は「岩下雄平様,カード情報…」なのでスキップ
                if i == 0:
                    continue

                if len(row) < 3:
                    # 想定よりカラムが少ない行はとりあえずスキップ
                    continue

                date_str = row[0].strip()
                shop = row[1].strip()
                amount_str = row[2].strip()

                if not date_str or not shop or not amount_str:
                    continue

                try:
                    amount = int(amount_str)
                except ValueError:
                    continue

                Transaction.objects.create(
                    date=parse_date_from_string(date_str),
                    shop=shop,
                    amount=amount,
                    memo="",        # 必要ならあとでメモ列を足す
                    member=None,    # 未仕分け
                )

            return redirect("transactions:unassigned")
    else:
        form = CSVUploadForm()

    return render(
        request,
        "transactions/upload_form.html",
        {"form": form},
    )

# AI 一括仕分け用：ルールに基づいて member を自動設定
OWNER_KEY_TO_MEMBER_NAME = {
    "nacchan": "なっちゃん",
    "yuhei": "ゆーへー",
    "shared": "共有",
}


@login_required
def auto_assign(request):
    """AI（ルール）で未判定明細をまとめて仕分けする"""

    # まだAIも人間も判定していない明細だけ対象
    qs = Transaction.objects.filter(decided_by="none")

    count = 0
    for t in qs:
        # ① 出費者の推定
        key = guess_owner(t.shop, t.date)
        if key is not None:
            member_name = OWNER_KEY_TO_MEMBER_NAME[key]

            try:
                member = Member.objects.get(name=member_name)
            except Member.DoesNotExist:
                member = None

            if member is not None:
                t.member = member
                t.decided_by = "rule"    # ルールによる自動判定
                t.is_confirmed = False   # まだ人間CK前
                count += 1

        # ② カテゴリの推定（出費者が決まらなくても実行してOK）
        if t.category is None:
            cat_name = guess_category(t.shop)
            if cat_name is not None:
                try:
                    category = Category.objects.get(name=cat_name)
                except Category.DoesNotExist:
                    category = None

                if category is not None:
                    t.category = category

        # ③ 何か変更があればここでまとめて保存
        t.save()
        count += 1

    messages.success(request, f"AI判定で {count} 件を自動仕分けしました。")

    # 未確定一覧に戻る
    return redirect("transactions:unassigned")

@login_required
def to_confirm_list(request):
    """
    member は入っているが、is_confirmed=False の明細一覧。
    → AIが入れたけど人間CKまだ、みたいな行たち
    """
    transactions = (
        Transaction.objects
        .filter(member__isnull=False, is_confirmed=False)
        .order_by("-date", "-id")
    )
    return render(
        request,
        "transactions/to_confirm_list.html",
        {"transactions": transactions},
    )

@login_required
def confirm_bulk(request):
    """チェックされた明細をまとめて '人間CK済み' にする"""
    if request.method != "POST":
        return redirect("transactions:to_confirm")

    ids = request.POST.getlist("ids")  # checkbox の name="ids"

    if not ids:
        messages.info(request, "選択された明細がありません。")
        return redirect("transactions:to_confirm")

    # AI案でも手動でも、とにかく member が入っていて未確定のものだけ対象
    qs = Transaction.objects.filter(
        pk__in=ids,
        member__isnull=False,
        is_confirmed=False,
    )

    updated = qs.update(
        is_confirmed=True,
        decided_by="manual",   # 人間が内容を確認した、という意味でmanualに寄せる
    )

    messages.success(request, f"{updated} 件の明細を『人間CK済み』にしました。")
    return redirect("transactions:to_confirm")