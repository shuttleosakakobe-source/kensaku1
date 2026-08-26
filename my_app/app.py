"""
顧客対応記録 入力フォーム (Streamlit + Google Sheets)

大阪中央店・大阪北店の2拠点で、顧客対応の記録を1件ずつ入力し、
指定のGoogleスプレッドシートに1行ずつ追記するフォームアプリです。

書き込み先:
  https://docs.google.com/spreadsheets/d/1w7voPP_y3gKVILOw-Nz9odn9ZC4q32TlGJ0ZnO5Y-0U/edit?gid=0#gid=0
  （gid=0 のシートに固定で書き込みます）

列構成:
  A: タイムスタンプ（日本時間）
  B: 拠点
  C: 名前
  D: 顧客コード
  E: 顧客名
  F: お客様担当者名
  G: 住所
  H: 電話番号
  I: サービス内容

事前準備 (README.md を参照):
  1. Google Cloud でサービスアカウントを作成し、JSON鍵を取得
  2. 上記スプレッドシートをサービスアカウントのメールアドレスに「編集者」共有
  3. .streamlit/secrets.toml にサービスアカウント情報を設定
  4. gid=0 のシートの1行目に見出し行（A〜I列）を入力しておく
"""

from datetime import datetime
from zoneinfo import ZoneInfo

import gspread
import pandas as pd
import streamlit as st
from google.oauth2.service_account import Credentials

# ------------------------------------------------------------
# 基本設定
# ------------------------------------------------------------
st.set_page_config(page_title="顧客対応記録フォーム", page_icon="📝", layout="centered")

SPREADSHEET_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1w7voPP_y3gKVILOw-Nz9odn9ZC4q32TlGJ0ZnO5Y-0U/edit?gid=0#gid=0"
)
TARGET_GID = 0  # gid=0 のシートに固定で書き込む

HEADERS = [
    "タイムスタンプ", "拠点", "名前", "顧客コード", "顧客名",
    "お客様担当者名", "住所", "電話番号", "サービス内容",
]

LOCATIONS = ["大阪中央店", "大阪北店"]
SERVICE_OPTIONS = ["サービスマスター", "ターミニックス", "メリーメイド", "その他（自由記述）"]

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


# ------------------------------------------------------------
# Google Sheets 接続
# ------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def get_worksheet():
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    client = gspread.authorize(creds)
    sh = client.open_by_url(SPREADSHEET_URL)
    return sh.get_worksheet_by_id(TARGET_GID)


def append_record(row: list) -> None:
    ws = get_worksheet()
    ws.append_row(row, value_input_option="USER_ENTERED")


def load_recent(n: int = 15) -> pd.DataFrame:
    ws = get_worksheet()
    values = ws.get_all_values()
    data_rows = values[1:] if len(values) > 1 else []
    trimmed = [r[: len(HEADERS)] + [""] * (len(HEADERS) - len(r)) for r in data_rows]
    df = pd.DataFrame(trimmed, columns=HEADERS)
    return df.tail(n).iloc[::-1]  # 新しい順に表示


# ------------------------------------------------------------
# 画面
# ------------------------------------------------------------
st.title("📝 顧客対応記録フォーム")
st.caption("入力して送信すると、スプレッドシートに1行追加されます。")

try:
    get_worksheet()
    connection_ok = True
except Exception as e:
    connection_ok = False
    st.error(
        "スプレッドシートに接続できませんでした。secrets.toml の設定と、"
        "サービスアカウントへの共有権限（編集者）を確認してください。\n\n"
        f"詳細: {e}"
    )

if connection_ok:
    with st.form("entry_form", clear_on_submit=True):
        location = st.selectbox("拠点 *", LOCATIONS)
        name = st.text_input("名前 *", help="対応した担当者の名前")
        customer_code = st.text_input("顧客コード")
        customer_name = st.text_input("顧客名 *")
        customer_contact = st.text_input("お客様担当者名")
        address = st.text_input("住所")
        phone = st.text_input("電話番号")
        service = st.selectbox("サービス内容 *", SERVICE_OPTIONS)

        service_other = ""
        if service == "その他（自由記述）":
            service_other = st.text_input("サービス内容（自由記述） *")

        submitted = st.form_submit_button("送信", type="primary", use_container_width=True)

        if submitted:
            errors = []
            if not name.strip():
                errors.append("「名前」は必須です。")
            if not customer_name.strip():
                errors.append("「顧客名」は必須です。")
            if service == "その他（自由記述）" and not service_other.strip():
                errors.append("「サービス内容（自由記述）」を入力してください。")

            if errors:
                for err in errors:
                    st.warning(err)
            else:
                timestamp = datetime.now(ZoneInfo("Asia/Tokyo")).strftime("%Y-%m-%d %H:%M:%S")
                service_value = service_other.strip() if service == "その他（自由記述）" else service
                row = [
                    timestamp,
                    location,
                    name.strip(),
                    customer_code.strip(),
                    customer_name.strip(),
                    customer_contact.strip(),
                    address.strip(),
                    phone.strip(),
                    service_value,
                ]
                try:
                    append_record(row)
                    st.success(f"登録しました（{timestamp} / {location} / {customer_name}）。")
                except Exception as e:
                    st.error(f"書き込みに失敗しました: {e}")

    st.divider()
    st.subheader("直近の入力履歴")
    if st.button("🔄 履歴を更新"):
        st.rerun()
    try:
        recent_df = load_recent(15)
        if recent_df.empty:
            st.caption("まだ入力データがありません。")
        else:
            st.dataframe(recent_df, use_container_width=True, hide_index=True)
    except Exception as e:
        st.error(f"履歴の読み込みに失敗しました: {e}")
