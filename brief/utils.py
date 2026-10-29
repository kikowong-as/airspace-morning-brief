import hashlib
import re
import unicodedata
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Taipei")


def now():
    return datetime.now(TZ)


def today_str():
    return now().strftime("%Y-%m-%d")


def yesterday_str():
    return (now() - timedelta(days=1)).strftime("%Y-%m-%d")


_SUFFIX = re.compile(r"\s*[-–|]\s*[^-–|]{1,16}$")


def clean_title(t):
    t = unicodedata.normalize("NFKC", t or "").strip()
    t = re.sub(r"【[^】]*】|\[[^\]]*\]", "", t)
    t = _SUFFIX.sub("", t)
    return re.sub(r"\s+", " ", t).strip()


def bigrams(t):
    t = re.sub(r"[\W_]+", "", t.lower())
    if len(t) < 2:
        return {t} if t else set()
    return {t[i:i + 2] for i in range(len(t) - 1)}


def lexical_sim(a, b):
    A, B = bigrams(a), bigrams(b)
    if not A or not B:
        return 0.0
    inter = len(A & B)
    jac = inter / len(A | B)
    small = min(len(A), len(B))
    # 短關鍵字完整被長標題包含（Google Trends「周杰倫」vs 新聞標題）
    contain = 0.85 if small >= 2 and inter == small else 0.0
    return max(jac, contain)


def topic_id(topic):
    return hashlib.sha1(topic.encode("utf-8")).hexdigest()[:8]


def parse_traffic(s):
    """'2000+' / '1,000+' / '20萬+' → int"""
    if not s:
        return 0
    s = str(s).replace(",", "").replace("+", "").strip()
    m = re.match(r"([\d.]+)\s*(萬|千|K|M)?", s, re.I)
    if not m:
        return 0
    n = float(m.group(1))
    mult = {"萬": 10000, "千": 1000, "k": 1000, "m": 1000000}.get((m.group(2) or "").lower(), 1)
    return int(n * mult)


def fmt_traffic(n):
    """搜尋量只給級距：約 N 萬+ / 約 N 千+，不呈現精確數字"""
    if n >= 10000:
        return f"約 {n // 10000} 萬+"
    if n >= 1000:
        return f"約 {n // 1000} 千+"
    return ""
