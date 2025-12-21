# 🖥 ターミナル（bash / PowerShell）基本メモ

Django や Python 開発でよく使う「お作法」「コマンド」「立ち回り」をまとめたメモ。

---

## 🔰 基本の概念

### ● 仮想環境（venv）
プロジェクトごとに Python ライブラリを分ける仕組み。
Django や pandas はここに入れる。

### ● サーバー起動
Django を実行して、ブラウザからアプリを見る動作。

### ● サーバー停止
ターミナルを占有している Django の実行を止めること。

---

# 🟦 1. よく使うコマンド（超頻出）

## ● 仮想環境を作る
```bash
python -m venv venv
```

## ● 仮想環境を有効化する

PowerShell:
```bash
venv\Scripts\Activate.ps1
```

コマンドプロンプト:
```bash
venv\Scripts\activate.bat
```
→ 有効化されると (venv) が先頭に付く。

## ● 仮想環境を無効化する
```bash
deactivate
```
↑これまだ使えなかった、後で確認

## ● ライブラリのインストール
```bash
pip install ライブラリ名
```

## ● 現在のライブラリ一覧（requirements生成）
```bash
pip freeze > requirements.txt
```

# 🟦 2. Django の基本コマンド
## ● プロジェクト作成
```bash
django-admin startproject プロジェクト名 .
```

## ● アプリ作成
```bash
python manage.py startapp アプリ名
```

## ● サーバー起動
```bash
python manage.py runserver
```

## ● サーバー停止
```bash
Ctrl + C
```
※ 赤文字が出ても、警告なら気にしなくてOK。

## ● マイグレーション（DB構造反映）

### 構造作成
```bash
python manage.py makemigrations
```

### 反映
```bash
python manage.py migrate
```

# 🟦 3. bash（ターミナル）でよく使う基礎操作
## ● カレントディレクトリ（今いる場所）
```bash
pwd
```

## ● ファイル一覧を見る
```bash
ls
```

## ● フォルダ移動
```bash
cd フォルダ名
```
1つ上に戻るなら：
```bash
cd ..
```

## ● フォルダを VSCode で開く
```bash
code .
```

# 🟦 4. Git の基本操作（超頻出）
## ● 変更を確認
```bash
git status
```

## ● 変更をステージング
```bash
git add .
```

## ● コミット
```bash
git commit -m "メッセージ"
```

## ● GitHub へアップロード
```bash
git push origin main
```

# 🟦 5. その他の「お作法」メモ
## ● サーバー動かしっぱなしにしない
別の作業に移る時は必ず Ctrl + C で停止する

## ● venv は GitHub に上げない
.gitignore に venv/ を入れる（済）

## ● Django プロジェクトのルートで作業する
（manage.py がある場所）

## ● 重要  
エラーが出ても「赤字＝悪」ではない！  
**WARNING は無視していいことも多い**

---

# 🟦 6. Django シェル（python manage.py shell）

## ● 起動
```bash
python manage.py shell
```

## ● 終了
```python
exit()
```
または  
```python
quit()
```

## ● よく使う操作例
```python
from transactions.models import Transaction
qs = Transaction.objects.filter(category__isnull=True)
```

---

# 🟦 7. きれいなサンプル DB を保存する方法

### SQLite を丸ごとコピーするのが一番簡単

- runserver を止める  
- db.sqlite3 をコピーして保存（snapshot）

---

# 🟩 8. Streamlit のお作法（基礎）

## ● インストール

```bash
pip install streamlit
```

## ● Streamlit アプリの配置（推奨）

Django プロジェクトのルート（manage.py と同じ階層）に置く：

```
kakeibo-analytics-app/
├─ manage.py
├─ db.sqlite3
└─ streamlit_app.py
```

## ● 起動

```bash
streamlit run streamlit_app.py
```

※ローカル

→ 初回だけメール登録の質問が出るが、空のまま Enter で OK  
→ ブラウザが http://localhost:8501 を開く

## ● 停止

```bash
Ctrl + C
```

## ● コードを保存すると自動で反映  
反映されない場合は右上の **Rerun** を押す

## ● SQLite を読む基本形

```python
import sqlite3
import pandas as pd
from pathlib import Path

DB_PATH = Path(__file__).parent / "db.sqlite3"

conn = sqlite3.connect(DB_PATH)
df = pd.read_sql_query("SELECT * FROM transactions_transaction", conn)
conn.close()
```

## ● よく使う加工

```python
df["date"] = pd.to_datetime(df["date"])
df["month"] = df["date"].dt.to_period("M").astype(str)
month_total = df.groupby("month")["amount"].sum()
st.line_chart(month_total)
```

## ● よく使う UI

```python
year = st.selectbox("年を選択", [2024, 2025])
st.dataframe(df)
```

---

