"""Job sources. Each collector returns a list[Job]; failures are swallowed and
logged so one broken site never aborts the morning run."""
from __future__ import annotations

import logging

from ..models import Job
from . import boards, gov, rss
from .scrape import scrape_links

log = logging.getLogger(__name__)


def _board_pages(cfg: dict) -> list[Job]:
    jobs = []
    for site in cfg.get("boards", {}).get("html", []) or []:
        found = scrape_links(site["name"], site["url"], site.get("link_contains", []))
        log.info("  html %-36s %3d", site["name"][:36], len(found))
        jobs.extend(found)
    return jobs


def collect_all(cfg: dict) -> list[Job]:
    jobs: list[Job] = []
    collectors = [
        ("job boards (APIs)", lambda: boards.collect(cfg)),
        ("job boards (RSS)", lambda: rss.collect_board_feeds(cfg)),
        ("job boards (HTML)", lambda: _board_pages(cfg)),
        ("government & parastatals", lambda: gov.collect(cfg)),
    ]
    for label, fn in collectors:
        try:
            found = fn()
            log.info("%-28s -> %3d listings", label, len(found))
            jobs.extend(found)
        except Exception as exc:  # noqa: BLE001 - resilience is the point
            log.exception("collector '%s' failed: %s", label, exc)

    # Re-label anything that is clearly a public-sector advert, whichever
    # source it arrived from, so it lands in the government section.
    return gov.classify([j.normalise() for j in jobs])
