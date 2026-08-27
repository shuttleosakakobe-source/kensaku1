"""
顧客対応記録 入力フォーム (Streamlit + GAS連携版／サービスアカウント不要)

大阪中央店・大阪北店の2拠点で、顧客対応の記録を1件ずつ入力し、
指定のGoogleスプレッドシートに1行ずつ追記するフォームアプリです。
「顧客コード」を入力すると、拠点ごとの顧客マスタシートを検索し、
「加盟店名」「加盟店コード」「顧客名」を自動入力します（見つからない場合は手入力できます）。
また、加盟店ごとに最大3件をまとめて印刷用フォーマットに反映し、PDFを作成できます。

【このバージョンの特徴】
Google CloudでのAPI有効化・サービスアカウント発行は一切不要です。
  - 書き込み: GAS（Google Apps Script）をウェブアプリとしてデプロイし、
    そのURLにこのアプリからJSONをPOSTして1行追記・印刷データ反映します
    （GAS側は自分のGoogleアカウント権限で書き込む）。
  - 読み込み（顧客マスタ検索・印刷対象データ取得）: スプレッドシートを
    「リンクを知っている全員が閲覧可」に設定し、公開CSVエクスポートURLを
    pandasで直接読み込みます。

【重要な注意】読み込みを公開CSV方式にするため、対象スプレッドシートは
「リンクを知っている全員 - 閲覧者」に共有する必要があります。これは
シート単位ではなくスプレッドシート全体（顧客名・住所・電話番号を含む
全タブ）が対象になります。リンクを知っている人なら誰でも閲覧できる
（Googleログイン不要）状態になる点を理解した上でご利用ください。

書き込み先:
  https://docs.google.com/spreadsheets/d/1w7voPP_y3gKVILOw-Nz9odn9ZC4q32TlGJ0ZnO5Y-0U/edit?gid=0#gid=0
  （gid=0 のシートに固定で書き込みます）

印刷用フォーマットシート:
  https://docs.google.com/spreadsheets/d/1w7voPP_y3gKVILOw-Nz9odn9ZC4q32TlGJ0ZnO5Y-0U/edit?gid=537872220#gid=537872220
  （同じスプレッドシート内、gid=537872220。加盟店ごとに最大3件を1ページに印刷するテンプレート）

列構成（書き込み先）:
  A: タイムスタンプ（日本時間）
  B: 拠点
  C: 担当者名
  D: 顧客コード
  E: 加盟店名（顧客コードから自動検索）
  F: 加盟店コード（顧客コードから自動検索）
  G: 顧客名（顧客コードから自動検索）
  H: お客様担当者
  I: 住所
  J: 電話番号
  K: サービス内容
  L: 問い合わせ内容
  M: コメント

顧客マスタ（顧客コードから顧客名・加盟店名・加盟店コードを検索する参照元、同じスプレッドシート内）:
  大阪北店   (gid=1050026582): A=加盟店名, B=顧客コード, C=顧客名, E=加盟店コード（2行目からデータ）
  大阪中央店 (gid=1628566858): A=加盟店名, B=顧客コード, C=顧客名, E=加盟店コード（2行目からデータ）

印刷用フォーマットシートのセル対応（1ページ最大3件、ブロックは15行おき）:
  C1: 加盟店名（ページ共通）
  各ブロック（1件目は開始行4、2件目は19、3件目は34）の相対位置:
    startRow+0: A=送信日(月/日) B=加盟店コード C=顧客名 D=顧客コード
    startRow+2: A=住所 B=電話番号 D=担当者名
    startRow+4: A=お客様担当者 C=サービス内容
    startRow+6: A=問い合わせ内容
    startRow+8: A=コメント

事前準備 (README.md を参照):
  1. スプレッドシートを「リンクを知っている全員が閲覧者」で共有する
  2. スプレッドシートの「拡張機能」→「Apps Script」で、GAS版フォームと同じ
     Code.gs（doPost / SYNC_PRINT_DATA対応済みのもの）を貼り付けてウェブアプリとしてデプロイする
  3. 発行された「ウェブアプリのURL」を、下の GAS_URL に貼り付ける
  4. gid=0 のシートの1行目に見出し行（A〜M列）を入力しておく
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
GAS_URL = "https://script.google.com/macros/s/AKfycbzzesJCutR6o9-_LEE-ytaoYlmEjOfpVo7FWD1igH33GgwgVaNXRp4EHpdXPTosqupxcw/exec"
# ▲▲▲ ここまで ▲▲▲

SPREADSHEET_ID = "1w7voPP_y3gKVILOw-Nz9odn9ZC4q32TlGJ0ZnO5Y-0U"
TARGET_GID = 0  # 書き込み先シート（gid=0）
PRINT_GID = 537872220  # 印刷用フォーマットシート

HEADERS = [
    "タイムスタンプ", "拠点", "担当者名", "顧客コード", "加盟店名", "加盟店コード", "顧客名",
    "お客様担当者", "住所", "電話番号", "サービス内容", "問い合わせ内容", "コメント",
]

LOCATIONS = ["大阪中央店", "大阪北店"]
SERVICE_OPTIONS = ["サービスマスター", "ターミニックス", "メリーメイド", "その他（自由記述）"]

# 拠点ごとの顧客マスタ参照設定（列は0始まりのインデックス: A=0, B=1, C=2, D=3, E=4）
MASTER_CONFIG = {
    "大阪北店": {"gid": 1050026582, "affiliate_name_col": 0, "code_col": 1, "name_col": 2, "affiliate_code_col": 4},
    "大阪中央店": {"gid": 1628566858, "affiliate_name_col": 0, "code_col": 1, "name_col": 2, "affiliate_code_col": 4},
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
    """拠点の顧客マスタを {顧客コード: {customer_name, affiliate_name, affiliate_code}} の形で読み込む"""
    cfg = MASTER_CONFIG[location]
    df = _fetch_csv(cfg["gid"])  # 1行目は見出しとして自動的に読み飛ばされる
    df = df.fillna("")

    lookup = {}
    max_col = max(cfg["affiliate_name_col"], cfg["code_col"], cfg["name_col"], cfg["affiliate_code_col"])
    if df.shape[1] <= max_col:
        return lookup

    for _, row in df.iterrows():
        code = str(row.iloc[cfg["code_col"]]).strip()
        if not code:
            continue
        lookup[code] = {
            "customer_name": str(row.iloc[cfg["name_col"]]).strip(),
            "affiliate_name": str(row.iloc[cfg["affiliate_name_col"]]).strip(),
            "affiliate_code": str(row.iloc[cfg["affiliate_code_col"]]).strip(),
        }
    return lookup


def lookup_customer(location: str, code: str):
    code = code.strip()
    if not code:
        return None
    return load_master(location).get(code)


@st.cache_data(ttl=30, show_spinner=False)
def load_all_records() -> pd.DataFrame:
    """書き込み先シートの全レコードを読み込む（印刷対象の抽出に使用）"""
    df = _fetch_csv(TARGET_GID)
    df = df.fillna("")
    if df.empty:
        return pd.DataFrame(columns=HEADERS)
    cols = HEADERS[: df.shape[1]] if df.shape[1] <= len(HEADERS) else HEADERS + [
        f"col{i}" for i in range(len(HEADERS), df.shape[1])
    ]
    df.columns = cols
    return df


# ------------------------------------------------------------
# 書き込み（GASウェブアプリにJSONをPOSTする。API・認証不要）
# ------------------------------------------------------------
def call_gas(payload: dict) -> dict:
    try:
        res = requests.post(GAS_URL, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                             headers={"Content-Type": "application/json"}, timeout=30)
        res.raise_for_status()
        return res.json()
    except Exception as e:
        return {"status": "error", "message": str(e)}


def submit_record(record: dict) -> dict:
    payload = dict(record)
    payload["action"] = "SUBMIT_RECORD"
    return call_gas(payload)


def sync_print_data(affiliate_name: str, blocks: list) -> dict:
    payload = {"action": "SYNC_PRINT_DATA", "c1Value": affiliate_name, "blocks": blocks}
    return call_gas(payload)


# ------------------------------------------------------------
# 印刷用データ組み立て
# ------------------------------------------------------------
def _short_date(timestamp: str) -> str:
    """'yyyy-MM-dd HH:mm:ss' 形式のタイムスタンプから 'MM/DD' を取り出す"""
    date_part = (timestamp or "").split(" ")[0]
    parts = date_part.split("-")
    if len(parts) == 3:
        return f"{parts[1]}/{parts[2]}"
    return date_part


def build_print_matrix(row: dict | None) -> list:
    """1件分のレコードを、ブロック開始行を起点にした9行×4列の行列に変換する"""
    blank = ["", "", "", ""]
    matrix = [blank[:] for _ in range(9)]
    if row is None:
        return matrix
    matrix[0] = [
        _short_date(row.get("タイムスタンプ", "")),
        row.get("加盟店コード", ""),
        row.get("顧客名", ""),
        row.get("顧客コード", ""),
    ]
    matrix[2] = [row.get("住所", ""), row.get("電話番号", ""), "", row.get("担当者名", "")]
    matrix[4] = [row.get("お客様担当者", ""), "", row.get("サービス内容", ""), ""]
    matrix[6] = [row.get("問い合わせ内容", ""), "", "", ""]
    matrix[8] = [row.get("コメント", ""), "", "", ""]
    return matrix


def build_print_pdf_url(row_end: int, col_end: int = 4) -> str:
    """印刷用フォーマットシートの範囲をPDFとして書き出すURLを作る
    （row_end/col_endは0始まりの終端。col_end=4はA〜D列を含む）"""
    params = {
        "format": "pdf",
        "gid": PRINT_GID,
        "size": "A4",
        "portrait": "true",
        "fitw": "true",
        "top_margin": "0.4",
        "bottom_margin": "0.4",
        "left_margin": "0.4",
        "right_margin": "0.4",
        "sheetnames": "false",
        "printtitle": "false",
        "pagenumbers": "false",
        "gridlines": "false",
        "fzr": "false",
        "horizontal_alignment": "CENTER",
        "vertical_alignment": "TOP",
        "r1": "0",
        "c1": "0",
        "r2": str(row_end),
        "c2": str(col_end),
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?{query}"


# ------------------------------------------------------------
# 画面
# ------------------------------------------------------------
st.title("📝 顧客対応記録フォーム")

if "【ここにデプロイID" in GAS_URL:
    st.warning(
        "GAS_URL が未設定です。README.md の手順にそって GAS をウェブアプリとしてデプロイし、"
        "発行された URL を app.py 冒頭の GAS_URL に貼り付けてください。"
    )

tab_entry, tab_print = st.tabs(["📝 入力", "🖨️ 印刷"])

# ============================================================
# 入力タブ
# ============================================================
with tab_entry:
    st.caption("入力して送信すると、スプレッドシートに1行追加されます。")

    # --- 顧客コード検索（フォームの外に置き、入力のたびに即検索する） ---
    location = st.selectbox("拠点 *", LOCATIONS, key="location_select")
    customer_code = st.text_input(
        "顧客コード", key="customer_code_input", help="入力すると加盟店名・加盟店コード・顧客名を自動検索します"
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
                st.session_state["affiliate_code_input"] = result["affiliate_code"]
            else:
                st.session_state["customer_name_input"] = ""
                st.session_state["affiliate_input"] = ""
                st.session_state["affiliate_code_input"] = ""

    if customer_code.strip():
        try:
            found = lookup_customer(location, customer_code)
        except Exception as e:
            found = None
            st.error(f"顧客マスタの読み込みに失敗しました: {e}")
        if found:
            st.success(
                f"✓ 顧客情報が見つかりました：{found['affiliate_name']} / "
                f"{found['affiliate_code']} / {found['customer_name']}"
            )
        else:
            st.warning("該当する顧客コードが見つかりませんでした。加盟店名・加盟店コード・顧客名は手入力してください。")

    with st.form("entry_form", clear_on_submit=True):
        name = st.text_input("担当者名 *", help="対応した担当者の名前")
        affiliate = st.text_input("加盟店名", key="affiliate_input")
        affiliate_code = st.text_input("加盟店コード", key="affiliate_code_input")
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
                    "affiliateCode": affiliate_code.strip(),
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

# ============================================================
# 印刷タブ
# ============================================================
with tab_print:
    st.caption("加盟店を選ぶと、その加盟店のデータを最大3件ずつ印刷用フォーマットに反映してPDFを作成します。")

    if st.button("🔄 データを更新", key="print_refresh"):
        st.cache_data.clear()
        st.rerun()

    try:
        all_df = load_all_records()
    except Exception as e:
        all_df = pd.DataFrame(columns=HEADERS)
        st.error(f"データの読み込みに失敗しました: {e}")

    affiliates = sorted([a for a in all_df["加盟店名"].unique() if a.strip()]) if not all_df.empty else []

    if not affiliates:
        st.info("印刷対象のデータがありません。")
    else:
        selected_affiliate = st.selectbox("印刷する加盟店", affiliates, key="print_affiliate_select")
        store_df = all_df[all_df["加盟店名"] == selected_affiliate].reset_index(drop=True)
        total = len(store_df)
        st.write(f"🏪 加盟店: **{selected_affiliate}** （該当データ: {total} 件）※1ページに最大3件まで配置されます。")

        chunk_size = 3
        chunks = [store_df.iloc[i:i + chunk_size] for i in range(0, total, chunk_size)]

        for page_idx, chunk in enumerate(chunks):
            st.markdown(f"#### 📄 ページ {page_idx + 1} / {len(chunks)}")
            with st.expander(f"プレビューを見る（{len(chunk)} 件）"):
                st.dataframe(
                    chunk[["顧客名", "顧客コード", "担当者名", "サービス内容"]],
                    use_container_width=True, hide_index=True,
                )

            if st.button("📥 反映してPDFを作成する", key=f"print_sync_btn_{page_idx}", type="primary"):
                blocks = []
                for slot in range(3):
                    start_row = 4 + slot * 15
                    row_dict = chunk.iloc[slot].to_dict() if slot < len(chunk) else None
                    blocks.append({"startRow": start_row, "matrix": build_print_matrix(row_dict)})

                with st.spinner("印刷用フォーマットシートへ反映しています..."):
                    res = sync_print_data(selected_affiliate, blocks)

                if res.get("status") == "success":
                    st.success("反映が完了しました。PDFを作成しています…")
                    try:
                        row_end = 1 + len(chunk) * 15
                        with st.spinner("PDFを作成しています..."):
                            pdf_res = requests.get(build_print_pdf_url(row_end), timeout=30)
                        content_type = pdf_res.headers.get("Content-Type", "")
                        if pdf_res.status_code == 200 and "pdf" in content_type.lower():
                            st.download_button(
                                "📄 PDFをダウンロード",
                                data=pdf_res.content,
                                file_name=f"{selected_affiliate}_p{page_idx + 1}.pdf",
                                mime="application/pdf",
                                key=f"pdf_dl_{page_idx}",
                            )
                        else:
                            print_url = (
                                f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}"
                                f"/edit?gid={PRINT_GID}#gid={PRINT_GID}"
                            )
                            st.warning(
                                "スプレッドシートへの反映は完了しましたが、アプリ上でのPDF取得に失敗しました"
                                "（共有設定などが原因の可能性があります）。"
                                f"[印刷用フォーマットシートを開く]({print_url}) から印刷（PDF保存）してください。"
                            )
                    except Exception as pdf_err:
                        st.warning(f"スプレッドシートへの反映は完了しましたが、PDF取得中にエラーが発生しました: {pdf_err}")
                else:
                    st.error(f"反映に失敗しました: {res.get('message', '不明なエラー')}")
