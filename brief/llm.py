"""LLM 抽象層。預算 0 → 預設 Gemini 免費額度（Google AI Studio 申請 key）；可用環境變數切換 Anthropic。
模型名稱會隨時間更新，請用環境變數覆寫：GEMINI_MODEL / GEMINI_EMBED_MODEL / ANTHROPIC_MODEL。"""
import json
import os
import re
import time

import requests


def _retry(fn, tries=3):
    last = None
    for i in range(tries):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(2 * (i + 1))
    raise last


def _parse_json(text):
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    return json.loads(text)


def generate_json(prompt):
    provider = os.environ.get("LLM_PROVIDER", "gemini")
    if provider == "anthropic":
        return _parse_json(_retry(lambda: _anthropic(prompt)))
    return _parse_json(_retry(lambda: _gemini(prompt)))


def _gemini(prompt):
    key = os.environ["GEMINI_API_KEY"]
    model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    r = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        params={"key": key}, timeout=120,
        json={"contents": [{"parts": [{"text": prompt}]}],
              "generationConfig": {"responseMimeType": "application/json", "temperature": 0.7}})
    r.raise_for_status()
    return r.json()["candidates"][0]["content"]["parts"][0]["text"]


def _anthropic(prompt):
    r = requests.post("https://api.anthropic.com/v1/messages", timeout=120,
                      headers={"x-api-key": os.environ["ANTHROPIC_API_KEY"],
                               "anthropic-version": "2023-06-01"},
                      json={"model": os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-5"),
                            "max_tokens": 8000,
                            "messages": [{"role": "user", "content": prompt}]})
    r.raise_for_status()
    return r.json()["content"][0]["text"]


def embed(texts):
    """回傳 {text: vector}；沒有 key 或失敗回傳 None（聚類會退回字面相似度）。"""
    key = os.environ.get("GEMINI_API_KEY")
    if not key or not texts:
        return None
    model = os.environ.get("GEMINI_EMBED_MODEL", "gemini-embedding-001")
    uniq = list(dict.fromkeys(texts))
    out = {}
    try:
        for i in range(0, len(uniq), 100):
            chunk = uniq[i:i + 100]
            r = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:batchEmbedContents",
                params={"key": key}, timeout=60,
                json={"requests": [{"model": f"models/{model}", "content": {"parts": [{"text": t}]}}
                                   for t in chunk]})
            r.raise_for_status()
            for t, e in zip(chunk, r.json()["embeddings"]):
                out[t] = e["values"]
        return out
    except Exception:  # noqa: BLE001
        return None
