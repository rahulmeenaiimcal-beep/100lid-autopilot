"""Turns a written episode (script JSON) plus its voice clips into a frame-exact
plan for the renderer (props.json) and for the sound mix.

The same builder is used for long videos (16:9) and Shorts (9:16)."""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Callable

from . import settings

FPS = 30


@dataclass
class Clip:
    speaker: str
    text: str
    duration: float              # seconds
    amp: list[float]             # loudness per video frame, 0..1
    path: str = ""               # audio file
    en: str = ""                 # English subtitle text for this line


@dataclass
class Plan:
    props: dict
    voice: list[tuple[int, Clip]] = field(default_factory=list)      # (start frame, clip)
    sfx: list[tuple[int, str]] = field(default_factory=list)         # (frame, kind)
    chapters: list[tuple[float, str]] = field(default_factory=list)  # (seconds, title)
    reveal_beats: list[dict] = field(default_factory=list)           # where each visual device sits (for learning)


VoiceFn = Callable[[str, str], Clip]

GAP_SAME = 0.12     # pause between two lines of the same speaker (seconds)
GAP_SWITCH = 0.26   # pause when the speaker changes
CHAPTER_SEC = 1.25
QUIZ_COUNT = 5


def f(sec: float) -> int:
    return int(round(sec * FPS))


def char_look(cid: str) -> dict:
    c = settings.cast().get(cid) or {}
    look = dict(c.get("look") or {})
    look["name"] = c.get("name_hi", cid)
    look.setdefault("height", 1.0)
    return look


def positions(n: int, vertical: bool) -> list[float]:
    if vertical:
        return {1: [0.5], 2: [0.27, 0.73], 3: [0.18, 0.5, 0.82]}.get(n, [0.5])
    return {1: [0.5], 2: [0.3, 0.7], 3: [0.2, 0.5, 0.8], 4: [0.14, 0.38, 0.62, 0.86]}.get(n, [0.5])


def _reveal_list(r) -> list[int]:
    if r is None:
        return []
    if isinstance(r, list):
        return [int(x) for x in r if isinstance(x, (int, float))]
    if isinstance(r, (int, float)):
        return [int(r)]
    return []


def visual_items(v: dict | None) -> int:
    if not v:
        return 0
    if v.get("kind") == "compare":
        return len(v.get("left", {}).get("points", [])) + len(v.get("right", {}).get("points", []))
    if v.get("kind") == "stat":
        return 0
    return len(v.get("items") or [])


def sub_chunks(text: str, start: int, end: int, max_chars: int = 84) -> list[dict]:
    """Splits an English line into subtitle cues of at most 2 short lines, timed by length."""
    from .captions import _split  # same splitting rules as the .srt files

    pieces = _split(text.strip(), max_chars) if text and text.strip() else []
    total = sum(len(p) for p in pieces) or 1
    out, t = [], float(start)
    for p in pieces:
        d = (end - start) * len(p) / total
        out.append({"from": int(t), "to": int(t + d), "text": p})
        t += d
    return out


def caption_chunks(text: str, start: int, end: int, max_words: int = 4) -> list[dict]:
    """Splits a spoken line into short on-screen caption pieces, timed by length."""
    words = [w for w in re.split(r"\s+", text.strip()) if w]
    if not words:
        return []
    chunks: list[list[str]] = []
    cur: list[str] = []
    for w in words:
        cur.append(w)
        if len(cur) >= max_words or re.search(r"[।,.!?—:]$", w):
            chunks.append(cur)
            cur = []
    if cur:
        chunks.append(cur)
    total = sum(len(" ".join(c)) for c in chunks) or 1
    out, t = [], start
    for c in chunks:
        txt = " ".join(c)
        d = (end - start) * len(txt) / total
        out.append({"from": int(t), "to": int(t + d), "text": txt})
        t += d
    return out


