"""
顧客対応記録 入力フォーム (Streamlit + GAS連携版／サービスアカウント不要)

大阪中央店・大阪北店の2拠点で、顧客対応の記録を1件ずつ入力し、
指定のGoogleスプレッドシートに1行ずつ追記するフォームアプリです。
「顧客コード」を入力すると、拠点ごとの顧客マスタシートを検索し、
「顧客名」「加盟店」を自動入力します（見つからない場合は手入力できます）。

【このバージョンの特徴】
Google CloudでのAPI有効化・サービスアカウント発行は一切不要です。
  - 書き込み: GAS（Google Apps Script）をウェブアプリとしてデプロイし、
    そのURLにこのアプリからJSONをPOSTして1行追記します（GAS側は自分のGoogleアカウント権限で書き込む）。
  - 読み込み（顧客マスタ検索・入力履歴表示）: スプレッドシートを
    「リンクを知っている全員が閲覧可」に設定し、公開CSVエクスポートURLを
    pandasで直接読み込みます。

【重要な注意】読み込みを公開CSV方式にするため、対象スプレッドシートは
「リンクを知っている全員 - 閲覧者」に共有する必要があります。これは
シート単位ではなくスプレッドシート全体（顧客名・住所・電話番号を含む
全タブ）が対象になります。リンクを知っている人なら誰でも閲覧できる
（Googleログイン不要）状態になる点を理解した上でご利用ください。
社外に見られたくない場合は、この方式ではなく service account 版
（サービスアカウントで権限を絞る版）をご検討ください。

書き込み先:
  https://docs.google.com/spreadsheets/d/1w7voPP_y3gKVILOw-Nz9odn9ZC4q32TlGJ0ZnO5Y-0U/edit?gid=0#gid=0
  （gid=0 のシートに固定で書き込みます）

列構成（書き込み先）:
  A: タイムスタンプ（日本時間）
  B: 拠点
  C: 担当者名
  D: 顧客コード
  E: 加盟店名（顧客コードから自動検索）
  F: 顧客名（顧客コードから自動検索）
  G: お客様担当者
  H: 住所
  I: 電話番号
  J: サービス内容
  K: 問い合わせ内容
  L: コメント

顧客マスタ（顧客コードから顧客名・加盟店を検索する参照元、同じスプレッドシート内）:
  大阪北店   (gid=1050026582): A=加盟店名, B=顧客コード, C=顧客名（2行目からデータ）
  大阪中央店 (gid=1628566858): B=顧客コード, C=顧客名, E=加盟店名（2行目からデータ）

事前準備 (README.md を参照):
  1. スプレッドシートを「リンクを知っている全員が閲覧者」で共有する
  2. スプレッドシートの「拡張機能」→「Apps Script」で、GAS版フォームと同じ
     Code.gs（doPost対応済みのもの）を貼り付けてウェブアプリとしてデプロイする
  3. 発行された「ウェブアプリのURL」を、下の GAS_URL に貼り付ける
  4. gid=0 のシートの1行目に見出し行（A〜L列）を入力しておく
"""

import io
import json

import pandas as pd
import requests
import streamlit as st

# ------------------------------------------------------------
# 基本設定
# ------------------------------------------------------------
st.set_page_config(page_title="顧客対応記録フォーム", page_icon="📝", layout="centered")

# ▼▼▼ ここを、デプロイしたGASウェブアプリのURLに書き換えてください ▼▼▼
GAS_URL = "https://script.google.com/macros/s/AKfycbwz3xx0o6w5D8BgFjKDzHQFWp-M4NMlVxA_m1iYH_xBOE46hahTms-RQL1cpqDUvqU7xg/exec"
# ▲▲▲ ここまで ▲▲▲

SPREADSHEET_ID = "1w7voPP_y3gKVILOw-Nz9odn9ZC4q32TlGJ0ZnO5Y-0U"
TARGET_GID = 0  # 書き込み先シート（gid=0）

