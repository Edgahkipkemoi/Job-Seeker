"""Render the daily digest. Delivery lives in jobseeker/notifiers/."""
from __future__ import annotations

import html
from dataclasses import dataclass, field
from datetime import date

from .models import Job


@dataclass
class Digest:
    """One day's results, rendered once and handed to every delivery channel."""
    local: list[Job] = field(default_factory=list)
    remote: list[Job] = field(default_factory=list)
    government: list[Job] = field(default_factory=list)
    stats: dict = field(default_factory=dict)

    @property
    def subject(self) -> str:
        return (f"[{date.today():%d %b}] {len(self.local)} Kenya · "
                f"{len(self.remote)} remote · {len(self.government)} government vacancies")

    @property
    def sections(self) -> list[tuple[str, list[Job]]]:
        return [
            ("Kenya-based roles", self.local),
            ("Remote & international roles", self.remote),
            ("Government, ministries & parastatals", self.government),
        ]

    @property
    def is_empty(self) -> bool:
        return not (self.local or self.remote or self.government)

    @property
    def html(self) -> str:
        return build_html(self.local, self.remote, self.government, self.stats)

    @property
    def text(self) -> str:
        return build_text(self.local, self.remote, self.government)


def meta_line(job: Job) -> str:
    """Company · location · source · age, skipping whatever we don't know."""
    bits = [b for b in (job.company, job.location, job.source) if b]
    if job.age_days is not None:
        bits.append("today" if job.age_days == 0 else f"{job.age_days}d ago")
    return " · ".join(bits)

STYLE = """
body{margin:0;padding:0;background:#f4f6f8;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;color:#1a202c}
.wrap{max-width:680px;margin:0 auto;padding:24px 16px}
.head{background:#0f172a;color:#fff;border-radius:12px;padding:24px}
.head h1{margin:0 0 6px;font-size:20px}
.head p{margin:0;font-size:13px;color:#94a3b8}
h2{font-size:15px;text-transform:uppercase;letter-spacing:.06em;color:#475569;margin:32px 0 12px;border-bottom:2px solid #e2e8f0;padding-bottom:8px}
.card{background:#fff;border:1px solid #e2e8f0;border-left:4px solid #2563eb;border-radius:8px;padding:14px 16px;margin-bottom:10px}
.card.gov{border-left-color:#16a34a}
.card a.t{font-size:15px;font-weight:600;color:#1d4ed8;text-decoration:none;line-height:1.35}
.meta{font-size:12px;color:#64748b;margin:6px 0 0}
.desc{font-size:13px;color:#334155;margin:8px 0 0;line-height:1.5}
.tags{margin-top:8px}
.tag{display:inline-block;background:#eff6ff;color:#1e40af;font-size:11px;padding:2px 7px;border-radius:10px;margin:0 4px 4px 0}
.score{float:right;background:#0f172a;color:#fff;font-size:11px;padding:2px 8px;border-radius:10px}
.empty{background:#fff;border:1px dashed #cbd5e1;border-radius:8px;padding:20px;text-align:center;color:#64748b;font-size:14px}
.foot{margin-top:32px;font-size:11px;color:#94a3b8;text-align:center;line-height:1.6}
"""


def _card(job: Job) -> str:
    gov = " gov" if job.category == "government" else ""
    tags = "".join(f'<span class="tag">{html.escape(k)}</span>' for k in job.matched_keywords)
    score = f'<span class="score">{job.score}</span>' if job.score > 0 else ""
    desc = f'<p class="desc">{html.escape(job.description)}</p>' if job.description else ""
    return (
        f'<div class="card{gov}">{score}'
        f'<a class="t" href="{html.escape(job.url)}">{html.escape(job.title)}</a>'
        f'<p class="meta">{html.escape(meta_line(job))}</p>'
        f"{desc}"
        f'<div class="tags">{tags}</div>'
        f"</div>"
    )


def _section(title: str, jobs: list[Job], empty_note: str) -> str:
    body = "".join(_card(j) for j in jobs) if jobs else f'<div class="empty">{empty_note}</div>'
    return f"<h2>{html.escape(title)} ({len(jobs)})</h2>{body}"


def build_html(local: list[Job], remote: list[Job], government: list[Job], stats: dict) -> str:
    today = date.today().strftime("%A, %d %B %Y")
    return f"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><style>{STYLE}</style></head>
<body><div class="wrap">
<div class="head">
  <h1>Daily Job Digest — {today}</h1>
  <p>{stats['matched']} matched roles · {stats['government']} public-sector vacancies ·
     {stats['scanned']} listings scanned across {stats['sources']} sources</p>
</div>
{_section("Kenya-based roles", local, "No new Kenya-based roles matched today.")}
{_section("Remote &amp; international roles", remote,
          "No new remote roles cleared the relevance threshold today.")}
{_section("Government, ministries &amp; parastatals", government,
          "No new public-sector vacancies published since the last run.")}
<p class="foot">
  Generated automatically at 07:00 EAT by your Job Seeker agent.<br>
  Each vacancy is reported once — repeats are suppressed for
  {stats['remember_days']} days.<br>
  Tune keywords, sources and thresholds in <code>config.yaml</code>.
</p>
</div></body></html>"""


def build_text(local: list[Job], remote: list[Job], government: list[Job]) -> str:
    lines = [f"DAILY JOB DIGEST — {date.today():%d %b %Y}", ""]
    for title, jobs in (("KENYA-BASED ROLES", local),
                        ("REMOTE & INTERNATIONAL ROLES", remote),
                        ("GOVERNMENT / MINISTRIES / PARASTATALS", government)):
        lines += [f"== {title} ({len(jobs)}) =="]
        if not jobs:
            lines.append("  (nothing new)")
        for job in jobs:
            lines += [f"* {job.title}", f"  {meta_line(job)}", f"  {job.url}", ""]
        lines.append("")
    return "\n".join(lines)
