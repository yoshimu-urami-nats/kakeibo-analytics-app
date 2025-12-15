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
st.markdown("---")



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
            member_id,
            category_id
        FROM transactions_transaction
    """
    df = pd.read_sql_query(query, conn, parse_dates=["date"])
    conn.close()
    return df

@st.cache_data
def load_category_master():

    conn = sqlite3.connect(DB_PATH)
    cat_df = pd.read_sql_query(
        "SELECT id, name FROM transactions_category",
        conn
    )
    conn.close()
    return dict(zip(cat_df["id"], cat_df["name"]))



# ---- データ読み込み ----
df = load_transactions()

# ★ カテゴリマスタを読み込んで、category_id → category_name に変換
CATEGORY_NAME = load_category_master()

if "category_id" in df.columns:
    df["category_name"] = df["category_id"].map(CATEGORY_NAME).fillna("未分類")
else:
    # 念のため（まだ category_id が無いケース）
    df["category_name"] = "未分類"

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


    df["date"] = pd.to_datetime(df["date"])
    df["month"] = df["date"].dt.to_period("M").astype(str)

    # 全体の月別合計（すでにあるやつ）
    month_total = df.groupby("month")["amount"].sum().reset_index()
    month_total.rename(columns={"amount": "total_amount"}, inplace=True)




    # 2カラムレイアウト：左 = 明細＆合計、右 = 円グラフ
    left_col, right_col = st.columns([2, 1])

    # 左カラム：合計 & 明細
    with left_col:
        # 今月の合計
        total_selected = int(filtered["amount"].sum())

        # ------------- 前月比を計算 -------------
        delta_text = None  # 表示なしの初期値

        # months は既に上で作っている「全月一覧」
        if selected_month in months:
            idx = months.index(selected_month)

            # 前の月が存在する場合のみ計算
            if idx > 0:
                prev_month = months[idx - 1]

                # month_total（上で作った月別集計）から前月の金額を取得
                prev_row = month_total[month_total["month"] == prev_month]["total_amount"]

                if not prev_row.empty:
                    prev_total = int(prev_row.iloc[0])

                    diff = total_selected - prev_total  # 金額差
                    if prev_total != 0:
                        rate = diff / prev_total * 100
                        delta_text = f"{diff:+,} 円（{rate:+.1f}%）"
                    else:
                        delta_text = f"{diff:+,} 円"

        # ------------- 表示 -------------
        st.markdown(f"### {selected_month} の合計支出")
        st.metric("合計支出", f"{total_selected:,} 円", delta=delta_text)

        st.subheader(f"{selected_month} の明細（先頭20件）")
        st.dataframe(filtered[["date", "amount", "memo", "member_name"]].head(20))


    # 右カラム：メンバー別円グラフ
# 右カラム：メンバー別 / カテゴリ別 円グラフ
with right_col:
    tab_member, tab_category = st.tabs(["メンバー別", "カテゴリ別"])

    # --- タブ1：メンバー別 ---
    with tab_member:
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

    # --- タブ2：カテゴリ別 ---
    with tab_category:
        category_total = filtered.groupby("category_name")["amount"].sum()

        if not category_total.empty:
            st.subheader(f"{selected_month} のカテゴリ別支出割合")

            fig, ax = plt.subplots()
            ax.pie(
                category_total.values,
                labels=category_total.index,
                autopct="%1.1f%%",
                startangle=90,
            )
            ax.axis("equal")  # 真円
            st.pyplot(fig)
        else:
            st.info("この月にはカテゴリ情報がありません。")

    with right_col:
        # …円グラフの下あたりに
        st.markdown("#### カテゴリ別 金額一覧")
        st.dataframe(
            category_total.reset_index().sort_values("amount", ascending=False),
            use_container_width=True,
        )



