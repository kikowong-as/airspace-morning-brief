"""監控：來源失敗連續天數、整體流程警信、08:30 看門狗。"""
import json
import os

from .utils import today_str

STATE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "state")
HEALTH = os.path.join(STATE, "health.json")
LAST_SENT = os.path.join(STATE, "last_sent.json")


def _load(p):
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save(p, d):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)


def should_notify(streak):
    """連續 3 天失敗通知一次，之後每 7 天再提醒，避免天天轟炸。"""
    return streak == 3 or (streak > 3 and (streak - 3) % 7 == 0)


def update_health(results, date=None):
    """results: {source: {ok, ...}}。回傳 (failed_today, need_notify)。
    同一天重跑（例如手動要早報）不會重複累加連續失敗天數：以「今天以前」的天數為基準重算。"""
    date = date or today_str()
    h = _load(HEALTH)
    failed, notify = [], []
    for name, r in results.items():
        e = h.setdefault(name, {"fail_streak": 0, "last_ok": "", "date": "", "base": 0})
        if e.get("date") != date:          # 新的一天：記下今天以前的連續失敗天數
            e["base"], e["date"] = e.get("fail_streak", 0), date
        if r["ok"]:
            e["fail_streak"], e["last_ok"] = 0, date
        else:
            e["fail_streak"] = e["base"] + 1
            failed.append(name)
            if should_notify(e["fail_streak"]):
                notify.append((name, e["fail_streak"], r.get("error", "")))
    _save(HEALTH, h)
    return failed, notify


def mark_sent(date=None):
    _save(LAST_SENT, {"date": date or today_str()})


def was_sent_today():
    return _load(LAST_SENT).get("date") == today_str()
