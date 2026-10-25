"""Writes a full episode (long video + its 3 Shorts + all YouTube text) with a free AI,
then checks the structure and length, and asks for fixes if needed."""
from __future__ import annotations

import copy
import json
import re
from datetime import datetime

from . import llm, settings
from .components_list import ALLOWED_ICONS, ANATOMY_OBJECTS, CUTAWAY_OBJECTS, DEVICE_KINDS, EMOTIONS, GESTURES, SETTINGS

SAMPLE_PATH = settings.SAMPLES / "ssy_episode.json"


def _trim_sample() -> str:
    """A shortened copy of the hand-written sample, used as a style and format example."""
    s = json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))
    s["sections"] = [s["sections"][i] for i in (0, 2, 5, 8, 10, 12) if i < len(s["sections"])]
    s["quiz"] = s["quiz"][:2]
    s["shorts"] = s["shorts"][:2]
    return json.dumps(s, ensure_ascii=False, indent=1)


def pick_cast(topic: dict, recent: list[dict]) -> dict:
    """Teacher + learner + a guest who suits the topic; rotates teachers for variety."""
    cast = settings.cast()
    series = topic.get("series", "")
    teacher = "meera" if series in ("rbi_economy", "banking_law") else "guruji"
    # keep it fresh: if the last two long videos had the same teacher, switch
    last = [r.get("cast", {}).get("teacher") for r in recent[-2:]]
    if len(last) == 2 and last[0] == last[1] == teacher:
        teacher = "guruji" if teacher == "meera" else "meera"
    guest = topic.get("guest") or "chotu"
    if guest not in cast:
        guest = "chotu"
    learner = "chotu"
    out = {"teacher": teacher, "learner": learner}
    if guest != learner:
        out["guest"] = guest
    # the other teacher appears as an expert sometimes (banking scenes)
    other = "meera" if teacher == "guruji" else "guruji"
    out["expert"] = other
    return out


def _cast_text(c: dict) -> str:
    cast = settings.cast()
    lines = []
    for role, cid in c.items():
        x = cast[cid]
        lines.append(f'- "{cid}" ({x["name_hi"]} / {x["name_en"]}), role in this video: {role}. Who they are: {x["about"]}.')
    return "\n".join(lines)


SYSTEM = """You are the head scriptwriter of 100LID, a Hindi YouTube channel that teaches government
schemes, banking laws, RBI and economy topics to exam aspirants (Bank PO/Clerk, SSC, Railway, State PSC)
through short animated stories with recurring cartoon characters.

NON-NEGOTIABLE RULES
1. Accuracy first. Use ONLY facts that appear in the RESEARCH NOTES. If a detail (a number, date, rate,
   section, name) is not in the notes, leave it out. Never invent statistics, quotes or dates.
   Rates and limits that change (interest rates, amounts) must be said as "as of" / "हाल में" and
   viewers told to check the official website.
2. Education only — never personal financial, legal or investment advice ("you should buy/invest").
3. Language: natural spoken Hindi in Devanagari, with English exam terms kept in English letters
   (e.g. "RBI ने repo rate बढ़ाया"). Short, speakable sentences (max ~22 words per line).
   Write numbers as digits (₹250, 2015, 8.2%). No emojis inside spoken lines.
4. Story-led and original: every video has its own little story arc with the given characters:
   a real-life problem in the hook → learning → the character's problem solved at the end.
   No generic filler, no repeated catchphrases across videos, no clickbait claims the video doesn't deliver.
5. Output VALID JSON only, exactly in the format of the EXAMPLE (same keys)."""


