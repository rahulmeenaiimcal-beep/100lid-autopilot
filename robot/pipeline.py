"""Makes one long video or one Short from start to finish, then uploads it and
asks for your OK."""
from __future__ import annotations

import json
import random
import re
import shutil
import time
from datetime import datetime, timedelta
from pathlib import Path

from . import audio, captions, factcheck, learn, previews, render, research, review, schedule, seo, settings, timeline, topics, tts, writer, youtube
from . import ledger as L


def log(msg: str) -> None:
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


def summary(md: str) -> None:
    """Adds a line to the run's summary page on GitHub (Actions → run)."""
    p = settings.env("GITHUB_STEP_SUMMARY")
    if p:
        with open(p, "a", encoding="utf-8") as f:
            f.write(md + "\n")
    print(md)


# ------------------------------------------------------------------ thumbnail
def thumb_props(ep: dict, d: dict, palette: int | None = None, layout: int | None = None) -> dict:
    t = (ep.get("meta") or {}).get("thumbnail") or {}
    cfg = settings.config()
    pal = palette if palette is not None else learn.pick(d, "palette", list(range(6)), 0)
    lay = layout if layout is not None else learn.pick(d, "layout", [0, 1], 0)
    return {
        "width": 1280,
        "height": 720,
        "brand": {"name": cfg["channel"]["name"], "handle": cfg["channel"]["handle"], "accent": "#ffd23f", "accent2": "#073b4c"},
        "series": ep.get("series", ""),
        "textTop": t.get("textTop", "")[:24],
        "textBig": t.get("textBig", "")[:30],
        "textSmall": t.get("textSmall", "")[:24],
        "emotion": t.get("emotion", "shocked"),
        "character": timeline.char_look(t.get("character", "chotu")),
        "icon": t.get("icon", "idea"),
        "palette": int(pal),
        "layout": int(lay),
    }


def _eid(topic_id: str) -> str:
    return f"{datetime.now():%Y%m%d-%H%M}-{re.sub(r'[^a-z0-9-]', '', topic_id.lower())[:40]}"


def _provider(who: str) -> str:
    return (who or "").split("/")[0]


def _check_channel() -> tuple[bool, str]:
    ch = youtube.my_channel()
    want = settings.config()["channel"].get("channel_id")
    got = ch.get("id")
    if want and got != want:
        return False, f"The YouTube login belongs to channel {got} ({ch.get('snippet', {}).get('title')}), not {want}. Upload stopped to protect your other channels."
    return True, ch.get("snippet", {}).get("title", "")


# ------------------------------------------------------------------ upload + review
def _upload_and_review(d: dict, rec: dict, mp4: Path, title: str, desc: str, tags: list[str], thumb: Path | None,
                       caps: dict, playlist_key: str, slot: datetime | None, sheet: Path | None, extra_notes: list[str],
                       localizations: dict | None) -> None:
    mode = settings.config().get("review_mode", "approve")
    ok, msg = _check_channel()
    if not ok:
        raise RuntimeError(msg)
    publish_at = schedule.to_utc_iso(slot) if (slot and mode in ("veto", "auto")) else None
    log(f"uploading ({'scheduled ' + schedule.pretty(slot) if publish_at else 'private'})")
    vid = youtube.upload(mp4, title, desc, tags, privacy="private", publish_at=publish_at, localizations=localizations)
    rec.update({"video_id": vid, "status": "scheduled" if publish_at else "uploaded", "uploaded_at": L.now_iso()})
    if thumb:
        rec["thumb_set"] = youtube.set_thumbnail(vid, thumb)
    if caps.get("hi"):
        youtube.add_caption(vid, "hi", "हिन्दी", caps["hi"])
    if caps.get("en"):
        youtube.add_caption(vid, "en", "English", caps["en"])
    series_name = settings.config()["series"].get(playlist_key, playlist_key)
    pl = d["playlists"].get(playlist_key)
    if not pl:
        try:
            pl = youtube.ensure_playlist(series_name, f"{series_name} — 100LID exam-prep explainers.")
            d["playlists"][playlist_key] = pl
        except Exception as e:
            log(f"playlist failed: {e}")
    if pl:
        youtube.add_to_playlist(pl, vid)
    if rec.get("pinned_comment"):
        d["pending_comments"].append({"video_id": vid, "text": rec["pinned_comment"]})
    # previews + review issue
    files = [p for p in (sheet, thumb) if p]
    base = previews.publish(rec["id"], files) if files else ""
    when = schedule.pretty(slot) if slot else "the next free slot"
    body = [
        f"## 🎬 {title}",
        "",
        f"**Watch it (only you can see it):** https://youtu.be/{vid}",
        f"**Edit in YouTube Studio:** https://studio.youtube.com/video/{vid}/edit",
        f"**Planned time:** {when}",
        "",
    ]
    if base:
        if thumb:
            body += [f"![thumbnail]({base}/{thumb.name})", ""]
        if sheet:
            body += [f"![scenes]({base}/{sheet.name})", ""]
    if mode == "approve":
        body += ["### Your decision", "Reply to this email or comment here with one word:",
                 "- **ok** → schedule it for the planned time", "- **now** → publish it right away",
                 "- **no** → keep it private (the robot makes a different video for this slot)", ""]
    else:
        body += ["### This video is already scheduled", "Reply **no** before the planned time to stop it.", ""]
    if extra_notes:
        body += ["### Please glance at"] + [f"- {n}" for n in extra_notes] + [""]
    if rec.get("kind") == "short" and rec.get("long_video_id"):
        body += [f"💡 Optional (10 seconds): in YouTube Studio, open this Short → **Related video** → choose https://youtu.be/{rec['long_video_id']} so viewers can jump to the full video."]
    n = review.open_issue(f"Review: {title[:90]}", "\n".join(body), ["review"])
    rec["issue"] = n


