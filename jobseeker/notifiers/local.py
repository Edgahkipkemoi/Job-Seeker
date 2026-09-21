"""Local delivery — the only channel that needs no credentials whatsoever.

Every run writes the digest to a fixed path and, where the desktop supports it,
raises a notification. Bookmark the file once and it is current every morning.
No account, no token, no sign-up, nothing to paste.
"""
from __future__ import annotations

import logging
import shutil
import subprocess
from datetime import date

from ..config import ROOT
from ..digest import Digest

log = logging.getLogger(__name__)

NAME = "local"
LATEST = ROOT / "digest.html"          # stable path — bookmark this one


def configured() -> bool:
    return True                        # nothing to configure, ever


def requirements() -> str:
    return "nothing — this channel needs no credentials"


def _notify(title: str, body: str) -> None:
    """Best-effort desktop notification; silently skipped where unsupported."""
    notifier = shutil.which("notify-send")
    if not notifier:
        return
    try:
        subprocess.run([notifier, "-a", "Job Seeker", title, body],
                       timeout=10, check=False)
    except Exception as exc:  # noqa: BLE001
        log.debug("local: desktop notification skipped (%s)", exc)


def _write(html_body: str, title: str, body: str) -> bool:
    try:
        LATEST.write_text(html_body, encoding="utf-8")
        archive = ROOT / "logs" / f"digest-{date.today():%Y-%m-%d}.html"
        archive.write_text(html_body, encoding="utf-8")
    except OSError as exc:
        log.error("local: could not write digest — %s", exc)
        return False
    _notify(title, body)
    log.info("local: digest written to %s", LATEST)
    return True


def send(digest: Digest) -> bool:
    return _write(
        digest.html,
        f"{len(digest.local)} Kenya · {len(digest.remote)} remote · "
        f"{len(digest.government)} government",
        "Today's job digest is ready — open digest.html",
    )


def send_test() -> bool:
    return _write(
        "<!doctype html><meta charset='utf-8'><title>Job Seeker</title>"
        "<body style='font-family:system-ui;padding:40px'>"
        "<h1>Job Seeker is working</h1>"
        "<p>This file is rewritten every morning at 07:00 with the day's vacancies.</p>",
        "Job Seeker", "Test digest written to digest.html",
    )