def _device_rules() -> str:
    return f"""VISUAL DEVICES (each "board" section shows exactly one; items appear one by one, synced with "reveal"):
- "exploded": a whole broken into its parts flying out (features, pillars, benefits). center + 3-6 items.
- "knolling": things neatly laid out on a mat (documents needed, eligibility items, components). 3-8 items, each with an icon.
- "cutaway": an object sliced open to show layers inside (stages over time, tiers/structure, what's inside). object one of {CUTAWAY_OBJECTS}; 2-5 items.
- "anatomy": a labelled dissection of an object (cheque, form, passbook, card, bank building, phone app) — each item is a labelled part. object one of {ANATOMY_OBJECTS}; 3-6 items.
- "stat": ONE big number (value, label, optional note).
- "timeline": history in 3-6 dated steps (year + label + detail).
- "compare": X vs Y, or Myth vs Fact (left/right with 1-4 points each).
- "steps": a process / how to apply / rules in order. 3-6 items.
- "keyfacts": the "Exam Corner" — 5-7 short exam-ready facts.
Icons must be one of: {", ".join(ALLOWED_ICONS)}.
Labels: max ~5 words; details: max ~9 words.

PLACEMENT FOR MAXIMUM WATCH TIME (viewers usually drift away at ~25%, ~50% and ~70% of a video):
- Hook (first 20-30 s): story problem + a fast "exploded" teaser of everything the video covers.
- Around 25%, 50% and 70%: put a SIGNATURE device (knolling, cutaway, anatomy or exploded) — use at least 3 of these 4 kinds in every long video, each at most twice.
- Never more than ~60 s without a change: alternate "stage" story scenes and "board" explainers.
- "stat" for the single most important number; "timeline" only if the topic has history.
- Near the end, before the quiz: one "keyfacts" Exam Corner.
- Settings for stage scenes: one of {SETTINGS}. Emotions: {EMOTIONS}. Gestures: {GESTURES}.
- "onscreen" (optional, max 6 words) on stage lines = a keyword sticker for the key fact of that line."""


def _seo_rules(topic: dict) -> str:
    year = datetime.now().year
    return f"""YOUTUBE TEXT (meta) — written to rank in YouTube search and to be clicked, but always honest:
- "title" (Hindi audience): start with the main English keyword people search, then the Hindi name, then an exam hook.
  Under 70 characters if possible, never over 95. Include {year} only if the topic has current numbers.
  Example pattern: "Sukanya Samriddhi Yojana 2026 | सुकन्या समृद्धि योजना | Bank Exam".
- "title_en": an English title for English-language viewers (same promise).
- "summary": 2-3 Hindi sentences, main keyword in the first sentence, naturally mentioning exams.
- "summary_en": the same in English.
- "tags": 15-25 search phrases (English + Hindi + common misspellings/short forms, exam names).
- "hashtags": exactly 3.
- "thumbnail": textTop (max 18 chars, e.g. exam name), textBig (2-4 BIG words, max 22 chars, a curiosity gap the video truly answers),
  textSmall (max 18 chars), emotion (shocked/excited/curious/worried), character (one of the cast ids), icon (from the icon list).
- "pinned_comment": a quiz question from the video with options, inviting answers.
- "sources": the official URLs from the notes that support the facts."""


def build_prompt(topic: dict, notes: str, cast_choice: dict, words: tuple[int, int], next_title: str, extra: str = "") -> str:
    cfg = settings.config()
    v = cfg["video"]
    return f"""Write a complete episode about: {topic['title_en']} ({topic.get('title_hi', '')}).
Series: {topic.get('series')}. Exam keywords: {", ".join(topic.get('keywords') or [])}.

CAST FOR THIS VIDEO (use these ids exactly; the teacher explains, the learner asks what viewers think,
the guest has the real-life problem; the expert may appear in one scene):
{_cast_text(cast_choice)}

LENGTH: the spoken lines of the long video (hook + sections + outro, not counting quiz/recap) must total
{words[0]}-{words[1]} Hindi words (about {cfg['video']['long_minutes'][0]}-{cfg['video']['long_minutes'][1]} minutes).
Use 9-14 sections. Give a "chapter" title (2-5 words) to 6-8 of them (a new chapter starts a new part of the video).
Quiz: exactly {v['quiz_questions']} MCQs (4 options, "answer" = index 0-3, short "explain").
Recap: 5-6 short points. Outro: 2-3 lines; next video title: "{next_title}".
Shorts: exactly {v['shorts_per_long']} — kinds "fact", "quiz", "myth" — each a standalone 40-55 second story
({v['short_words'][0]}-{v['short_words'][1]} words, 5-8 lines), first line = a scroll-stopping hook, last line points to the full video.
"fact" and "myth" shorts have one visual; "quiz" short has a "quiz" object instead.

{_device_rules()}

{_seo_rules(topic)}
{extra}
RESEARCH NOTES (the only allowed source of facts):
<<<
{notes}
>>>

EXAMPLE (format and style only — a different topic; copy its structure and keys, not its facts):
{_trim_sample()}

Return only the JSON for the new episode, with "topic_id": "{topic['id']}", "series": "{topic.get('series')}", "as_of": "{datetime.now():%B %Y}", and "cast": {json.dumps(cast_choice)}."""


