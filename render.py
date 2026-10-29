"""第三層：產出早報（HTML + 純文字）。設計目標：30 秒掃完 → 先給「今日重點」，再依區列出卡片。"""
import html
import os
from urllib.parse import urlencode

from .analyze import LIGHT
from .utils import fmt_traffic

E = html.escape
TYPE_COLOR = {"幽默": "#b45309", "實用": "#0f766e", "共鳴": "#7c3aed", "新聞點": "#1d4ed8"}


def heat_text(s):
    parts = []
    tr = fmt_traffic(s.traffic)
    if tr:
        parts.append(f"搜尋量 {tr}")
    parts.append(f"{len(s.sources)} 個來源")
    if s.growth == "new":
        parts.append("🆕 新上榜")
    elif s.growth == "rising":
        parts.append("📈 名次上升")
    return "・".join(parts)


def feedback_links(s, date):
    base = os.environ.get("FEEDBACK_URL", "")
    if not base:
        return ""
    a = s.analysis
    mk = lambda v, label, color: (
        f'<a href="{E(base)}?{urlencode({"d": date, "id": s.id, "t": a.get("topic", s.topic), "v": v})}" '
        f'style="color:{color};text-decoration:none;border:1px solid {color};border-radius:12px;padding:2px 10px;margin-right:6px;font-size:12px">{label}</a>')
    return f'<div style="margin-top:8px">{mk("used", "👍 用了", "#15803d")}{mk("skip", "👎 不用", "#6b7280")}</div>'


