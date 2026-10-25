"""Keeps small preview images (contact sheets, thumbnails) on a separate `previews`
branch so review emails can show them. The branch is rewritten each time with only
the last 21 days of images, so it never grows."""
from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path

from . import settings

KEEP_DAYS = 21


def _git(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True)


def publish(folder_name: str, files: list[Path]) -> str:
    """Returns the base raw URL for the folder, or '' if not possible."""
    repo, token = settings.env("GITHUB_REPOSITORY"), settings.env("GITHUB_TOKEN")
    if not (repo and token):
        return ""
    url = f"https://x-access-token:{token}@github.com/{repo}.git"
    tmp = settings.WORK / "previews-branch"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    r = _git(["clone", "--depth", "1", "--branch", "previews", url, str(tmp)], settings.ROOT)
    if r.returncode != 0:
        shutil.rmtree(tmp, ignore_errors=True)
        tmp.mkdir(parents=True)
        _git(["init", "-q", "-b", "previews"], tmp)
    shutil.rmtree(tmp / ".git", ignore_errors=True)
    # drop old folders
    cutoff = time.time() - KEEP_DAYS * 86400
    for d in tmp.iterdir():
        stamp = d / ".stamp"
        if d.is_dir() and stamp.exists() and float(stamp.read_text() or 0) < cutoff:
            shutil.rmtree(d, ignore_errors=True)
    dest = tmp / folder_name
    dest.mkdir(parents=True, exist_ok=True)
    (dest / ".stamp").write_text(str(time.time()))
    for f in files:
        if f and Path(f).exists():
            shutil.copy(f, dest / Path(f).name)
    (tmp / "README.md").write_text("Preview images for review emails. Rewritten automatically; old ones are removed.\n")
    _git(["init", "-q", "-b", "previews"], tmp)
    _git(["config", "user.name", "autopilot-bot"], tmp)
    _git(["config", "user.email", "autopilot-bot@users.noreply.github.com"], tmp)
    _git(["add", "-A"], tmp)
    _git(["commit", "-q", "-m", f"previews: {folder_name}"], tmp)
    p = _git(["push", "-q", "--force", url, "HEAD:previews"], tmp)
    if p.returncode != 0:
        print("preview push failed:", p.stderr[-500:].replace(token, "***"))
        return ""
    return f"https://raw.githubusercontent.com/{repo}/previews/{folder_name}"
