"""Everything that talks to YouTube: uploads, thumbnails, subtitles, playlists,
scheduling, comments and analytics. Uses the official YouTube Data API v3 and
YouTube Analytics API v2 (both long-term stable Google APIs)."""
from __future__ import annotations

import time
from datetime import date, timedelta
from pathlib import Path

from . import settings

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]

_yt = None
_ya = None


def ready() -> bool:
    return all(settings.env(k) for k in ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN"))


def _creds():
    from google.oauth2.credentials import Credentials  # type: ignore

    return Credentials(
        None,
        refresh_token=settings.env("YT_REFRESH_TOKEN"),
        client_id=settings.env("YT_CLIENT_ID"),
        client_secret=settings.env("YT_CLIENT_SECRET"),
        token_uri="https://oauth2.googleapis.com/token",
        scopes=SCOPES,
    )


def yt():
    global _yt
    if _yt is None:
        from googleapiclient.discovery import build  # type: ignore

        _yt = build("youtube", "v3", credentials=_creds(), cache_discovery=False)
    return _yt


def ya():
    global _ya
    if _ya is None:
        from googleapiclient.discovery import build  # type: ignore

        _ya = build("youtubeAnalytics", "v2", credentials=_creds(), cache_discovery=False)
    return _ya


def _retry(fn, tries=4):
    from googleapiclient.errors import HttpError  # type: ignore

    for i in range(tries):
        try:
            return fn()
        except HttpError as e:
            code = getattr(e.resp, "status", 0)
            if code in (500, 502, 503, 504) and i < tries - 1:
                time.sleep(5 * (i + 1))
                continue
            raise


def my_channel() -> dict:
    r = _retry(lambda: yt().channels().list(part="id,snippet,statistics", mine=True).execute())
    items = r.get("items") or []
    return items[0] if items else {}


def upload(path: Path, title: str, description: str, tags: list[str], *, privacy: str = "private",
           publish_at: str | None = None, localizations: dict | None = None, short: bool = False) -> str:
    from googleapiclient.http import MediaFileUpload  # type: ignore

    cfg = settings.config()["publish"]
    status = {
        "privacyStatus": "private" if publish_at else privacy,
        "selfDeclaredMadeForKids": bool(cfg.get("made_for_kids", False)),
        "containsSyntheticMedia": bool(cfg.get("contains_synthetic_media", False)),
        "embeddable": True,
        "license": "youtube",
    }
    if publish_at:
        status["publishAt"] = publish_at
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": cfg.get("category_id", "27"),
            "defaultLanguage": "hi",
            "defaultAudioLanguage": "hi",
        },
        "status": status,
    }
    if localizations:
        body["localizations"] = localizations
    parts = "snippet,status" + (",localizations" if localizations else "")
    media = MediaFileUpload(str(path), chunksize=8 * 1024 * 1024, resumable=True, mimetype="video/mp4")
    req = yt().videos().insert(part=parts, body=body, media_body=media, notifySubscribers=True)
    resp = None
    fails = 0
    while resp is None:
        try:
            _, resp = req.next_chunk()
        except Exception:
            fails += 1
            if fails > 6:
                raise
            time.sleep(5 * fails)
    return resp["id"]


def set_thumbnail(video_id: str, jpg: Path) -> bool:
    from googleapiclient.http import MediaFileUpload  # type: ignore

    try:
        _retry(lambda: yt().thumbnails().set(videoId=video_id, media_body=MediaFileUpload(str(jpg), mimetype="image/jpeg")).execute())
        return True
    except Exception as e:  # custom thumbnails need a verified channel
        print(f"thumbnail not set: {e}")
        return False


def add_caption(video_id: str, lang: str, name: str, srt: Path) -> bool:
    from googleapiclient.http import MediaFileUpload  # type: ignore

    try:
        _retry(lambda: yt().captions().insert(
            part="snippet",
            body={"snippet": {"videoId": video_id, "language": lang, "name": name, "isDraft": False}},
            media_body=MediaFileUpload(str(srt), mimetype="application/octet-stream"),
        ).execute())
        return True
    except Exception as e:
        print(f"caption {lang} not added: {e}")
        return False


