"""Delivery channels.

Each channel module exposes: NAME, configured(), requirements(), send(digest)
and send_test(). Channels are chosen in config.yaml under `delivery.channels`;
a channel that is listed but missing its credentials is skipped with a clear
message rather than failing the run.
"""
from __future__ import annotations

import logging

from ..digest import Digest
from . import discord, email_smtp, local, telegram

log = logging.getLogger(__name__)

CHANNELS = {m.NAME: m for m in (local, telegram, email_smtp, discord)}


def _selected(cfg: dict):
    names = cfg.get("delivery", {}).get("channels") or ["local"]
    chosen = []
    for name in names:
        module = CHANNELS.get(name)
        if module is None:
            log.warning("unknown delivery channel %r — valid: %s",
                        name, ", ".join(CHANNELS))
            continue
        chosen.append(module)
    return chosen


def deliver(cfg: dict, digest: Digest) -> bool:
    """Send via every configured channel. True if at least one succeeded."""
    return _dispatch(cfg, lambda m: m.send(digest), "digest")


def deliver_test(cfg: dict) -> bool:
    return _dispatch(cfg, lambda m: m.send_test(), "test message")


def _dispatch(cfg: dict, action, label: str) -> bool:
    modules = _selected(cfg)
    if not modules:
        log.error("no valid delivery channels configured in config.yaml")
        return False

    ready = [m for m in modules if m.configured()]
    for module in modules:
        if module not in ready:
            log.error("%s: not configured — needs %s", module.NAME, module.requirements())

    if not ready:
        log.error("no delivery channel has credentials; nothing sent")
        return False

    results = {m.NAME: bool(action(m)) for m in ready}
    ok = [n for n, r in results.items() if r]
    failed = [n for n, r in results.items() if not r]
    if ok:
        log.info("%s sent via: %s", label, ", ".join(ok))
    if failed:
        log.error("%s failed via: %s", label, ", ".join(failed))
    return bool(ok)