def card(s, date):
    a = s.analysis
    light = a.get("light", "none")
    icon = LIGHT.get(light, "⚪")
    h = [f'<div style="border:1px solid #e5e7eb;border-radius:10px;padding:12px 14px;margin:10px 0">',
         f'<div style="font-size:16px;font-weight:700">{icon} {E(a.get("topic", s.topic))}</div>',
         f'<div style="font-size:12px;color:#6b7280;margin-top:2px">{E(heat_text(s))}　|　{E("、".join(s.sources))}</div>']
    if a.get("light_reason"):
        h.append(f'<div style="font-size:13px;margin-top:6px">{E(a["light_reason"])}</div>')
    if a.get("risk_note"):
        h.append(f'<div style="font-size:13px;margin-top:4px;background:#fef9c3;border-radius:6px;padding:4px 8px">⚠️ {E(a["risk_note"])}</div>')
    if a.get("fashion_link"):
        gf = {"女": "女裝", "男": "男裝（r.fav）", "通用": "男女皆可"}.get(a.get("gender_fit"), "")
        h.append(f'<div style="font-size:13px;margin-top:6px">👗 {E(a["fashion_link"])}'
                 f'{f" <span style='color:#6b7280'>｜{gf}</span>" if gf else ""}</div>')
    for ang in a.get("angles", []):
        c = TYPE_COLOR.get(ang["type"], "#374151")
        h.append(f'<div style="font-size:13px;margin-top:3px"><span style="color:{c};font-weight:600">[{E(ang["type"])}]</span> {E(ang["idea"])}</div>')
    if a.get("sample_post"):
        h.append(f'<div style="font-size:13px;margin-top:8px;border-left:3px solid #d1d5db;padding-left:8px;color:#374151">{E(a["sample_post"])}</div>')
    if light in ("green", "yellow"):
        h.append(feedback_links(s, date))
    h.append("</div>")
    return "".join(h)


def section(title, subtitle, spots, date):
    usable = [s for s in spots if s.analysis.get("light") in ("green", "yellow", "none")]
    reds = [s for s in spots if s.analysis.get("light") == "red"]
    h = [f'<h2 style="font-size:17px;margin:22px 0 2px">{title}</h2><div style="font-size:12px;color:#6b7280">{subtitle}</div>']
    if not spots:
        h.append('<div style="color:#6b7280;font-size:13px;margin-top:8px">今日此區無資料。</div>')
    h += [card(s, date) for s in usable]
    if reds:
        lis = "".join(f'<li>{E(s.analysis.get("topic", s.topic))}<span style="color:#6b7280">（{E(s.analysis.get("light_reason", ""))}）</span></li>' for s in reds)
        h.append(f'<div style="margin-top:10px;font-size:13px"><b>🔴 不可借（僅供避雷）</b><ul style="margin:4px 0;padding-left:20px">{lis}</ul></div>')
    return "".join(h)


def top_picks(by_zone):
    greens = [s for z in ("news", "style") for s in by_zone.get(z, []) if s.analysis.get("light") == "green"]
    greens.sort(key=lambda s: -s.score)
    return greens[:3]


def render(by_zone, date, brand_name, failed_sources, ai_error, notes=None):
    picks = top_picks(by_zone)
    if picks:
        lis = "".join(
            f'<li style="margin:4px 0"><b>{E(s.analysis["topic"])}</b>'
            f'{" — " + E(s.analysis["angles"][0]["idea"]) if s.analysis.get("angles") else ""}</li>' for s in picks)
        pick_html = f'<div style="background:#ecfdf5;border-radius:10px;padding:10px 14px"><b>⚡ 30 秒重點：今天最值得做</b><ol style="margin:6px 0 0;padding-left:20px;font-size:14px">{lis}</ol></div>'
    else:
        pick_html = '<div style="background:#f3f4f6;border-radius:10px;padding:10px 14px">今天沒有 🟢 可借的熱點，建議休息或做常態內容。</div>'
    foot = []
    if ai_error:
        foot.append(f"⚠️ {E(ai_error)}（熱點已列出但未完成借勢分析）")
    if failed_sources:
        foot.append("⚠️ 以下來源今日抓取失敗：" + E("、".join(failed_sources)))
    for n in notes or []:
        foot.append(E(n))
    foot_html = "".join(f'<div style="font-size:12px;color:#92400e;margin-top:4px">{f}</div>' for f in foot) or \
        '<div style="font-size:12px;color:#6b7280">所有來源正常。</div>'
    body = (
        f'<div style="font-family:-apple-system,\'Noto Sans TC\',\'PingFang TC\',sans-serif;max-width:640px;margin:auto;color:#111827">'
        f'<h1 style="font-size:20px;margin:0 0 4px">☀️ {E(brand_name)} 每日熱點早報</h1>'
        f'<div style="font-size:12px;color:#6b7280;margin-bottom:12px">{date}　🟢 可借　🟡 小心（人工確認）　🔴 不可借</div>'
        f'{pick_html}'
        f'{section("一、今日時事熱點", "當天話題，越多來源同時出現排越前面", by_zone.get("news", []), date)}'
        f'{section("二、穿搭與消費趨勢", "週級別趨勢，與時事分開排行", by_zone.get("style", []), date)}'
        f'<hr style="border:none;border-top:1px solid #e5e7eb;margin:20px 0 8px">{foot_html}'
        f'<div style="font-size:11px;color:#9ca3af;margin-top:8px">搜尋量為級距估計，非精確數字。燈號由固定規則判定，黃燈請人工確認後再發。</div></div>')
    return body


def render_text(by_zone, date, brand_name, failed_sources, ai_error):
    lines = [f"{brand_name} 每日熱點早報 {date}", ""]
    for z, name in (("news", "一、今日時事熱點"), ("style", "二、穿搭與消費趨勢")):
        lines.append(name)
        for s in by_zone.get(z, []):
            a = s.analysis
            lines.append(f"{LIGHT.get(a.get('light'), '⚪')} {a.get('topic', s.topic)}（{heat_text(s)}）")
            if a.get("angles"):
                lines.append(f"   → [{a['angles'][0]['type']}] {a['angles'][0]['idea']}")
        lines.append("")
    if ai_error:
        lines.append(ai_error)
    if failed_sources:
        lines.append("抓取失敗來源：" + "、".join(failed_sources))
    return "\n".join(lines)


PAGE = """<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="generated" content="@@GEN@@"><meta name="brief-date" content="@@DATE@@">
<title>@@NAME@@ 每日熱點早報 @@DATE@@</title>
<style>
body{margin:0;background:#f9fafb;font-family:-apple-system,"PingFang TC","Noto Sans TC",sans-serif}
.bar{position:sticky;top:0;z-index:5;background:#111827;color:#fff;padding:10px 14px;display:flex;flex-wrap:wrap;gap:8px;align-items:center;font-size:13px}
.bar a{color:#d1d5db;text-decoration:none}.bar .sp{flex:1}
.bar input{width:84px;padding:6px 8px;border-radius:8px;border:0;font-size:14px}
.bar button{padding:7px 12px;border-radius:8px;border:0;background:#fbbf24;color:#111827;font-weight:700;font-size:14px;cursor:pointer}
.bar button:disabled{opacity:.5}
#stale{display:none;background:#fee2e2;color:#991b1b;padding:10px 14px;font-size:14px}
#msg{display:none;background:#fef3c7;color:#92400e;padding:8px 14px;font-size:14px}
.wrap{padding:16px;background:#fff;max-width:680px;margin:0 auto;min-height:80vh}
</style></head><body>
<div class="bar"><span>最後更新 @@GENTXT@@</span><span class="sp"></span>
@@BTNHTML@@<a href="archive/index.html">歷史</a><a href="weekly.html">每週彙整</a></div>
<div id="stale"></div><div id="msg"></div>
<div class="wrap">@@BODY@@</div>
<script>
var BTN="@@BTN@@",GEN="@@GEN@@",DATE="@@DATE@@";
function tw(){var o={};new Intl.DateTimeFormat("en-CA",{timeZone:"Asia/Taipei",year:"numeric",month:"2-digit",day:"2-digit",hour:"2-digit",minute:"2-digit",hour12:false}).formatToParts(new Date()).forEach(function(x){o[x.type]=x.value});return o}
(function(){var n=tw(),today=n.year+"-"+n.month+"-"+n.day,mins=(+n.hour%24)*60+ +n.minute;
 if(DATE!==today&&mins>=510){var e=document.getElementById("stale");e.style.display="block";
  e.textContent="⚠️ 今天的早報還沒產出（目前顯示的是 "+DATE+"）。可以按右上「要早報」重新產生；若一直沒更新，請到 GitHub Actions 查看錯誤。"}})();
var pin=document.getElementById("pin");try{if(pin)pin.value=localStorage.getItem("pin")||""}catch(e){}
function say(t){var m=document.getElementById("msg");m.style.display="block";m.textContent=t}
function ask(){var b=document.getElementById("ask");b.disabled=true;say("送出中…");
 fetch(BTN,{method:"POST",headers:{"Content-Type":"text/plain"},body:JSON.stringify({pin:pin.value})})
 .then(function(r){return r.json()}).then(function(r){
  if(!r.ok){say(r.msg);b.disabled=false;return}
  try{localStorage.setItem("pin",pin.value)}catch(e){}
  say("⏳ 產生中，約 3–5 分鐘，完成後頁面會自動更新（可以先關掉，晚點再開）");
  var t0=Date.now(),iv=setInterval(function(){
   fetch("index.html?_="+Date.now(),{cache:"no-store"}).then(function(x){return x.text()}).then(function(h){
    var m=h.match(/name="generated" content="([^"]+)"/);if(m&&m[1]!==GEN){clearInterval(iv);location.reload()}
    else if(Date.now()-t0>12*60*1000){clearInterval(iv);say("等太久了，請到 GitHub Actions 查看是否失敗");b.disabled=false}
   }).catch(function(){})},15000)
 }).catch(function(e){say("失敗："+e.message);b.disabled=false})}
</script></body></html>"""


def page(body, date, generated_iso, name, button_url=""):
    btn = ('<input id="pin" type="password" inputmode="numeric" placeholder="密碼" autocomplete="off">'
           '<button id="ask" onclick="ask()">要早報</button>') if button_url else ""
    gentxt = generated_iso.replace("T", " ")[:16]
    out = PAGE
    for k, v in (("@@GENTXT@@", gentxt), ("@@GEN@@", generated_iso), ("@@DATE@@", date), ("@@NAME@@", name),
                 ("@@BTNHTML@@", btn), ("@@BTN@@", button_url), ("@@BODY@@", body)):
        out = out.replace(k, v)
    return out
