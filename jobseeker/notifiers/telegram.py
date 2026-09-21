"""Telegram delivery — the lowest-friction channel.

Setup takes about 90 seconds and needs no email account, no 2FA and no domain:
  1. Open Telegram, message @BotFather, send /newbot, follow the prompts
  2. Copy the token it gives you into TELEGRAM_BOT_TOKEN in .env
  3. Send your new bot any message (e.g. "hi") so it is allowed to reply

That is all. TELEGRAM_CHAT_ID is discovered automatically on the first send and
written back to .env, so the bot token is the only value you ever paste.
"""
from __future__ import annotations

import html
import logging
import os

from .. import http
from ..config import ROOT, env
from ..digest import Digest, meta_line

log = logging.getLogger(__name__)

NAME = "telegram"
API = "https://api.telegram.org/bot{token}/{method}"
LIMIT = 3800          # Telegram's hard cap is 4096; leave room for headers


def configured() -> bool:
    # The chat id resolves itself, so the token alone is enough to be usable.
    return bool(env("TELEGRAM_BOT_TOKEN"))


def requirements() -> str:
    return "TELEGRAM_BOT_TOKEN in .env (get it from @BotFather; chat id is automatic)"


def _post(method: str, payload: dict) -> dict | None:
    token = env("TELEGRAM_BOT_TOKEN")
    resp = http.get_json(API.format(token=token, method=method), params=payload)
    if resp is None:
        return None
    if not resp.get("ok"):
        log.error("telegram: API rejected %s — %s", method, resp.get("description"))
        return None
    return resp


def discover_chat_id() -> list[str]:
    """Print the chat ids that have messaged this bot. Run after saying hi to it."""
    resp = _post("getUpdates", {})
    if resp is None:
        return []
    found = []
    for update in resp.get("result", []):
        chat = (update.get("message") or update.get("channel_post") or {}).get("chat", {})
        if chat.get("id") and str(chat["id"]) not in found:
            label = chat.get("username") or chat.get("title") or chat.get("first_name", "")
            found.append(str(chat["id"]))
            log.info("  chat id %s  (%s)", chat["id"], label)
    if not found:
        log.warning("No chats found. Send your bot a message in Telegram first, then re-run.")
    return found


def _chunks(digest: Digest) -> list[str]:
    """Split the digest into messages that fit Telegram's length limit,
    breaking only between jobs so no entry is ever cut in half."""
    esc = html.escape
    header = f"<b>Daily Job Digest</b>\n{esc(digest.subject)}"
    messages, current = [], header

    for title, jobs in digest.sections:
        if not jobs:
            continue
        block = f"\n\n<b>{esc(title)} ({len(jobs)})</b>"
        if len(current) + len(block) > LIMIT:
            messages.append(current)
            current = block.lstrip()
        else:
            current += block

        for job in jobs:
            entry = (f'\n\n<a href="{esc(job.url)}">{esc(job.title)}</a>'
                     f"\n<i>{esc(meta_line(job))}</i>")
            if len(current) + len(entry) > LIMIT:
                messages.append(current)
                current = entry.lstrip()
            else:
                current += entry

    if current.strip():
        messages.append(current)
    return messages


def _persist_chat_id(chat_id: str) -> None:
    """Write the discovered id back to .env so later runs skip the lookup."""
    env_path = ROOT / ".env"
    try:
        lines = env_path.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            if line.startswith("TELEGRAM_CHAT_ID="):
                lines[i] = f"TELEGRAM_CHAT_ID={chat_id}"
                break
        else:
            lines.append(f"TELEGRAM_CHAT_ID={chat_id}")
        env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        log.info("telegram: saved chat id %s to .env", chat_id)
    except OSError as exc:
        log.warning("telegram: could not save chat id (%s) — it will be looked up again", exc)


def _chat_id() -> str | None:
    """Use the configured id, or find it from whoever messaged the bot."""
    existing = env("TELEGRAM_CHAT_ID")
    if existing:
        return existing
    log.info("telegram: no chat id set — discovering it from recent messages")
    found = discover_chat_id()
    if not found:
        return None
    os.environ["TELEGRAM_CHAT_ID"] = found[0]
    _persist_chat_id(found[0])
    return found[0]


def _send_message(text: str) -> bool:
    chat_id = _chat_id()
    if chat_id is None:
        return False
    return _post("sendMessage", {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": "true",
    }) is not None


def send(digest: Digest) -> bool:
    messages = _chunks(digest)
    sent = sum(1 for m in messages if _send_message(m))
    if sent == len(messages):
        log.info("telegram: delivered %d message(s)", sent)
        return True
    log.error("telegram: only %d of %d messages delivered", sent, len(messages))
    return False


def send_test() -> bool:
    ok = _send_message("<b>Job Seeker</b>\nYour agent is wired up correctly. "
                       "The first real digest arrives at 07:00.")
    if ok:
        log.info("telegram: test message delivered")
    return ok
