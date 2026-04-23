import streamlit as st
import pandas as pd

# 1. 画面デザイン設定
st.set_page_config(page_title="商品データAI検索", layout="wide")

st.title("🚀 スマート商品検索")
st.write("品コードや品記号を自由に入力してください。関連するデータを自動で抽出します。")

# 2. データ読み込み
SHEET_ID = '1_7zcANuyis77mx0OfAw1TNZ2sfYn7Cifb74mmilSIH4'
URL = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv'

@st.cache_data
def load_data():
    df = pd.read_csv(URL)
    df.columns = [str(c).strip() for c in df.columns]
    for col in df.columns:
        df[col] = df[col].astype(str).str.replace(r'\.0$', '', regex=True)
    return df

try:
    df = load_data()
    col_code = df.columns[0]
    col_sign = df.columns[1]
    col_page = df.columns[2] if len(df.columns) > 2 else None

    # 3. 検索UI
    search_query = st.text_input("検索ワードを入力", placeholder="入力を始めると自動で検索します...")

    if search_query:
        query = search_query.strip().lower()
        result_df = df[
            df[col_code].str.lower().str.contains(query) | 
            df[col_sign].str.lower().str.contains(query)
        ]

        if not result_df.empty:
            st.success(f"{len(result_df)} 件の候補が見つかりました。")
            
            if len(result_df) > 1:
                target_item = st.selectbox("詳細を表示する項目を選択", options=result_df[col_sign].tolist())
                final_result = result_df[result_df[col_sign] == target_item].iloc[0]
            else:
                final_result = result_df.iloc[0]

            # 4. 結果表示（ここが重要！）
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.subheader("基本情報")
                st.info(f"**品コード:** {final_result[col_code]}")
                st.info(f"**品記号:** {final_result[col_sign]}")
                
                res_page = 1
                if col_page and final_result[col_page] != "nan":
                    res_page = final_result[col_page]
                    st.warning(f"📖 カタログ {res_page} ページを表示中")

            with col2:
                # PDFを表示するための設定
                pdf_url = f"https://drive.google.com/file/d/1ls9767Kregs2RGKOXU4q_MRjEJmwIhkT/preview"
                st.markdown(
                    f'<iframe src="{pdf_url}" width="100%" height="800px"></iframe>',
                    unsafe_allow_html=True
                )
        else:
            st.warning("一致するデータがありません。")
    else:
        st.info("キーワードを入力してください。")

except Exception as e:
    st.error("エラーが発生しました。")
    st.write(e)
