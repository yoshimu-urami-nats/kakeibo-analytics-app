# transactions/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Transaction
from .forms import TransactionForm, AssignMemberForm


@login_required
def transaction_list(request):
    transactions = Transaction.objects.all().order_by("-date", "-id")
    return render(
        request,
        "transactions/transaction_list.html",
        {"transactions": transactions},
    )


@login_required
def transaction_create(request):
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
    """member がまだ未設定の明細だけを一覧表示"""
    transactions = Transaction.objects.filter(
        member__isnull=True
    ).order_by("-date", "-id")

    return render(
        request,
        "transactions/unassigned_list.html",
        {"transactions": transactions},
    )

@login_required
def assign_member(request, pk):
    # 対象の明細を1件取得（なければ 404）
    transaction = get_object_or_404(Transaction, pk=pk)

    if request.method == "POST":
        # POST された「誰の出費か」でフォームを作る（対象の明細に紐付け）
        form = AssignMemberForm(request.POST, instance=transaction)
        if form.is_valid():
            form.save()  # member だけ更新される
            # 登録が終わったら「未仕分け一覧」に戻る
            return redirect("transactions:unassigned")
    else:
        # GET の時は、現在の member を初期値としてフォームを表示
        form = AssignMemberForm(instance=transaction)

    context = {
        "transaction": transaction,
        "form": form,
    }
    return render(request, "transactions/assign_member.html", context)

import csv
from django.shortcuts import render, redirect
from .models import Transaction

def upload_csv(request):
    if request.method == "POST":
        csv_file = request.FILES.get("csv_file")

        if not csv_file:
            return render(request, "transactions/upload_form.html", {
                "error": "CSVファイルを選択してください"
            })

        # デコードして読み込む
        decoded = csv_file.read().decode("utf-8").splitlines()
        reader = csv.reader(decoded)

        header = next(reader, None)

        # 1行ずつ取り込む
        for row in reader:

            if not row:
                continue

            # CSV の列順に合わせて取り込む（例）
            # 日付, 店名, 金額, メモ
            date, shop, amount, memo = row

            Transaction.objects.create(
                date=date,
                shop=shop,
                amount=int(amount),
                memo=memo,
                member=None,  # ← 未仕分けとして保存
            )

        # 取り込み完了 → 未仕分け画面へ
        return redirect("transactions:unassigned")

    # 初期表示（フォーム表示）
    return render(request, "transactions/upload_form.html")

