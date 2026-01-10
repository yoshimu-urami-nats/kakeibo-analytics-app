# 家計簿アプリ開発ロードマップ  
（クレカCSV取込 + 誰の出費か登録 + 傾向分析 + 来月予測）

---

## 🎯 開発のゴール

### ▼ 第一段階
- 「家計簿 + 誰出費登録 + CSVアップロード」が動く版
- Web上で明細が見れて、家族の誰の出費か設定できる
- pandasで最低限の集計が見れる

### ▼ 第二段階
- 傾向分析ページ（カテゴリ別 / 月別グラフ）
- sklearnで来月の支出予測
- スマホ対応UI（Bootstrap）
- README整備してGitHubにアップ


---

## ✅ フェーズ1：Django触ってWebアプリの「骨」を作る  
（ログイン + トップページ表示）

**作業内容**
- Djangoインストール  
- プロジェクト作成  
- ログイン／ログアウト実装  
- 仮のトップページ作成  



---

## ✅ フェーズ2：クレカ明細の登録・閲覧（MVP）

**作業内容**
- Transactionモデル作成（date, shop, amount, memo など）
- Member（誰の出費か）モデル紐づけ
- 管理画面からテストデータ登録
- 一覧表示／詳細表示ページ作成



---

## ✅ フェーズ3：CSVアップロード ＋ pandas 取り込み

**作業内容**
- CSVアップロードフォーム
- pandasでCSV読み込み
- カラム名の揃え方など前処理
- データをDBへ保存

---

## ✅ フェーズ4：傾向分析ページ

**作業内容**
- pandasで月次集計
- カテゴリ別集計
- テーブル表示
- 棒グラフなど簡単なグラフ表示

---

## ✅ フェーズ5：来月の支出予測（機械学習の入り口）

**作業内容**
- 月ごとの合計を作る
- sklearnで線形回帰 or 移動平均による予測
- 「来月の予測値」を算出
- 分析ページに結果を表示

---

## ✅ フェーズ6：見た目整える／スマホ対応／README整備

**作業内容**
- Bootstrapで最低限のレイアウト作成
- ナビバー／カード／レスポンシブ対応
- GitHubにアップ
- READMEに「目的／機能／使った技術／工夫点」を記述


---
---

家計簿アプリ：DB運用仕様メモ

方針
- DBは PostgreSQL 1本運用
- 編集可能なデータは「未確定」のみに限定する
- Streamlit は「確定データ」を表示して、集計を安定させる
---

DBのカラムの説明  
---

import_month（取り込み月）
- 目的：
  - クレカ明細が「前月15日〜当月15日〆」などで分かりづらいため、
    “どの月として取り込んだか” を明示する
  - 月次インポート / 月次バックアップの単位にする
- 型：
  - DateField（その月の1日を入れる）例：2025-12-01
  - 表示は YYYY/MM などに整形
---

is_closed（確定フラグ）
- 目的：
  - 当月のみ編集可、過去月は編集不可にして事故を防ぐ
- 運用：
  - CSVインポート時は is_closed = False で登録する
  - Djangoの編集ページは is_closed=False のみ表示（＝当月編集用）
  - 「確定」ボタンで、対象月（import_month）の is_closed を一括で True にする
  - 確定済みデータ（is_closed=True）は編集不可にする
---
## 画面/機能の役割

### Django（編集）
- 役割：当月（未確定）データの編集・確定
- 表示：
  - import_month を選択（基本は最新月）
  - is_closed=False のみ一覧・編集できる
- 操作：
  - CSVインポート（import_monthを付与、is_closed=False）
  - 編集（memo/category/memberなど）
  - 確定（対象 import_month の is_closed を True にする）
  - ※必要なら「取り込み月ごとのCSV書き出し（バックアップ）」も用意する

### Streamlit（閲覧・集計）
- 役割：確定データの集計・可視化（ポートフォリオ閲覧含む）
- 基本：
  - is_closed=True のみ表示
- オプション：
  - 「当月も含める」チェックONで is_closed=False も集計対象にする

---

## バックアップ
- 月次バックアップとして、import_month 単位でCSV書き出しできるようにする
- 例：backup/2025-12-transactions.csv
---
DB（transactions_transaction）最終形

id,date,shop,amount,member_id,category_id,memo,import_month,is_closed

id：主キー（Djangoが自動で作るのでモデルに書かなくてOK）

date：DateField（表示は yyyy/mm/dd(曜日) に整形して出す）

shop：CharField

amount：IntegerField

member：ForeignKey → DB列として member_id ができる

category：ForeignKey → DB列として category_id ができる

memo：CharField（空OK）

import_month：DateField（月初日運用がラク。表示は yyyy/mm）

is_closed：BooleanField（確定済み）