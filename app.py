import streamlit as st
import pandas as pd

# 1. 画面デザイン設定（ワイドモード）
st.set_page_config(page_title="商品データAI検索", layout="wide")

st.title("🚀 スマート商品検索システム")
st.write("品コード・品記号のどちらからでも検索できます。関連するPDFページも自動で表示します。")

# 2. スプレッドシート読み込み設定
SHEET_ID = '1_7zcANuyis77mx0OfAw1TNZ2sfYn7Cifb74mmilSIH4'
URL = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv'

@st.cache_data
def load_data():
    try:
        df = pd.read_csv(URL)
        df.columns = [str(c).strip() for c in df.columns]
        # 小数点(.0)を消して文字列として扱う
        for col in df.columns:
            df[col] = df[col].astype(str).str.replace(r'\.0$', '', regex=True)
        return df
    except Exception as e:
        st.error("スプレッドシートの読み込みに失敗しました。共有設定を確認してください。")
        return pd.DataFrame()

# 3. 実行処理
df = load_data()

if not df.empty:
    col_code = df.columns[0]  # A列
    col_sign = df.columns[1]  # B列
    col_page = df.columns[2] if len(df.columns) > 2 else None  # C列

    # 検索窓
    search_query = st.text_input("🔍 検索ワードを入力（記号やコードの一部でOK）", placeholder="ここに入力...")

    if search_query:
        query = search_query.strip().lower()
        # あいまい検索を実行
        result_df = df[
            df[col_code].str.lower().str.contains(query) | 
            df[col_sign].str.lower().str.contains(query)
        ]

        if not result_df.empty:
            st.success(f"{len(result_df)} 件の候補が見つかりました。")
            
            # 複数ヒットした場合は選択させる
            if len(result_df) > 1:
                target_item = st.selectbox("詳細を表示する項目を選択してください", options=result_df[col_sign].tolist())
                final_result = result_df[result_df[col_sign] == target_item].iloc[0]
            else:
                final_result = result_df.iloc[0]

            # 画面を分割（左に情報、右にPDF）
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.subheader("📦 基本情報")
                st.info(f"**品コード:** {final_result[col_code]}")
                st.info(f"**品記号:** {final_result[col_sign]}")
                
                # ページ番号取得
                res_page = "1"
                if col_page and final_result[col_page] != "nan":
                    res_page = final_result[col_page]
                
                st.warning(f"📖 カタログ {res_page} ページ付近")
                
                # PDFを別タブで開くボタン（これが最も確実です）
                pdf_base_url = "https://drive.google.com/file/d/1ls9767Kregs2RGKOXU4q_MRjEJmwIhkT"
                st.link_button("📄 PDFを全画面で開く", f"{pdf_base_url}/view?usp=sharing")

            with col2:
                st.subheader("📄 プレビュー")
                # 埋め込み表示
                pdf_embed_url = f"{pdf_base_url}/preview"
                st.markdown(
                    f'<iframe src="{pdf_embed_url}" width="100%" height="800px" allow="autoplay"></iframe>',
                    unsafe_allow_html=True
                )
        else:
            st.warning("一致するデータが見つかりません。")
    else:
        st.info("検索ワードを入力してください。")
