import streamlit as st
import pandas as pd

# 1. 画面のデザイン設定
st.set_page_config(page_title="商品検索アプリ", layout="centered")

st.title("🔍 商品検索アプリ")
st.write("品記号をリストから選択、または直接入力してください。")

# 2. スプレッドシートの読み込み
SHEET_ID = '1_7zcANuyis77mx0OfAw1TNZ2sfYn7Cifb74mmilSIH4'
URL = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv'

@st.cache_data # データを毎回読み込まないようにキャッシュして高速化
def load_data():
    df = pd.read_csv(URL)
    df.columns = [str(c).strip() for c in df.columns]
    return df

try:
    df = load_data()
    col_code = df.columns[0]  # A列：品コード
    col_sign = df.columns[1]  # B列：品記号

    # 全ての品記号をリストとして取得（重複削除）
    sign_list = df[col_sign].astype(str).unique().tolist()
    sign_list.sort() # アルファベット順に並び替え

    # 3. 検索UI（セレクトボックスに変更）
    # index=None にすることで、最初は何も選択されていない状態にします
    selected_sign = st.selectbox(
        "品記号を選択または検索",
        options=sign_list,
        index=None,
        placeholder="ここに入力して検索..."
    )

    if selected_sign:
        # 選択された品記号と一致する行を抽出
        result = df[df[col_sign].astype(str) == selected_sign]

        if not result.empty:
            raw_code = result.iloc[0][col_code]
            
            # 小数点を除去する処理
            try:
                if pd.notnull(raw_code):
                    # 数値なら整数に変換、文字ならそのまま
                    display_code = int(float(raw_code)) if isinstance(raw_code, (int, float, complex)) or str(raw_code).replace('.','',1).isdigit() else raw_code
                else:
                    display_code = "データなし"
            except:
                display_code = raw_code

            st.success("該当する品コードが見つかりました！")
            st.markdown(f"### 品コード: `{display_code}`")
            
    # データ確認用
    with st.expander("登録データ一覧を表示"):
        st.write(df)

except Exception as e:
    st.error("データの読み込みに失敗しました。")
    st.info("スプレッドシートの共有設定を確認してください。")