HEADERS = [
    "タイムスタンプ", "拠点", "担当者名", "顧客コード", "加盟店名", "顧客名",
    "お客様担当者", "住所", "電話番号", "サービス内容", "問い合わせ内容", "コメント",
]

LOCATIONS = ["大阪中央店", "大阪北店"]
SERVICE_OPTIONS = ["サービスマスター", "ターミニックス", "メリーメイド", "その他（自由記述）"]

# 拠点ごとの顧客マスタ参照設定（列は0始まりのインデックス: A=0, B=1, C=2, D=3, E=4）
MASTER_CONFIG = {
    "大阪北店": {"gid": 1050026582, "code_col": 1, "name_col": 2, "affiliate_col": 0},
    "大阪中央店": {"gid": 1628566858, "code_col": 1, "name_col": 2, "affiliate_col": 4},
}

REQUEST_HEADERS = {"User-Agent": "Mozilla/5.0"}


def csv_url(gid: int) -> str:
    return f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&gid={gid}"


def _fetch_csv(gid: int) -> pd.DataFrame:
    """公開CSVエクスポートを取得してDataFrameにする（fsspec等の追加依存なしでrequestsのみ使用）"""
    res = requests.get(csv_url(gid), headers=REQUEST_HEADERS, timeout=20)
    res.raise_for_status()
    return pd.read_csv(io.StringIO(res.content.decode("utf-8-sig")), dtype=str)


# ------------------------------------------------------------
# 読み込み（公開CSVエクスポートを直接読む。API・認証不要）
# ------------------------------------------------------------
@st.cache_data(ttl=60, show_spinner=False)
def load_master(location: str) -> dict:
    """拠点の顧客マスタを {顧客コード: {customer_name, affiliate_name}} の形で読み込む"""
    cfg = MASTER_CONFIG[location]
    df = _fetch_csv(cfg["gid"])  # 1行目は見出しとして自動的に読み飛ばされる
    df = df.fillna("")

    lookup = {}
    max_col = max(cfg["code_col"], cfg["name_col"], cfg["affiliate_col"])
    if df.shape[1] <= max_col:
        return lookup

    for _, row in df.iterrows():
        code = str(row.iloc[cfg["code_col"]]).strip()
        if not code:
            continue
        lookup[code] = {
            "customer_name": str(row.iloc[cfg["name_col"]]).strip(),
            "affiliate_name": str(row.iloc[cfg["affiliate_col"]]).strip(),
        }
    return lookup


def lookup_customer(location: str, code: str):
    code = code.strip()
    if not code:
        return None
    return load_master(location).get(code)


def load_recent(n: int = 15) -> pd.DataFrame:
    df = _fetch_csv(TARGET_GID)
    df = df.fillna("")
    if df.empty:
        return pd.DataFrame(columns=HEADERS)
    # 列名がヘッダー行とズレていても表示できるよう、列数を合わせて付け替える
    cols = HEADERS[: df.shape[1]] if df.shape[1] <= len(HEADERS) else HEADERS + [
        f"col{i}" for i in range(len(HEADERS), df.shape[1])
    ]
    df.columns = cols
    return df.tail(n).iloc[::-1]


# ------------------------------------------------------------
# 書き込み（GASウェブアプリにJSONをPOSTする。API・認証不要）
# ------------------------------------------------------------
def submit_record(record: dict) -> dict:
    try:
        res = requests.post(GAS_URL, data=json.dumps(record, ensure_ascii=False).encode("utf-8"),
                             headers={"Content-Type": "application/json"}, timeout=30)
        res.raise_for_status()
        return res.json()
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ------------------------------------------------------------
# 画面
# ------------------------------------------------------------
st.title("📝 顧客対応記録フォーム")
st.caption("入力して送信すると、スプレッドシートに1行追加されます。")

if "【ここにデプロイID" in GAS_URL:
    st.warning(
        "GAS_URL が未設定です。README.md の手順にそって GAS をウェブアプリとしてデプロイし、"
        "発行された URL を app.py 冒頭の GAS_URL に貼り付けてください。"
    )

