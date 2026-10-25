"""Collects reference notes for a topic before anything is written:
official pages listed in the topic bank + Wikipedia (English and Hindi).
The writer may only use facts found here; the fact-checker checks against them too."""
from __future__ import annotations

import re

import requests
from bs4 import BeautifulSoup

UA = {"User-Agent": "100LID-autopilot/1.0 (educational YouTube channel research bot)"}


def _clean(text: str) -> str:
    text = re.sub(r"\[\d+\]", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    return text.strip()


def wiki(title: str, lang: str = "en", limit: int = 9000) -> str:
    if not title:
        return ""
    api = f"https://{lang}.wikipedia.org/w/api.php"
    try:
        r = requests.get(api, params={"action": "query", "prop": "extracts", "explaintext": 1, "titles": title, "redirects": 1, "format": "json"}, headers=UA, timeout=30)
        pages = r.json().get("query", {}).get("pages", {})
        for p in pages.values():
            if "extract" in p and p["extract"]:
                return _clean(p["extract"])[:limit]
        # not found: search
        r = requests.get(api, params={"action": "query", "list": "search", "srsearch": title, "srlimit": 1, "format": "json"}, headers=UA, timeout=30)
        hits = r.json().get("query", {}).get("search", [])
        if hits:
            return wiki(hits[0]["title"], lang, limit) if hits[0]["title"] != title else ""
    except Exception:
        return ""
    return ""


def page(url: str, keywords: list[str], limit: int = 7000) -> str:
    try:
        r = requests.get(url, headers=UA, timeout=40)
        if not r.ok or "html" not in r.headers.get("content-type", "html"):
            return ""
        soup = BeautifulSoup(r.text, "html.parser")
        for t in soup(["script", "style", "nav", "footer", "header", "noscript", "form"]):
            t.decompose()
        text = _clean(soup.get_text("\n"))
    except Exception:
        return ""
    if len(text) <= limit:
        return text
    # keep the paragraphs that mention the topic's keywords
    paras = [p for p in text.split("\n") if len(p) > 40]
    kw = [k.lower() for k in keywords if k]
    scored = sorted(paras, key=lambda p: -sum(p.lower().count(k) for k in kw))
    out, n = [], 0
    for p in scored:
        if n + len(p) > limit:
            break
        out.append(p)
        n += len(p)
    return "\n".join(out)


def gather(topic: dict) -> dict:
    """Returns {'notes': str, 'sources': [urls actually used]}."""
    notes, used = [], []
    if topic.get("_notes"):
        notes.append(topic["_notes"])
    kws = [topic.get("title_en", ""), topic.get("title_hi", "")] + list(topic.get("keywords") or [])
    for url in topic.get("sources") or []:
        t = page(url, kws)
        if len(t) > 300:
            notes.append(f"### Official source: {url}\n{t}")
            used.append(url)
    en = wiki(topic.get("wiki_en") or topic.get("title_en", ""), "en")
    if en:
        notes.append(f"### Wikipedia (English): {topic.get('wiki_en') or topic.get('title_en')}\n{en}")
        used.append(f"https://en.wikipedia.org/wiki/{(topic.get('wiki_en') or topic.get('title_en', '')).replace(' ', '_')}")
    hi = wiki(topic.get("wiki_hi") or topic.get("title_hi", ""), "hi", 5000)
    if hi:
        notes.append(f"### Wikipedia (Hindi): {topic.get('wiki_hi') or topic.get('title_hi')}\n{hi}")
    text = "\n\n".join(notes)
    return {"notes": text[:26000], "sources": used}
