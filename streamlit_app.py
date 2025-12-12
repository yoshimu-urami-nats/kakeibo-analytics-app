import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import altair as alt

# 日本語フォント設定（Windows 想定）
plt.rcParams["font.family"] = "Meiryo"
plt.rcParams["axes.unicode_minus"] = False  # マイナス記号の文字化け防止


# メンバーID対応表（今後DBから読むように拡張可）
MEMBER_NAME = {
    3: "共有",
    4: "なっちゃん",
    5: "ゆーへー",
}

# ---- DB へのパス設定 ----
BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "db.sqlite3"

st.set_page_config(page_title="家計簿ダッシュボード", layout="wide")

st.title("📊 家計簿ダッシュボード")
st.caption("Django の SQLite DB からリアルタイムで集計中")

st.divider()


@st.cache_data
def load_transactions():
    """SQLite から明細を読み込んで DataFrame にする"""
    conn = sqlite3.connect(DB_PATH)
    query = """
        SELECT
            id,
            date,
            amount,
            memo,
            member_id
        FROM transactions_transaction
    """
    df = pd.read_sql_query(query, conn, parse_dates=["date"])
    conn.close()
    return df


# ---- データ読み込み ----
df = load_transactions()

if df.empty:
    st.warning("まだ明細データが入ってないみたい。")
else:
    with st.expander("生の明細データ（先頭5件だけ）"):
        st.dataframe(df.head())

    # 月別合計を出してみる
    df["date"] = pd.to_datetime(df["date"])
    df["month"] = df["date"].dt.to_period("M").astype(str)
    month_total = df.groupby("month")["amount"].sum().reset_index()
    month_total.rename(columns={"amount": "total_amount"}, inplace=True)


    st.subheader("月別支出合計（全員ぶん）")
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

    # 2カラムレイアウト：左 = 明細＆合計、右 = 円グラフ
    left_col, right_col = st.columns([2, 1])

    # 左カラム：合計 & 明細
    with left_col:
        total_selected = int(filtered["amount"].sum())
        st.metric(f"{selected_month} の合計支出", f"{total_selected:,} 円")

        st.subheader(f"{selected_month} の明細（先頭20件）")
        st.dataframe(
            filtered[["date", "amount", "memo", "member_name"]].head(20)
        )

    # 右カラム：メンバー別円グラフ
    with right_col:
        member_total = filtered.groupby("member_name")["amount"].sum()

        if not member_total.empty:
            st.subheader(f"{selected_month} のメンバー別支出割合")

            fig, ax = plt.subplots()
            ax.pie(
                member_total.values,
                labels=member_total.index,
                autopct="%1.1f%%",
                startangle=90,
            )
            ax.axis("equal")  # 真円
            st.pyplot(fig)
        else:
            st.info("この月には明細がありません。")


