/**
 * 回饋收集：早報每則熱點的「👍 用了 / 👎 不用」連結 → 記錄到這份試算表。
 * 部署：試算表 → 擴充功能 → Apps Script → 貼上 → 部署 → 網頁應用程式
 *       （執行身分：我；存取權：所有人）→ 把網址設成 GitHub Secret FEEDBACK_URL。
 * 每週彙整：試算表 → 檔案 → 分享 → 發布到網路 → 選「回饋」分頁、格式 CSV → 網址設成 FEEDBACK_CSV_URL。
 * 欄位：timestamp | date | id | topic | vote(used/skip)
 */
function doGet(e) {
  var p = e.parameter || {};
  if (p.v !== 'used' && p.v !== 'skip') {
    return HtmlService.createHtmlOutput('參數錯誤');
  }
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sh = ss.getSheetByName('回饋') || ss.insertSheet('回饋');
  var lock = LockService.getScriptLock();
  lock.waitLock(5000);
  try {
    sh.appendRow([new Date(), p.d || '', p.id || '', p.t || '', p.v]);
  } finally {
    lock.releaseLock();
  }
  return HtmlService.createHtmlOutput(
    '<meta name="viewport" content="width=device-width,initial-scale=1">' +
    '<div style="font-family:sans-serif;text-align:center;margin-top:20vh;font-size:20px">' +
    (p.v === 'used' ? '✅ 已記錄：用了' : '✅ 已記錄：不用') + '<br><small style="color:#888">可以關閉這個分頁了</small></div>');
}
