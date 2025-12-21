import os
from pathlib import Path

import sqlite3
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import altair as alt
import platform
import plotly.express as px

# 日本語フォント設定（Windows 想定）
if platform.system() == "Windows":
    plt.rcParams["font.family"] = "Meiryo"  # ローカル用
plt.rcParams["axes.unicode_minus"] = False


# メンバーID対応表（今後DBから読むように拡張可）
MEMBER_NAME = {
    1: "Aさん",
    2: "Bさん",
    3: "共有",
    4: "なっちゃん",
    5: "ゆーへー",
}

# ---- DB へのパス設定 ----
BASE_DIR = Path(__file__).parent

env_db = os.environ.get("KAIKEIBO_DB_PATH")
if env_db:
    DB_PATH = BASE_DIR / env_db
else:
    DB_PATH = BASE_DIR / "db.sqlite3"


MODE = os.getenv("KAKEIBO_MODE", "demo")  # デフォルトはデモモード

st.set_page_config(page_title="家計簿ダッシュボード", layout="wide")

st.title("家計簿ダッシュボード")

if MODE == "demo":
    st.caption("デモCSVから集計中（ポートフォリオ用）")
else:
    st.caption("Django の SQLite DB から集計中（家庭用）")

st.markdown("---")



@st.cache_data
def load_transactions():
    """デモ時はCSV、本番時はSQLiteから明細を読む"""

    if MODE == "demo":
        # デモ用CSVを読む（Render / ポートフォリオ用）
        csv_path = BASE_DIR / "data_demo" / "demo_transactions.csv"
        df = pd.read_csv(csv_path)
        df["date"] = pd.to_datetime(df["date"])
        return df

    # それ以外（本番モード）は従来通りSQLiteから読む
    conn = sqlite3.connect(DB_PATH)
    query = """
    SELECT
        t.id,
        t.date,
        t.amount,
        t.memo AS merchant,
        t.member_id,
        COALESCE(c.name, '未分類') AS category_name
    FROM transactions_transaction t
    LEFT JOIN transactions_category c
        ON t.category_id = c.id
    """
    df = pd.read_sql_query(query, conn, parse_dates=["date"])
    conn.close()
    return df


# @st.cache_data
# def load_category_master():
#     # デモモード：DBに触らずCSVなどからカテゴリマスタを作る
#     if MODE == "demo":
#         csv_path = BASE_DIR / "data_demo" / "demo_transactions.csv"
#         df = pd.read_csv(csv_path)

#         # ↓ここは実際のカラム名に合わせて調整してね
#         # 例: demo_transactions.csv に "category_id", "category_name" がある場合
#         cat_df = (
#             df[["category_id", "category_name"]]
#             .drop_duplicates()
#             .rename(columns={"category_id": "id", "category_name": "name"})
#         )

#     # 家庭用モード：今まで通り SQLite から読む
#     else:
#         conn = sqlite3.connect(DB_PATH)
#         query = "SELECT id, name FROM transactions_category"
#         cat_df = pd.read_sql_query(query, conn)
#         conn.close()

#     # {id: name} の dict を返す想定なら
#     return dict(zip(cat_df["id"], cat_df["name"]))




# ---- データ読み込み ----
df = load_transactions()

# # ★ カテゴリマスタを読み込んで、category_id → category_name に変換
# CATEGORY_NAME = load_category_master()

# if "category_id" in df.columns:
#     df["category_name"] = df["category_id"].map(CATEGORY_NAME).fillna("未分類")
# else:
#     # 念のため（まだ category_id が無いケース）
#     df["category_name"] = "未分類"

if df.empty:
    st.warning("まだ明細データが入ってないみたい。")
