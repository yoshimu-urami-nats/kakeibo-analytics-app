# 家計簿データ分析Webアプリ（Django × pandas × sklearn）

## 📌 概要
このプロジェクトは、クレジットカード明細（CSV）をWeb上で管理し、
「誰の出費か」の割り振り・月次集計・カテゴリ分析・来月支出の予測まで行う
データ分析Webアプリです。

## 🎯 目的
- データ分析系SEへの転職を見据えた実践的なポートフォリオ作成
- Web開発×データ分析×機械学習をワンストップで扱う経験を積む

## 🧩 技術スタック
- **Backend:** Python / Django  
- **Frontend:** HTML, Bootstrap  
- **Database:** SQLite  
- **Data Analysis:** pandas, numpy, scikit-learn  
- **Deploy:** Render（予定）

## 🗂 構成
```
kakeibo-analytics-app/
├── README.md
├── requirements.txt
├── .gitignore
├── docs/
│   ├── roadmap.md
│   ├── er-diagram.png
│   ├── ui-mockup.png
│   └── memo/（今日置いたメモなど）
│
├── kakeibo_app/            ← Djangoプロジェクト本体
│   ├── kakeibo_app/        ← 設定（settings.py など）
│   ├── accounts/           ← ログイン関連（Django標準でも可）
│   ├── members/            ← 家族（Member）
│   ├── transactions/       ← CSV取込・明細管理
│   ├── analytics/          ← pandas分析 / sklearn予測
│   ├── templates/          ← HTMLテンプレ
│   ├── static/             ← CSS / JS / 画像
│   └── ...（いつもどおりのDjango構成）
│
└── sample_data/
    ├── sample_creditcard.csv
    └── sample_output.csv
```

**docs/ フォルダに思考過程を置く予定**
- 仕様書（roadmap.md）  
- ER図（er-diagram.png）  
- 全体アーキテクチャ図（任意）  
- メモ  

## 🗺 開発ロードマップ
- フェーズ1：ログイン＋明細一覧
- フェーズ2：Transaction・Member実装
- フェーズ3：CSVアップロード＋pandas ETL
- フェーズ4：傾向分析（pandas）
- フェーズ5：予測（sklearn）
- フェーズ6：UI調整＋スマホ対応

## 📊 サンプルデータ
`sample_data/sample_creditcard.csv`

## 🚀 今後の展望
- 本番デプロイ
- CSV形式の自動判別
- カテゴリ自動推定（軽いML）

## 💻 公開用（デモ）について

このアプリの本体ロジック（CSV取込・分析・予測）は Django（Python） で実装しています。  

一方、  
“動いている様子を誰でも簡単に見られるデモ” のために、  
Streamlit Cloud（無料）で公開用のミニUIを別途提供予定です。  

- Django：本番想定のバックエンド・分析ロジック
- Streamlit：ポートフォリオ閲覧用の軽量フロント

※ 公開URLは準備でき次第 README に追記します。

## 🚀 デプロイ方針
- Backend（Django） → ローカル開発 or 学習用環境（Render 検討中）
- Demo（Streamlit） → Streamlit Community Cloud（無料）
