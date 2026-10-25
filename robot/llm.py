"""Free AI writers behind one function. Tries each provider in config.yaml in order.
If a model name has been retired, it asks the provider which models exist and
picks the closest match, so the robot keeps working as model names change."""
from __future__ import annotations

import json
import re
import time

import requests

from . import settings

_model_cache: dict[str, list[str]] = {}


class LLMError(RuntimeError):
    pass


def _available(p: dict, key: str) -> list[str]:
    if p["name"] in _model_cache:
        return _model_cache[p["name"]]
    try:
        r = requests.get(p["base_url"].rstrip("/") + "/models", headers={"Authorization": f"Bearer {key}"}, timeout=30)
        ids = [m.get("id", "") for m in r.json().get("data", [])] if r.ok else []
        ids = [i.split("/")[-1] if i.startswith("models/") else i for i in ids]
    except Exception:
        ids = []
    _model_cache[p["name"]] = ids
    return ids


def _candidates(p: dict, key: str) -> list[str]:
    wanted = list(p.get("models") or [])
    avail = _available(p, key)
    if not avail:
        return wanted
    out = [m for m in wanted if m in avail]
    prefer = p.get("prefer", "")
    extra = sorted(
        [m for m in avail if prefer and prefer in m and "lite" not in m and "image" not in m and "tts" not in m and "embed" not in m and m not in out],
        reverse=True,
    )
    return out + extra[:3] or wanted


def _extract_json(text: str):
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t)
    try:
        return json.loads(t)
    except Exception:
        pass
    start = min([i for i in (t.find("{"), t.find("[")) if i >= 0], default=-1)
    if start < 0:
        raise ValueError("no JSON found")
    end = max(t.rfind("}"), t.rfind("]"))
    return json.loads(t[start : end + 1])


def chat(system: str, user: str, *, want_json: bool = False, temperature: float = 0.7, max_tokens: int = 16000, avoid: str | None = None):
    """Returns (text_or_json, 'provider/model'). `avoid` skips a provider (e.g. for an independent fact-check)."""
    errors = []
    providers = settings.config()["llm"]["providers"]
    ordered = [p for p in providers if p["name"] != avoid] + [p for p in providers if p["name"] == avoid]
    for p in ordered:
        key = settings.env(p["key_env"])
        if not key:
            errors.append(f"{p['name']}: no key")
            continue
        for model in _candidates(p, key):
            for attempt in range(2):
                try:
                    body = {
                        "model": model,
                        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                    }
                    if want_json:
                        body["response_format"] = {"type": "json_object"}
                    r = requests.post(
                        p["base_url"].rstrip("/") + "/chat/completions",
                        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                        json=body,
                        timeout=300,
                    )
                    if r.status_code == 400 and want_json and "response_format" in r.text:
                        body.pop("response_format", None)
                        r = requests.post(p["base_url"].rstrip("/") + "/chat/completions", headers={"Authorization": f"Bearer {key}"}, json=body, timeout=300)
                    if r.status_code in (429, 500, 502, 503, 504):
                        time.sleep(8 * (attempt + 1))
                        continue
                    if not r.ok:
                        errors.append(f"{p['name']}/{model}: HTTP {r.status_code}")
                        break
                    text = r.json()["choices"][0]["message"]["content"] or ""
                    if want_json:
                        return _extract_json(text), f"{p['name']}/{model}"
                    return text, f"{p['name']}/{model}"
                except (ValueError, KeyError, json.JSONDecodeError) as e:
                    errors.append(f"{p['name']}/{model}: bad output ({e})")
                except requests.RequestException as e:
                    errors.append(f"{p['name']}/{model}: {e.__class__.__name__}")
                    time.sleep(5)
    raise LLMError("All AI writers failed: " + "; ".join(errors[-8:]))