# ------------------------------------------------------------------ long video
def make_long(d: dict, slot: datetime | None, upload: bool = True, sample: bool = False) -> dict:
    t0 = time.time()
    settings.ensure_dirs()
    if sample:
        ep = json.loads((settings.SAMPLES / "ssy_episode.json").read_text(encoding="utf-8"))
        topic = {"id": ep["topic_id"], "series": ep["series"]}
        notes, fc, problems, who = "", {"fixed": [], "unresolved": [], "checked_by": "hand-written sample"}, [], "sample"
    else:
        topic = topics.choose(d)
        log(f"topic: {topic['title_en']}")
        res = research.gather(topic)
        notes = res["notes"]
        if len(notes) < 800:
            raise RuntimeError(f"Not enough research material found for {topic['id']}")
        recent = [v for v in d["videos"] if v.get("kind") == "long"]
        cast_choice = writer.pick_cast(topic, recent)
        next_title = topics.peek_next_title(d, topic["id"])
        notes_plus = notes + learn.device_hint(d)
        ep, who, problems = writer.write_episode(topic, notes_plus, cast_choice, next_title)
        ep.setdefault("meta", {})
        ep["meta"]["sources"] = list(dict.fromkeys((ep["meta"].get("sources") or []) + res["sources"]))[:8]
        log(f"script by {who}: {writer.spoken_words(ep)} words, problems: {problems or 'none'}")
        fc = factcheck.check(ep, notes, _provider(who)) if settings.config()["llm"].get("fact_check", True) else {"fixed": [], "unresolved": []}
        log(f"fact-check by {fc.get('checked_by')}: {len(fc['fixed'])} fixed, {len(fc['unresolved'])} to look at")
    eid = _eid(topic["id"])
    ep_path = L.save_episode(eid, {**ep, "_factcheck": fc, "_writer": who})
    d["episodes"][eid] = {"topic_id": topic["id"], "series": ep.get("series"), "created": L.now_iso(), "path": ep_path,
                          "shorts_done": [], "long_video_id": None, "title": ep.get("meta", {}).get("title", "")}
    work = settings.WORK / eid
    work.mkdir(parents=True, exist_ok=True)
    log("recording voices")
    voices = tts.Voices(settings.WORK / "voice")
    plan = timeline.build_long(ep, voices)
    secs = plan.props["durationInFrames"] / timeline.FPS
    log(f"timeline: {secs / 60:.1f} min, {len(plan.props['shots'])} shots, voices {voices.used}")
    wav = audio.mix(plan, ep.get("series", "schemes"), work / "mix.wav", seed=random.randint(0, 999))
    log("rendering video")
    mp4 = render.video(plan.props, wav, settings.OUT / f"{eid}.mp4", f"{eid}-long")
    log(f"rendered in {(time.time() - t0) / 60:.1f} min so far")
    tp = thumb_props(ep, d)
    thumb = render.still(tp, settings.OUT / f"{eid}-thumb.png", f"{eid}-thumb")
    caps = captions.make(plan, settings.OUT, english=settings.config()["publish"].get("english_subtitles", True))
    shutil.copy(caps["hi"], settings.OUT / f"{eid}.hi.srt")
    if caps.get("en"):
        shutil.copy(caps["en"], settings.OUT / f"{eid}.en.srt")
    times = [b["from"] / timeline.FPS + 2 for b in plan.reveal_beats][:7] + [secs * 0.92]
    sheet = render.contact_sheet(mp4, [1.5] + times, settings.OUT / f"{eid}-sheet.jpg")
    meta = ep.get("meta") or {}
    title = seo.clean_title(meta.get("title", topic.get("title_en", "")))
    pl_url = f"https://www.youtube.com/playlist?list={d['playlists'][ep.get('series')]}" if d["playlists"].get(ep.get("series")) else ""
    desc = seo.long_description(ep, plan.chapters, pl_url, (ep.get("outro") or {}).get("next_title", ""))
    tags = seo.tags(meta.get("tags") or [], [topic.get("title_en", ""), "100LID", "bank exam", "SSC", "exam GK in Hindi"])
    loc = None
    if settings.config()["publish"].get("english_title_description", True) and meta.get("title_en"):
        loc = {"en": {"title": seo.clean_title(meta["title_en"]), "description": seo.long_description_en(ep, plan.chapters)}}
    rec = {
        "id": eid, "kind": "long", "episode": eid, "topic_id": topic["id"], "series": ep.get("series"),
        "slot": schedule.key("long", slot) if slot else None, "title": title, "status": "made", "created": L.now_iso(),
        "cast": ep.get("cast"), "beats": plan.reveal_beats, "frames": plan.props["durationInFrames"], "seconds": round(secs),
        "thumb": {"palette": tp["palette"], "layout": tp["layout"], "emotion": tp["emotion"]},
        "writer": who, "factcheck_fixed": len(fc.get("fixed", [])), "pinned_comment": meta.get("pinned_comment"),
    }
    d["videos"].append(rec)
    notes_for_you = []
    if fc.get("unresolved"):
        notes_for_you += [f"Fact-check doubt: {u}" for u in fc["unresolved"][:6]]
    if problems:
        notes_for_you += [f"Script note: {p}" for p in problems]
    if fc.get("fixed"):
        notes_for_you.append(f"The fact-checker corrected {len(fc['fixed'])} statement(s) automatically (details in {ep_path}).")
    if upload and youtube.ready():
        _upload_and_review(d, rec, mp4, title, desc, tags, thumb, caps, ep.get("series", "schemes"), slot, sheet, notes_for_you, loc)
        d["episodes"][eid]["long_video_id"] = rec.get("video_id")
    else:
        rec["status"] = "test"
        d["episodes"][eid]["test"] = True
        base = previews.publish(eid, [sheet, thumb])
        summary(f"### Test video made (not uploaded)\n- **{title}** — {secs / 60:.1f} min\n- Download it from this run's page under **Artifacts**.")
        if base:
            summary(f"\n![thumbnail]({base}/{thumb.name})\n\n![scenes]({base}/{sheet.name})")
    summary(f"- Long video **{title}** ready in {(time.time() - t0) / 60:.0f} min · voices: {voices.used} · writer: {who}")
    return rec


