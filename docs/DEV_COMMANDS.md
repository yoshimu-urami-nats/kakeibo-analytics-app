# ターミナル（bash）基本メモ

## 仮想環境（venv）
### 仮想環境を有効化

```bash
source venv/Scripts/activate
```
→ 有効化されると (venv) が先頭に付く。

<br>

### requirements.txtを修正した時：venvを作り直す

- venv を削除（フォルダ消すだけ）
- 新しく作る  

```bash
python -m venv venv
```
- 有効化
- requirements.txt だけで復元  

```bash
pip install -r requirements.txt
```
※ すでに入っていても ズレ修正目的でOK

<br>

# ブランチ関連

## main に切り替え

```bash
git checkout main
```

## マージ

```bash
git merge ブランチ名
```

<br>

## ローカルのstreamlit

```bash
streamlit run streamlit_app.py
```

<br>

# Django
## サーバー起動
```bash
python manage.py runserver
```

## サーバー停止
```bash
Ctrl + C
```

## マイグレーション（DB構造反映）

反映
```bash
python manage.py migrate
```

migrate してないDBを使おうとするとエラーが出るので注意

<br>

# Django シェル

## 起動
```bash
python manage.py shell
```

## 終了
```python
quit()
```

## DBのデータのみ削除・採番リセット(Shell)
```python
python manage.py shell
```

データ削除
```python
from transactions.models import Transaction
Transaction.objects.all().delete()
```
✅ transactions_transaction テーブルの「行（データ）」だけ削除  
❌ テーブル構造は消えない  
❌ Member / Category / User / auth 系は一切触らない  

採番（ID）を 1 からやり直す方法（Postgres)
```python
from django.db import connection

with connection.cursor() as cursor:
    cursor.execute(
        "SELECT setval(pg_get_serial_sequence('transactions_transaction','id'), 1, false);"
    )
```

<br>

## メモジェネレータ

```python
python tools/memo_gen.py
```