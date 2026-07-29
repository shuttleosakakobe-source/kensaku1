import streamlit as st
import pandas as pd

# ページ設定
st.set_page_config(page_title="メンテナンス依頼システム", page_icon="🔒")

# --- スプレッドシートデータの取得関数 ---
@st.cache_data(ttl=60)  # 60秒間キャッシュして何度も読み込むのを防ぐ
def load_user_data():
    # ご提示のURLからCSV出力用URLを生成
    sheet_id = "1AkMb1J2m3VZAIyMCKmr3T3E8-kJB0BDDdWQJuEn7YGc"
    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid=0"
    
    try:
        # スプレッドシートをPandas DataFrameとして読み込み
        df = pd.read_csv(csv_url)
        return df
    except Exception as e:
        st.error(f"スプレッドシートの読み込みに失敗しました: {e}")
        return None

# --- セッション状態（ログイン状態）の初期化 ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_name" not in st.session_state:
    st.session_state.user_name = ""
if "user_email" not in st.session_state:
    st.session_state.user_email = ""

# --- 画面切り替え ---
if not st.session_state.logged_in:
    # ================= ログイン画面 =================
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
                    # 列名の余分な空白を除去
                    df_users.columns = df_users.columns.str.strip()
                    
                    # A列（メールアドレス）とC列（担当者名）の存在確認
                    # ※列名が異なる場合はインデックス位置（0列目, 2列目）で取得
                    email_col = df_users.columns[0]  # A列
                    name_col = df_users.columns[2]   # C列
                    
                    # 入力されたメールアドレスの検索
                    user_match = df_users[df_users[email_col].astype(str).str.strip().str.lower() == email_input.strip().lower()]
                    
                    if not user_match.empty:
                        # 認証成功
                        matched_name = user_match.iloc[0][name_col]
                        
                        st.session_state.logged_in = True
                        st.session_state.user_email = email_input.strip()
                        st.session_state.user_name = matched_name
                        
                        st.success(f"ログイン成功！ 担当者: {matched_name} 様")
                        st.rerun()  # 画面を再描画してメイン画面へ切り替え
                    else:
                        st.error("登録されていないメールアドレスです。")

else:
    # ================= ログイン後のメイン画面 =================
    # サイドバーにユーザー情報とログアウトボタンを表示
    st.sidebar.write(f"👤 **{st.session_state.user_name}** 様")
    st.sidebar.caption(f"📧 {st.session_state.user_email}")
    
    if st.sidebar.button("ログアウト"):
        st.session_state.logged_in = False
        st.session_state.user_name = ""
        st.session_state.user_email = ""
        st.rerun()

    # メインコンテンツエリア
    st.title("🛠️ メンテナンス依頼システム")
    st.write(f"ようこそ、**{st.session_state.user_name}** さん！")
    
    st.info("ここに今後「メンテナンス依頼書」の機能を実装していきます。")
