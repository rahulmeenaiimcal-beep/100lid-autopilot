"""Review by email: for every new video the robot opens a GitHub issue (GitHub emails
you). You reply "ok" (schedule it), "now" (publish now) or "no" (keep it private).
Replying to the GitHub email itself also works."""
from __future__ import annotations

import re

import requests

from . import settings

API = "https://api.github.com"


def _repo() -> str:
    return settings.env("GITHUB_REPOSITORY")


def _h() -> dict:
    return {"Authorization": f"Bearer {settings.env('GITHUB_TOKEN')}", "Accept": "application/vnd.github+json"}


def enabled() -> bool:
    return bool(settings.env("GITHUB_TOKEN") and _repo())


LABELS = {
    "review": ("fbca04", "A new video is waiting for your OK"),
    "scheduled": ("0e8a16", "Approved and scheduled"),
    "rejected": ("b60205", "Kept private"),
    "report": ("1d76db", "3-day performance report"),
    "problem": ("d93f0b", "Something needs your attention"),
}


def ensure_labels() -> None:
    if not enabled():
        return
    for name, (color, desc) in LABELS.items():
        requests.post(f"{API}/repos/{_repo()}/labels", headers=_h(), json={"name": name, "color": color, "description": desc}, timeout=30)


def open_issue(title: str, body: str, labels: list[str]) -> int | None:
    if not enabled():
        return None
    ensure_labels()
    r = requests.post(f"{API}/repos/{_repo()}/issues", headers=_h(), json={"title": title[:250], "body": body[:60000], "labels": labels}, timeout=30)
    return r.json().get("number") if r.ok else None


def comment(number: int, body: str) -> None:
    if enabled() and number:
        requests.post(f"{API}/repos/{_repo()}/issues/{number}/comments", headers=_h(), json={"body": body[:60000]}, timeout=30)


def close(number: int, labels: list[str] | None = None) -> None:
    if not (enabled() and number):
        return
    body = {"state": "closed"}
    if labels is not None:
        body["labels"] = labels
    requests.patch(f"{API}/repos/{_repo()}/issues/{number}", headers=_h(), json=body, timeout=30)


def close_open(label: str, keep: int | None = None) -> None:
    if not enabled():
        return
    r = requests.get(f"{API}/repos/{_repo()}/issues", headers=_h(), params={"labels": label, "state": "open", "per_page": 50}, timeout=30)
    for it in r.json() if r.ok else []:
        if it.get("number") != keep:
            close(it["number"])


def decision(text: str) -> str | None:
    """Reads a reply. Returns 'ok', 'now', 'no' or None (not a decision)."""
    t = (text or "").strip().lower()
    t = re.split(r"\n\s*on .{5,80}wrote:|\n>", t)[0]  # ignore quoted email text
    words = re.findall(r"[\wऀ-ॿ👍👎✅❌]+", t)
    first = " ".join(words[:4])
    if re.search(r"\b(now|abhi|turant)\b|अभी", first):
        return "now"
    if re.search(r"\b(no|nahi|nahin|reject|stop|cancel)\b|नहीं|👎|❌", first):
        return "no"
    if re.search(r"\b(ok|okay|yes|haan|ha|approve|approved|go|done|theek)\b|हाँ|हां|ठीक|👍|✅", first):
        return "ok"
    return None


def has_open(label: str) -> bool:
    if not enabled():
        return False
    r = requests.get(f"{API}/repos/{_repo()}/issues", headers=_h(), params={"labels": label, "state": "open", "per_page": 1}, timeout=30)
    return bool(r.ok and r.json())
