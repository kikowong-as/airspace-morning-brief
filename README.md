# Airspace 每日熱點早報（網站版）

每天清晨自動蒐集台灣熱點 → 去重排序 → AI 借勢分析 → **更新一個網站**（不寄信）。預算 0：GitHub Actions + GitHub Pages + Gemini 免費額度。

```
06:00  第一層  各來源抓取 → 黑名單過濾 → 語意聚類 → 計分排序（時事 / 穿搭 兩區分開）
       第二層  AI 借勢分析（AI 答事實題，紅綠燈由程式依固定定義判定）
       第三層  產出 docs/index.html（今天）＋ docs/archive/（歷史），commit 回 repo → GitHub Pages 自動發布
網站   右上「要早報」按鈕：隨時重新產生；完成後頁面自動刷新
週一   回饋彙整 → docs/weekly.html，並調整來源權重
```

## 網站功能
- 首頁 = 今天的早報（先看「30 秒重點」，再看兩區卡片；🟢可借 🟡小心 🔴不可借）。
- 頂端列：最後更新時間、「要早報」按鈕、歷史、每週彙整。
- **異常提示**：台灣時間 08:30 後若頁面不是今天的，頁面頂端會自動出現紅色警示（取代原本的看門狗信）。單一來源失敗則顯示在早報最下方；連續 3 天失敗會在頁尾加註給維護者。
- 每則 🟢🟡 有「👍 用了 / 👎 不用」連結（選用，見下）。

## 兩區的資料從哪來
- **區一 今日時事**：Google Trends 台灣、Yahoo 新聞、ETtoday、Dcard 熱門、YouTube 熱門與 Shorts。
- **區二 穿搭與消費趨勢**：Google 新聞關鍵字（穿搭、男生穿搭、女生穿搭、服裝 流行趨勢、潮流 單品，近 7 天）＋ YouTube 關鍵字（近 7 天依觀看數）。男女並列。
- 需要解析網頁的來源（LINE TODAY、蝦皮/momo、Threads、X、Pinterest…）預設關閉，驗證網址後再開。
- 選題男女兼顧：商品為服裝，每則標示 女裝 / 男裝（r.fav）/ 男女皆可。

## 上線步驟
1. 建 GitHub repo，上傳整個資料夾。**要用免費 GitHub Pages，repo 必須是 public**（見下方隱私說明）。
2. 申請免費 key：Gemini（Google AI Studio）、YouTube Data API（Google Cloud）。
3. Repo → Settings → Secrets and variables → Actions：`GEMINI_API_KEY`、`YOUTUBE_API_KEY`（其他見下）。
4. Repo → Settings → **Pages** → Source：Deploy from a branch → 分支 `main`、資料夾 `/docs`。
5. Actions → daily-brief → Run workflow 手動跑第一次；完成後網址是 `https://<帳號>.github.io/<repo名>/`。

### 「要早報」按鈕（選用）
GitHub 網站/App → Actions → daily-brief → Run workflow 本身就能手動觸發。要在網站上放按鈕：
1. GitHub → Settings → Developer settings → Fine-grained tokens，建立只對這個 repo 有 **Actions: Read and write** 的 token。
2. script.google.com 新增專案，貼上 `apps_script/button/Code.gs` 與 `index.html`（HTML 檔命名 `index`）。
3. 專案設定 → 指令碼屬性：`GH_TOKEN`、`GH_REPO`（`帳號/repo名`）、`GH_REF`（預設 main）、`PIN`（自訂密碼）。
4. 部署 → 網頁應用程式 → 執行身分「我」、存取權「所有人」→ 複製網址，設成 GitHub Secret `BUTTON_URL`，再跑一次 workflow。
權杖只存在 Google 後端；有 PIN，錯 5 次鎖 15 分鐘，10 分鐘內只能要一次。同一天重跑不會重複累加失敗天數。

### 回饋「用了/不用」（選用）
建一份試算表，貼上 `apps_script/feedback.gs` 部署成網頁應用程式 → Secret `FEEDBACK_URL`；把「回饋」分頁發布成 CSV → Secret `FEEDBACK_CSV_URL`。沒設就不顯示回饋連結、不做每週調整。

## 隱私（請先決定）
GitHub Pages 的網址不用登入就能看，且免費方案需要 public repo——**知道網址的人都能讀到早報內容，repo 裡的程式與歷史資料也是公開的**（金鑰在 Secrets 裡，不會公開）。若早報只能內部看：
- 付費 GitHub（Pro/Team）可用 private repo 的 Pages 並限制存取；或
- 改放 Cloudflare Pages，並用 Cloudflare Access（免費、最多 50 人）加登入。我可以另外幫您改。

## 本機預覽與測試
`python run.py --mock` → 開 `out/preview.html`（假資料，不連網）。`python -m unittest discover -s tests`。

## 規格對應
- **兩區分開排行**、**訊號強度 × 成長速度**（昨日榜上沒有 ×1.5、名次上升 ×1.2；第一天沒有昨日資料不加成）、**搜尋量只顯示「約 N 萬+」級距**。
- **紅綠燈固定**：燈號由 `decide_light()` 依規格表判定，黑名單關鍵字優先；🔴 不給切入角度與貼文；`risk_note` 只在 🟡 出現。
- **失敗處理**：單一來源失敗 → 頁尾標註；連續 3 天 → 頁尾加註；整體失敗 → 08:30 後頁面紅色提示（Actions 失敗時 GitHub 也會寄預設通知給 repo 擁有者）。

## 我補的假設
1. 規格時程表沒有時間 → 假設 06:00 啟動（改 `.github/workflows/*.yml` 的 cron，UTC，台灣 −8 小時）。
2. 「6 題」只列 3 題 → 依 4.3 輸出欄位推為：情緒、借勢燈號、與服飾連結、切入角度、範例貼文、風險提醒。

## 已知限制
- **開發環境無法連網，所有來源都沒實際連線驗證。** 已驗證：RSS 解析、Google 新聞收集器（假回應）、聚類/計分/燈號、網站輸出與頁面 JS 語法、11 項單元測試。**未驗證**：各網站真實回應、Gemini/YouTube 實際呼叫、GitHub Pages 發布、按鈕跨網域呼叫 Apps Script。標 `verify: true` 的來源請先用 `tools/probe.py` 驗證。
- 區二抓的是「媒體與影片在談什麼」，不等於實際消費熱度，上線一兩週後看內容再調關鍵字。
- Dcard 常擋雲端機房 IP，失敗時會在頁尾標註。
- 沒有 Gemini key 時聚類只靠字面比對；有 key 時用 embedding（邏輯用假向量測過，真實效果需觀察）。
- 「要早報」到頁面更新需 3–5 分鐘（產生約 2 分鐘 + Pages 發布約 1–2 分鐘）。
