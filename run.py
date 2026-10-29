#!/usr/bin/env python3
"""Airspace 每日熱點早報（網站版）。
  python run.py                 完整流程（抓取 → 分析 → 更新 docs/ 網站）
  python run.py --mock          離線預覽：假資料 + 假 AI，輸出 out/preview.html，不寄信
  python run.py --no-send       真實抓取與分析，但只輸出 out/preview.html，不更新網站
  python run.py weekly          每週回饋彙整與權重調整
"""
import json
import os
import sys
import traceback

import yaml

from brief import analyze, health, llm, mock, pipeline, render, site
from brief.collectors import collect_all
from brief.utils import now, today_str

ROOT = os.path.dirname(os.path.abspath(__file__))


def load_yaml(name):
    with open(os.path.join(ROOT, "config", name), encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_history(by_zone, date):
    data = {z: [{"id": s.id, "topic": s.topic, "sources": s.sources, "score": s.score,
                 "light": s.analysis.get("light", "none")} for s in spots] for z, spots in by_zone.items()}
    p = os.path.join(pipeline.STATE, "history", f"{date}.json")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)


def build(mock_mode):
    cfg, brand, bl = load_yaml("sources.yaml"), load_yaml("brand.yaml"), load_yaml("blacklist.yaml")
    if mock_mode:
        items, results = mock.mock_items(), {"（模擬）Dcard": {"ok": False, "count": 0, "error": "示範：來源失敗標註"}}
    else:
        items, results = collect_all(cfg, pipeline.load_weights())            # 第一層：抓取
    embeddings = None if mock_mode else llm.embed([i.title for i in items])   # 語意聚類（無 key 則退回字面）
    by_zone = pipeline.build_hotspots(items, cfg, bl, embeddings)             # 去重/過濾/計分排序
    if mock_mode:                                                             # 第二層：借勢分析
        for z in by_zone.values():
            facts = {f["id"]: f for f in mock.mock_facts(z)}
            for s in z:
                analyze.apply_rules(s, facts[s.id], bl["red_keywords"])
        ai_error = None
    else:
        by_zone, ai_error = analyze.analyze(by_zone, brand, bl)
    return brand, by_zone, results, ai_error


def main(argv):
    cmd = argv[1] if len(argv) > 1 and not argv[1].startswith("--") else "daily"
    flags = set(a for a in argv[1:] if a.startswith("--"))
    date = today_str()

    if cmd == "weekly":
        from brief import weekly
        report, _ = weekly.run_weekly()
        print(report)
        if "--no-send" not in flags:
            site.publish_weekly(report, date)
        return 0

    mock_mode = "--mock" in flags
    brand, by_zone, results, ai_error = build(mock_mode)
    failed, notify = health.update_health(results, date) if not mock_mode else ([n for n, r in results.items() if not r["ok"]], [])
    notes = [f"🔧 來源「{n}」已連續 {d} 天失敗（{e}），請維護者檢查。" for n, d, e in notify]
    body = render.render(by_zone, date, brand["name"], failed, ai_error, notes)
    page = render.page(body, date, now().isoformat(timespec="seconds"), brand["name"], os.environ.get("BUTTON_URL", ""))
    os.makedirs(os.path.join(ROOT, "out"), exist_ok=True)
    out = os.path.join(ROOT, "out", "preview.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"已輸出 {out}")
    if mock_mode:  # 預覽：輸出完整網站資料夾 out/site/，連結才打得開
        site.DOCS = os.path.join(ROOT, "out", "site")
        site.publish(page, date)
        print(f"預覽網站：{site.DOCS}/index.html")
        return 0
    if "--no-send" in flags:
        return 0
    site.publish(page, date)
    save_history(by_zone, date)
    health.mark_sent(date)
    print("網站已更新 docs/index.html")
    return 0


def alert(subject, detail):
    """選用：有設定 SMTP 才寄警信；沒有就只印出（GitHub 預設會對失敗的 workflow 寄通知）。"""
    try:
        from brief import mailer
        if mailer.configured():
            mailer.alert(subject, detail)
    except Exception:
        pass


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except Exception:  # 整體流程失敗：不靜默略過，立刻寄警信後再讓 CI 失敗
        err = traceback.format_exc()
        print(err, file=sys.stderr)
        alert("Airspace 早報整體流程失敗", err[-1800:])
        sys.exit(1)
