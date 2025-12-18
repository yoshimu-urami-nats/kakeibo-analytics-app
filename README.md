<p align="center">
  <img src="docs/assets/kakeibo_app_logo.png" width="1200" />
</p>

<h1 align="center">kakeibo-analytics-app</h1>

<p align="center">
  おうち家計簿、アプリ。
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11-blue.svg" />
  <img src="https://img.shields.io/badge/streamlit-app-red.svg" />
  <img src="https://img.shields.io/badge/deploy-render-purple.svg" />
  <img src="https://img.shields.io/badge/database-sqlite-lightgrey.svg" />
  <img src="https://img.shields.io/badge/status-active-success.svg" />
</p>



## Overview

クレジットカード明細（CSV / SQLite）をもとに、  
**月別・メンバー別・カテゴリ別** に家計の支出構造を可視化する  
データ分析ダッシュボードです。



## Features

-  月別支出推移（全体 / メンバー別）
-  月次支出合計と前年差分
-  メンバー別・カテゴリ別の支出割合
-  支出明細の一覧表示
-  デモ / 本番データの切替設計



##  Live Demo

 https://kakeibo-analytics-app.onrender.com/

※ デモでは個人情報を含まないダミーデータを使用しています。



##  Tech Stack

- Python
- pandas
- Streamlit
- matplotlib / Plotly
- SQLite
- Render



##  Project Structure

```text
kakeibo-analytics-app/
├── streamlit_app.py
├── requirements.txt
├── data_demo/
│   ├── demo_transactions.csv
│   └── demo.db.sqlite3
├── data_real/        # gitignore
│   └── real.db.sqlite3
├── docs/
└── README.md
```



##  Data Policy

- 実データはリポジトリに含めません
- デモ / 本番はフォルダ + 環境変数で分離
- MODE 切替はコード変更なし



##  Author

yoshimu-urami-nats