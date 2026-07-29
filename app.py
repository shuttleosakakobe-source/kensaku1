import streamlit as st
import datetime
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# --- ページ設定 ---
st.set_page_config(page_title="メンテナンス依頼フォーム", layout="wide")

# --- スプレッドシート接続設定 ---
SPREADSHEET_KEY = "19T0DlLHq48j20jFz73LFlPN1C5RdgqkaRTt2KXpgETs"

@st.cache_resource
def get_gspread_client():
    try:
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

# --- ヘッダー自動設定（1商品につき「記号」「伝票出力」「数量」「単価」の4項目） ---
def ensure_headers(ws):
    if ws and len(ws.get_all_values()) == 0:
        headers = ["送信日時", "依頼種別", "担当者名", "顧客コード"]
        for i in range(1, 6):
            headers.extend([f"商品{i}_記号", f"商品{i}_伝票出力", f"商品{i}_数量", f"商品{i}_単価"])
        ws.append_row(headers)

# --- 顧客検索処理（過去データから顧客コードで検索） ---
def search_customer_data(customer_code):
    ws = get_worksheet()
    if ws and customer_code.strip():
        records = ws.get_all_records()
        if records:
            df = pd.DataFrame(records)
            if "顧客コード" in df.columns:
                matched = df[df["顧客コード"].astype(str) == customer_code.strip()]
                if not matched.empty:
                    latest_row = matched.iloc[-1]
                    return latest_row.get("担当者名", "")
    return None

# --- アプリ画面レイアウト ---
st.title("🛠️ メンテナンス依頼フォーム")

tab1, tab2 = st.tabs(["📝 依頼入力", "📋 送信履歴確認"])

# -------------------------------------------------------------------
# TAB 1: 担当者用 入力フォーム
# -------------------------------------------------------------------
with tab1:
    st.subheader("■ 基本情報")
    col_b1, col_b2 = st.columns(2)
    with col_b1:
        request_type = st.selectbox("依頼種別", ["商品発注", "修理依頼", "その他"])

    st.markdown("---")
    st.subheader("■ 顧客 & 担当者情報")
    
    # セッション状態の初期化
    if "staff_name_val" not in st.session_state:
        st.session_state["staff_name_val"] = ""
        
    col_c1, col_c2, col_c3 = st.columns([2, 1, 2])
    with col_c1:
        customer_code = st.text_input("顧客コード", placeholder="例: 10001")
    
    with col_c2:
        st.write(" ") # レイアウト位置調整
        st.write(" ")
        if st.button("🔍 顧客検索", use_container_width=True):
            if customer_code:
                found_staff = search_customer_data(customer_code)
                if found_staff:
                    st.session_state["staff_name_val"] = found_staff
                    st.success(f"顧客データが見つかりました（前回担当: {found_staff}）")
                else:
                    st.info("該当する過去データがありませんでした。新規入力してください。")
            else:
                st.warning("顧客コードを入力してください。")

    with col_c3:
        staff_name = st.text_input("担当者名", value=st.session_state["staff_name_val"])

    st.markdown("---")
    st.subheader("■ 商品明細（最大5件）")
    st.caption("※商品記号が未入力の行は、「伝票出力」「数量」「単価」を含め、自動的にすべて空白として送信されます。")
    
    # 5件分の商品入力欄
    items_input = []
    
    for i in range(1, 6):
        st.markdown(f"**【商品 {i}】**")
        col1, col2, col3, col4 = st.columns([2, 1.2, 1, 1])
        
        with col1:
            code = st.text_input(f"商品記号", key=f"code_{i}")
        with col2:
            print_output = st.selectbox(f"伝票出力", ["有", "無"], key=f"print_{i}")
        with col3:
            qty = st.number_input(f"数量", min_value=0, value=0, key=f"qty_{i}")
        with col4:
            price = st.number_input(f"単価", min_value=0, value=0, key=f"price_{i}")
        
        # 💡 条件制御:
        # 商品記号が入力されている場合のみ「記号・伝票出力・数量・単価」を保持
        # 商品記号が未入力（空欄）の場合は、すべて空白("")をセットする
        if code.strip():
            items_input.extend([code.strip(), print_output, qty, price])
        else:
            items_input.extend(["", "", "", ""])

    st.markdown("---")
    
    # 送信ボタン
    if st.button("送信する", type="primary", use_container_width=True):
        if not staff_name or not customer_code:
            st.warning("「顧客コード」と「担当者名」を入力してください。")
        else:
            ws = get_worksheet()
            if ws:
                ensure_headers(ws)
                
                # 1行分のデータを作成
                now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                row_data = [now_str, request_type, staff_name, customer_code] + items_input
                
                # スプレッドシートへ追加
                ws.append_row(row_data)
                st.success("✅ 送信が完了しました！")
                st.balloons()

# -------------------------------------------------------------------
# TAB 2: 送信履歴確認
# -------------------------------------------------------------------
with tab2:
    st.subheader("📋 送信済みデータ確認")
    
    if st.button("最新状態に更新"):
        st.cache_data.clear()
        st.rerun()
        
    ws = get_worksheet()
    if ws:
        records = ws.get_all_records()
        if records:
            df = pd.DataFrame(records)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("まだ送信されたデータはありません。")
