import streamlit as st
import pandas as pd
import datetime

# ページ設定
st.set_page_config(page_title="メンテナンス依頼システム", page_icon="🔒", layout="wide")

SHEET_ID = "1AkMb1J2m3VZAIyMCKmr3T3E8-kJB0BDDdWQJuEn7YGc"

# --- ユーザーデータ（gid=0）取得 ---
@st.cache_data(ttl=60)
def load_user_data():
    csv_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0"
    try:
        df = pd.read_csv(csv_url)
        return df
    except Exception as e:
        st.error(f"ユーザーマスターの読み込みに失敗しました: {e}")
        return None

# --- 顧客マスターデータ（gid=127347205）取得 ---
@st.cache_data(ttl=60)
def load_customer_data():
    csv_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=127347205"
    try:
        df = pd.read_csv(csv_url, dtype=str)  # 顧客コードのゼロ落ちを防ぐため文字列指定
        return df
    except Exception as e:
        st.error(f"顧客マスターの読み込みに失敗しました: {e}")
        return None

# --- セッション状態の初期化 ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_name" not in st.session_state:
    st.session_state.user_name = ""
if "user_email" not in st.session_state:
    st.session_state.user_email = ""
if "searched_customer" not in st.session_state:
    st.session_state.searched_customer = None

# ================= ログイン画面 =================
if not st.session_state.logged_in:
    st.title("🔑 ログイン")
    st.caption("登録済みのメールアドレスを入力してください")

    email_input = st.text_input("メールアドレス", placeholder="example@domain.com")
    
    if st.button("ログイン", type="primary"):
        if not email_input:
            st.warning("メールアドレスを入力してください。")
        else:
            with st.spinner("認証中..."):
                df_users = load_user_data()
                if df_users is not None:
                    df_users.columns = df_users.columns.str.strip()
                    email_col = df_users.columns[0]  # A列
                    name_col = df_users.columns[2]   # C列
                    
                    user_match = df_users[df_users[email_col].astype(str).str.strip().str.lower() == email_input.strip().lower()]
                    
                    if not user_match.empty:
                        matched_name = user_match.iloc[0][name_col]
                        st.session_state.logged_in = True
                        st.session_state.user_email = email_input.strip()
                        st.session_state.user_name = matched_name
                        st.success(f"ログイン成功！ 担当者: {matched_name} 様")
                        st.rerun()
                    else:
                        st.error("登録されていないメールアドレスです。")