else:
    with st.expander("生の明細データ（先頭5件だけ）"):
        st.dataframe(df.head())

    # 月別合計を出してみる
    df["month"] = df["date"].dt.to_period("M").astype(str)
    month_total = df.groupby("month")["amount"].sum().reset_index()
    month_total.rename(columns={"amount": "total_amount"}, inplace=True)


    st.markdown("### 月別支出合計（全員ぶん）")

    chart = (
        alt.Chart(month_total)
        .mark_line(point=True)
        .encode(
            x=alt.X("month:N", title="月"),
            y=alt.Y("total_amount:Q", title="合計支出（円）"),
            tooltip=[
                alt.Tooltip("month:N", title="月"),
                alt.Tooltip("total_amount:Q", title="合計支出", format=","),
            ],
        )
        .properties(height=280)
    )

    st.altair_chart(chart, use_container_width=True)

    # ★ メンバー別 × 月別の集計データ
    df_for_member = df.copy()
    df_for_member["member_name"] = df_for_member["member_id"].map(MEMBER_NAME)

    member_month_total = (
        df_for_member
        .groupby(["month", "member_name"])["amount"]
        .sum()
        .reset_index()
    )

    # ---- メンバー別の月別支出推移 ----
    st.subheader("月別支出推移（メンバー別）")

    member_chart = (
        alt.Chart(member_month_total)
        .mark_line(point=True)
        .encode(
            x=alt.X("month:N", title="月"),
            y=alt.Y("amount:Q", title="支出（円）"),
            color=alt.Color("member_name:N", title="メンバー"),
            tooltip=[
                alt.Tooltip("month:N", title="月"),
                alt.Tooltip("member_name:N", title="メンバー"),
                alt.Tooltip("amount:Q", title="支出", format=","),
            ],
        )
        .properties(height=280)
    )

    st.altair_chart(member_chart, use_container_width=True)



    # ---- 月を選べるセレクトボックス（全幅）----
    months = sorted(df["month"].unique())
    default_index = len(months) - 1 if months else 0

    colA, colB, colC = st.columns([1,2,1])
    with colB:
        selected_month = st.selectbox(
            "月を選択（明細をチェックする用）",
            months,
            index=default_index,
        )

    # ---- 選択した月のデータを用意 ----
    filtered = df[df["month"] == selected_month].copy()
    filtered["member_name"] = filtered["member_id"].map(MEMBER_NAME)

    # 全体の月別合計（すでにあるやつ）
    month_total = df.groupby("month")["amount"].sum().reset_index()
    month_total.rename(columns={"amount": "total_amount"}, inplace=True)

    # 2カラムレイアウト：左 = 明細＆合計、右 = 円グラフ
    left_col, right_col = st.columns([2, 1])

    # 左カラム：合計 & 明細
    with left_col:
        total_selected = int(filtered["amount"].sum())
        st.markdown(f"### {selected_month} の合計支出")
        st.metric("合計支出", f"{total_selected:,} 円")

        st.subheader(f"{selected_month} の明細（先頭20件）")
        st.dataframe(filtered[["date", "amount", "merchant", "member_name"]].head(20))

    # 右カラム：メンバー別 / カテゴリ別 円グラフ
    with right_col:
        tab_member, tab_category = st.tabs(["メンバー別", "カテゴリ別"])

        # --- タブ1：メンバー別 ---
        with tab_member:
            member_total = filtered.groupby("member_name")["amount"].sum()
            if not member_total.empty:
                st.subheader(f"{selected_month} のメンバー別支出割合")

                # plotly用にDataFrame化
                member_df = member_total.reset_index().rename(columns={"amount": "amount"})

                fig = px.pie(
                    member_df,
                    names="member_name",
                    values="amount",
                )
                fig.update_traces(textinfo="percent+label")
                st.plotly_chart(fig, use_container_width=True)

            else:
                st.info("この月には明細がありません。")


        # --- タブ2：カテゴリ別 ---
        with tab_category:
            category_total = filtered.groupby("category_name")["amount"].sum()

            if not category_total.empty:
                st.subheader(f"{selected_month} のカテゴリ別支出割合")

                category_df = category_total.reset_index().rename(columns={"amount": "amount"})

                fig = px.pie(
                    category_df,
                    names="category_name",
                    values="amount",
                )
                fig.update_traces(textinfo="percent+label")
                st.plotly_chart(fig, use_container_width=True)

                # 円グラフの下にテーブルを表示
                st.markdown("#### カテゴリ別 金額一覧")
                st.dataframe(
                    category_total.reset_index().sort_values("amount", ascending=False),
                    use_container_width=True,
                )
            else:
                st.info("この月にはカテゴリ情報がありません。")





