"""One shared, polite HTTP session with retries — every source uses this."""
from __future__ import annotations

import logging
import time

import requests

log = logging.getLogger(__name__)
_session: requests.Session | None = None
_settings = {"timeout": 25, "retries": 2, "ua": "Mozilla/5.0"}


def configure(runtime: dict) -> None:
    _settings["timeout"] = runtime.get("timeout_seconds", 25)
    _settings["retries"] = runtime.get("retries", 2)
    _settings["ua"] = runtime.get("user_agent", "Mozilla/5.0")


def session() -> requests.Session:
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers.update(
            {
                "User-Agent": _settings["ua"],
                "Accept": "text/html,application/xhtml+xml,application/xml,application/json;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            }
        )
    return _session


def get(url: str, **kwargs) -> requests.Response | None:
    """GET with retries. Returns None instead of raising — one dead source
    must never take down the whole run."""
    kwargs.setdefault("timeout", _settings["timeout"])
    last = None
    for attempt in range(_settings["retries"] + 1):
        try:
            resp = session().get(url, **kwargs)
            if resp.status_code == 200:
                return resp
            last = f"HTTP {resp.status_code}"
        except requests.RequestException as exc:
            last = type(exc).__name__
        if attempt < _settings["retries"]:
            time.sleep(1.5 * (attempt + 1))
    log.warning("fetch failed: %s (%s)", url, last)
    return None


def get_json(url: str, **kwargs):
    resp = get(url, **kwargs)
    if resp is None:
        return None
    try:
        return resp.json()
    except ValueError:
        log.warning("not JSON: %s", url)
        return None