# ================= ログイン後のメイン画面 =================
else:
    # サイドバー情報
    st.sidebar.write(f"👤 **{st.session_state.user_name}** 様")
    st.sidebar.caption(f"📧 {st.session_state.user_email}")
    
    if st.sidebar.button("ログアウト"):
        st.session_state.logged_in = False
        st.session_state.user_name = ""
        st.session_state.user_email = ""
        st.session_state.searched_customer = None
        st.rerun()

    st.title("📝 メンテナンス依頼書")
    
    if "request_type" not in st.session_state:
        st.session_state.request_type = "商品発注"

    # 依頼種別選択ボタン
    st.subheader("1. 依頼の種類を選択してください")
    request_types = [
        "商品発注", "納品数量変更", "単発ルート変更",
        "ルート変更", "期間ストップ", "契約内容変更",
        "客残訂正", "解約処理", "その他"
    ]
    
    cols = st.columns(3)
    for i, req_type in enumerate(request_types):
        is_selected = (st.session_state.request_type == req_type)
        button_type = "primary" if is_selected else "secondary"
        with cols[i % 3]:
            if st.button(req_type, key=f"btn_{req_type}", type=button_type, use_container_width=True):
                st.session_state.request_type = req_type
                st.rerun()

    st.divider()

    # 選択された種別のフォーム表示エリア
    current_type = st.session_state.request_type
    st.subheader(f"2. {current_type} の入力フォーム")

    # --------------------------------------------------
    # 【商品発注】フォームの実装
    # --------------------------------------------------
    if current_type == "商品発注":
        
        # --- A. 顧客検索エリア ---
        st.markdown("#### 🔍 顧客情報の検索")
        c1, c2 = st.columns([3, 1])
        with c1:
            customer_code_input = st.text_input("顧客コードを入力", placeholder="例: 10001", key="cust_code_input")
        with c2:
            st.write("") # ボタンの位置調整用スペース
            st.write("")
            search_btn = st.button("検索", type="primary", use_container_width=True)

        # 検索ボタンが押された時の処理
        if search_btn:
            if not customer_code_input:
                st.warning("顧客コードを入力してください。")
            else:
                with st.spinner("顧客情報を検索中..."):
                    df_cust = load_customer_data()
                    if df_cust is not None:
                        # 列名調整
                        df_cust.columns = df_cust.columns.str.strip()
                        
                        # インデックスで列を取得（A列:0, B列:1, C列:2, E列:4）
                        col_a_store_name = df_cust.columns[0]  # 加盟店名
                        col_b_cust_code  = df_cust.columns[1]  # 顧客コード
                        col_c_cust_name  = df_cust.columns[2]  # お客様名
                        col_e_store_code = df_cust.columns[4]  # 加盟店コード
                        
                        # B列で一致確認
                        match = df_cust[df_cust[col_b_cust_code].astype(str).str.strip() == customer_code_input.strip()]
                        
                        if not match.empty:
                            row = match.iloc[0]
                            st.session_state.searched_customer = {
                                "code": customer_code_input.strip(),
                                "store_name": str(row[col_a_store_name]),
                                "cust_name": str(row[col_c_cust_name]),
                                "store_code": str(row[col_e_store_code])
                            }
                            st.success("顧客情報が見つかりました！")
                        else:
                            st.session_state.searched_customer = None
                            st.error("指定された顧客コードが見つかりませんでした。")

        # 顧客情報の自動表示
        if st.session_state.searched_customer:
            cust_info = st.session_state.searched_customer
            res_c1, res_c2, res_c3 = st.columns(3)
            with res_c1:
                st.text_input("加盟店名", value=cust_info["store_name"], disabled=True)
            with res_c2:
                st.text_input("お客様名", value=cust_info["cust_name"], disabled=True)
            with res_c3:
                st.text_input("加盟店コード", value=cust_info["store_code"], disabled=True)
        
        st.divider()

        # --- B. 商品発注 明細エリア（5行作成） ---
        st.markdown("#### 📦 発注商品明細（最大5件）")
        
        order_details = []
        
        # ヘッダー列表示
        h1, h2, h3, h4, h5 = st.columns([1, 3, 2, 2, 2])
        h1.markdown("**行**")
        h2.markdown("**商品記号**")
        h3.markdown("**発注数**")
        h4.markdown("**単価**")
        h5.markdown("**伝票出力**")

        # 5行のフォームを作成
        for row_idx in range(1, 6):
            c_no, c_code, c_qty, c_price, c_slip = st.columns([1, 3, 2, 2, 2])
            
            c_no.write(f"#{row_idx}")
            item_code = c_code.text_input(f"商品記号_{row_idx}", label_visibility="collapsed", key=f"item_code_{row_idx}")
            qty = c_qty.number_input(f"発注数_{row_idx}", min_value=0, step=1, label_visibility="collapsed", key=f"qty_{row_idx}")
            price = c_price.number_input(f"単価_{row_idx}", min_value=0, step=100, label_visibility="collapsed", key=f"price_{row_idx}")
            slip = c_slip.selectbox(f"伝票出力_{row_idx}", ["無", "有"], label_visibility="collapsed", key=f"slip_{row_idx}")

            if item_code or qty > 0:
                order_details.append({
                    "行": row_idx,
                    "商品記号": item_code,
                    "発注数": qty,
                    "単価": price,
                    "伝票出力": slip
                })

        st.divider()

        # --- C. 納品情報エリア ---
        st.markdown("#### 🚚 納品情報")
        d_col1, d_col2, d_col3 = st.columns(3)
        
        with d_col1:
            delivery_date = st.date_input("納品日", value=datetime.date.today())
        with d_col2:
            delivery_route = st.text_input("納品ルート", placeholder="例: 月曜Aルート")
        with d_col3:
            # デフォルトはログインした担当者名
            delivery_person = st.text_input("納品者", value=st.session_state.user_name)

        st.write("")
        if st.button("送信する", type="primary", use_container_width=True):
            if not st.session_state.searched_customer:
                st.error("顧客検索を行ってください。")
            elif not order_details:
                st.error("商品情報を1件以上入力してください。")
            else:
                st.success("【商品発注】の受付が完了しました！（送信処理等は別途追加可能です）")
                # 入力結果のプレビュー表示（デバッグ用）
                st.json({
                    "顧客情報": st.session_state.searched_customer,
                    "明細": order_details,
                    "納品日": str(delivery_date),
                    "納品ルート": delivery_route,
                    "納品者": delivery_person
                })

    elif current_type == "納品数量変更":
        st.info("【納品数量変更】のフォームをここに作成します")

    elif current_type == "単発ルート変更":
        st.info("【単発ルート変更】のフォームをここに作成します")

    elif current_type == "ルート変更":
        st.info("【ルート変更】のフォームをここに作成します")

    elif current_type == "期間ストップ":
        st.info("【期間ストップ】のフォームをここに作成します")

    elif current_type == "契約内容変更":
        st.info("【契約内容変更】のフォームをここに作成します")

    elif current_type == "客残訂正":
        st.info("【客残訂正】のフォームをここに作成します")

    elif current_type == "解約処理":
        st.info("【解約処理】のフォームをここに作成します")

    elif current_type == "その他":
        st.info("【その他】のフォームをここに作成します")
