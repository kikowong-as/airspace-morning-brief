"""第一層：各來源抓取。每個 collector 回傳 list[RawItem]；失敗就丟例外，由 collect_all 記錄，不中斷整體。"""
import os
import re
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import requests
from bs4 import BeautifulSoup

from .models import RawItem
from .utils import TZ, clean_title, parse_traffic

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
      "(KHTML, like Gecko) Version/17.0 Safari/605.1.15")
HT_NS = "{https://trends.google.com/trending/rss}"
HT_NS_OLD = "{https://trends.google.com/trends/trendingsearches/daily}"


def _get(url, **kw):
    r = requests.get(url, headers={"User-Agent": UA, "Accept-Language": "zh-TW,zh;q=0.9"},
                     timeout=20, **kw)
    r.raise_for_status()
    return r


def _mk(src, title, rank, url="", traffic=0):
    return RawItem(title=clean_title(title), source=src["name"], zone=src["zone"], rank=rank,
                   url=url, traffic=traffic, weight=src.get("weight", 1.0))


def parse_rss(xml_bytes):
    """回傳 [(title, link, approx_traffic_text)]，不依賴 feedparser。"""
    root = ET.fromstring(xml_bytes)
    out = []
    for it in root.iter("item"):
        title = (it.findtext("title") or "").strip()
        link = (it.findtext("link") or "").strip()
        traffic = it.findtext(HT_NS + "approx_traffic") or it.findtext(HT_NS_OLD + "approx_traffic") or ""
        if title:
            out.append((title, link, traffic))
    if not out:  # Atom
        ns = "{http://www.w3.org/2005/Atom}"
        for e in root.iter(ns + "entry"):
            title = (e.findtext(ns + "title") or "").strip()
            l = e.find(ns + "link")
            if title:
                out.append((title, l.get("href") if l is not None else "", ""))
    return out


def c_google_trends(src):
    rows = parse_rss(_get(src["url"]).content)
    return [_mk(src, t, i + 1, l, parse_traffic(tr)) for i, (t, l, tr) in enumerate(rows)]


def c_rss(src):
    if not src.get("url"):
        raise ValueError("未設定 url")
    rows = parse_rss(_get(src["url"]).content)[: src.get("limit", 30)]
    return [_mk(src, t, i + 1, l) for i, (t, l, _) in enumerate(rows)]


def c_dcard(src):
    # 注意：Dcard 有 Cloudflare 防護，雲端機房 IP（如 GitHub Actions）可能被擋 → 失敗會由監控告警
    posts = _get(src["url"]).json()
    return [_mk(src, p["title"], i + 1, f"https://www.dcard.tw/f/{p.get('forumAlias', '')}/p/{p['id']}")
            for i, p in enumerate(posts)]


def _iso_secs(d):
    m = re.fullmatch(r"PT(?:(\d+)M)?(?:(\d+)S)?", d or "")
    return (int(m.group(1) or 0) * 60 + int(m.group(2) or 0)) if m else 9999


def c_youtube(src):
    key = os.environ.get("YOUTUBE_API_KEY")
    if not key:
        raise RuntimeError("缺少 YOUTUBE_API_KEY")
    r = _get("https://www.googleapis.com/youtube/v3/videos", params={
        "part": "snippet,contentDetails", "chart": "mostPopular", "regionCode": "TW",
        "maxResults": 30, "key": key})
    items = []
    for i, v in enumerate(r.json().get("items", [])):
        short = _iso_secs(v["contentDetails"].get("duration")) <= 60
        items.append(_mk(src, v["snippet"]["title"], i + 1,
                         f"https://www.youtube.com/{'shorts' if short else 'watch?v='}{'/' if short else ''}{v['id']}"))
    return items


def c_html(src):
    if not src.get("url") or not src.get("selector"):
        raise ValueError("未設定 url / selector（請先用 tools/probe.py 驗證）")
    soup = BeautifulSoup(_get(src["url"]).text, "html.parser")
    seen, out = set(), []
    for el in soup.select(src["selector"]):
        t = el.get_text(" ", strip=True)
        if t and t not in seen:
            seen.add(t)
            out.append(_mk(src, t, len(out) + 1))
    return out[: src.get("limit", 30)]


def c_google_news(src):
    """Google 新聞關鍵字搜尋 RSS（公開、免 key）。標題尾巴的「- 媒體名」會被 clean_title 去掉。"""
    q = f"{src['query']} when:{src.get('when', '7d')}"
    r = _get("https://news.google.com/rss/search",
             params={"q": q, "hl": "zh-TW", "gl": "TW", "ceid": "TW:zh-Hant"})
    rows = parse_rss(r.content)[: src.get("limit", 20)]
    return [_mk(src, t, i + 1, l) for i, (t, l, _) in enumerate(rows)]


def c_youtube_search(src):
    """YouTube 官方 API 關鍵字搜尋，取近 N 天觀看數最高的影片（search.list 每次耗 100 配額，免費每日 1 萬）。"""
    key = os.environ.get("YOUTUBE_API_KEY")
    if not key:
        raise RuntimeError("缺少 YOUTUBE_API_KEY")
    since = (datetime.now(TZ) - timedelta(days=src.get("days", 7))).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    r = _get("https://www.googleapis.com/youtube/v3/search", params={
        "part": "snippet", "q": src["query"], "type": "video", "regionCode": "TW",
        "relevanceLanguage": "zh-Hant", "order": "viewCount", "publishedAfter": since,
        "maxResults": 15, "key": key})
    return [_mk(src, v["snippet"]["title"], i + 1, f"https://www.youtube.com/watch?v={v['id']['videoId']}")
            for i, v in enumerate(r.json().get("items", []))]


COLLECTORS = {"google_trends": c_google_trends, "rss": c_rss, "dcard": c_dcard,
              "youtube": c_youtube, "youtube_search": c_youtube_search,
              "google_news": c_google_news, "html": c_html}


def active_sources(cfg):
    phase = cfg["settings"].get("phase", 1)
    allowed = {"A"} | ({"B"} if phase >= 2 else set())
    return [s for s in cfg["sources"] if s.get("enabled") and s.get("tier") in allowed]


def collect_all(cfg, weights=None):
    """回傳 (items, results)；results[name] = {ok, count, error}。單一來源失敗不影響其他來源。"""
    weights = weights or {}

    def run(src):
        try:
            items = COLLECTORS[src["type"]](src)
            for it in items:
                it.weight = src.get("weight", 1.0) * weights.get(src["name"], 1.0)
            ok = bool(items)
            return src["name"], items, {"ok": ok, "count": len(items),
                                        "error": "" if ok else "抓到 0 筆"}
        except Exception as e:  # noqa: BLE001 — 任何錯誤都只記錄
            return src["name"], [], {"ok": False, "count": 0, "error": f"{type(e).__name__}: {e}"[:200]}

    items, results = [], {}
    with ThreadPoolExecutor(max_workers=6) as ex:
        for name, its, res in ex.map(run, active_sources(cfg)):
            items += its
            results[name] = res
    return items, results
