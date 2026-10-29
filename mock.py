"""離線預覽 / 測試用的假資料（不連網、不呼叫 AI）。"""
from .models import RawItem


def mock_items():
    N = lambda t, s, r, w=1.0, tr=0: RawItem(t, s, "news", r, "", tr, w)
    S = lambda t, s, r: RawItem(t, s, "style", r, "", 0, 1.0)
    return [
        N("周杰倫演唱會開賣", "Google Trends", 1, 1.5, 200000), N("周杰倫 演唱會 秒殺", "Yahoo 娛樂", 2),
        N("周杰倫演唱會票價曝光", "ETtoday", 4), N("周杰倫演唱會搶票心得", "Dcard", 3, 1.2),
        N("寒流來襲 北部下探10度", "Google Trends", 2, 1.5, 50000), N("寒流明天最強 全台急凍", "Yahoo 頭條", 1),
        N("寒流穿搭怎麼穿不臃腫", "Dcard", 6, 1.2),
        N("某藝人宣布結婚", "Yahoo 娛樂", 1), N("某藝人閃婚 對象曝光", "ETtoday", 2), N("某藝人婚訊", "Google Trends", 5, 1.5, 20000),
        N("國道追撞車禍 3人死亡", "Yahoo 頭條", 3), N("國道車禍釀3死", "ETtoday", 5),
        N("立委質詢預算", "Yahoo 頭條", 6),
        N("週末 咖啡廳 打卡", "Dcard", 9, 1.2),
        N("成人影片網站", "Dcard", 20, 1.2),
        S("寬褲 回歸", "Pinterest Trends", 1), S("寬褲穿搭", "蝦皮熱搜", 2), S("美式復古 帽T", "momo 熱銷榜", 1),
        S("大地色系 針織外套", "Vogue Taiwan", 1),
    ]


def mock_facts(spots):
    """依關鍵字產生假的 AI 事實回答，用來預覽版面。"""
    out = []
    for s in spots:
        t = s.topic
        f = {"id": s.id, "topic": t[:20], "sentiment": "正面", "tragedy": False, "controversial": False,
             "celeb_or_brand": False, "link_possible": True, "light_reason": "情緒正面，能連到日常穿搭情境",
             "fashion_link": "從這個話題帶到實際穿搭場景與商品",
             "angles": [{"type": "幽默", "idea": "用誇張的口吻自嘲，帶出商品"},
                        {"type": "實用", "idea": "給 3 個具體穿搭建議"},
                        {"type": "共鳴", "idea": "說出大家心裡那句話"},
                        {"type": "新聞點", "idea": "用時事當開場，一句話帶到商品"}],
             "sample_post": f"關於「{t[:8]}」，我們有話想說……", "risk_note": "", "gender_fit": "男" if "帽T" in t else "通用"}
        if "車禍" in t or "立委" in t:
            f.update(tragedy=True, sentiment="負面", link_possible=False, light_reason="涉及案件或政治")
        elif "藝人" in t or "周杰倫" in t:
            f.update(celeb_or_brand=True, light_reason="牽涉藝人，借勢前須確認", risk_note="避免暗示藝人代言或使用商品")
        out.append(f)
    return out
