"""
顧客対応記録 入力フォーム (Streamlit + GAS連携版／サービスアカウント不要)

大阪中央店・大阪北店の2拠点で、顧客対応の記録を1件ずつ入力し、
指定のGoogleスプレッドシートに1行ずつ追記するフォームアプリです。
「顧客コード」を入力して「検索」ボタンを押すと、拠点ごとの顧客マスタシートを検索し、
「加盟店名」「加盟店コード」「顧客名」「お客様担当者」「住所」「電話番号」を自動入力します
（見つからない場合は手入力できます）。
また、加盟店ごとに最大3件をまとめて印刷用フォーマットに反映し、PDFを作成してダウンロードできます。
反映が完了したレコードは書き込み先シートのN列（印刷済）に自動でチェックが入り、以降は印刷タブの
一覧に表示されなくなります（「印刷済みも表示する」で再表示可能）。

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

顧客マスタ（顧客コードから顧客名・加盟店名・加盟店コード・お客様担当者・住所・電話番号を検索する
参照元、同じスプレッドシート内。D列は未使用）:
  大阪北店   (gid=1050026582): A=加盟店名, B=顧客コード, C=顧客名, E=加盟店コード,
             F=お客様担当者, G=住所, H=電話番号（2行目からデータ）
  大阪中央店 (gid=1628566858): 大阪北店と同じ列構成

なお「入力フォームの並び順」はアプリ側だけの表示上の並びで、書き込み先スプレッドシートの
列構成（上記）には影響しません。フォームでは「お客様担当者」を「電話番号」と「サービス内容」の
間に表示しています。

印刷用フォーマットシートのセル対応（1ページ最大3件、ブロックは15行おき）:
  ※ 印刷用テンプレート自体に印字されているラベル（送信日/顧客コード/顧客名/シャトルコード等）
     に合わせて実データを書き込む。「シャトルコード」欄には加盟店コードを書き込む。
  ※ テンプレートの見出しの黒帯（各ブロックの相対1,3,5,7行目）は書き込み対象に含めない
     （実データが入る行だけをピンポイントで書き込み、見出しを消してしまわないようにする）。
  C1: 加盟店名（ページ共通、書き込み先データのE列に対応、末尾に「様」を付けて表示）
  各ブロック（1件目は開始行4、2件目は19、3件目は34）の相対位置:
    startRow+0: A=送信日(○月○日形式、書き込み先A列)  B=顧客コード(D列)  C=顧客名(G列、末尾に「様」)  D=シャトルコード＝加盟店コード(F列)
    startRow+2: A=住所(I列)  D=担当者名(C列)
    startRow+4: A=お客様担当者(H列、末尾に「様」)  B=電話番号(J列、先頭0が消えないようテキスト形式で書き込み)  C=サービス内容(K列)
    startRow+6: A=問い合わせ内容(L列)
    startRow+8: A=コメント(M列)

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
GAS_URL = "https://script.google.com/macros/s/【ここにデプロイIDを貼り付け】/exec"
# ▲▲▲ ここまで ▲▲▲

SPREADSHEET_ID = "1w7voPP_y3gKVILOw-Nz9odn9ZC4q32TlGJ0ZnO5Y-0U"
TARGET_GID = 0  # 書き込み先シート（gid=0）
PRINT_GID = 537872220  # 印刷用フォーマットシート

HEADERS = [
    "タイムスタンプ", "拠点", "担当者名", "顧客コード", "加盟店名", "加盟店コード", "顧客名",
    "お客様担当者", "住所", "電話番号", "サービス内容", "問い合わせ内容", "コメント",
]
# N列（14列目、書き込み先データではHEADERSの次の列）: 印刷済みチェック欄
# （ユーザー側で追加したチェックボックス列。印刷タブで「反映してPDFを作成する」を押すと、
# 対象レコードにチェックが入り、以降は印刷タブの一覧に表示されなくなる。
# 実際にN列へチェックを入れる処理はCode.gs側のPRINTED_COLで行う）
PRINTED_HEADER = "印刷済"

LOCATIONS = ["大阪中央店", "大阪北店"]
SERVICE_OPTIONS = ["サービスマスター", "ターミニックス", "メリーメイド", "その他（自由記述）"]

# 拠点ごとの顧客マスタ参照設定（列は0始まりのインデックス: A=0, B=1, C=2, D=3, E=4, F=5, G=6, H=7）
# F=お客様担当者, G=住所, H=電話番号 を追加（両店舗とも同じ列構成）
MASTER_CONFIG = {
    "大阪北店": {
        "gid": 1050026582, "affiliate_name_col": 0, "code_col": 1, "name_col": 2, "affiliate_code_col": 4,
        "contact_col": 5, "address_col": 6, "phone_col": 7,
    },
    "大阪中央店": {
        "gid": 1628566858, "affiliate_name_col": 0, "code_col": 1, "name_col": 2, "affiliate_code_col": 4,
        "contact_col": 5, "address_col": 6, "phone_col": 7,
    },
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
    """拠点の顧客マスタを {顧客コード: {customer_name, affiliate_name, affiliate_code,
    customer_contact, address, phone}} の形で読み込む"""
    cfg = MASTER_CONFIG[location]
    df = _fetch_csv(cfg["gid"])  # 1行目は見出しとして自動的に読み飛ばされる
    df = df.fillna("")

    lookup = {}
    max_col = max(
        cfg["affiliate_name_col"], cfg["code_col"], cfg["name_col"], cfg["affiliate_code_col"],
        cfg["contact_col"], cfg["address_col"], cfg["phone_col"],
    )
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
            "customer_contact": str(row.iloc[cfg["contact_col"]]).strip(),
            "address": str(row.iloc[cfg["address_col"]]).strip(),
            "phone": str(row.iloc[cfg["phone_col"]]).strip(),
        }
    return lookup


def lookup_customer(location: str, code: str):
    code = code.strip()
    if not code:
        return None
    return load_master(location).get(code)


def _is_printed(value) -> bool:
    """印刷済み列（チェックボックス）の値が「チェック済み」を表すかどうかを判定する
    （Googleスプレッドシートのチェックボックスは公開CSVでは TRUE/FALSE の文字列になる）"""
    v = str(value if value is not None else "").strip().lower()
    return v in {"true", "1", "済", "✓", "レ", "yes", "y", "on"}


@st.cache_data(ttl=30, show_spinner=False)
def load_all_records() -> pd.DataFrame:
    """書き込み先シートの全レコードを読み込む（印刷対象の抽出に使用）。
    行番号（_sheet_row）と印刷済みフラグ（PRINTED_HEADER列があれば）も付与する。"""
    df = _fetch_csv(TARGET_GID)
    df = df.fillna("")
    all_cols = HEADERS + [PRINTED_HEADER]
    if df.empty:
        return pd.DataFrame(columns=all_cols + ["_sheet_row"])

    extra = df.shape[1] - len(HEADERS)
    if extra <= 0:
        cols = HEADERS[: df.shape[1]]
    else:
        extra_names = [PRINTED_HEADER] + [f"col{i}" for i in range(len(HEADERS) + 1, df.shape[1])]
        cols = HEADERS + extra_names[:extra]
    df.columns = cols
    df["_sheet_row"] = df.index + 2  # 1行目は見出し、データは2行目から
    if PRINTED_HEADER not in df.columns:
        df[PRINTED_HEADER] = ""
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


def sync_print_data(affiliate_name: str, blocks: list, printed_rows: list) -> dict:
    payload = {
        "action": "SYNC_PRINT_DATA",
        "c1Value": _with_sama(affiliate_name),
        "blocks": blocks,
        "printedRows": printed_rows,  # 印刷済みチェック（N列）を入れる行番号
    }
    return call_gas(payload)


# ------------------------------------------------------------
# 印刷用データ組み立て
# ------------------------------------------------------------
def _short_date(timestamp: str) -> str:
    """'yyyy-MM-dd HH:mm:ss' 形式のタイムスタンプから '○月○日' の形式を取り出す"""
    date_part = (timestamp or "").split(" ")[0]
    parts = date_part.split("-")
    if len(parts) == 3:
        try:
            month = int(parts[1])
            day = int(parts[2])
            return f"{month}月{day}日"
        except ValueError:
            pass
    return date_part


def _with_sama(value: str) -> str:
    """名称の後ろに「様」を付ける（空欄の場合は付けない）"""
    value = (value or "").strip()
    return f"{value}様" if value else ""


def build_print_cells(row: dict | None) -> list:
    """1件分のレコードを、ブロック開始行からの相対オフセット・列・値の1セルずつのリストに変換する。
    テンプレートの見出しの黒帯（相対1,3,5,7行目）は書き込み対象に含めない。
    各セルは1つずつ個別に書き込む（そのセルが結合範囲の一部でも、結合の左上セルに
    正しく書き込まれるようにするため。特に「お問い合わせ内容」「コメント」は結合幅が
    他と違う可能性があるので、行単位ではなくセル単位で扱う）。
    顧客名・お客様担当者は印刷時に「様」を付けて表示する。"""
    if row is None:
        row = {}
    return [
        {"offset": 0, "col": 1, "value": _short_date(row.get("タイムスタンプ", ""))},
        {"offset": 0, "col": 2, "value": row.get("顧客コード", "")},
        {"offset": 0, "col": 3, "value": _with_sama(row.get("顧客名", ""))},
        {"offset": 0, "col": 4, "value": row.get("加盟店コード", "")},
        {"offset": 2, "col": 1, "value": row.get("住所", "")},
        {"offset": 2, "col": 4, "value": row.get("担当者名", "")},
        {"offset": 4, "col": 1, "value": _with_sama(row.get("お客様担当者", ""))},
        {"offset": 4, "col": 2, "value": row.get("電話番号", "")},
        {"offset": 4, "col": 3, "value": row.get("サービス内容", "")},
        {"offset": 6, "col": 1, "value": row.get("問い合わせ内容", "")},
        {"offset": 8, "col": 1, "value": row.get("コメント", "")},
    ]


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


# 入力タブのフォームは「バージョン番号」をキーに含めることでクリアする。
# session_state.pop() でウィジェットの値を消そうとすると、ブラウザ側がまだ古い値を
# 保持しているタイミング次第で消えたり消えなかったりする現象があったため、
# 送信成功時・クリアボタンの両方で form_version を1つ増やし、
# 「まったく新しいキーを持つ、まっさらなウィジェット」を作り直す方式にしている。
if "form_version" not in st.session_state:
    st.session_state["form_version"] = 0


def _field_key(base: str) -> str:
    return f"{base}_{st.session_state['form_version']}"


def _clear_entry_form():
    """入力タブのフォームを全項目クリアする（送信成功時／クリアボタンの両方から呼ばれる）"""
    st.session_state["form_version"] += 1
    st.session_state.pop("_lookup_result", None)


# ------------------------------------------------------------
# 画面
# ------------------------------------------------------------
# 送信直後は st.rerun() で画面がすぐ再描画されるため、その場で st.toast() を呼んでも
# 表示される前に消えてしまう。次の実行の一番最初でポップアップ表示するように、
# 「表示待ちのメッセージ」を session_state 経由で1回だけ持ち越す。
_pending_toast = st.session_state.pop("_pending_toast", None)
if _pending_toast:
    st.toast(_pending_toast, icon="✅")

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

    # --- 顧客コード検索（「検索」ボタンを押したときだけ検索する） ---
    location = st.selectbox("拠点 *", LOCATIONS, key="location_select")

    code_col, btn_col, clear_col = st.columns([3, 1, 1])
    with code_col:
        customer_code = st.text_input(
            "顧客コード", key=_field_key("customer_code_input"),
            help="入力後に「検索」を押すと加盟店名・加盟店コード・顧客名・お客様担当者・住所・電話番号を自動検索します",
        )
    with btn_col:
        st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
        search_clicked = st.button("🔍 検索", key="lookup_btn", use_container_width=True)
    with clear_col:
        st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
        clear_clicked = st.button("🧹 クリア", key="clear_form_btn", use_container_width=True)

    if clear_clicked:
        _clear_entry_form()
        st.rerun()

    if search_clicked:
        code = customer_code.strip()
        if not code:
            st.warning("顧客コードを入力してから「検索」を押してください。")
            st.session_state.pop("_lookup_result", None)
        else:
            try:
                result = lookup_customer(location, code)
            except Exception as e:
                st.error(f"顧客マスタの読み込みに失敗しました: {e}")
                st.session_state.pop("_lookup_result", None)
            else:
                if result:
                    st.session_state[_field_key("customer_name_input")] = result["customer_name"]
                    st.session_state[_field_key("affiliate_input")] = result["affiliate_name"]
                    st.session_state[_field_key("affiliate_code_input")] = result["affiliate_code"]
                    st.session_state[_field_key("contact_input")] = result["customer_contact"]
                    st.session_state[_field_key("address_input")] = result["address"]
                    st.session_state[_field_key("phone_input")] = result["phone"]
                # 見つからなかった場合は、既に入力されている「顧客名」等を消さない
                # （手入力していた内容が検索失敗で消えて、送信時に「必須」エラーになるのを防ぐ）
                st.session_state["_lookup_result"] = {
                    "combo": f"{location}:{code}",
                    "found": bool(result),
                    "affiliate_name": result["affiliate_name"] if result else "",
                    "affiliate_code": result["affiliate_code"] if result else "",
                    "customer_name": result["customer_name"] if result else "",
                }

    # 検索ボタンを押した時点のコード・拠点のままなら、その結果メッセージを表示し続ける
    # （検索後に顧客コードや拠点を変更した場合は、再度「検索」を押すまで表示しない）
    lookup_result = st.session_state.get("_lookup_result")
    if lookup_result and lookup_result["combo"] == f"{location}:{customer_code.strip()}":
        if lookup_result["found"]:
            st.success(
                f"✓ 顧客情報が見つかりました：{lookup_result['affiliate_name']} / "
                f"{lookup_result['affiliate_code']} / {lookup_result['customer_name']}"
                "（お客様担当者・住所・電話番号も自動入力しました）"
            )
        else:
            st.warning(
                "該当する顧客コードが見つかりませんでした。"
                "加盟店名・加盟店コード・顧客名・お客様担当者・住所・電話番号は手入力してください。"
            )

    # clear_on_submit は使わない。加盟店名・加盟店コード・顧客名を検索結果で
    # あらかじめ session_state にセットしている都合上、clear_on_submit との
    # 組み合わせで「表示上は値が入っているのに送信時に空扱いされる」不具合が
    # 起きることがあるため、送信後のクリアは全項目を自前で行う（下記参照）。
    with st.form("entry_form", clear_on_submit=False):
        name = st.text_input("担当者名 *", help="対応した担当者の名前", key=_field_key("name_input"))
        affiliate = st.text_input("加盟店名", key=_field_key("affiliate_input"))
        affiliate_code = st.text_input("加盟店コード", key=_field_key("affiliate_code_input"))
        customer_name = st.text_input("顧客名 *", key=_field_key("customer_name_input"))
        address = st.text_input("住所", key=_field_key("address_input"))
        phone = st.text_input("電話番号", key=_field_key("phone_input"))
        customer_contact = st.text_input("お客様担当者", key=_field_key("contact_input"))
        service = st.selectbox("サービス内容 *", SERVICE_OPTIONS, key=_field_key("service_select"))

        service_other = ""
        if service == "その他（自由記述）":
            service_other = st.text_input("サービス内容（自由記述） *", key=_field_key("service_other_input"))

        inquiry_content = st.text_area("問い合わせ内容", key=_field_key("inquiry_input"))
        comment = st.text_area("コメント", key=_field_key("comment_input"))

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
                    # 直後に st.rerun() するのでその場のメッセージはすぐ消えてしまう。
                    # 次の画面表示の一番最初でポップアップ（トースト）表示されるようにする。
                    st.session_state["_pending_toast"] = (
                        f"登録しました（{result.get('timestamp')} / {location} / {customer_name}）"
                    )
                    # clear_on_submit を使わず、フォーム内の全項目をここで明示的にリセットする
                    # （連続で入力したときに前の顧客の情報が残ってしまう不具合を避けるため）。
                    _clear_entry_form()
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error(f"送信に失敗しました: {result.get('message', '不明なエラー')}")

# ============================================================
# 印刷タブ
# ============================================================
with tab_print:
    st.caption("加盟店を選ぶと、その加盟店のデータを最大3件ずつ印刷用フォーマットに反映してPDFを作成します。")
    st.caption("印刷済み（N列にチェック）のレコードは、一覧から自動的に非表示になります。")

    col_refresh, col_show_all = st.columns([1, 2])
    with col_refresh:
        if st.button("🔄 データを更新", key="print_refresh"):
            st.cache_data.clear()
            st.rerun()
    with col_show_all:
        show_printed = st.checkbox("印刷済みも表示する", key="print_show_printed")

    try:
        all_df = load_all_records()
    except Exception as e:
        all_df = pd.DataFrame(columns=HEADERS + [PRINTED_HEADER, "_sheet_row"])
        st.error(f"データの読み込みに失敗しました: {e}")

    target_df = all_df if show_printed else all_df[~all_df[PRINTED_HEADER].apply(_is_printed)] if not all_df.empty else all_df

    affiliates = sorted([a for a in target_df["加盟店名"].unique() if a.strip()]) if not target_df.empty else []

    if not affiliates:
        st.info("印刷対象のデータがありません（すべて印刷済みの場合は「印刷済みも表示する」で確認できます）。")
    else:
        selected_affiliate = st.selectbox("印刷する加盟店", affiliates, key="print_affiliate_select")
        store_df = target_df[target_df["加盟店名"] == selected_affiliate].reset_index(drop=True)
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
                printed_rows = []
                for slot in range(3):
                    start_row = 4 + slot * 15
                    if slot < len(chunk):
                        row_dict = chunk.iloc[slot].to_dict()
                        sheet_row = row_dict.get("_sheet_row")
                        if sheet_row:
                            printed_rows.append(int(sheet_row))
                    else:
                        row_dict = None
                    blocks.append({"startRow": start_row, "cells": build_print_cells(row_dict)})

                with st.spinner("印刷用フォーマットシートへ反映しています..."):
                    res = sync_print_data(selected_affiliate, blocks, printed_rows)

                if res.get("status") == "success":
                    st.success("反映が完了しました（印刷済みとしてチェックしました）。PDFを作成しています…")
                    st.cache_data.clear()  # 次回の一覧読み込みから、今回印刷した分を除外する
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
                    st.caption("反映済みのため、次に「🔄 データを更新」を押すとこのレコードは一覧から消えます。")
                else:
                    st.error(f"反映に失敗しました: {res.get('message', '不明なエラー')}")
