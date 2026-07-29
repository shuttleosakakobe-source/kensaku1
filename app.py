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

# --- ヘッダー自動設定（後続アプリが読み込みやすい固定列構造） ---
def ensure_headers(ws):
    if ws and len(ws.get_all_values()) == 0:
        headers = ["送信日時", "依頼種別", "担当者名", "顧客コード"]
        for i in range(1, 6):
            headers.extend([f"商品{i}_記号", f"商品{i}_数量", f"商品{i}_単価"])
        ws.append_row(headers)

# --- アプリ画面レイアウト ---
st.title("🛠️ メンテナンス依頼フォーム")

tab1, tab2 = st.tabs(["📝 依頼入力", "📋 送信履歴確認"])

# -------------------------------------------------------------------
# TAB 1: 担当者用 入力フォーム
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
    
    # 商品1〜5の入力フォーム生成
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
        
        # 未入力の場合は空文字（""）をセットして列の数を揃える
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
                
                # 1行分のデータを作成（後続アプリがパースしやすい1行形式）
                now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                row_data = [now_str, request_type, staff_name, customer_code] + items_input
                
                # スプレッドシートへ追加
                ws.append_row(row_data)
                st.success("✅ 送信が完了しました！")
                st.balloons()

# -------------------------------------------------------------------
# TAB 2: 送信後の確認用画面（担当者が送信漏れ・誤りを確認するため）
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
            
            # 簡易検索（自分の送信データを確認用）
            search_kw = st.text_input("顧客コードまたは担当者名で検索", value="", placeholder="例: 10001")
            
            filtered_df = df.copy()
            if search_kw.strip():
                kw = search_kw.strip().lower()
                mask = (
                    filtered_df["顧客コード"].astype(str).str.lower().str.contains(kw) |
                    filtered_df["担当者名"].astype(str).str.lower().str.contains(kw)
                )
                filtered_df = filtered_df[mask]
                
            st.dataframe(filtered_df, use_container_width=True, hide_index=True)
        else:
            st.info("まだ送信されたデータはありません。")
