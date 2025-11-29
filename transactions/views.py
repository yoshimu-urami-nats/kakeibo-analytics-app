from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .models import Transaction
from .forms import TransactionForm


@login_required
def transaction_list(request):
    transactions = Transaction.objects.select_related("member").all()
    return render(
        request,
        "transactions/transaction_list.html",
        {"transactions": transactions},
    )

@login_required
def transaction_create(request):
    """明細の新規登録"""

    if request.method == "POST":
        form = TransactionForm(request.POST)
        if form.is_valid():
            form.save()
            # 登録後は一覧に戻る
            return redirect("transactions:list")
    else:
        # 初期表示（GET）のとき
        form = TransactionForm()

    return render(
        request,
        "transactions/transaction_form.html",
        {"form": form},
    )