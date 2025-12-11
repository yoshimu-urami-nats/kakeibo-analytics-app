import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

# 日本語フォント設定（Windows 想定）
plt.rcParams["font.family"] = "Meiryo"
plt.rcParams["axes.unicode_minus"] = False  # マイナス記号の文字化け防止


# メンバーID対応表（今後DBから読むように拡張可）
MEMBER_NAME = {
    3: "共有",
    4: "なっちゃん",
    5: "ゆーへー",
}

st.title("📊 家計簿ダッシュボード（本物DBテスト）")

# ---- DB へのパス設定 ----
BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "db.sqlite3"


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
    st.subheader("生の明細データ（先頭5件だけ）")
    st.dataframe(df.head())

    # 月別合計を出してみる
    df["month"] = df["date"].dt.to_period("M").astype(str)
    month_total = df.groupby("month")["amount"].sum()

    st.subheader("月別支出合計（全員ぶん）")
    st.line_chart(month_total)

    # ---- 月を選べるセレクトボックス ----
    months = sorted(df["month"].unique())

    # デフォルトを「一番新しい月」にしておく
    default_index = len(months) - 1 if months else 0

    selected_month = st.selectbox(
        "月を選択（明細をチェックする用）",
        months,
        index=default_index,
    )

    # 選択した月のデータだけに絞り込み
    filtered = df[df["month"] == selected_month]

    # member_id を名前に変換
    filtered["member_name"] = filtered["member_id"].map(MEMBER_NAME)

    # 合計金額をひと目で出す
    total_selected = int(filtered["amount"].sum())
    st.metric(f"{selected_month} の合計支出", f"{total_selected:,} 円")

    # 選択した月の明細を少しだけ表示
    st.subheader(f"{selected_month} の明細（先頭20件）")
    st.dataframe(
        filtered[["date", "amount", "memo", "member_name"]].head(20)
    )

    # ---- 選択した月のメンバー別支出割合（円グラフ）----
    member_total = filtered.groupby("member_id")["amount"].sum()

    if not member_total.empty:
        st.subheader(f"{selected_month} のメンバー別支出割合")

        fig, ax = plt.subplots()
        ax.pie(
            member_total.values,
            labels=[MEMBER_NAME.get(m, f"member {m}") for m in member_total.index],
            autopct="%1.1f%%",
            startangle=90,
        )
        ax.axis("equal")  # 真円にする

        st.pyplot(fig)
    else:
        st.info("この月には明細がありません。")

