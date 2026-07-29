import streamlit as st
import datetime
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# --- ページ設定 ---
st.set_page_config(page_title="メンテナンス依頼アプリ", layout="wide")

# --- スプレッドシート接続設定 ---
SPREADSHEET_KEY = "19T0DlLHq48j20jFz73LFlPN1C5RdgqkaRTt2KXpgETs"

@st.cache_resource
def get_gspread_client():
    try:
        # Streamlit Secrets から認証情報を取得
        credentials = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        return gspread.authorize(credentials)
    except Exception as e:
        st.error(f"認証情報の設定が必要です: {e}")
        return None

def get_worksheet():
    gc = get_gspread_client()
    if gc:
        try:
            sh = gc.open_by_key(SPREADSHEET_KEY)
            return sh.get_worksheet(0)
        except Exception as e:
            st.error(f"スプレッドシートを開けませんでした: {e}")
    return None

# --- ヘッダー自動設定（初回のみ） ---
def ensure_headers(ws):
    if ws and len(ws.get_all_values()) == 0:
        headers = ["送信日時", "依頼種別", "担当者名", "顧客コード"]
        for i in range(1, 6):
            headers.extend([f"商品{i}_記号", f"商品{i}_数量", f"商品{i}_単価"])
        ws.append_row(headers)

# --- アプリ画面レイアウト ---
st.title("🛠️ メンテナンス依頼・データ管理")

tab1, tab2 = st.tabs(["📝 依頼フォーム入力", "📋 送信データ一覧・詳細確認"])

# -------------------------------------------------------------------
# TAB 1: 入力フォーム
# -------------------------------------------------------------------
with tab1:
    st.subheader("■ 基本情報")
    col_b1, col_b2, col_b3 = st.columns(3)
    with col_b1:
        request_type = st.selectbox("依頼種別", ["商品発注", "修理依頼", "その他"])
    with col_b2:
        staff_name = st.text_input("担当者名")
    with col_b3:
        customer_code = st.text_input("顧客コード")

    st.markdown("---")
    st.subheader("■ 商品明細（最大5件）")
    
    # 5件分の入力枠を作成
    items_input = []
    
    for i in range(1, 6):
        st.markdown(f"**【商品 {i}】**")
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            code = st.text_input(f"商品記号", key=f"code_{i}")
        with col2:
            qty = st.number_input(f"数量", min_value=0, value=0, key=f"qty_{i}")
        with col3:
            price = st.number_input(f"単価", min_value=0, value=0, key=f"price_{i}")
        
        # 入力があれば値を保持、空欄なら空文字として保持
        if code.strip():
            items_input.extend([code.strip(), qty, price])
        else:
            items_input.extend(["", "", ""])

    st.markdown("---")
    
    # 送信ボタン
    if st.button("送信する", type="primary", use_container_width=True):
        if not staff_name or not customer_code:
            st.warning("「担当者名」と「顧客コード」を入力してください。")
        else:
            ws = get_worksheet()
            if ws:
                ensure_headers(ws)
                
                # 1行分のデータを作成
                now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                row_data = [now_str, request_type, staff_name, customer_code] + items_input
                
                # 書き込み実行
                ws.append_row(row_data)
                st.success("✅ スプレッドシートへ正常に送信されました！")
                st.balloons()

# -------------------------------------------------------------------
# TAB 2: 一覧・詳細確認画面（データ表示）
# -------------------------------------------------------------------
with tab2:
    st.subheader("📋 送信済みデータ一覧")
    
    if st.button("最新データに更新"):
        st.cache_data.clear()
        
    ws = get_worksheet()
    if ws:
        records = ws.get_all_records()
        if records:
            df = pd.DataFrame(records)
            
            # 1. 一覧表を表示（全体データ）
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            st.markdown("---")
            st.subheader("🔍 伝票風 詳細プレビュー")
            
            # 2. 特定の行を選択して綺麗に表示する機能
            selected_index = st.number_input("詳細を表示したい行番号 (1〜)", min_value=1, max_value=len(df), value=len(df))
            
            selected_row = df.iloc[selected_index - 1]
            
            # カード形式で詳細を表示
            st.info(f"**送信日時:** {selected_row.get('送信日時')} | **依頼種別:** {selected_row.get('依頼種別')} | **担当者:** {selected_row.get('担当者名')} | **顧客コード:** {selected_row.get('顧客コード')}")
            
            # 空白でない商品だけをピックアップして綺麗に表にする
            detail_items = []
            for i in range(1, 6):
                code = selected_row.get(f"商品{i}_記号")
                if code and str(code).strip() != "":
                    detail_items.append({
                        "商品番号": f"商品 {i}",
                        "商品記号": code,
                        "数量": selected_row.get(f"商品{i}_数量"),
                        "単価": selected_row.get(f"商品{i}_単価")
                    })
            
            if detail_items:
                st.table(pd.DataFrame(detail_items))
            else:
                st.write("※商品明細の入力はありません。")
                
        else:
            st.info("まだデータが登録されていません。")
