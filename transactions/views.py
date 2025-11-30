# transactions/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required

import csv
import io
import datetime

from .models import Transaction
from .forms import TransactionForm, AssignMemberForm, CSVUploadForm


# 日付文字列 "2025/10/01" → date型 に変換する小さいヘルパー
def parse_date_from_string(date_str: str) -> datetime.date:
    # クレカCSVが「2025/10/01」形式前提
    return datetime.datetime.strptime(date_str, "%Y/%m/%d").date()


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
            form.save()
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
    """まだ「誰の出費か」が決まっていない明細の一覧"""
    transactions = (
        Transaction.objects.filter(member__isnull=True)
        .order_by("-date", "-id")
    )
    return render(
        request,
        "transactions/unassigned_list.html",
        {"transactions": transactions},
    )


@login_required
def assign_member(request, pk):
    """1件の明細について「誰の出費か」を登録する画面"""
    transaction = get_object_or_404(Transaction, pk=pk)

    if request.method == "POST":
        form = AssignMemberForm(request.POST, instance=transaction)
        if form.is_valid():
            form.save()
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
