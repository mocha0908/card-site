import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="カードラッシュ価格表", layout="wide")
st.title("🃏 カードラッシュ 価格一覧")

# --- 最終更新日時 ---
if os.path.exists("last_updated.txt"):
    with open("last_updated.txt", "r") as f:
        last_updated = f.read().strip()
else:
    last_updated = "未更新"
st.info(f"📅 最終更新日時: **{last_updated}**")

# === タブの作成 ===
tab1, tab2 = st.tabs(["🛒 販売額リスト", "💰 買取額リスト"])

# ==========================================
# タブ1：販売額 (Sales)
# ==========================================
with tab1:
    st.header("販売価格")
    csv_file = "card_data.csv"

    if os.path.exists(csv_file):
        df = pd.read_csv(csv_file)
        
        # 検索
        search_sales = st.text_input("カード名で検索 (販売)", "")
        if search_sales:
            df = df[df['商品名'].str.contains(search_sales, case=False)]

        # ダウンロード
        csv_data = df.to_csv(index=False).encode('utf-8_sig')
        st.download_button("📥 販売リストをCSVでDL", csv_data, "sales_prices.csv", "text/csv")

        # 表示
        st.dataframe(
            df,
            column_config={
                "画像URL": st.column_config.ImageColumn("画像"),
                "商品URL": st.column_config.LinkColumn("リンク"),
                "価格": st.column_config.NumberColumn("価格", format="%d円"),
            },
            use_container_width=True,
            height=800
        )
    else:
        st.warning("販売データ収集中...")

# ==========================================
# タブ2：買取額 (Buying)
# ==========================================
with tab2:
    st.header("買取価格")
    buy_csv = "buying_data.csv"

    if os.path.exists(buy_csv):
        df_buy = pd.read_csv(buy_csv)

        # 検索
        search_buy = st.text_input("カード名で検索 (買取)", "")
        if search_buy:
            df_buy = df_buy[df_buy['カード名'].str.contains(search_buy, case=False)]

        # 注目カード絞り込みフィルタ
        is_hot = st.checkbox("🔥 強化買取（人気カード）のみ表示")
        if is_hot and '人気カード' in df_buy.columns:
            # データ内のtrue/falseが文字列かブール値かによるため念のため変換
            df_buy = df_buy[df_buy['人気カード'].astype(str).str.lower() == 'true']

        # ダウンロード
        csv_data_buy = df_buy.to_csv(index=False).encode('utf-8_sig')
        st.download_button("📥 買取リストをCSVでDL", csv_data_buy, "buying_prices.csv", "text/csv")

        # 表示
        st.dataframe(
            df_buy,
            column_config={
                "画像URL": st.column_config.ImageColumn("画像"),
                "買取価格": st.column_config.NumberColumn("買取価格", format="%d円"),
                "人気カード": st.column_config.CheckboxColumn("強化買取"),
            },
            use_container_width=True,
            height=800
        )
    else:
        st.warning("買取データ収集中...（GitHubで実行してください）")