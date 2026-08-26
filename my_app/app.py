/**
 * 顧客対応記録 入力フォーム (Google Apps Script 版)
 *
 * このスクリプトは対象スプレッドシートに「バインド」して使います
 * （スプレッドシートの「拡張機能」→「Apps Script」から開いたプロジェクトに
 *   このファイルと index.html を貼り付けてください）。
 *
 * 書き込み先: このスクリプトがバインドされているスプレッドシートの gid=0 のシート
 * 列構成（書き込み先）:
 *   A: タイムスタンプ（日本時間）
 *   B: 拠点
 *   C: 名前
 *   D: 顧客コード
 *   E: 顧客名
 *   F: お客様担当者名
 *   G: 住所
 *   H: 電話番号
 *   I: サービス内容
 *   J: 加盟店（顧客コードから自動検索）
 *   K: コメント
 *
 * 顧客マスタ（顧客コードから顧客名・加盟店を検索する参照元、同じスプレッドシート内）:
 *   大阪北店 (gid=1050026582)：A=加盟店名, B=顧客コード, C=顧客名（2行目からデータ）
 *   大阪中央店 (gid=1628566858)：B=顧客コード, C=顧客名, E=加盟店名（2行目からデータ）
 */

var TARGET_GID = 0; // 書き込み先シート（gid=0）
var TIMEZONE = 'Asia/Tokyo';

// 拠点ごとの顧客マスタの参照設定（列番号は1始まり: A=1, B=2, C=3, D=4, E=5）
var MASTER_CONFIG = {
  '大阪北店': { gid: 1050026582, codeCol: 2, nameCol: 3, affiliateCol: 1 },
  '大阪中央店': { gid: 1628566858, codeCol: 2, nameCol: 3, affiliateCol: 5 },
};

/**
 * ウェブアプリとしてアクセスされたときに index.html を返す
 */
function doGet() {
  return HtmlService.createTemplateFromFile('index')
    .evaluate()
    .setTitle('顧客対応記録フォーム')
    .addMetaTag('viewport', 'width=device-width, initial-scale=1')
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}

/**
 * index.html から他のファイルをインクルードするためのヘルパー（今回は未使用だが将来の拡張用）
 */
function include(filename) {
  return HtmlService.createHtmlOutputFromFile(filename).getContent();
}

/**
 * JSON APIとしてのエンドポイント（Streamlit版など、外部アプリからの書き込み用）
 * サービスアカウント等の認証は不要。POST本文にJSONで顧客対応記録を送ると1行追記する。
 *
 * リクエスト例:
 *   POST {デプロイURL}/exec
 *   Content-Type: application/json
 *   { "location": "...", "name": "...", "customerCode": "...", "customerName": "...",
 *     "affiliateName": "...", "customerContact": "...", "address": "...", "phone": "...",
 *     "service": "...", "serviceOther": "...", "comment": "..." }
 *
 * レスポンス: { "status": "success", "timestamp": "..." } または { "status": "error", "message": "..." }
 */
function doPost(e) {
  var output;
  try {
    if (!e || !e.postData || !e.postData.contents) {
      throw new Error('リクエストの本文が空です。');
    }
    var record = JSON.parse(e.postData.contents);
    var result = submitRecord(record);
    output = result;
  } catch (err) {
    output = { status: 'error', message: err.message };
  }
  return ContentService
    .createTextOutput(JSON.stringify(output))
    .setMimeType(ContentService.MimeType.JSON);
}

/**
 * 指定gidのシートを取得する
 */
function getSheetByGid_(gid) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheets = ss.getSheets();
  for (var i = 0; i < sheets.length; i++) {
    if (sheets[i].getSheetId() === gid) {
      return sheets[i];
    }
  }
  return null;
}

/**
 * 書き込み先シート（gid=0）を取得する。見つからない場合は先頭のシートを返す。
 */
