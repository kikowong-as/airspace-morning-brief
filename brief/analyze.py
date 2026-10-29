"""第二層：AI 借勢分析。
關鍵設計：AI 只負責回答「事實題」（情緒、有無爭議、是否災難案件政治傷亡、是否牽涉藝人/品牌、能否連結商品），
紅綠燈由程式依固定定義判定，不由 AI 自由心證；黑名單關鍵字命中也強制紅燈。"""
import json

from . import llm

LIGHT = {"green": "🟢", "yellow": "🟡", "red": "🔴"}
TYPES = ["幽默", "實用", "共鳴", "新聞點"]

PROMPT = """你是台灣服飾品牌「{name}」的社群小編顧問。以下是今天的熱點清單，請逐則分析。

【品牌設定】
品類：{category}；受眾：{audience}
主力商品：{products}；發文平台：{platforms}
品牌禁忌：{dont}

【每則熱點請回答】
1. sentiment：對大眾的情緒是「正面」「負面」或「中性」
2. tragedy：是否涉及災難、案件、政治、他人傷病死亡？(true/false)
3. controversial：是否帶有爭議面？(true/false)
4. celeb_or_brand：是否牽涉特定藝人、公眾人物或其他品牌？(true/false)
5. link_possible：能否與服飾商品或穿搭/生活情境建立「合理、不勉強」的連結？(true/false)
6. light_reason：一句話說明你的判斷理由
7. fashion_link：與服飾的具體連結點（一句話；若無法連結留空字串）
8. angles：3 到 5 個切入角度，每個是 {{"type": "幽默|實用|共鳴|新聞點", "idea": "具體方向，一句話"}}，四種類型至少各出現一次再補足；tragedy 為 true 時給空陣列
9. sample_post：一句可直接用的貼文開頭（語氣自然即可；tragedy 為 true 時給空字串）
10. risk_note：若 controversial 或 celeb_or_brand 為 true，寫一句風險提醒，否則空字串
11. topic：整理成簡潔易懂的熱點名稱（不超過 20 字）
12. gender_fit：這個熱點適合「女」裝、「男」裝，還是「通用」？品牌以女性客群為主、r.fav 支線面向男性，切入角度請盡量讓男女裝都用得上，不要預設只寫女性向；若確實偏單一性別，如實標示

【輸出】只回傳 JSON 陣列，每則一個物件，欄位為 id, topic, sentiment, tragedy, controversial, celeb_or_brand, link_possible, light_reason, fashion_link, angles, sample_post, risk_note, gender_fit。不要任何其他文字。

【熱點清單】
{items}
"""


def decide_light(facts, topic, red_keywords):
    """固定紅綠燈定義。回傳 (light, 觸發原因或空字串)。"""
    hits = [k for k in red_keywords if k in topic]
    if hits:
        return "red", f"命中黑名單關鍵字「{hits[0]}」"
    if facts.get("tragedy"):
        return "red", "涉及災難、案件、政治或傷病死亡"
    if not facts.get("link_possible"):
        return "red", "無法與品牌建立合理連結"
    if facts.get("controversial") or facts.get("celeb_or_brand") or facts.get("sentiment") == "負面":
        return "yellow", "帶有爭議、牽涉藝人/其他品牌或情緒偏負面，須人工確認"
    return "green", ""


def _fix_angles(angles):
    out = []
    for a in angles or []:
        t, idea = (a.get("type") or "").strip(), (a.get("idea") or "").strip()
        if idea:
            out.append({"type": t if t in TYPES else "共鳴", "idea": idea})
    return out[:5]


def apply_rules(spot, facts, red_keywords):
    light, trig = decide_light(facts, spot.topic, red_keywords)
    reason = (facts.get("light_reason") or "").strip()
    if trig.startswith("命中"):      # 關鍵字規則推翻了 AI 的判斷，要讓讀者看得出來
        reason = f"{trig}。{reason}" if reason else trig
    elif not reason:
        reason = trig
    a = {
        "topic": (facts.get("topic") or spot.topic).strip(),
        "zone": spot.zone, "sources": spot.sources,
        "sentiment": facts.get("sentiment", "中性"),
        "gender_fit": facts.get("gender_fit") if facts.get("gender_fit") in ("女", "男", "通用") else "通用",
        "light": light, "light_reason": reason,
        "fashion_link": (facts.get("fashion_link") or "").strip(),
        "angles": _fix_angles(facts.get("angles")),
        "sample_post": (facts.get("sample_post") or "").strip(),
        "risk_note": (facts.get("risk_note") or "").strip() if light == "yellow" else "",
    }
    if light == "red":  # 紅燈不提供借勢建議
        a.update(angles=[], sample_post="", fashion_link="")
    if light == "yellow" and not a["risk_note"]:
        a["risk_note"] = trig
    spot.analysis = a
    return spot


def analyze(spots_by_zone, brand, blacklist):
    """回傳 (spots_by_zone, error)。LLM 失敗時 error 有訊息，熱點保留（無分析）讓早報照常產出。"""
    flat = [s for z in ("news", "style") for s in spots_by_zone.get(z, [])]
    if not flat:
        return spots_by_zone, None
    items = "\n".join(
        f"- id={s.id} | 區={'時事' if s.zone == 'news' else '穿搭趨勢'} | 熱點={s.topic} | 相關標題={'；'.join(s.titles[:3])} | 來源={'、'.join(s.sources)}"
        for s in flat)
    prompt = PROMPT.format(
        name=brand["name"], category=brand["category"], audience=brand["audience"],
        products="、".join(brand["products"]), platforms="、".join(brand["platforms"]),
        dont="；".join(brand["brand_dont"]), items=items)
    reds = blacklist.get("red_keywords", [])
    try:
        data = llm.generate_json(prompt)
        by_id = {d.get("id"): d for d in data if isinstance(d, dict)}
    except Exception as e:  # noqa: BLE001
        for s in flat:  # 仍套用關鍵字規則，至少紅燈不會漏
            hit = [k for k in reds if k in s.topic]
            s.analysis = {"topic": s.topic, "zone": s.zone, "sources": s.sources,
                          "light": "red" if hit else "none", "light_reason": f"命中黑名單關鍵字「{hit[0]}」" if hit else "AI 分析失敗，未判定",
                          "angles": [], "sample_post": "", "fashion_link": "", "risk_note": "", "sentiment": ""}
        return spots_by_zone, f"AI 分析失敗：{type(e).__name__}: {e}"[:200]
    for s in flat:
        facts = by_id.get(s.id)
        if facts is None:
            s.analysis = {"topic": s.topic, "zone": s.zone, "sources": s.sources, "light": "none",
                          "light_reason": "AI 未回傳此則", "angles": [], "sample_post": "",
                          "fashion_link": "", "risk_note": "", "sentiment": ""}
        else:
            apply_rules(s, facts, reds)
    return spots_by_zone, None