# ------------------------------------------------------------------ short
def pending_short(d: dict, upload: bool = True) -> tuple[str, int, dict, dict] | None:
    """The best not-yet-made Short from recent episodes (prefers ones whose long video exists)."""
    weights = (d.get("learning", {}).get("weights", {}) or {}).get("short_kind", {})
    best = None
    for eid, e in sorted(d["episodes"].items(), key=lambda kv: kv[1].get("created", ""), reverse=True)[:6]:
        if e.get("rejected") or (e.get("test") and upload):
            continue
        ep = L.load_episode(eid)
        if not ep:
            continue
        for i, sh in enumerate(ep.get("shorts") or []):
            if i in e.get("shorts_done", []):
                continue
            score = (2 if e.get("long_video_id") else 0) + weights.get(str(sh.get("kind")), 1.0) + random.random() * 0.3
            if best is None or score > best[0]:
                best = (score, eid, i, sh, ep)
    if not best:
        return None
    return best[1], best[2], best[3], best[4]


def make_short(d: dict, slot: datetime | None, upload: bool = True) -> dict | None:
    t0 = time.time()
    settings.ensure_dirs()
    got = pending_short(d, upload)
    if not got:
        log("no Short waiting to be made")
        return None
    eid, idx, sh, ep = got
    sid = f"{eid}-s{idx}"
    voices = tts.Voices(settings.WORK / "voice")
    plan = timeline.build_short(ep, sh, voices)
    work = settings.WORK / sid
    work.mkdir(parents=True, exist_ok=True)
    wav = audio.mix(plan, "shorts", work / "mix.wav", seed=idx)
    mp4 = render.video(plan.props, wav, settings.OUT / f"{sid}.mp4", sid)
    caps = captions.make(plan, settings.OUT, english=settings.config()["publish"].get("english_subtitles", True))
    secs = plan.props["durationInFrames"] / timeline.FPS
    sheet = render.contact_sheet(mp4, [0.8, secs * 0.35, secs * 0.65, secs - 1.5], settings.OUT / f"{sid}-sheet.jpg", cols=4)
    long_id = d["episodes"][eid].get("long_video_id")
    title = seo.clean_title(sh.get("title") or (ep.get("meta") or {}).get("title", ""))
    if "#shorts" not in title.lower() and len(title) < 90:
        title += " #Shorts"
    desc = seo.short_description(ep, sh, f"https://youtu.be/{long_id}" if long_id else "")
    tags = seo.tags(((ep.get("meta") or {}).get("tags") or [])[:12] + ["shorts", "exam facts"])
    rec = {
        "id": sid, "kind": "short", "episode": eid, "short_index": idx, "short_kind": sh.get("kind"),
        "topic_id": ep.get("topic_id"), "series": "shorts", "slot": schedule.key("short", slot) if slot else None,
        "title": title, "status": "made", "created": L.now_iso(), "long_video_id": long_id, "seconds": round(secs),
        "pinned_comment": None,
    }
    d["videos"].append(rec)
    d["episodes"][eid].setdefault("shorts_done", []).append(idx)
    if upload and youtube.ready():
        _upload_and_review(d, rec, mp4, title, desc, tags, None, caps, "shorts", slot, sheet, [], None)
    else:
        rec["status"] = "test"
        summary(f"### Test Short made (not uploaded): **{title}** ({secs:.0f}s)")
    summary(f"- Short **{title}** ready in {(time.time() - t0) / 60:.0f} min")
    return rec


