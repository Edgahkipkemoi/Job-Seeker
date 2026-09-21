"""Public job-board APIs. All of these are free; only Adzuna needs a key."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from urllib.parse import quote_plus

from .. import http
from ..config import env
from ..models import Job

log = logging.getLogger(__name__)


def _iso(value) -> datetime | None:
    if not value:
        return None
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        except (ValueError, OSError, OverflowError):
            return None
    text = str(value).strip().replace("Z", "+00:00")
    for candidate in (text, text[:19], text[:10]):
        try:
            return datetime.fromisoformat(candidate)
        except ValueError:
            continue
    return None


def remotive(queries: list[str]) -> list[Job]:
    jobs = []
    for query in queries:
        data = http.get_json(f"https://remotive.com/api/remote-jobs?search={quote_plus(query)}&limit=40")
        for item in (data or {}).get("jobs", []):
            jobs.append(
                Job(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    source="Remotive",
                    company=item.get("company_name", ""),
                    location=item.get("candidate_required_location", "Remote"),
                    description=item.get("description", ""),
                    posted_at=_iso(item.get("publication_date")),
                )
            )
    return jobs


def remoteok() -> list[Job]:
    data = http.get_json("https://remoteok.com/api")
    jobs = []
    for item in (data or [])[1:]:      # first element is legal boilerplate
        if not isinstance(item, dict):
            continue
        jobs.append(
            Job(
                title=item.get("position") or item.get("title", ""),
                url=item.get("url", ""),
                source="RemoteOK",
                company=item.get("company", ""),
                location=item.get("location", "Remote"),
                description=f"{' '.join(item.get('tags', []))} {item.get('description', '')}",
                posted_at=_iso(item.get("date") or item.get("epoch")),
            )
        )
    return jobs


def arbeitnow() -> list[Job]:
    data = http.get_json("https://www.arbeitnow.com/api/job-board-api")
    return [
        Job(
            title=item.get("title", ""),
            url=item.get("url", ""),
            source="Arbeitnow",
            company=item.get("company_name", ""),
            location=item.get("location", ""),
            description=f"{' '.join(item.get('tags', []))} {item.get('description', '')}",
            posted_at=_iso(item.get("created_at")),
        )
        for item in (data or {}).get("data", [])
    ]


def jobicy() -> list[Job]:
    jobs = []
    for tag in ("dev", "devops", "engineering", "supporting"):
        data = http.get_json(f"https://jobicy.com/api/v2/remote-jobs?count=50&industry={tag}")
        for item in (data or {}).get("jobs", []):
            jobs.append(
                Job(
                    title=item.get("jobTitle", ""),
                    url=item.get("url", ""),
                    source="Jobicy",
                    company=item.get("companyName", ""),
                    location=item.get("jobGeo", "Remote"),
                    description=item.get("jobExcerpt", "") or item.get("jobDescription", ""),
                    posted_at=_iso(item.get("pubDate")),
                )
            )
    return jobs


def himalayas() -> list[Job]:
    data = http.get_json("https://himalayas.app/jobs/api?limit=100")
    return [
        Job(
            title=item.get("title", ""),
            url=item.get("applicationLink") or item.get("guid", ""),
            source="Himalayas",
            company=item.get("companyName", ""),
            location=", ".join(item.get("locationRestrictions", []) or ["Remote"]),
            description=item.get("excerpt", "") or item.get("description", ""),
            posted_at=_iso(item.get("pubDate")),
        )
        for item in (data or {}).get("jobs", [])
    ]


def adzuna(queries: list[str], countries: list[str]) -> list[Job]:
    app_id, app_key = env("ADZUNA_APP_ID"), env("ADZUNA_APP_KEY")
    if not (app_id and app_key):
        log.info("  adzuna skipped (no API credentials in .env)")
        return []
    jobs = []
    for country in countries:
        for query in queries:
            url = (
                f"https://api.adzuna.com/v1/api/jobs/{country}/search/1"
                f"?app_id={app_id}&app_key={app_key}&results_per_page=30"
                f"&what={quote_plus(query)}&max_days_old=14&content-type=application/json"
            )
            data = http.get_json(url)
            for item in (data or {}).get("results", []):
                jobs.append(
                    Job(
                        title=item.get("title", ""),
                        url=item.get("redirect_url", ""),
                        source="Adzuna",
                        company=(item.get("company") or {}).get("display_name", ""),
                        location=(item.get("location") or {}).get("display_name", ""),
                        description=item.get("description", ""),
                        posted_at=_iso(item.get("created")),
                    )
                )
    return jobs


def collect(cfg: dict) -> list[Job]:
    boards_cfg = cfg.get("boards", {})
    search = cfg.get("search", {})
    queries = search.get("queries", [])
    countries = search.get("countries", ["ke"])

    tasks = {
        "remotive": lambda: remotive(queries),
        "remoteok": remoteok,
        "arbeitnow": arbeitnow,
        "jobicy": jobicy,
        "himalayas": himalayas,
        "adzuna": lambda: adzuna(queries, countries),
    }
    jobs = []
    for name, fn in tasks.items():
        if not boards_cfg.get(name, False):
            continue
        try:
            found = fn()
            log.info("  api %-34s %3d", name, len(found))
            jobs.extend(found)
        except Exception as exc:  # noqa: BLE001
            log.warning("  api %-34s failed: %s", name, exc)
    return jobs
