import os
from pathlib import Path

import pandas as pd
import streamlit as st
import altair as alt
import plotly.express as px

from dotenv import load_dotenv
load_dotenv()  # カレント直下の .env を読む

# Postgres接続（Render用 / ローカルも同じ）
import psycopg
from urllib.parse import urlparse


BASE_DIR = Path(__file__).parent
DATABASE_URL = os.getenv("DATABASE_URL")  # 必須


st.set_page_config(page_title="家計簿ダッシュボード", layout="wide")
st.title("家計簿ダッシュボード")

# どのデータソースで動いてるか（表示用）
source_label = "Postgres"

def _connect_postgres(database_url: str):
    u = urlparse(database_url)
    return psycopg.connect(
        dbname=u.path.lstrip("/"),
        user=u.username,
        password=u.password,
        host=u.hostname,
        port=u.port or 5432,
        sslmode="require",
    )


@st.cache_data
def load_transactions():

    if not DATABASE_URL:
        # ここに来たら設定漏れなので、分かりやすく止める
        st.error("DATABASE_URL が未設定です。(.env か Render の環境変数に設定してね)")
        st.stop()

    query = """
    SELECT
        t.id,
        t.date,
        t.amount,
        t.shop AS merchant,
        m.name AS member_name,
        COALESCE(c.name, '未分類') AS category_name,
        t.source_file,
        t.is_closed
    FROM transactions_transaction t
    LEFT JOIN members_member m
        ON t.member_id = m.id
    LEFT JOIN transactions_category c
        ON t.category_id = c.id
    WHERE t.is_closed = TRUE
    ;
    """

    conn = _connect_postgres(DATABASE_URL)
    df = pd.read_sql_query(query, conn, parse_dates=["date"])
    conn.close()
    return df



df = load_transactions()

# 件数
row_count = len(df)

# 期間（min / max）
if row_count > 0 and "date" in df.columns:
    dt = pd.to_datetime(df["date"], errors="coerce")
    date_min = dt.min()
    date_max = dt.max()
    if pd.notna(date_min) and pd.notna(date_max):
        period_text = f"{date_min:%Y-%m-%d} 〜 {date_max:%Y-%m-%d}"
    else:
        period_text = "日付不明"
else:
    period_text = "データなし"

st.caption(
    f"データソース: {source_label} ｜ 件数: {row_count} ｜ 期間: {period_text}"
)

st.markdown("---")


if df.empty:
    st.warning("まだ明細データが入ってないみたい。")
    st.stop()

# === ここから追加（cycle_monthの代わり） ===

# source_file から 202601 みたいな "YYYYMM" を抜き出して月キーにする
# 例: "202601.csv" -> "2026-01"
df["source_file_month"] = (
    df["source_file"].astype(str)
    .str.extract(r"(\d{6})")[0]  # YYYYMM
    .fillna("unknown")
)

df["source_file_month"] = df["source_file_month"].apply(
    lambda s: f"{s[:4]}-{s[4:]}" if s != "unknown" else "unknown"
)

# プルダウン用（unknownは最後に回す）
months = sorted([m for m in df["source_file_month"].unique() if m != "unknown"])
if "unknown" in set(df["source_file_month"].unique()):
    months.append("unknown")

# === ここまで追加 ===

with st.expander("生の明細データ（先頭5件だけ）"):
    st.dataframe(df.head())

# 月列
# 締め月（16日〜翌15日）として集計したいので、日付を15日ぶん戻して月を作る
# 例: 2025-02-01 は ( -15日 ) => 2025-01 扱い（= 1/16〜2/15の締め月）
df["cycle_month"] = (df["date"] - pd.Timedelta(days=15)).dt.to_period("M").astype(str)


# 月別合計（全員）
month_total = df.groupby("source_file_month")["amount"].sum().reset_index()
month_total.rename(columns={"amount": "total_amount"}, inplace=True)

st.markdown("### 月別支出合計（ファイル名ベース）")
st.altair_chart(
    alt.Chart(month_total)
    .mark_line(point=True)
    .encode(
        x=alt.X("source_file_month:N", title="月（ファイル名）", sort=months),
        y=alt.Y("total_amount:Q", title="合計支出（円）"),
        tooltip=[
            alt.Tooltip("source_file_month:N", title="月"),
            alt.Tooltip("total_amount:Q", title="合計支出", format=","),
        ],
    )
    .properties(height=280),
    use_container_width=True,
)

# メンバー別 × 月別
df_for_member = df.copy()

member_month_total = (
    df.groupby(["source_file_month", "member_name"])["amount"].sum().reset_index()
)

st.subheader("月別支出推移（メンバー別 / ファイル名ベース）")
st.altair_chart(
    alt.Chart(member_month_total)
    .mark_line(point=True)
    .encode(
        x=alt.X("source_file_month:N", title="月（ファイル名）", sort=months),
        y=alt.Y("amount:Q", title="支出（円）"),
        color=alt.Color("member_name:N", title="メンバー"),
        tooltip=[
            alt.Tooltip("source_file_month:N", title="月"),
            alt.Tooltip("member_name:N", title="メンバー"),
            alt.Tooltip("amount:Q", title="支出", format=","),
        ],
    )
    .properties(height=280),
    use_container_width=True,
)


# 月選択
default_index = len(months) - 1 if months else 0

colA, colB, colC = st.columns([1, 2, 1])
with colB:
    selected_month = st.selectbox("月を選択（ファイル名）", months, index=default_index)

filtered = df[df["source_file_month"] == selected_month].copy()


left_col, right_col = st.columns([2, 1])

with left_col:
    total_selected = int(filtered["amount"].sum())
    st.markdown(f"### {selected_month} の合計支出")
    st.metric("合計支出", f"{total_selected:,} 円")
    st.subheader(f"{selected_month} の明細（支出TOP20）")

    top20 = (
        filtered[filtered["amount"] > 0]          # 支出だけ（必要なら）
        .sort_values("amount", ascending=False)
        .head(20)
        .copy()
    )

    # 表示用：順位(1..20) を作る。IDや元indexは見せない
    top20 = top20.reset_index(drop=True)
    top20.insert(0, "rank", top20.index + 1)

    # 日付は文字にしておくと表示が安定
    top20["date"] = pd.to_datetime(top20["date"]).dt.strftime("%Y-%m-%d")

    # 金額は表示用に文字列へ（ここがポイント）
    top20["amount_disp"] = top20["amount"].apply(lambda x: f"¥{int(x):,}")

    st.dataframe(
        top20[["rank", "date", "amount_disp", "merchant", "member_name"]],
        hide_index=True,
        column_config={
            "rank": st.column_config.NumberColumn("順位"),  # ここはformat無しでOK
            "date": st.column_config.TextColumn("日付"),
            "amount_disp": st.column_config.TextColumn("金額"),
            "merchant": st.column_config.TextColumn("店名・サービス"),
            "member_name": st.column_config.TextColumn("メンバー"),
        },
    )


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