# ------------------------------------------------------------------ decisions on review issues
def handle_reply(d: dict, issue: int, text: str) -> str:
    rec = next((v for v in reversed(d["videos"]) if v.get("issue") == issue), None)
    if not rec or not rec.get("video_id"):
        return "not a video review issue"
    dec = review.decision(text)
    if not dec:
        return "no decision found in reply"
    out = {"issue": issue, "video_id": rec["video_id"]}
    if dec == "no":
        youtube.set_visibility(rec["video_id"], "private")
        out.update(status="rejected", rejected_reason=text.strip()[:300])
        review.comment(issue, "👍 Kept private. The robot will make a different video for this slot.")
        review.close(issue, ["rejected"])
    elif dec == "now":
        youtube.set_visibility(rec["video_id"], "public")
        out.update(status="public", published_at=L.now_iso())
        review.comment(issue, f"✅ Published now: https://youtu.be/{rec['video_id']}")
        review.close(issue, ["scheduled"])
    else:  # ok -> schedule at its slot (or publish now if that time has passed)
        slot = None
        if rec.get("slot"):
            try:
                slot = datetime.fromisoformat(rec["slot"].split("@", 1)[1])
            except Exception:
                slot = None
        if not slot or slot < schedule.now() + timedelta(minutes=20):
            youtube.set_visibility(rec["video_id"], "public")
            out.update(status="public", published_at=L.now_iso())
            review.comment(issue, f"✅ Its planned time had passed, so it is published now: https://youtu.be/{rec['video_id']}")
        else:
            youtube.set_visibility(rec["video_id"], "private", schedule.to_utc_iso(slot))
            out.update(status="scheduled")
            review.comment(issue, f"✅ Scheduled for **{schedule.pretty(slot)}**.")
        review.close(issue, ["scheduled"])
    L.write_decision(out)
    return out["status"]


def post_pending_comments(d: dict) -> None:
    keep = []
    public = {v["video_id"] for v in d["videos"] if v.get("status") == "public" and v.get("video_id")}
    for c in d.get("pending_comments", []):
        if c["video_id"] in public:
            if not youtube.comment(c["video_id"], c["text"]):
                keep.append(c)
        else:
            keep.append(c)
    d["pending_comments"] = keep[-50:]
