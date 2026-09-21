#!/usr/bin/env python3
"""Daily job-search agent.

    python run.py                   # full run: search, de-duplicate, deliver
    python run.py --dry-run         # write the digest to disk, deliver nothing
    python run.py --no-store        # ignore de-duplication (re-report everything)
    python run.py --test            # send a one-line test via every channel
    python run.py --telegram-chat-id  # look up your Telegram chat id
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import date
from pathlib import Path

from jobseeker import digest as digest_mod
from jobseeker import http, notifiers, sources
from jobseeker.config import ROOT, load_config
from jobseeker.matcher import Matcher
from jobseeker.store import Store


def setup_logging(verbose: bool) -> None:
    (ROOT / "logs").mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(message)s",
        datefmt="%H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(ROOT / "logs" / "jobseeker.log", encoding="utf-8"),
        ],
    )
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def main() -> int:
    ap = argparse.ArgumentParser(description="Daily job search + email digest")
    ap.add_argument("--dry-run", action="store_true", help="write digest to disk, do not email")
    ap.add_argument("--no-store", action="store_true", help="skip de-duplication against past runs")
    ap.add_argument("--test", "--test-email", dest="test", action="store_true",
                    help="send a short test message via every configured channel")
    ap.add_argument("--telegram-chat-id", action="store_true",
                    help="print the Telegram chat ids that have messaged your bot")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    setup_logging(args.verbose)
    log = logging.getLogger("jobseeker")
    cfg = load_config()

    http.configure(cfg.get("runtime", {}))

    if args.telegram_chat_id:
        from jobseeker.notifiers import telegram
        if not os.environ.get("TELEGRAM_BOT_TOKEN", "").strip():
            log.error("set TELEGRAM_BOT_TOKEN in .env first (get it from @BotFather)")
            return 1
        return 0 if telegram.discover_chat_id() else 1

    if args.test:
        return 0 if notifiers.deliver_test(cfg) else 1

    search = cfg.get("search", {})
    matcher = Matcher(cfg.get("keywords", {}), search.get("max_age_days", 14))

    log.info("=" * 60)
    log.info("Job search run — %s", date.today().isoformat())

    raw = sources.collect_all(cfg)
    log.info("collected %d raw listings", len(raw))

    relevant = [j for j in (matcher.score(j) for j in raw) if matcher.is_relevant(j)]
    log.info("%d listings passed relevance filtering", len(relevant))

    runtime = cfg.get("runtime", {})
    store = Store(ROOT / runtime.get("database", "data/seen.db"),
                  runtime.get("remember_days", 45))
    if args.no_store:
        # --no-store skips the cross-run memory, but never the within-run
        # de-duplication: the same job routinely arrives from several sources.
        seen, fresh = set(), []
        for job in relevant:
            if job.fingerprint not in seen:
                seen.add(job.fingerprint)
                fresh.append(job)
    else:
        fresh = store.filter_new(relevant)
    log.info("%d are new since the last run", len(fresh))

    min_score = search.get("min_score", 8)
    gov_min = cfg.get("government", {}).get("min_score", 0)
    cap = search.get("max_per_section", 40)

    def rank(jobs):
        return sorted(jobs, key=lambda j: (-j.score, j.age_days if j.age_days is not None else 99))

    # Kenya-based roles get their own section, their own cap and a lower score
    # threshold — local listings are far scarcer and far more actionable, so
    # the international remote pool must not crowd them out.
    local_min = search.get("local_min_score", min_score)
    general = [j for j in fresh if j.category == "general"]
    local = rank([j for j in general if matcher.is_local(j) and j.score >= local_min])[:cap]
    remote = rank([j for j in general if not matcher.is_local(j) and j.score >= min_score])[:cap]
    government = sorted(
        [j for j in fresh if j.category == "government" and j.score >= gov_min],
        key=lambda j: (-j.score, j.title),
    )[:cap]

    stats = {
        "matched": len(local) + len(remote),
        "government": len(government),
        "scanned": len(raw),
        "sources": len({j.source for j in raw}),
        "remember_days": runtime.get("remember_days", 45),
    }
    digest = digest_mod.Digest(local=local, remote=remote,
                               government=government, stats=stats)

    if digest.is_empty and not runtime.get("send_even_if_empty", True):
        log.info("nothing new and send_even_if_empty is off — exiting quietly")
        store.close()
        return 0

    if args.dry_run:
        out = ROOT / "logs" / f"digest-{date.today():%Y-%m-%d}.html"
        Path(out).write_text(digest.html, encoding="utf-8")
        log.info("DRY RUN — digest written to %s (nothing delivered)", out)
        store.close()
        return 0

    sent = notifiers.deliver(cfg, digest)
    if sent:
        sent_jobs = local + remote + government
        store.mark_sent(sent_jobs)
        pruned = store.prune()
        log.info("recorded %d listings as sent; pruned %d stale rows",
                 len(sent_jobs), pruned)
    store.close()
    return 0 if sent else 1


if __name__ == "__main__":
    sys.exit(main())
