"""Discord delivery via an incoming webhook.

Setup needs no account beyond Discord itself: open any server you own →
Server Settings → Integrations → Webhooks → New Webhook → Copy Webhook URL,
and paste it into DISCORD_WEBHOOK_URL in .env.
"""
from __future__ import annotations

import logging

from .. import http
from ..config import env
from ..digest import Digest, meta_line

log = logging.getLogger(__name__)

NAME = "discord"
LIMIT = 1900          # Discord's hard cap is 2000


def configured() -> bool:
    return bool(env("DISCORD_WEBHOOK_URL"))


def requirements() -> str:
    return "DISCORD_WEBHOOK_URL in .env"


def _chunks(digest: Digest) -> list[str]:
    messages, current = [], f"**Daily Job Digest**\n{digest.subject}"
    for title, jobs in digest.sections:
        if not jobs:
            continue
        for piece in [f"\n\n__**{title} ({len(jobs)})**__"] + [
            f"\n\n[{job.title}](<{job.url}>)\n*{meta_line(job)}*" for job in jobs
        ]:
            if len(current) + len(piece) > LIMIT:
                messages.append(current)
                current = piece.lstrip()
            else:
                current += piece
    if current.strip():
        messages.append(current)
    return messages


def _post(content: str) -> bool:
    resp = http.session().post(env("DISCORD_WEBHOOK_URL"), json={"content": content}, timeout=30)
    if resp.status_code not in (200, 204):
        log.error("discord: webhook returned HTTP %s", resp.status_code)
        return False
    return True


def send(digest: Digest) -> bool:
    messages = _chunks(digest)
    try:
        sent = sum(1 for m in messages if _post(m))
    except Exception as exc:  # noqa: BLE001
        log.error("discord: send failed — %s", exc)
        return False
    if sent == len(messages):
        log.info("discord: delivered %d message(s)", sent)
        return True
    log.error("discord: only %d of %d messages delivered", sent, len(messages))
    return False


def send_test() -> bool:
    try:
        ok = _post("**Job Seeker**\nYour agent is wired up correctly. "
                   "The first real digest arrives at 07:00.")
    except Exception as exc:  # noqa: BLE001
        log.error("discord: send failed — %s", exc)
        return False
    if ok:
        log.info("discord: test message delivered")
    return ok
