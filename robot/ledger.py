"""The robot's memory, saved in data/ledger.json (and full scripts in data/episodes/).
Kept small on purpose so the repository never grows too big."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from . import settings

PATH = settings.DATA / "ledger.json"
EPISODES = settings.DATA / "episodes"
MAX_VIDEOS = 600  # older entries are summarised so the file stays small


def load(apply: bool = True) -> dict:
    if PATH.exists():
        d = json.loads(PATH.read_text(encoding="utf-8"))
    else:
        d = {}
    d.setdefault("videos", [])
    d.setdefault("episodes", {})
    d.setdefault("playlists", {})
    d.setdefault("learning", {})
    d.setdefault("pending_comments", [])
    d.setdefault("archive", {"videos": 0})
    if apply:
        _apply_decisions(d)
    return d


DECISIONS = settings.DATA / "decisions"


def write_decision(dec: dict) -> None:
    """Your replies are stored as small separate files so they never clash with a
    video being made at the same moment; the next run folds them into the ledger."""
    DECISIONS.mkdir(parents=True, exist_ok=True)
    (DECISIONS / f"issue-{dec['issue']}.json").write_text(json.dumps(dec, ensure_ascii=False), encoding="utf-8")


def _apply_decisions(d: dict) -> None:
    if not DECISIONS.exists():
        return
    for f in sorted(DECISIONS.glob("*.json")):
        try:
            dec = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            f.unlink(missing_ok=True)
            continue
        for v in reversed(d["videos"]):
            if v.get("issue") == dec.get("issue") or (dec.get("video_id") and v.get("video_id") == dec.get("video_id")):
                for k in ("status", "published_at", "rejected_reason"):
                    if dec.get(k):
                        v[k] = dec[k]
                if dec.get("status") == "rejected" and v.get("kind") == "long" and v.get("episode") in d["episodes"]:
                    d["episodes"][v["episode"]]["rejected"] = True
                break
        f.unlink(missing_ok=True)


def save(d: dict) -> None:
    settings.DATA.mkdir(parents=True, exist_ok=True)
    if len(d["videos"]) > MAX_VIDEOS:
        old = d["videos"][: len(d["videos"]) - MAX_VIDEOS]
        d["videos"] = d["videos"][-MAX_VIDEOS:]
        d["archive"]["videos"] = d["archive"].get("videos", 0) + len(old)
    PATH.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def save_episode(eid: str, ep: dict) -> str:
    EPISODES.mkdir(parents=True, exist_ok=True)
    p = EPISODES / f"{eid}.json"
    p.write_text(json.dumps(ep, ensure_ascii=False, indent=1), encoding="utf-8")
    return str(p.relative_to(settings.ROOT))


def load_episode(eid: str) -> dict | None:
    p = EPISODES / f"{eid}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def find(d: dict, **kw) -> dict | None:
    for v in reversed(d["videos"]):
        if all(v.get(k) == val for k, val in kw.items()):
            return v
    return None
