# Architecture

<br>

## Overview

本アプリは Django を中心とした単一Webアプリ構成である。  
データ登録・編集・分析・予測までを Django 内で完結させている。  

Streamlit は現在使用していない（保留）。

<br>

## Application Layer
### Django Web Application

役割：
- CSVインポート
- 明細の確認・分類・編集
- 管理画面（Admin）
- 集計処理
- 分析表示
- 支出予測ロジック
- Predictionページ表示

予測機能も Django の view 内で処理し、  
テンプレートにレンダリングしている。

<br>

## Database
### PostgreSQL（Render Managed DB）

- Django から Read / Write
- 本番データの永続化
- 単一データソース

<br>

## Hosting

- Django：Render Web Service（gunicorn）
- DB：Render Managed PostgreSQL

<br>

## Data Flow
### ① CSV取込・編集

User  
→ Django  
→ PostgreSQL（Write）

---

### ② 分析・予測

User  
→ Django  
→ PostgreSQL（Read）  
→ Django 内で集計・予測計算  
→ HTMLレンダリング  

<br>

## Design Policy

- 管理・分析・予測を単一アプリ内で統合
- サービス分離は行わず、シンプル構成を優先
- 分析ロジックは Django 側で一元管理
- 将来的に API 化 / 分析基盤分離可能な構成

<br>

## Current Status

- Streamlit：未使用（将来拡張候補）
- 予測処理：Django 内実装
- DB接続：単一ユーザー（権限分離なし）