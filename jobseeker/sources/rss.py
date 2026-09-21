"""Generic RSS/Atom adapter — most Kenyan job sites are WordPress and expose a
/feed/ endpoint, which is far more reliable than scraping their HTML."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from time import mktime
from urllib.parse import quote_plus

import re

import feedparser

from .. import http
from ..models import Job

log = logging.getLogger(__name__)


def _published(entry) -> datetime | None:
    for key in ("published_parsed", "updated_parsed"):
        parsed = entry.get(key)
        if parsed:
            try:
                return datetime.fromtimestamp(mktime(parsed), tz=timezone.utc)
            except (ValueError, OverflowError):
                pass
    return None


GNEWS_SUFFIX = re.compile(r"\s+-\s+([^-]{2,45})$")


def parse_feed(
    url: str,
    source_name: str,
    category: str = "general",
    company_override: str | None = None,
    strip_publisher: bool = False,
) -> list[Job]:
    resp = http.get(url)
    if resp is None:
        return []
    feed = feedparser.parse(resp.content)
    jobs = []
    for entry in feed.entries:
        link = entry.get("link") or ""
        title = entry.get("title") or ""
        if not link or not title:
            continue
        summary = entry.get("summary") or ""
        if not summary and entry.get("content"):
            summary = entry["content"][0].get("value", "")

        publisher = ""
        if strip_publisher:
            match = GNEWS_SUFFIX.search(title)
            if match:
                publisher = match.group(1).strip()
                title = title[: match.start()].strip()

        jobs.append(
            Job(
                title=title,
                url=link,
                source=publisher or source_name,
                company=company_override if company_override is not None
                        else (entry.get("author", "") or ""),
                description=summary,
                posted_at=_published(entry),
                category=category,
            )
        )
    return jobs


def collect_board_feeds(cfg: dict) -> list[Job]:
    jobs = []
    for feed in cfg.get("boards", {}).get("rss", []) or []:
        found = parse_feed(feed["url"], feed["name"])
        log.info("  rss %-34s %3d", feed["name"], len(found))
        jobs.extend(found)
    return jobs


def google_news(query: str, source_name: str) -> list[Job]:
    """Google News RSS. Catches ministry/parastatal adverts that are announced
    in the press before (or instead of) appearing on a careers page."""
    url = (
        "https://news.google.com/rss/search?q="
        + quote_plus(f"{query} when:14d")
        + "&hl=en-KE&gl=KE&ceid=KE:en"
    )
    # A constant company keeps the fingerprint keyed on the headline alone, so
    # the same advert reported by several outlets appears once.
    return parse_feed(
        url,
        source_name,
        category="government",
        company_override="Kenya public sector news",
        strip_publisher=True,
    )