function getTargetSheet_() {
  var sheet = getSheetByGid_(TARGET_GID);
  if (sheet) return sheet;
  return SpreadsheetApp.getActiveSpreadsheet().getSheets()[0];
}

/**
 * 拠点と顧客コードから、顧客マスタの該当行を検索する。
 * @param {string} location - '大阪北店' | '大阪中央店'
 * @param {string} customerCode
 * @return {{customerName:string, affiliateName:string}|null}
 */
function lookupCustomer(location, customerCode) {
  var config = MASTER_CONFIG[location];
  var code = (customerCode || '').toString().trim();
  if (!config || !code) return null;

  var sheet = getSheetByGid_(config.gid);
  if (!sheet) throw new Error('顧客マスタのシートが見つかりません（' + location + '）。');

  var lastRow = sheet.getLastRow();
  if (lastRow < 2) return null;

  var maxCol = Math.max(config.codeCol, config.nameCol, config.affiliateCol);
  var values = sheet.getRange(2, 1, lastRow - 1, maxCol).getValues();

  for (var i = 0; i < values.length; i++) {
    var row = values[i];
    var rowCode = (row[config.codeCol - 1] || '').toString().trim();
    if (rowCode === code) {
      return {
        customerName: (row[config.nameCol - 1] || '').toString().trim(),
        affiliateName: (row[config.affiliateCol - 1] || '').toString().trim(),
      };
    }
  }
  return null; // 見つからなかった
}

/**
 * フォームから送信されたデータを1行追記する
 * @param {Object} record - {location, name, customerCode, customerName, affiliateName,
 *                            customerContact, address, phone, service, serviceOther, comment}
 */
function submitRecord(record) {
  if (!record) {
    throw new Error('データが空です。');
  }
  var name = (record.name || '').toString().trim();
  var customerName = (record.customerName || '').toString().trim();
  var service = (record.service || '').toString().trim();
  var serviceOther = (record.serviceOther || '').toString().trim();

  if (!name) throw new Error('「名前」は必須です。');
  if (!customerName) throw new Error('「顧客名」は必須です。');
  if (!service) throw new Error('「サービス内容」は必須です。');
  if (service === 'その他（自由記述）' && !serviceOther) {
    throw new Error('「サービス内容（自由記述）」を入力してください。');
  }

  var lock = LockService.getScriptLock();
  lock.waitLock(30000);
  try {
    var sheet = getTargetSheet_();
    var timestamp = Utilities.formatDate(new Date(), TIMEZONE, 'yyyy-MM-dd HH:mm:ss');
    var serviceValue = service === 'その他（自由記述）' ? serviceOther : service;

    sheet.appendRow([
      timestamp,
      (record.location || '').toString().trim(),
      name,
      (record.customerCode || '').toString().trim(),
      customerName,
      (record.customerContact || '').toString().trim(),
      (record.address || '').toString().trim(),
      (record.phone || '').toString().trim(),
      serviceValue,
      (record.affiliateName || '').toString().trim(),
      (record.comment || '').toString().trim(),
    ]);

    return { status: 'success', timestamp: timestamp };
  } finally {
    lock.releaseLock();
  }
}

/**
 * 直近N件の入力履歴を新しい順で返す（確認用の一覧表示に使用）
 */
function getRecentRecords(n) {
  n = n || 15;
  var sheet = getTargetSheet_();
  var lastRow = sheet.getLastRow();
  if (lastRow < 2) return [];

  var startRow = Math.max(2, lastRow - n + 1);
  var numRows = lastRow - startRow + 1;
  var values = sheet.getRange(startRow, 1, numRows, 11).getValues();

  // 表示用に文字列化しつつ新しい順に並べ替える
  var rows = values.map(function (r) {
    return r.map(function (cell) {
      if (Object.prototype.toString.call(cell) === '[object Date]') {
        return Utilities.formatDate(cell, TIMEZONE, 'yyyy-MM-dd HH:mm:ss');
      }
      return cell;
    });
  });
  return rows.reverse();
}
