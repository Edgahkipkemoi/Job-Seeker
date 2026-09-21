"""Score a job against the CV profile defined in config.yaml."""
from __future__ import annotations

import re

from .models import Job

# A public-sector item only counts as a vacancy if it names a role or uses
# recruitment wording — otherwise Google News sweeps and careers-page PDF
# links fill the digest with press articles and annual reports.
GOV_JOB_RE = re.compile(
    r"\b(vacanc\w*|recruit\w*|hiring|advertis\w*|shortlist\w*|"
    r"applications? (are )?invited|job opportunit\w*|"
    r"officer|manager|engineer|assistant|analyst|technician|clerk|supervisor|"
    r"developer|specialist|coordinator|administrator|intern|graduate|trainee|"
    r"director|secretary|accountant|auditor|driver|nurse|jobs?)\b",
    re.I,
)

# Procurement notices, reports and publications look superficially similar to
# adverts on the same careers pages — bin them.
GOV_NOISE_RE = re.compile(
    r"\b(tender|procurement|prequalification|pre-qualification|supplier|"
    r"bid document|expression of interest|annual report|report|survey|"
    r"policy|bulletin|statement|agreement|circular|speech|press release|"
    r"gazette|newsletter|minutes|guidelines?)\b",
    re.I,
)


# Google News sweeps pull in recruitment stories from India, the Gulf and
# South-East Asia. A public-sector item has to be anchored to Kenya.
KENYA_RE = re.compile(
    r"\b(kenya\w*|nairobi|mombasa|kisumu|nakuru|eldoret|county|"
    r"psc|tsc|kmtc|knh|kra|kenha|kplc|parastatal|"
    r"public service commission|state department|huduma)\b",
    re.I,
)


# Press sweeps also surface commentary *about* public hiring — court rulings,
# policy debate, scandals — rather than adverts. Bin those.
GOV_NEWS_NOISE_RE = re.compile(
    r"\b(calls? for|ordered|orders|court|ruling|judge|petition|fake|scandal|"
    r"probe|warns?|slams?|criticis\w*|protest|strike|opinion|analysis|"
    r"retrench\w*|layoffs?|lament\w*|decries?)\b",
    re.I,
)

NEWS_COMPANY = "Kenya public sector news"

# Roles based in (or explicitly open to) Kenya. These get their own section so
# the far larger pool of international remote listings cannot crowd them out.
LOCAL_RE = re.compile(
    r"\b(kenya\w*|nairobi|mombasa|kisumu|nakuru|eldoret|east africa|"
    r"brightermonday|myjobmag|jobwebkenya|career point)\b",
    re.I,
)


class Matcher:
    def __init__(self, keywords: dict, max_age_days: int = 14):
        self.must_any = [k.lower() for k in keywords.get("must_any", [])]
        self.weighted = {k.lower(): int(v) for k, v in (keywords.get("weighted") or {}).items()}
        self.exclude = [k.lower() for k in keywords.get("exclude", [])]
        self.max_age_days = max_age_days

    @staticmethod
    def _contains(haystack: str, needle: str) -> bool:
        # Word-boundary match where the keyword is plain, substring where it
        # contains punctuation (".", "/", "+") that \b handles badly.
        if re.search(r"[^\w\s]", needle):
            return needle in haystack
        return re.search(rf"\b{re.escape(needle)}\b", haystack) is not None

    def score(self, job: Job) -> Job:
        title = job.title.lower()
        body = f"{job.title} {job.company} {job.location} {job.description}".lower()

        if any(self._contains(title, bad) for bad in self.exclude):
            job.score = -1
            return job

        total, hits = 0, []
        for kw, weight in self.weighted.items():
            in_title = self._contains(title, kw)
            in_body = self._contains(body, kw)
            if in_title or in_body:
                total += weight * (2 if in_title else 1)
                hits.append(kw)

        job.score = total
        job.matched_keywords = sorted(hits, key=lambda k: -self.weighted[k])[:8]
        return job

    @staticmethod
    def is_local(job: Job) -> bool:
        return bool(LOCAL_RE.search(f"{job.location} {job.source} {job.company} {job.description}"))

    def is_relevant(self, job: Job) -> bool:
        """Government postings bypass the keyword gate — the brief is to report
        every open public-sector vacancy, not only the coding ones."""
        if job.score < 0:
            return False
        age = job.age_days
        if age is not None and age > self.max_age_days:
            return False
        if job.category == "government":
            title = job.title
            if not GOV_JOB_RE.search(title) or GOV_NOISE_RE.search(title):
                return False
            # Deliberately excludes company/source: those carry our own labels,
            # which would make the Kenya test match everything.
            if not KENYA_RE.search(f"{title} {job.location} {job.description}"):
                return False
            if job.company == NEWS_COMPANY and GOV_NEWS_NOISE_RE.search(title):
                return False
            return True
        body = f"{job.title} {job.description}".lower()
        return any(self._contains(body, kw) for kw in self.must_any)
