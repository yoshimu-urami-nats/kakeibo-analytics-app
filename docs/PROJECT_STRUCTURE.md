# Project Structure（最終更新：2026-02-14）

このドキュメントは、リポジトリの全体構造と「どこに何があるか」を素早く思い出すためのメモ。

---

## ざっくり全体像

- **Django本体**：`account / transactions / members / kakeibo_app`
- **共通資産**：`static / docs`
- **開発補助**：`tools`
- **ローカル専用（コミットしない）**：`_local`（実データ、メモ、検証用）

---

## ツリー（主要）

```text
kakeibo-analytics-app/
├── account/                 # ログイン/ホーム/予測/EDAなど画面側（テンプレ含む）
├── transactions/            # 取引（CSV取込、一覧、割当、月次サマリ、分類ルール）
├── members/                 # メンバー定義（な/ゆ/共有などの管理）
├── kakeibo_app/             # Djangoプロジェクト設定（settings/urls/wsgi/asgi）
├── static/                  # CSS/画像（全アプリ共通）
├── docs/                    # 設計/ルール/コマンド/構造メモ
├── tools/                   # 生成・補助スクリプト（デモデータ、メモ生成など）
├── _local/                  # ローカル専用（gitignore）
├── manage.py
├── requirements.txt
└── runtime.txt
```
---

## 各フォルダの用途
### account/

- 役割：ログイン、トップ（home）、予測/EDA系ページの表示、共通レイアウト
- 主な入口
  - `account/views.py`
  - `account/templates/account/`（`base.html`, `home.html`, `login.html`, `prediction.html`, `eda.html` 等）

---

### transactions/

- 役割：取引データの中核（一覧、割当、確認、分類ルール、CSV取込）
- 主な入口
  - `transactions/views.py`：一覧/割当/適用など画面の司令塔
  - `transactions/models.py`：Transaction/Category等のDB定義
  - `transactions/rules.py`：分類ルール（重要）
  - `transactions/forms.py`：入力・検索・割当UI
  - `transactions/templates/transactions/`：一覧・部分テンプレ（`_transaction_rows.html` 等）
  - `transactions/management/commands/import_past_csv.py`：過去CSV一括取込コマンド

---

### members/

- 役割：メンバー（支払者/負担者/共有など）のマスタ管理
- 主な入口
  - `members/models.py`
  - `members/views.py`（必要に応じて）

---

### kakeibo_app/

- 役割：Djangoプロジェクト設定
- 主な入口
  - `kakeibo_app/settings.py`
  - `kakeibo_app/urls.py`

---

### static/

- 役割：CSS/画像
- 主な入口
  - `static/app_min.css`
  - `static/images/*`

---

### docs/

- 役割：設計・運用メモ（コミット対象）
- ファイル
  - `docs/Architecture.md`：全体設計メモ
  - `docs/PROJECT_MAP.md`：機能・ページ・ファイル対応表
  - `docs/RULES.md`：分類ルールなど仕様メモ
  - `docs/DEV_COMMANDS.md`：よく使うコマンド集
  - `docs/assets/`：ロゴなど

---

### tools/

- 役割：開発補助スクリプト
- ファイル
  - `tools/demo_data_generator.py`：デモCSV生成
  - `tools/memo_gen.py`：作業メモ生成

---

### _local/（gitignore）

- 役割：ローカル専用（コミットしない）
- 想定内容
  - `data_real/`：実データCSV/Excel、バックアップ、月別データ
  - `memo/`：自分用メモ
  - `scripts/`：一時検証スクリプト
  - `streamlit/`：Streamlit実験（必要な場合）
  
※ `_local` 配下は原則コミットしない。

---

### よく触る「入口」まとめ

- 画面（表示や導線）
  - `account/views.py`
  - `transactions/views.py`
  - `account/templates/account/base.html`
  - `transactions/templates/transactions/transaction_list.html`
- 取引のDB・分類
  - `transactions/models.py`
  - `transactions/rules.py`
- CSV取込
  - `transactions/management/commands/import_past_csv.py`
- 見た目（CSS）
  - `static/app_min.css`

---

### 運用ルール（自分向け）

- 実データ・個人メモ・検証ファイルは `_local/` に置く
- 仕様や設計として残すものは `docs/` に置く
- 「分類ルールを変えたら」 `transactions/rules.py` と `docs/RULES.md` をセットで更新する