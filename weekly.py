"""每週回饋彙整：讀「用了/不用」紀錄 → 算各來源採用率 → 調整 state/weights.json → 寄週報。"""
import csv
import io
import json
import os
from collections import defaultdict

import requests

from .health import _save
from .pipeline import STATE, load_history


def fetch_feedback(url):
    text = requests.get(url, timeout=30).content.decode("utf-8-sig")
    # 欄位：timestamp, date, id, topic, vote(used|skip)
    return [r for r in csv.reader(io.StringIO(text)) if len(r) >= 5 and r[4] in ("used", "skip")]


def compute(rows, min_votes=5):
    src_stat = defaultdict(lambda: [0, 0])      # source → [used, total]
    light_stat = defaultdict(lambda: [0, 0])
    hist_cache = {}
    for _, date, tid, topic, vote in [r[:5] for r in rows]:
        hist_cache.setdefault(date, load_history(date))
        for zone in ("news", "style"):
            for h in hist_cache[date].get(zone, []):
                if h["id"] == tid:
                    for s in h["sources"]:
                        src_stat[s][1] += 1
                        src_stat[s][0] += vote == "used"
                    light_stat[h.get("light", "?")][1] += 1
                    light_stat[h.get("light", "?")][0] += vote == "used"
    weights = {}
    for s, (u, t) in src_stat.items():
        if t >= min_votes:  # 票數太少不調，避免雜訊；每次調幅 ±25%，總倍率限制 0.6–1.6
            rate = u / t
            weights[s] = round(min(1.6, max(0.6, 1 + 0.5 * (rate - 0.5))), 2)
    return src_stat, light_stat, weights


def run_weekly():
    url = os.environ.get("FEEDBACK_CSV_URL")
    if not url:
        return "未設定 FEEDBACK_CSV_URL，略過本週彙整。", {}
    rows = fetch_feedback(url)
    src_stat, light_stat, weights = compute(rows)
    old = {}
    p = os.path.join(STATE, "weights.json")
    if os.path.exists(p):
        old = json.load(open(p, encoding="utf-8"))
    old.update(weights)
    _save(p, old)
    lines = [f"本週回饋共 {len(rows)} 筆。", "", "各來源採用率（用了 / 總回饋）："]
    for s, (u, t) in sorted(src_stat.items(), key=lambda x: -x[1][1]):
        lines.append(f"  {s}: {u}/{t}（{u / t:.0%}）→ 權重 {old.get(s, 1.0)}")
    lines += ["", "各燈號採用率："] + [f"  {k}: {u}/{t}" for k, (u, t) in light_stat.items()]
    lines += ["", "提醒：品牌設定檔 config/brand.yaml 可依本週「不用」的類型微調語氣與禁忌。"]
    return "\n".join(lines), weights