class Builder:
    def __init__(self, ep: dict, voice: VoiceFn, fmt: str):
        self.ep = ep
        self.voice = voice
        self.fmt = fmt
        self.vertical = fmt == "short"
        size = settings.config()["render"]["short_size" if self.vertical else "long_size"]
        self.W, self.H = size
        self.t = 0                       # current frame
        self.shots: list[dict] = []
        self.talk: list[dict] = []
        self.amp: list[int] = []
        self.captions: list[dict] = []
        self.subs: list[dict] = []        # burned-in English subtitles (long videos)
        self.burn_en = (not self.vertical) and bool(settings.config()["video"].get("burn_english_subtitles_on_long", True))
        self.plan_voice: list[tuple[int, Clip]] = []
        self.sfx: list[tuple[int, str]] = []
        self.chapters: list[tuple[float, str]] = []
        self.beats: list[dict] = []
        self.cast_ids: list[str] = []
        self.last_speaker: str | None = None
        self.emotion_state: dict[str, str] = {}

    # ---------------------------------------------------------------- audio helpers
    def _use(self, cid: str) -> None:
        if cid and cid not in self.cast_ids and cid in settings.cast():  # "_presenter" (your clips) is not a cartoon
            self.cast_ids.append(cid)

    def say(self, speaker: str, text: str, en: str = "") -> tuple[int, int, Clip]:
        """Adds one spoken line at the current time; returns (start, end) frames."""
        self._use(speaker)
        gap = 0 if self.last_speaker is None else (GAP_SAME if speaker == self.last_speaker else GAP_SWITCH)
        self.t += f(gap)
        clip = self.voice(speaker, text)
        clip.en = (en or "").strip()
        start = self.t
        n = max(1, f(clip.duration))
        end = start + n
        self.plan_voice.append((start, clip))
        self.talk.append({"from": start, "to": end, "id": speaker})
        need = end + 1 - len(self.amp)
        if need > 0:
            self.amp.extend([0] * need)
        for i in range(n):
            a = clip.amp[i] if i < len(clip.amp) else 0
            self.amp[start + i] = max(0, min(9, int(round(a * 9))))
        if self.vertical and settings.config()["video"].get("burn_captions_on_shorts", True):
            self.captions.extend(caption_chunks(text, start, end))
        if self.burn_en and clip.en:
            self.subs.extend(sub_chunks(clip.en, start, end))
        self.t = end
        self.last_speaker = speaker
        return start, end, clip

    def pause(self, sec: float) -> None:
        self.t += f(sec)

    # ---------------------------------------------------------------- shots
    def add_shot(self, start: int, layout: str, **kw) -> dict:
        shot = {"from": start, "duration": max(1, self.t - start), "layout": layout}
        shot.update({k: v for k, v in kw.items() if v is not None})
        self.shots.append(shot)
        return shot

    def stage_chars(self, ids: list[str], speaker: str | None, line: dict | None) -> list[dict]:
        ids = [i for i in ids if i in settings.cast()]
        xs = positions(len(ids), self.vertical)
        out = []
        for cid, x in zip(ids, xs):
            if line and cid == speaker:
                emo = line.get("emotion") or "neutral"
                ges = line.get("gesture") or "explain"
                self.emotion_state[cid] = emo
            else:
                emo = self.emotion_state.get(cid, "neutral")
                ges = "none"
            out.append({"id": cid, "x": x, "facing": 1 if x < 0.5 else -1, "emotion": emo, "gesture": ges})
        return out

    def block_hook(self, hook: dict) -> None:
        """Opening: the story problem with a big headline, then a fast teaser of
        everything the video covers (the exploded view) on the last hook line."""
        start = self.t
        lines = hook.get("lines") or []
        v = hook.get("visual")
        story = lines[:-1] if (v and len(lines) >= 2) else lines
        teaser = lines[-1:] if (v and len(lines) >= 2) else []
        ids = []
        for ln in story:
            if ln["speaker"] not in ids:
                ids.append(ln["speaker"])
        ids = ids[:3]
        self.sfx.append((start, "hit"))
        for ln in story:
            self.say(ln["speaker"], ln["text"], ln.get("en", ""))
        chars = self.stage_chars(ids, story[0]["speaker"] if story else None, story[0] if story else None)
        self.add_shot(
            start,
            "hook",
            title=hook.get("title"),
            subtitle=hook.get("subtitle"),
            setting=hook.get("setting") or "studio",
            chars=chars,
        )
        if teaser:
            self.block_board({"visual": v, "lines": teaser, "presenter": teaser[0]["speaker"], "_fast": True})
            if self.beats:
                self.beats[-1]["where"] = "hook"
        else:
            self.pause(0.35)
            self.shots[-1]["duration"] = self.t - start

    def block_chapter(self, title: str, number: int) -> None:
        if self.vertical:
            return
        start = self.t
        self.pause(CHAPTER_SEC)
        self.sfx.append((start, "whoosh"))
        self.chapters.append((start / FPS, title))
        self.add_shot(start, "chapter", title=title, subtitle=f"भाग {number}")
        self.last_speaker = None

    def block_stage(self, sec: dict) -> None:
        lines = sec.get("lines") or []
        ids = sec.get("chars") or []
        if not ids:
            for ln in lines:
                if ln["speaker"] not in ids:
                    ids.append(ln["speaker"])
        ids = ids[: (3 if not self.vertical else 2)]
        prev = None
        for i, ln in enumerate(lines):
            start = self.t
            s0, s1, _ = self.say(ln["speaker"], ln["text"], ln.get("en", ""))
            if i == len(lines) - 1:
                self.pause(0.15)
            cam = "wide" if i == 0 or i % 3 == 2 else ("close" if ln["speaker"] != prev else "push")
            stick = None
            if ln.get("onscreen"):
                stick = [{"text": ln["onscreen"], "from": (s0 - start) + 8, "to": (s1 - start)}]
                self.sfx.append((s0 + 8, "pop"))
            self.add_shot(
                start,
                "stage",
                setting=sec.get("setting") or "studio",
                chars=self.stage_chars(ids, ln["speaker"], ln),
                camera=cam,
                sticker=stick,
            )
            prev = ln["speaker"]

    def block_board(self, sec: dict) -> None:
        v = sec.get("visual")
        lines = sec.get("lines") or []
        presenter = sec.get("presenter") or self.teacher()
        self._use(presenter)
        start = self.t
        self.sfx.append((start, "whoosh"))
        n_items = visual_items(v)
        reveal: dict[int, int] = {}
        explicit = any(ln.get("reveal") is not None for ln in lines)
        for i, ln in enumerate(lines):
            s0, s1, _ = self.say(ln["speaker"], ln["text"], ln.get("en", ""))
            idxs = _reveal_list(ln.get("reveal"))
            if not explicit and n_items:
                # first line introduces, the next lines reveal one item each
                k = i - 1 if len(lines) > n_items else i
                idxs = [k] if 0 <= k < n_items else []
            for j, ix in enumerate(idxs):
                if ix not in reveal:
                    reveal[ix] = (s0 - start) + 4 + j * 14
                    self.sfx.append((s0 + 4 + j * 14, "pop"))
        self.pause(0.3)
        dur = self.t - start
        rv = []
        for ix in range(n_items):
            if ix in reveal:
                rv.append(reveal[ix])
            else:
                rv.append(int(dur * (ix + 1) / (n_items + 1)))
        rv = sorted(rv) if not explicit else rv
        if sec.get("_fast"):
            rv = [6 + 13 * i for i in range(n_items)]
        self.add_shot(start, "board", visual=v, reveal=rv, presenter=presenter)
        if v:
            self.beats.append({"kind": v.get("kind"), "from": start, "to": self.t, "where": "body"})

    def block_quiz(self, q: dict, n: int, total: int, presenter: str) -> None:
        start = self.t
        letters = "ABCD"
        s0, s1, _ = self.say(presenter, f"प्रश्न {n}: {q['q']}", f"Question {n}: {q['q_en']}" if q.get("q_en") else "")
        count_from = (s1 - start) + f(0.3)
        self.sfx.append((start + count_from, "tick"))
        self.t = start + count_from + f(QUIZ_COUNT)
        reveal_at = self.t - start
        self.sfx.append((self.t, "ding"))
        self.last_speaker = None
        ans = q["options"][q["answer"]] if 0 <= q.get("answer", 0) < len(q["options"]) else ""
        explain = q.get("explain") or ""
        ans_en = (q.get("options_en") or [""] * 4)[q["answer"]] if len(q.get("options_en") or []) == len(q["options"]) else ""
        en = f"The correct answer is {letters[q['answer']]}: {ans_en}. {q.get('explain_en', '')}".strip() if ans_en else ""
        self.say(presenter, f"सही जवाब है {letters[q['answer']]}: {ans}। {explain}".strip(), en)
        self.pause(0.35)
        self.add_shot(
            start,
            "quiz",
            presenter=presenter,
            quiz={**q, "qNo": n, "total": total, "countFrom": count_from, "countTo": count_from + f(QUIZ_COUNT), "revealAt": reveal_at},
        )
        self.beats.append({"kind": "quiz", "from": start, "to": self.t, "where": "quiz"})

    def block_recap(self, points: list[str], presenter: str) -> None:
        start = self.t
        en_pts = self.ep.get("recap_en") if len(self.ep.get("recap_en") or []) == len(points) else [""] * len(points)
        self.say(presenter, "चलो, एक minute में recap करते हैं।", "Let's do a quick one-minute recap." if any(en_pts) else "")
        rv = []
        for p, pe in zip(points, en_pts):
            s0, _, _ = self.say(presenter, p, pe)
            rv.append(s0 - start)
        self.pause(0.5)
        self.add_shot(start, "recap", title="Quick Recap · याद रखें", recap=points, reveal=rv, presenter=presenter)

    def block_outro(self, outro: dict) -> None:
        start = self.t
        for ln in outro.get("lines") or []:
            self.say(ln["speaker"], ln["text"], ln.get("en", ""))
        self.pause(1.6)
        self.add_shot(start, "outro", nextTitle=outro.get("next_title"))

    def block_clip(self, info: dict, kind: str) -> None:
        """Your own recorded clip (tip / intro / outro), with exact subtitles."""
        if not info or not info.get("wav") or info.get("duration", 0) <= 0:
            return
        self.t += f(0.25)
        start = self.t
        n = max(1, f(info["duration"]))
        clip = Clip(speaker="_presenter", text=info.get("text", ""), duration=info["duration"], amp=[0.0] * n, path=info["wav"], en=info.get("en", ""))
        self.plan_voice.append((start, clip))
        if len(self.amp) < start + n + 1:
            self.amp.extend([0] * (start + n + 1 - len(self.amp)))
        for sg in info.get("segments") or []:
            a, b = start + f(sg["start"]), start + f(sg["end"])
            if self.burn_en and sg.get("en"):
                self.subs.extend(sub_chunks(sg["en"], a, b))
            if self.vertical and sg.get("hi"):
                self.captions.extend(caption_chunks(sg["hi"], a, b))
        self.t = start + n + f(0.2)
        self.last_speaker = None
        name = settings.config().get("clips", {}).get("presenter_name", "Rahul Sir")
        label = {"tip": f"💡 {name} का Exam Tip", "intro": name, "outro": name}.get(kind, name)
        self.add_shot(start, "clip", clip={"file": info["file"], "w": info.get("w", 1920), "h": info.get("h", 1080), "label": label, "kind": kind})
        self.beats.append({"kind": f"clip_{kind}", "from": start, "to": self.t, "where": kind})

    def teacher(self) -> str:
        c = self.ep.get("cast") or {}
        return c.get("teacher") or "guruji"

    # ---------------------------------------------------------------- whole video
    def build_long(self) -> Plan:
        ep = self.ep
        self.block_hook(ep["hook"])
        if ep.get("_intro_clip"):
            self.block_clip(ep["_intro_clip"], "intro")
        ch = 0
        for sec in ep.get("sections") or []:
            if sec.get("chapter"):
                ch += 1
                self.block_chapter(sec["chapter"], ch)
            if sec.get("mode") == "board" and sec.get("visual"):
                self.block_board(sec)
            else:
                self.block_stage(sec)
        if ep.get("_tip_clip"):
            self.block_clip(ep["_tip_clip"], "tip")
        quiz = ep.get("quiz") or []
        if quiz:
            ch += 1
            self.block_chapter("Quiz Time! 🧠", ch)
            for i, q in enumerate(quiz):
                self.block_quiz(q, i + 1, len(quiz), self.teacher())
        if ep.get("recap"):
            ch += 1
            self.block_chapter("Recap", ch)
            self.block_recap(ep["recap"], self.teacher())
        if ep.get("_outro_clip"):
            self.block_clip(ep["_outro_clip"], "outro")
        if ep.get("outro"):
            self.block_outro(ep["outro"])
        return self.finish(title=ep.get("meta", {}).get("title", ""))

    def build_short(self, sh: dict) -> Plan:
        lines = sh.get("lines") or []
        cast_ids = sh.get("cast") or [self.teacher()]
        teacher = next((c for c in cast_ids if settings.cast().get(c, {}).get("role") == "teacher"), cast_ids[-1])
        if not lines:
            raise ValueError("short has no lines")
        # 1) hook: first line over a big headline
        start = self.t
        self.sfx.append((start, "hit"))
        self.say(lines[0]["speaker"], lines[0]["text"], lines[0].get("en", ""))
        hook_chars = self.stage_chars([lines[0]["speaker"]], lines[0]["speaker"], {"emotion": "excited", "gesture": "point"})
        hook_v = None  # on a phone screen the headline + character alone hit harder
        self.add_shot(start, "hook", title=sh.get("hook_text") or sh.get("title"), setting="studio", chars=hook_chars,
                      visual=hook_v, reveal=[0, 18, 36, 54, 72] if hook_v else None)
        rest = lines[1:]
        if sh.get("kind") == "quiz" and sh.get("quiz"):
            q = dict(sh["quiz"])
            qstart = self.t
            self.t += f(0.2)
            count_from = self.t - qstart
            self.sfx.append((self.t, "tick"))
            self.t += f(QUIZ_COUNT)
            reveal_at = self.t - qstart
            self.sfx.append((self.t, "ding"))
            self.last_speaker = None
            for ln in rest:
                self.say(ln["speaker"], ln["text"], ln.get("en", ""))
            self.pause(0.6)
            self.add_shot(qstart, "quiz", presenter=teacher,
                          quiz={**q, "qNo": 1, "total": 1, "countFrom": count_from, "countTo": count_from + f(QUIZ_COUNT), "revealAt": reveal_at})
        elif sh.get("visual"):
            self.block_board({"visual": sh["visual"], "lines": rest, "presenter": teacher})
        else:
            self.block_stage({"lines": rest, "setting": "studio", "chars": cast_ids})
        return self.finish(title=sh.get("title", ""))

    def finish(self, title: str) -> Plan:
        total = self.t + f(0.3)
        if len(self.amp) < total:
            self.amp.extend([0] * (total - len(self.amp)))
        if self.shots:
            last = self.shots[-1]
            last["duration"] = total - last["from"]
        cfg = settings.config()
        cast = {cid: char_look(cid) for cid in self.cast_ids}
        series_key = self.ep.get("series", "")
        props = {
            "format": self.fmt,
            "fps": FPS,
            "width": self.W,
            "height": self.H,
            "durationInFrames": total,
            "brand": {"name": cfg["channel"]["name"], "handle": cfg["channel"]["handle"], "accent": "#ffd23f", "accent2": "#073b4c"},
            "series": cfg.get("series", {}).get(series_key, series_key),
            "title": title,
            "cast": cast,
            "talk": self.talk,
            "amp": "".join(str(a) for a in self.amp[:total]),
            "shots": self.shots,
            "captions": self.captions,
            "subs": self.subs,
            "chapters": [{"from": f(s), "title": t} for s, t in self.chapters],
        }
        return Plan(props=props, voice=self.plan_voice, sfx=self.sfx, chapters=self.chapters, reveal_beats=self.beats)


def build_long(ep: dict, voice: VoiceFn) -> Plan:
    return Builder(ep, voice, "long").build_long()


def build_short(ep: dict, short: dict, voice: VoiceFn) -> Plan:
    b = Builder(ep, voice, "short")
    return b.build_short(short)


# ---------------------------------------------------------------- for previews without real voices
def estimate_clip(speaker: str, text: str) -> Clip:
    words = max(1, len(text.split()))
    dur = 0.5 + words / 2.55
    n = f(dur)
    amp = [0.0] * n
    for i in range(n):
        syl = 0.5 + 0.5 * math.sin(i * 1.7) * math.sin(i * 0.37 + 1)
        amp[i] = max(0.0, min(1.0, syl)) if 3 < i < n - 3 else 0.0
    return Clip(speaker, text, dur, amp)