# ---------------------------------------------------------------- checking
def spoken_words(ep: dict) -> int:
    n = 0
    for ln in (ep.get("hook") or {}).get("lines") or []:
        n += len(ln.get("text", "").split())
    for s in ep.get("sections") or []:
        for ln in s.get("lines") or []:
            n += len(ln.get("text", "").split())
    for ln in (ep.get("outro") or {}).get("lines") or []:
        n += len(ln.get("text", "").split())
    return n


def _fix_visual(v: dict | None) -> dict | None:
    if not isinstance(v, dict) or v.get("kind") not in DEVICE_KINDS:
        return None
    v.setdefault("title", "")
    k = v["kind"]
    if k in ("knolling", "exploded", "cutaway", "anatomy", "timeline", "steps", "keyfacts"):
        items = [i for i in (v.get("items") or []) if isinstance(i, dict) and i.get("label")]
        v["items"] = items[:8 if k == "knolling" else 7]
        if not v["items"]:
            return None
        for it in v["items"]:
            if it.get("icon") and it["icon"] not in ALLOWED_ICONS:
                it["icon"] = "check"
            if k == "knolling" and not it.get("icon"):
                it["icon"] = "document"
    if k == "exploded":
        c = v.get("center") or {}
        v["center"] = {"label": c.get("label") or v.get("title", "")[:16], "icon": c.get("icon") if c.get("icon") in ALLOWED_ICONS else "idea"}
    if k == "cutaway" and v.get("object") not in CUTAWAY_OBJECTS:
        v["object"] = "box"
    if k == "anatomy" and v.get("object") not in ANATOMY_OBJECTS:
        v["object"] = "generic"
    if k == "stat":
        if not v.get("value"):
            return None
        v.setdefault("label", "")
        if v.get("icon") and v["icon"] not in ALLOWED_ICONS:
            v["icon"] = "chart"
    if k == "compare":
        for side in ("left", "right"):
            s = v.get(side) or {}
            v[side] = {"title": s.get("title", ""), "points": [str(p) for p in (s.get("points") or [])][:4]}
    return v


