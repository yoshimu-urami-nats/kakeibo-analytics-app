from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required


from .models import Transaction
from .forms import TransactionForm

@login_required
def unassigned_list(request):
    """member がまだ未設定の明細だけを一覧表示"""

    transactions = Transaction.objects.filter(member__isnull=True).order_by("-date", "-id")

    return render(
        request,
        "transactions/unassigned_list.html",
        {"transactions": transactions},
    )


@login_required
def assign_member(request, pk):
    """1件の明細について『誰の出費か』を登録する"""

    transaction = get_object_or_404(Transaction, pk=pk)

    if request.method == "POST":
        # member だけを更新したいけど、とりあえず既存フォームをそのまま流用
        form = TransactionForm(request.POST, instance=transaction)
        if form.is_valid():
            form.save()
            return redirect("transactions:unassigned")
    else:
        form = TransactionForm(instance=transaction)

    return render(
        request,
        "transactions/assign_member.html",
        {
            "form": form,
            "transaction": transaction,
        },
    )
