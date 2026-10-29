/**
 * 「要早報」按鈕：網頁上按一下 → 呼叫 GitHub Actions 的 daily-brief → 約 3–5 分鐘後網站更新。
 * GitHub 權杖存在 Script Properties（網頁看不到）；用 PIN 擋外人；10 分鐘內只能要一次。
 *
 * 設定（專案設定 → 指令碼屬性）：
 *   GH_TOKEN  GitHub fine-grained token（只給這個 repo 的 Actions: Read and write）
 *   GH_REPO   例如 your-name/airspace-morning-brief
 *   GH_REF    分支名，預設 main
 *   PIN       自訂按鈕密碼
 * 網站上的「要早報」按鈕會 POST 到這個網址（doPost）；直接開網址也有一個簡易按鈕頁（doGet）。
 * 部署：部署 → 新增部署作業 → 網頁應用程式 → 執行身分：我；存取權：所有人 → 把網址存成手機主畫面捷徑。
 */
function doGet() {
  return HtmlService.createHtmlOutputFromFile('index')
    .setTitle('Airspace 早報')
    .addMetaTag('viewport', 'width=device-width, initial-scale=1');
}

function doPost(e) {
  var pin = '';
  try { pin = JSON.parse(e.postData.contents).pin; } catch (err) {}
  return ContentService.createTextOutput(JSON.stringify(requestBrief(pin)))
    .setMimeType(ContentService.MimeType.JSON);
}

function requestBrief(pin) {
  var props = PropertiesService.getScriptProperties();
  var cache = CacheService.getScriptCache();
  var lock = LockService.getScriptLock();
  lock.waitLock(10000);
  try {
    if (Number(cache.get('fails') || 0) >= 5) {
      return { ok: false, msg: '密碼錯誤次數過多，請 15 分鐘後再試' };
    }
    if (!pin || pin !== props.getProperty('PIN')) {
      cache.put('fails', String(Number(cache.get('fails') || 0) + 1), 900);
      return { ok: false, msg: '密碼錯誤' };
    }
    cache.remove('fails');
    var now = Date.now(), last = Number(props.getProperty('LAST_RUN') || 0);
    if (now - last < 10 * 60 * 1000) {
      return { ok: false, msg: '10 分鐘內已經要過一次了，請等網站更新' };
    }
    var res = UrlFetchApp.fetch(
      'https://api.github.com/repos/' + props.getProperty('GH_REPO') + '/actions/workflows/daily.yml/dispatches', {
        method: 'post',
        contentType: 'application/json',
        headers: {
          Authorization: 'Bearer ' + props.getProperty('GH_TOKEN'),
          Accept: 'application/vnd.github+json',
          'X-GitHub-Api-Version': '2022-11-28'
        },
        payload: JSON.stringify({ ref: props.getProperty('GH_REF') || 'main' }),
        muteHttpExceptions: true
      });
    var code = res.getResponseCode();
    if (code === 204) {
      props.setProperty('LAST_RUN', String(now));
      return { ok: true, msg: '✅ 已開始產生，約 約 3–5 分鐘後網站更新' };
    }
    return { ok: false, msg: 'GitHub 回應 ' + code + '：' + res.getContentText().slice(0, 150) };
  } finally {
    lock.releaseLock();
  }
}
