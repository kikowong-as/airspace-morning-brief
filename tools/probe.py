#!/usr/bin/env python3
"""驗證來源用。在「可以連網」的電腦上執行：
  python tools/probe.py rss  https://tw.news.yahoo.com/rss
  python tools/probe.py html https://example.com "h3.title a"
印出前 15 筆會被抓到的標題，確認網址 / 選擇器可用後，再填進 config/sources.yaml 並把 enabled 改成 true。
注意：JS 動態渲染的頁面（如 Threads、X、Pinterest）用 requests 抓不到內容，需改用其他方式，或乾脆不要用這個來源。"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from brief.collectors import c_html, c_rss  # noqa: E402

if len(sys.argv) < 3:
    sys.exit(__doc__)
kind, url = sys.argv[1], sys.argv[2]
src = {"name": "probe", "zone": "news", "url": url, "selector": sys.argv[3] if len(sys.argv) > 3 else "", "weight": 1}
items = (c_rss if kind == "rss" else c_html)(src)
print(f"共 {len(items)} 筆")
for i in items[:15]:
    print(f"{i.rank:>2}. {i.title}")
