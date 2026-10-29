"""把早報寫成靜態網站（docs/），由 GitHub Pages 提供。每天覆蓋 index.html，並保留 archive/ 歷史。"""
import html
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs")


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def publish(page_html, date):
    _write(os.path.join(DOCS, "index.html"), page_html)
    _write(os.path.join(DOCS, "archive", f"{date}.html"), page_html)
    _write(os.path.join(DOCS, ".nojekyll"), "")
    if not os.path.exists(os.path.join(DOCS, "weekly.html")):   # 第一次週彙整之前，避免連結 404
        publish_weekly("尚無資料：需要先累積「用了/不用」回饋，每週一早上 09:00 會自動產生第一份彙整。", "—")
    days = sorted((f[:-5] for f in os.listdir(os.path.join(DOCS, "archive")) if f.endswith(".html") and f != "index.html"),
                  reverse=True)
    li = "".join(f'<li><a href="{d}.html">{html.escape(d)}</a></li>' for d in days)
    _write(os.path.join(DOCS, "archive", "index.html"),
           '<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
           '<title>歷史早報</title><body style="font-family:-apple-system,sans-serif;max-width:480px;margin:24px auto;padding:0 16px">'
           f'<h2>歷史早報</h2><p><a href="../index.html">← 回今天</a></p><ul style="line-height:2">{li}</ul></body>')


def publish_weekly(report_text, date):
    _write(os.path.join(DOCS, "weekly.html"),
           '<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
           '<title>每週回饋彙整</title><body style="font-family:-apple-system,sans-serif;max-width:640px;margin:24px auto;padding:0 16px">'
           f'<h2>每週回饋彙整　{html.escape(date)}</h2><p><a href="index.html">← 回今天</a></p>'
           f'<pre style="white-space:pre-wrap;line-height:1.6">{html.escape(report_text)}</pre></body>')
