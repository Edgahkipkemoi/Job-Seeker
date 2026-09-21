"""Generic careers-page scraper.

Most Kenyan government and parastatal sites publish vacancies as plain links
(often straight to a PDF advert) with no feed and no API, so link extraction
with a relevance heuristic is the only workable approach.
"""
from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from .. import http
from ..models import Job

# Anchor text that looks like an actual vacancy rather than site furniture
VACANCY_HINT = re.compile(
    r"\b(officer|manager|engineer|assistant|analyst|technician|clerk|supervisor|"
    r"developer|specialist|coordinator|administrator|intern|graduate|trainee|"
    r"vacanc\w*|recruit\w*|advert\w*|position|posts?|opportunit\w*|job)\b",
    re.I,
)

NAV_NOISE = {
    "careers", "career", "jobs", "vacancies", "vacancy", "read more", "more",
    "apply", "apply now", "home", "about us", "contact us", "downloads",
    "job opportunities", "career opportunities", "current vacancies",
    "view all jobs", "all jobs", "search jobs", "browse jobs",
}


def scrape_links(
    name: str,
    url: str,
    link_contains: list[str] | None = None,
    category: str = "general",
    location: str = "Kenya",
    max_links: int = 40,
) -> list[Job]:
    resp = http.get(url)
    if resp is None:
        return []

    soup = BeautifulSoup(resp.text, "lxml")
    hints = [h.lower() for h in (link_contains or [])]
    host = urlparse(url).netloc
    jobs, seen = [], set()

    for anchor in soup.find_all("a", href=True):
        text = " ".join(anchor.get_text(" ", strip=True).split())
        href = urljoin(url, anchor["href"])

        if not (12 <= len(text) <= 220) or text.lower() in NAV_NOISE or href in seen:
            continue

        low = href.lower()
        if hints and not any(h in low for h in hints):
            continue
        # Either the link text reads like a vacancy, or the URL itself does
        # (many adverts are PDFs named e.g. "ict-officer-vacancy.pdf").
        href_vacancy = any(h in low for h in
                           ("vacanc", "recruit", "advert", "career", "job", "appointment"))
        if not (VACANCY_HINT.search(text) or href_vacancy):
            continue

        seen.add(href)
        jobs.append(
            Job(
                title=text,
                url=href,
                source=name,
                company=name if category == "government" else "",
                location=location,
                description=f"Listed on {host}. Open the link for the full advert, "
                            f"requirements and application deadline.",
                category=category,
            )
        )

    # A page dumping 40+ links is usually an index we over-matched; keep the
    # most specific titles rather than flooding the digest.
    if len(jobs) > max_links:
        jobs.sort(key=lambda j: len(j.title), reverse=True)
        jobs = jobs[:max_links]
    return jobs