def ensure_playlist(title: str, description: str = "") -> str:
    page = None
    while True:
        r = _retry(lambda: yt().playlists().list(part="snippet", mine=True, maxResults=50, pageToken=page).execute())
        for p in r.get("items", []):
            if p["snippet"]["title"].strip() == title.strip():
                return p["id"]
        page = r.get("nextPageToken")
        if not page:
            break
    r = _retry(lambda: yt().playlists().insert(
        part="snippet,status",
        body={"snippet": {"title": title[:150], "description": description, "defaultLanguage": "hi"}, "status": {"privacyStatus": "public"}},
    ).execute())
    return r["id"]


def add_to_playlist(playlist_id: str, video_id: str) -> None:
    try:
        _retry(lambda: yt().playlistItems().insert(
            part="snippet", body={"snippet": {"playlistId": playlist_id, "resourceId": {"kind": "youtube#video", "videoId": video_id}}}
        ).execute())
    except Exception as e:
        print(f"playlist add failed: {e}")


def comment(video_id: str, text: str) -> bool:
    try:
        _retry(lambda: yt().commentThreads().insert(
            part="snippet", body={"snippet": {"videoId": video_id, "topLevelComment": {"snippet": {"textOriginal": text}}}}
        ).execute())
        return True
    except Exception as e:  # comments can't be posted while a video is private
        print(f"comment not posted: {e}")
        return False


def set_visibility(video_id: str, privacy: str = "private", publish_at: str | None = None) -> None:
    cfg = settings.config()["publish"]
    status = {
        "privacyStatus": "private" if publish_at else privacy,
        "selfDeclaredMadeForKids": bool(cfg.get("made_for_kids", False)),
        "containsSyntheticMedia": bool(cfg.get("contains_synthetic_media", False)),
        "embeddable": True,
        "license": "youtube",
    }
    if publish_at:
        status["publishAt"] = publish_at
    _retry(lambda: yt().videos().update(part="status", body={"id": video_id, "status": status}).execute())


def video_status(ids: list[str]) -> dict[str, dict]:
    out = {}
    for i in range(0, len(ids), 50):
        r = _retry(lambda: yt().videos().list(part="status,statistics,contentDetails,snippet", id=",".join(ids[i : i + 50])).execute())
        for it in r.get("items", []):
            out[it["id"]] = it
    return out


def analytics(ids: list[str], start: date | None = None) -> dict[str, dict]:
    """Per-video totals since `start`."""
    if not ids:
        return {}
    start = start or (date.today() - timedelta(days=365))
    out = {}
    metrics = "views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,subscribersGained,likes,comments,shares"
    for i in range(0, len(ids), 100):
        r = _retry(lambda: ya().reports().query(
            ids="channel==MINE", startDate=start.isoformat(), endDate=date.today().isoformat(),
            metrics=metrics, dimensions="video", filters="video==" + ",".join(ids[i : i + 100]), maxResults=200,
        ).execute())
        cols = [c["name"] for c in r.get("columnHeaders", [])]
        for row in r.get("rows", []) or []:
            d = dict(zip(cols, row))
            out[d["video"]] = d
    return out


def retention(video_id: str) -> list[tuple[float, float]]:
    """Audience retention curve: (fraction of video, share of viewers still watching)."""
    try:
        r = _retry(lambda: ya().reports().query(
            ids="channel==MINE", startDate="2015-01-01", endDate=date.today().isoformat(),
            metrics="audienceWatchRatio", dimensions="elapsedVideoTimeRatio", filters=f"video=={video_id}",
        ).execute())
        return [(float(a), float(b)) for a, b in (r.get("rows") or [])]
    except Exception:
        return []


def channel_daily(days: int = 30) -> list[dict]:
    start = date.today() - timedelta(days=days)
    r = _retry(lambda: ya().reports().query(
        ids="channel==MINE", startDate=start.isoformat(), endDate=date.today().isoformat(),
        metrics="views,estimatedMinutesWatched,subscribersGained,subscribersLost", dimensions="day",
    ).execute())
    cols = [c["name"] for c in r.get("columnHeaders", [])]
    return [dict(zip(cols, row)) for row in (r.get("rows") or [])]


def traffic_sources(days: int = 30) -> list[dict]:
    start = date.today() - timedelta(days=days)
    try:
        r = _retry(lambda: ya().reports().query(
            ids="channel==MINE", startDate=start.isoformat(), endDate=date.today().isoformat(),
            metrics="views,estimatedMinutesWatched", dimensions="insightTrafficSourceType", sort="-views",
        ).execute())
        cols = [c["name"] for c in r.get("columnHeaders", [])]
        return [dict(zip(cols, row)) for row in (r.get("rows") or [])]
    except Exception:
        return []
