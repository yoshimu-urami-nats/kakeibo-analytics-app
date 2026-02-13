# Kakeibo Analytics App - Project Map

## 1. プロジェクト概要

目的：
- クレカCSVを取り込み
- 明細を分類（な / ゆ / 共有）
- 月次集計
- 将来予測
- 可視化

使用技術：
- Django
- SQLite
- Bootstrap + 自作CSS
- 線形回帰（予測）


---

## 2. アプリ構成

### account
役割：
- ホーム画面
- 予測ページ
- EDAページ

主要ファイル：
- views.py
- templates/account/*.html


### transactions
役割：
- 明細管理
- CSVインポート
- 明細一覧・編集

主要ファイル：
- models.py
- views.py
- templates/transactions/*.html


### members
役割：
- メンバー管理（な / ゆ / 共有）


---

## 3. 主要モデル

### Transaction

| フィールド | 型 | 用途 |
|------------|----|------|
| date | DateField | 取引日 |
| shop | CharField | 店名 |
| amount | IntegerField | 金額 |
| member | FK(Member) | 支払者 |
| category | FK(Category) | 分類 |
| memo | TextField | 補足 |
| source_file | CharField | 取込元CSV |
| is_closed | Boolean | 確定フラグ |


---

## 4. URL → View → Template 対応表

| URL | View | Template | 役割 |
|-----|------|----------|------|
| / | home | home.html | トップ |
| /transactions/ | transaction_list | transaction_list.html | 明細一覧 |
| /prediction/ | prediction | prediction.html | 予測 |
| /prediction/breakdown/ | prediction_breakdown | prediction_breakdown.html | 予測内訳 |

（←ここは実際のurls.py見ながら埋める）


---

## 5. データの流れ

CSV取込
↓
Transaction保存
↓
member/category分類
↓
月次集計
↓
予測ロジック
↓
predictionページ表示


---

## 6. 今後の整理方針

- ロジックはservices.pyへ分離予定
- viewsは薄く保つ
- docsに設計を集約