# --- 顧客コード検索（フォームの外に置き、入力のたびに即検索する） ---
location = st.selectbox("拠点 *", LOCATIONS, key="location_select")
customer_code = st.text_input(
    "顧客コード", key="customer_code_input", help="入力すると加盟店名・顧客名を自動検索します"
)

combo_key = f"{location}:{customer_code.strip()}"
if combo_key != st.session_state.get("_last_lookup_combo"):
    st.session_state["_last_lookup_combo"] = combo_key
    if customer_code.strip():
        try:
            result = lookup_customer(location, customer_code)
        except Exception:
            result = None
        if result:
            st.session_state["customer_name_input"] = result["customer_name"]
            st.session_state["affiliate_input"] = result["affiliate_name"]
        else:
            st.session_state["customer_name_input"] = ""
            st.session_state["affiliate_input"] = ""

if customer_code.strip():
    try:
        found = lookup_customer(location, customer_code)
    except Exception as e:
        found = None
        st.error(f"顧客マスタの読み込みに失敗しました: {e}")
    if found:
        st.success(f"✓ 顧客情報が見つかりました：{found['affiliate_name']} / {found['customer_name']}")
    else:
        st.warning("該当する顧客コードが見つかりませんでした。加盟店名・顧客名は手入力してください。")

with st.form("entry_form", clear_on_submit=True):
    name = st.text_input("担当者名 *", help="対応した担当者の名前")
    affiliate = st.text_input("加盟店名", key="affiliate_input")
    customer_name = st.text_input("顧客名 *", key="customer_name_input")
    customer_contact = st.text_input("お客様担当者")
    address = st.text_input("住所")
    phone = st.text_input("電話番号")
    service = st.selectbox("サービス内容 *", SERVICE_OPTIONS)

    service_other = ""
    if service == "その他（自由記述）":
        service_other = st.text_input("サービス内容（自由記述） *")

    inquiry_content = st.text_area("問い合わせ内容")
    comment = st.text_area("コメント")

    submitted = st.form_submit_button("送信", type="primary", use_container_width=True)

    if submitted:
        errors = []
        if "【ここにデプロイID" in GAS_URL:
            errors.append("GAS_URL が未設定のため送信できません。")
        if not name.strip():
            errors.append("「担当者名」は必須です。")
        if not customer_name.strip():
            errors.append("「顧客名」は必須です。")
        if service == "その他（自由記述）" and not service_other.strip():
            errors.append("「サービス内容（自由記述）」を入力してください。")

        if errors:
            for err in errors:
                st.warning(err)
        else:
            record = {
                "location": location,
                "name": name.strip(),
                "customerCode": customer_code.strip(),
                "affiliateName": affiliate.strip(),
                "customerName": customer_name.strip(),
                "customerContact": customer_contact.strip(),
                "address": address.strip(),
                "phone": phone.strip(),
                "service": service,
                "serviceOther": service_other.strip(),
                "inquiryContent": inquiry_content.strip(),
                "comment": comment.strip(),
            }
            result = submit_record(record)
            if result.get("status") == "success":
                st.success(f"登録しました（{result.get('timestamp')} / {location} / {customer_name}）。")
                st.session_state.pop("customer_code_input", None)
                st.session_state.pop("_last_lookup_combo", None)
                st.cache_data.clear()
                st.rerun()
            else:
                st.error(f"送信に失敗しました: {result.get('message', '不明なエラー')}")

st.divider()
st.subheader("直近の入力履歴")
if st.button("🔄 履歴を更新"):
    st.cache_data.clear()
    st.rerun()
try:
    recent_df = load_recent(15)
    if recent_df.empty:
        st.caption("まだ入力データがありません。")
    else:
        st.dataframe(recent_df, use_container_width=True, hide_index=True)
except Exception as e:
    st.error(f"履歴の読み込みに失敗しました: {e}")