def validate(ep: dict, cast_choice: dict) -> tuple[dict, list[str]]:
    """Repairs small problems in place and lists big ones."""
    problems: list[str] = []
    ep = copy.deepcopy(ep)
    allowed = set(settings.cast())
    ep["cast"] = cast_choice
    teacher = cast_choice.get("teacher", "guruji")

    def fix_lines(lines):
        out = []
        for ln in lines or []:
            if not isinstance(ln, dict) or not str(ln.get("text", "")).strip():
                continue
            if ln.get("speaker") not in allowed:
                ln["speaker"] = teacher
            if ln.get("emotion") not in EMOTIONS:
                ln.pop("emotion", None)
            if ln.get("gesture") not in GESTURES:
                ln.pop("gesture", None)
            ln["text"] = re.sub(r"\s+", " ", str(ln["text"])).strip()
            out.append(ln)
        return out

    hook = ep.get("hook") or {}
    hook["lines"] = fix_lines(hook.get("lines"))
    hook["visual"] = _fix_visual(hook.get("visual"))
    if hook.get("setting") not in SETTINGS:
        hook["setting"] = "home"
    if not hook["lines"]:
        problems.append("hook has no lines")
    ep["hook"] = hook
    secs = []
    for s in ep.get("sections") or []:
        s["lines"] = fix_lines(s.get("lines"))
        if not s["lines"]:
            continue
        if s.get("mode") == "board":
            s["visual"] = _fix_visual(s.get("visual"))
            if not s["visual"]:
                s["mode"] = "stage"
            if s.get("presenter") not in allowed:
                s["presenter"] = teacher
        if s.get("mode") != "board":
            s["mode"] = "stage"
            if s.get("setting") not in SETTINGS:
                s["setting"] = hook["setting"]
            s["chars"] = [c for c in (s.get("chars") or []) if c in allowed][:3] or list(dict.fromkeys(l["speaker"] for l in s["lines"]))[:3]
        secs.append(s)
    ep["sections"] = secs
    quiz = []
    for q in ep.get("quiz") or []:
        try:
            opts = [str(o) for o in q["options"]][:4]
            a = int(q["answer"])
            if len(opts) == 4 and 0 <= a < 4 and q.get("q"):
                quiz.append({"q": q["q"], "options": opts, "answer": a, "explain": q.get("explain", "")})
        except Exception:
            continue
    ep["quiz"] = quiz[:5]
    if len(ep["quiz"]) < 3:
        problems.append("fewer than 3 valid quiz questions")
    ep["recap"] = [str(r) for r in (ep.get("recap") or [])][:6]
    o = ep.get("outro") or {}
    o["lines"] = fix_lines(o.get("lines"))
    ep["outro"] = o
    shorts = []
    for sh in ep.get("shorts") or []:
        sh["lines"] = fix_lines(sh.get("lines"))
        if len(sh["lines"]) < 2:
            continue
        sh["cast"] = [c for c in (sh.get("cast") or []) if c in allowed] or [teacher]
        if sh.get("kind") == "quiz":
            q = sh.get("quiz") or {}
            if not (isinstance(q.get("options"), list) and len(q["options"]) == 4):
                sh["kind"] = "fact"
                sh.pop("quiz", None)
        if sh.get("kind") != "quiz":
            sh["visual"] = _fix_visual(sh.get("visual"))
        shorts.append(sh)
    ep["shorts"] = shorts
    if not shorts:
        problems.append("no valid shorts")
    kinds = [s["visual"]["kind"] for s in secs if s.get("mode") == "board"]
    sig = {k for k in kinds if k in ("knolling", "cutaway", "anatomy", "exploded")}
    if len(sig) < 2:
        problems.append(f"only {len(sig)} signature devices ({', '.join(sorted(sig)) or 'none'})")
    meta = ep.get("meta") or {}
    if not meta.get("title"):
        problems.append("no title")
    th = meta.get("thumbnail") or {}
    if th.get("character") not in allowed:
        th["character"] = cast_choice.get("guest") or cast_choice.get("learner") or teacher
    if th.get("icon") not in ALLOWED_ICONS:
        th["icon"] = "idea"
    if th.get("emotion") not in EMOTIONS:
        th["emotion"] = "shocked"
    meta["thumbnail"] = th
    ep["meta"] = meta
    return ep, problems


def write_episode(topic: dict, notes: str, cast_choice: dict, next_title: str) -> tuple[dict, str, list[str]]:
    cfg = settings.config()
    lo, hi = cfg["video"]["long_words"]
    prompt = build_prompt(topic, notes, cast_choice, (lo, hi), next_title)
    ep, who = llm.chat(SYSTEM, prompt, want_json=True, temperature=0.75, max_tokens=24000)
    ep, problems = validate(ep, cast_choice)
    n = spoken_words(ep)
    if n < lo * 0.85 or problems:
        why = []
        if n < lo * 0.85:
            why.append(f"The spoken lines total only {n} words; they must total {lo}-{hi}. Add depth: more story scenes, examples and explanation — no filler, no repetition, facts only from the notes.")
        if problems:
            why.append("Fix these problems: " + "; ".join(problems) + ".")
        fix = (
            "Here is your episode JSON:\n" + json.dumps(ep, ensure_ascii=False) + "\n\n" + " ".join(why)
            + "\nReturn the complete corrected episode JSON (all keys).\n\nRESEARCH NOTES:\n<<<\n" + notes + "\n>>>"
        )
        try:
            ep2, who2 = llm.chat(SYSTEM, fix, want_json=True, temperature=0.6, max_tokens=24000)
            ep2, problems2 = validate(ep2, cast_choice)
            if spoken_words(ep2) >= n and len(problems2) <= len(problems):
                ep, problems, who = ep2, problems2, who2
        except llm.LLMError:
            pass
    return ep, who, problems
