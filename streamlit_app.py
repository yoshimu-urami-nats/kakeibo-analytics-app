import os
from pathlib import Path
import platform
import sqlite3

import pandas as pd
import streamlit as st
import altair as alt
import plotly.express as px

# Postgres接続（Render用）
import psycopg2
from urllib.parse import urlparse


# 日本語フォント設定（Windows 想定）
# ※matplotlib使ってないなら不要。使う時だけ戻す。
# import matplotlib.pyplot as plt
# if platform.system() == "Windows":
#     plt.rcParams["font.family"] = "Meiryo"
# plt.rcParams["axes.unicode_minus"] = False


MEMBER_NAME = {
    1: "Aさん",
    2: "Bさん",
    3: "共有",
    4: "なっちゃん",
    5: "ゆーへー",
}

BASE_DIR = Path(__file__).parent
MODE = os.getenv("KAKEIBO_MODE", "demo")  # demo / local など
DATABASE_URL = os.getenv("DATABASE_URL")  # Renderで設定する想定

env_db = os.environ.get("KAIKEIBO_DB_PATH")
DB_PATH = (BASE_DIR / env_db) if env_db else (BASE_DIR / "db.sqlite3")


st.set_page_config(page_title="家計簿ダッシュボード", layout="wide")
st.title("家計簿ダッシュボード")

if MODE == "demo":
    st.caption("デモCSVから集計中（ポートフォリオ用）")
elif DATABASE_URL:
    st.caption("Render(Postgres) から集計中（ポートフォリオ本番想定）")
else:
    st.caption("ローカルSQLiteから集計中（家庭用）")

st.markdown("---")


def _connect_postgres(database_url: str):
    """
    Renderの DATABASE_URL 例:
    postgres://user:pass@host:5432/dbname
    """
    u = urlparse(database_url)
    return psycopg2.connect(
        dbname=u.path.lstrip("/"),
        user=u.username,
        password=u.password,
        host=u.hostname,
        port=u.port or 5432,
        sslmode="require",  # Renderは基本これでOK
    )


@st.cache_data
def load_transactions():
    """
    1) demo: CSV
    2) DATABASE_URLあり: Postgres(Render)
    3) それ以外: SQLite(ローカル)
    """
    if MODE == "demo":
        csv_path = BASE_DIR / "data_demo" / "demo_transactions.csv"
        df = pd.read_csv(csv_path)
        df["date"] = pd.to_datetime(df["date"])
        return df

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

    # Render(Postgres)
    if DATABASE_URL:
        conn = _connect_postgres(DATABASE_URL)
        df = pd.read_sql_query(query, conn, parse_dates=["date"])
        conn.close()
        return df

    # ローカル(SQLite)
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(query, conn, parse_dates=["date"])
    conn.close()
    return df


df = load_transactions()

if df.empty:
    st.warning("まだ明細データが入ってないみたい。")
    st.stop()

with st.expander("生の明細データ（先頭5件だけ）"):
    st.dataframe(df.head())

# 月列
df["month"] = df["date"].dt.to_period("M").astype(str)

# 月別合計（全員）
month_total = df.groupby("month")["amount"].sum().reset_index()
month_total.rename(columns={"amount": "total_amount"}, inplace=True)

st.markdown("### 月別支出合計（全員ぶん）")
st.altair_chart(
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
    .properties(height=280),
    use_container_width=True,
)

# メンバー別 × 月別
df_for_member = df.copy()
df_for_member["member_name"] = df_for_member["member_id"].map(MEMBER_NAME)

member_month_total = (
    df_for_member.groupby(["month", "member_name"])["amount"].sum().reset_index()
)

st.subheader("月別支出推移（メンバー別）")
st.altair_chart(
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
    .properties(height=280),
    use_container_width=True,
)

# 月選択
months = sorted(df["month"].unique())
default_index = len(months) - 1 if months else 0

colA, colB, colC = st.columns([1, 2, 1])
with colB:
    selected_month = st.selectbox("月を選択（明細をチェックする用）", months, index=default_index)

filtered = df[df["month"] == selected_month].copy()
filtered["member_name"] = filtered["member_id"].map(MEMBER_NAME)

left_col, right_col = st.columns([2, 1])

with left_col:
    total_selected = int(filtered["amount"].sum())
    st.markdown(f"### {selected_month} の合計支出")
    st.metric("合計支出", f"{total_selected:,} 円")
    st.subheader(f"{selected_month} の明細（先頭20件）")
    st.dataframe(filtered[["date", "amount", "merchant", "member_name"]].head(20))

with right_col:
    tab_member, tab_category = st.tabs(["メンバー別", "カテゴリ別"])

    with tab_member:
        member_total = filtered.groupby("member_name")["amount"].sum()
        if member_total.empty:
            st.info("この月には明細がありません。")
        else:
            member_df = member_total.reset_index().rename(columns={"amount": "amount"})
            fig = px.pie(member_df, names="member_name", values="amount")
            fig.update_traces(textinfo="percent+label")
            st.plotly_chart(fig, use_container_width=True)

    with tab_category:
        category_total = filtered.groupby("category_name")["amount"].sum()
        if category_total.empty:
            st.info("この月にはカテゴリ情報がありません。")
        else:
            category_df = category_total.reset_index().rename(columns={"amount": "amount"})
            fig = px.pie(category_df, names="category_name", values="amount")
            fig.update_traces(textinfo="percent+label")
            st.plotly_chart(fig, use_container_width=True)

            st.markdown("#### カテゴリ別 金額一覧")
            st.dataframe(
                category_total.reset_index().sort_values("amount", ascending=False),
                use_container_width=True,
            )
