"""A second, independent AI reads every fact in the episode against the research
notes and corrects anything wrong or unsupported. Anything it can't fix is
listed in the review issue so you can look at it."""
from __future__ import annotations

import json

from . import llm

SYSTEM = """You are a strict fact-checker for an Indian exam-preparation channel.
You receive RESEARCH NOTES and a numbered list of STATEMENTS (Hindi with English terms) from a video script.
For each statement that is factually WRONG, or states a specific fact (number, date, rate, limit, name,
section, year) that the notes do not support and that you are not certain is true, return a fix.
Do not rewrite style, do not touch statements that are fine, do not add new facts.
A fix must be the full corrected statement in the same language and style, or "" to delete it if it cannot be made correct.
Return JSON: {"issues": [{"id": <number>, "problem": "<short English reason>", "fix": "<corrected statement or empty>"}], "verdict": "ok" | "minor" | "major"}"""


def _statements(ep: dict) -> list[tuple[str, object, str, str]]:
    """(id-path, container, key, text) for every factual-looking string."""
    out: list[tuple[str, object, str, str]] = []

    def add(path, cont, key):
        val = cont.get(key) if isinstance(cont, dict) else None
        if isinstance(val, str) and val.strip():
            out.append((path, cont, key, val))

    def visual(v, path):
        if not isinstance(v, dict):
            return
        for k in ("title", "value", "label", "note"):
            add(f"{path}.{k}", v, k)
        for i, it in enumerate(v.get("items") or []):
            add(f"{path}.items[{i}].label", it, "label")
            add(f"{path}.items[{i}].detail", it, "detail")
            add(f"{path}.items[{i}].year", it, "year")
        for side in ("left", "right"):
            s = v.get(side) or {}
            for i, p in enumerate(s.get("points") or []):
                out.append((f"{path}.{side}.points[{i}]", s["points"], i, p))

    for i, ln in enumerate(ep.get("hook", {}).get("lines") or []):
        add(f"hook.lines[{i}]", ln, "text")
    visual(ep.get("hook", {}).get("visual"), "hook.visual")
    for si, s in enumerate(ep.get("sections") or []):
        for i, ln in enumerate(s.get("lines") or []):
            add(f"s{si}.lines[{i}]", ln, "text")
            add(f"s{si}.lines[{i}].onscreen", ln, "onscreen")
        visual(s.get("visual"), f"s{si}.visual")
    for qi, q in enumerate(ep.get("quiz") or []):
        add(f"quiz[{qi}].q", q, "q")
        add(f"quiz[{qi}].explain", q, "explain")
        if 0 <= q.get("answer", -1) < len(q.get("options", [])):
            out.append((f"quiz[{qi}].correct_option", q["options"], q["answer"], q["options"][q["answer"]]))
    for i, r in enumerate(ep.get("recap") or []):
        out.append((f"recap[{i}]", ep["recap"], i, r))
    for shi, sh in enumerate(ep.get("shorts") or []):
        for i, ln in enumerate(sh.get("lines") or []):
            add(f"short{shi}.lines[{i}]", ln, "text")
        visual(sh.get("visual"), f"short{shi}.visual")
        q = sh.get("quiz") or {}
        add(f"short{shi}.quiz.q", q, "q")
        add(f"short{shi}.quiz.explain", q, "explain")
    return out


def check(ep: dict, notes: str, writer_provider: str) -> dict:
    st = _statements(ep)
    listing = "\n".join(f"{i}. {t}" for i, (_, _, _, t) in enumerate(st))
    user = f"RESEARCH NOTES:\n<<<\n{notes}\n>>>\n\nSTATEMENTS:\n{listing}"
    try:
        res, who = llm.chat(SYSTEM, user, want_json=True, temperature=0.1, max_tokens=8000, avoid=writer_provider)
    except llm.LLMError as e:
        return {"checked_by": None, "fixed": [], "unresolved": [f"fact-check could not run: {e}"], "verdict": "unchecked"}
    fixed, unresolved = [], []
    for iss in (res or {}).get("issues") or []:
        try:
            idx = int(iss["id"])
            path, cont, key, old = st[idx]
        except Exception:
            continue
        fix = str(iss.get("fix", "")).strip()
        if fix and fix != old:
            cont[key] = fix
            fixed.append({"where": path, "was": old, "now": fix, "why": iss.get("problem", "")})
        elif not fix:
            unresolved.append(f"{path}: {old} — {iss.get('problem', '')}")
    return {"checked_by": who, "fixed": fixed, "unresolved": unresolved, "verdict": (res or {}).get("verdict", "ok")}
