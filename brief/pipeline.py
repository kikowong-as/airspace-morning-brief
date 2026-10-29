"""第一層後半：黑名單過濾 → 語意聚類 → 計分排序，產出「熱點原料清單」（兩區分開排行）。"""
import json
import math
import os
from collections import defaultdict

from .models import Hotspot
from .utils import lexical_sim, topic_id, yesterday_str

STATE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "state")


def drop_filter(items, drop_words):
    return [i for i in items if not any(w in i.title for w in drop_words)]


def _cos(a, b):
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return sum(x * y for x, y in zip(a, b)) / (na * nb) if na and nb else 0.0


def cluster(items, lex_th=0.45, emb_th=0.82, embeddings=None):
    """貪婪聚類：同一事件的不同標題併成一組。有 embedding 用語意相似度，否則用字面相似度。
    embeddings: {title: vector} 或 None"""
    items = sorted(items, key=lambda i: (-i.weight, i.rank))
    clusters = []
    for it in items:
        best, best_s = None, 0.0
        for c in clusters:
            for m in c:
                s = lexical_sim(it.title, m.title)
                th = lex_th
                if embeddings and it.title in embeddings and m.title in embeddings:
                    s = max(s if s >= 0.85 else 0.0, _cos(embeddings[it.title], embeddings[m.title]))
                    th = emb_th
                if s >= th and s > best_s:
                    best, best_s = c, s
        if best is not None:
            best.append(it)
        else:
            clusters.append([it])
    return clusters


def _rank_factor(rank):
    return max(0.3, 1 - 0.05 * (rank - 1))


def load_history(date):
    p = os.path.join(STATE, "history", f"{date}.json")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return {}


GROWTH_MULT = {"new": 1.5, "rising": 1.2, "stable": 1.0}


def prev_position(topic, zone, prev):
    """昨天榜上的名次（0 起算）；沒有回傳 None。"""
    for idx, h in enumerate(prev.get(zone, [])):
        if lexical_sim(topic, h["topic"]) >= 0.5:
            return idx
    return None


def score_clusters(clusters, zone, prev):
    """訊號強度（來源越多越高）× 成長速度。
    成長：昨天榜上沒有 = new ×1.5；昨天有且今天名次往前 = rising ×1.2；其餘 ×1.0。
    沒有昨日資料（第一天上線）時不給任何成長加成。"""
    base = []
    for c in clusters:
        by_src = {}
        for it in c:  # 每個來源只取該來源內最好的名次
            by_src[it.source] = max(by_src.get(it.source, 0), it.weight * _rank_factor(it.rank))
        top = max(c, key=lambda i: (i.weight, -i.rank))
        base.append((sum(by_src.values()), top.title, by_src, c))
    base.sort(key=lambda b: -b[0])
    has_prev = bool(prev.get(zone))
    spots = []
    for now_pos, (signal, topic, by_src, c) in enumerate(base):
        g = "stable"
        if has_prev:
            pp = prev_position(topic, zone, prev)
            g = "new" if pp is None else ("rising" if now_pos < pp else "stable")
        spots.append(Hotspot(
            id=topic_id(topic), topic=topic, zone=zone,
            sources=sorted(by_src), titles=[i.title for i in c][:6],
            score=round(signal * GROWTH_MULT[g], 3),
            traffic=max((i.traffic for i in c), default=0), growth=g))
    spots.sort(key=lambda h: -h.score)
    return spots


def build_hotspots(items, cfg, blacklist, embeddings=None):
    st = cfg["settings"]
    items = drop_filter(items, blacklist.get("drop", []))
    prev = load_history(yesterday_str())
    out = {}
    for zone, top_n in (("news", st["top_news"]), ("style", st["top_style"])):
        zi = [i for i in items if i.zone == zone]
        cl = cluster(zi, st["cluster_threshold"], st["embed_threshold"], embeddings)
        out[zone] = score_clusters(cl, zone, prev)[:top_n]
    return out


def load_weights():
    p = os.path.join(STATE, "weights.json")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return {}
