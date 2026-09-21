"""Core data structures shared by every source."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def clean_text(raw: str | None, limit: int = 600) -> str:
    """Strip HTML tags and collapse whitespace down to a readable snippet."""
    if not raw:
        return ""
    text = _WS_RE.sub(" ", _TAG_RE.sub(" ", raw)).strip()
    return text[:limit] + ("…" if len(text) > limit else "")


@dataclass
class Job:
    title: str
    url: str
    source: str
    company: str = ""
    location: str = ""
    description: str = ""
    posted_at: datetime | None = None
    category: str = "general"          # "general" or "government"
    score: int = 0
    matched_keywords: list[str] = field(default_factory=list)

    @property
    def fingerprint(self) -> str:
        """Stable id used for de-duplication across runs and across sources.

        Keyed on title + employer where we know the employer, so the same
        vacancy syndicated to three boards under three URLs collapses to one
        entry. Without an employer we fall back to the URL.
        """
        title = _WS_RE.sub(" ", self.title.lower()).strip()
        company = _WS_RE.sub(" ", self.company.lower()).strip()
        key = f"{title}|{company}" if company else \
              f"{title}|{self.url.split('?')[0].rstrip('/').lower()}"
        return hashlib.sha256(key.encode()).hexdigest()[:32]

    @property
    def age_days(self) -> int | None:
        if not self.posted_at:
            return None
        now = datetime.now(timezone.utc)
        posted = self.posted_at
        if posted.tzinfo is None:
            posted = posted.replace(tzinfo=timezone.utc)
        return max((now - posted).days, 0)

    def normalise(self) -> "Job":
        self.title = clean_text(self.title, 200) or "Untitled vacancy"
        self.company = clean_text(self.company, 120)
        self.location = clean_text(self.location, 120)
        self.description = clean_text(self.description, 600)
        return self
