import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# --- ページ設定 ---
st.set_page_config(page_title="シリアル在庫管理システム", layout="wide")

# --- Google Sheets 接続設定 ---
# SecretsからURLを読み込んで接続します
conn = st.connection("gsheets", type=GSheetsConnection)

# データの読み込み関数
def get_data(worksheet_name):
    return conn.read(worksheet=worksheet_name, ttl=0)

# --- タイトルと認証 ---
st.title("📦 シリアル在庫管理システム")
ADMIN_PASSWORD = "admin"  # 管理用パスワード

st.sidebar.title("🔐 認証")
input_pass = st.sidebar.text_input("管理用パスワード", type="password")
is_admin = (input_pass == ADMIN_PASSWORD)

# --- メニュー ---
if is_admin:
    menu = ["🏠 在庫一覧", "➕ 1件登録", "🚚 出庫・移動", "⚙️ 各種管理"]
else:
    menu = ["🏠 在庫一覧", "➕ 1件登録", "🚚 出庫・移動"]

choice = st.sidebar.selectbox("機能メニュー", menu)

# 最新データの取得
try:
    df_inv = get_data("inventory")
    df_loc = get_data("locations")
    location_options = df_loc["location_name"].dropna().tolist()
except Exception as e:
    st.error("スプレッドシートの読み込みに失敗しました。Secretsの設定やシート名を確認してください。")
    st.stop()

# --- 1. 在庫一覧 ---
if choice == "🏠 在庫一覧":
    st.subheader("📊 現在の在庫状況")
    search_q = st.text_input("🔍 検索", placeholder="シリアル番号や商品名で検索...")
    
    display_df = df_inv.copy()
    if search_q:
        display_df = display_df[display_df.apply(lambda row: row.astype(str).str.contains(search_q).any(), axis=1)]
    
    st.dataframe(display_df, use_container_width=True, hide_index=True)

# --- 2. 1件登録 ---
elif choice == "➕ 1件登録":
    st.subheader("📝 新規登録")
    with st.form("add_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            sn = st.text_input("シリアル番号（必須）")
            p_name = st.text_input("商品名")
        with col2:
            loc = st.selectbox("保管場所", location_options) if location_options else st.selectbox("保管場所", ["未登録"])
            src = st.text_input("入庫元")
        
        user_name = st.text_input("👤 担当者名（必須）")
        if st.form_submit_button("スプレッドシートに保存"):
            if sn and user_name:
                new_row = pd.DataFrame([{
                    "シリアル番号": sn, "商品名": p_name, "現在保管場所": loc,
                    "入庫元": src, "出庫先": "", "ステータス": "在庫中",
                    "最終更新日時": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "登録・更新者": user_name
                }])
                # 既存データと結合して更新
                updated_df = pd.concat([df_inv, new_row], ignore_index=True)
                conn.update(worksheet="inventory", data=updated_df)
                st.success(f"登録完了！スプレッドシートを更新しました: {sn}")
            else:
                st.error("必須項目を入力してください。")

# --- 3. 出庫・移動 ---
elif choice == "🚚 出庫・移動":
    st.subheader("🚚 出庫・移動の記録")
    target_sn = st.selectbox("対象シリアル番号", df_inv["シリアル番号"].tolist())
    new_dest = st.text_input("送り先 / 出庫先")
    new_status = st.selectbox("新ステータス", ["出荷済", "修理中", "廃棄", "在庫中"])
    user_name = st.text_input("👤 担当者名")
    
    if st.button("更新を確定"):
        if target_sn and new_dest and user_name:
            # 該当行を特定して更新
            df_inv.loc[df_inv["シリアル番号"] == target_sn, ["出庫先", "ステータス", "最終更新日時", "登録・更新者"]] = \
                [new_dest, new_status, datetime.now().strftime("%Y-%m-%d %H:%M"), user_name]
            conn.update(worksheet="inventory", data=df_inv)
            st.success("スプレッドシートの情報を更新しました。")

# --- 4. 各種管理 ---
elif choice == "⚙️ 各種管理":
    st.subheader("🏘️ 保管場所の追加")
    new_loc = st.text_input("新しい場所の名前")
    if st.button("場所を登録"):
        if new_loc:
            new_row = pd.DataFrame([{"location_name": new_loc}])
            updated_loc = pd.concat([df_loc, new_row], ignore_index=True)
            conn.update(worksheet="locations", data=updated_loc)
            st.success(f"場所を追加しました: {new_loc}")
            st.rerun()
