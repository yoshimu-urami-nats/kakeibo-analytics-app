<p align="center">
  <img src="docs/assets/kakeibo_app_logo.png" width="1200" />
</p>

<h1 align="center">kakeibo-analytics-app</h1>

<p align="center">
  家計簿データを 分析・予測・可視化する Django製データ分析Webアプリ<br>
クレジットカード明細（CSV）を読み込み、月次支出分析・異常検知・支出予測を行います
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.14-blue" />
  <img src="https://img.shields.io/badge/Framework-Django-0C4B33" />
  <img src="https://img.shields.io/badge/ORM-Django--ORM-darkgreen" />
  <img src="https://img.shields.io/badge/Database-PostgreSQL(Supabase)-336791" />
  <img src="https://img.shields.io/badge/Deploy-Render-6e40c9" />
  <img src="https://img.shields.io/badge/Status-Active-brightgreen" />
</p>



## Overview

クレジットカード明細（CSV）を元に

- 月別・カテゴリ別の支出分析
- メンバー別の支出集計
- 支出の異常検知
- 来月支出の予測（バックテスト付き）

を行う **データ分析型の家計簿アプリ**です。

分析ロジックは Django View から分離し、`services` 層として実装しています。


---

##  Live Demo

 https://kakeibo-django.onrender.com
 
### Demo Account
閲覧用ゲストアカウント  
ID: guest  
Password: test012345  

※ ゲストアカウントでは個人情報を保護するため  
店舗名・明細情報はダミーデータ（HOGE）で表示されます。

---

# Features

### 支出分析 (EDA)

- 月次支出推移
- カテゴリ別支出割合
- メンバー別支出
- 支出ランキング

---

### 支出ゾーン分析

直近ベース期間の中央値 (median) と 75 パーセンタイル (p75) を基準に、
今月の支出をカテゴリ別に判定します。

- 安定ゾーン：今月支出が中央値以下
- 高めゾーン：中央値超〜75パーセンタイル以下
- 負担感あり：75パーセンタイル超

---

### 支出予測

線形回帰による **翌月支出予測**

さらに

- 過去データを用いた **バックテスト**
- 予測誤差 / 誤差率の可視化
- カテゴリ別寄与分析

を表示します。

---

### 異常支出検出

支出分布を元に **Zスコア分析**を行い

- 異常に高い支出
- 特異な月

を検出します。

---

# Architecture

分析ロジックは Django View から分離し  
**Service Layer** として実装しています。

views.py  
   ↓  
services/  
   ├─ eda_service.py  
   ├─ prediction_service.py  
   ├─ zones_service.py  
   └─ event_detection_service.py

- View → UI制御
- Service → 分析ロジック

---

# Tech Stack

| Category | Technology |
|---|---|
Backend | Python / Django |
Database | PostgreSQL (Supabase) |
Data Processing | Django ORM / Python statistics
Hosting | Render |



---

# Project Docs

詳細設計は `docs` フォルダにまとめています。

- Architecture
- Project Map
- Project Structure
- Prediction Design

---

# Data Policy

このリポジトリには実データは含まれていません。

デモ環境では

- 明細
- 店舗名
- 個人情報

は **ダミーデータ (HOGE)** に置き換えられています。

---

# Author

Yoshimu U. Nats

## Special Thanks

- y-iwashi
  - 開発相談 / レビュー協力

- snrnapa
  - 開発相談