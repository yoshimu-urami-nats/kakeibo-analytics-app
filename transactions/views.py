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


