"""Kenyan Government ministries, parastatals and state corporations.

Public-sector careers pages rarely offer an API or a feed, so this module
combines three angles:
  1. HTML scrape of each institution's careers/vacancies page
  2. RSS feeds of aggregators that republish government adverts
  3. Google News RSS sweeps, which catch adverts published in the press

A fourth angle lives in ``classify``: any listing from a general Kenyan source
whose text names a ministry, county, authority or commission is re-labelled as
a public-sector vacancy, so nothing is missed just because it arrived via an
aggregator feed.
"""
from __future__ import annotations

import logging
import re

from ..models import Job
from .rss import google_news, parse_feed
from .scrape import scrape_links

log = logging.getLogger(__name__)

GOV_PATTERN = re.compile(
    r"\b(ministry of|state department|public service commission|"
    r"county government|county public service|parastatal|state corporation|"
    r"national government|government of kenya|teachers service commission|"
    r"kenya revenue authority|central bank of kenya|judiciary|"
    r"\w+ authority of kenya|kenya \w+ authority|\w+ regulatory authority|"
    r"national \w+ (authority|council|fund|agency)|"
    r"\w+ development authority|public university|kenya \w+ board)\b",
    re.I,
)


def classify(jobs: list[Job]) -> list[Job]:
    """Promote listings that are clearly public-sector into the gov category."""
    for job in jobs:
        if job.category == "government":
            continue
        haystack = f"{job.title} {job.company} {job.description}"
        if GOV_PATTERN.search(haystack):
            job.category = "government"
    return jobs


def collect(cfg: dict) -> list[Job]:
    gov_cfg = cfg.get("government", {})
    if not gov_cfg.get("enabled", True):
        return []

    jobs: list[Job] = []

    for feed in gov_cfg.get("rss", []) or []:
        found = parse_feed(feed["url"], feed["name"], category="government")
        log.info("  gov rss  %-32s %3d", feed["name"][:32], len(found))
        jobs.extend(found)

    for site in gov_cfg.get("html", []) or []:
        try:
            found = scrape_links(
                site["name"], site["url"], site.get("link_contains", []),
                category="government",
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("  gov html %-32s failed: %s", site["name"][:32], exc)
            continue
        log.info("  gov html %-32s %3d", site["name"][:32], len(found))
        jobs.extend(found)

    for query in gov_cfg.get("news_queries", []) or []:
        found = google_news(query, "Google News (Kenya public sector)")
        log.info("  gov news %-32s %3d", query[:32], len(found))
        jobs.extend(found)

    return jobs
