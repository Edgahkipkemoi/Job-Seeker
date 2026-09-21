# Job Seeker — Daily Automated Job Digest

Twice a day — **07:00 and 21:25 Africa/Nairobi** — this agent sweeps the internet and
delivers a digest in three sections, each with direct application links:

1. **Kenya-based roles** — local openings matching your CV, held to a lower score
   threshold because they are scarcer and more actionable.
2. **Remote & international roles** — software development, full-stack, Elixir/Phoenix,
   React/Next.js, DevOps, network engineering and technical support.
3. **Government, ministries & parastatals** — every open Kenyan public-sector vacancy
   found, regardless of whether it matches your technical keywords.

Vacancies you have already been sent are remembered for 45 days, so each digest
contains only what is genuinely new.

---

## Quick start

```bash
cd "/home/work/My Projects/JOB SEEKER"

./setup.sh                        # 1. virtualenv + dependencies + .env
nano .env                         # 2. fill in ONE delivery channel (below)
nano config.yaml                  # 3. set delivery.channels to match
./.venv/bin/python run.py --test  # 4. confirm delivery works
./install_cron.sh                 # 5. schedule the 07:00 daily run
```

---

## Choosing a delivery channel

Set `delivery.channels` in `config.yaml` to one or more of `local`, `telegram`, `email`,
`discord`, then fill in that channel's block in `.env`. Listing several sends to all of them.

Effort, lowest first:

| Channel | What you have to do | Reaches your phone |
|---|---|---|
| **local** | Nothing. Already working. | No — open `digest.html` |
| **telegram** | Paste one bot token | Yes |
| **email** | Sign up with an SMTP provider | Yes |
| **discord** | Copy a webhook URL | Yes |

### local — zero setup, and it is the default

Every run writes **`digest.html`** in this folder and raises a desktop notification
where the system supports it. Bookmark that file once; it is rewritten each morning
at 07:00. No account, no token, no sign-up.

This is the only channel that cannot fail for credential reasons, so it is worth
keeping in `channels` alongside whichever push channel you add.

### Telegram — one value to paste

1. In Telegram, message **@BotFather** and send `/newbot`. Follow the prompts.
2. Paste the token it gives you into `TELEGRAM_BOT_TOKEN` in `.env`.
3. Send your new bot any message — it cannot message you until you do.
4. Set `channels: ["local", "telegram"]` in `config.yaml`.

The chat id is discovered on the first send and written back to `.env`, so the token
is the only thing you ever supply. Long digests split across several messages,
always breaking between jobs.

> **Instagram and WhatsApp are not options here.** Both require a Meta Business
> account, a registered app and API review before any message can be sent
> programmatically — considerably more work than any channel above, not less.

### Email — any SMTP provider

Nothing here is Gmail-specific; only three values change.

| Provider | Host | Free tier | Setup cost |
|---|---|---|---|
| **Brevo** | `smtp-relay.brevo.com` | 300/day | Sign up, generate an SMTP key. No 2FA. |
| **Resend** | `smtp.resend.com` | 100/day | API key doubles as the SMTP password. |
| **Gmail** | `smtp.gmail.com` | — | Needs 2-Step Verification **and** an [App Password](https://myaccount.google.com/apppasswords). |

```ini
SMTP_HOST=smtp-relay.brevo.com
SMTP_PORT=587
SMTP_USER=<the login your provider shows you>
SMTP_PASSWORD=<the SMTP key it generates>
MAIL_FROM=<the address you send from>
MAIL_TO=shakurtatum@gmail.com
```

`MAIL_TO` accepts a comma-separated list for more than one inbox.

### Discord — a webhook URL and nothing else

Server Settings → Integrations → Webhooks → New Webhook → Copy Webhook URL,
paste into `DISCORD_WEBHOOK_URL`, set `channels: ["discord"]`.

---

## Running it by hand

```bash
./.venv/bin/python run.py                    # full run: search, de-duplicate, deliver
./.venv/bin/python run.py --dry-run          # writes logs/digest-YYYY-MM-DD.html, sends nothing
./.venv/bin/python run.py --no-store         # ignore de-duplication, re-report everything
./.venv/bin/python run.py --test             # short test message via every channel
./.venv/bin/python run.py --telegram-chat-id # look up your Telegram chat id
./.venv/bin/python run.py -v                 # verbose logging
```

`--dry-run` is the one to use while tuning `config.yaml`: open the generated HTML
file in a browser to see exactly what the 07:00 email would have contained.

---

## Where the jobs come from

| Layer | Sources |
|---|---|
| **Job-board APIs** | Remotive, RemoteOK, Arbeitnow, Jobicy, Himalayas, Adzuna *(optional key)* |
| **RSS feeds** | MyJobMag Kenya, JobWebKenya, Career Point Kenya, WeWorkRemotely (Programming + DevOps) |
| **Scraped boards** | BrighterMonday Kenya (Software & Data, IT & Telecoms, Engineering & Technology) |
| **Government & parastatals** | MyGov Kenya, Public Service Commission, PSC Jobs Portal, Kenya Revenue Authority, Communications Authority of Kenya, Central Bank of Kenya, Kenyatta National Hospital, KeNHA, Safaricom |
| **Press sweeps** | Google News RSS queries for ministry, county and state-corporation adverts |

A listing from *any* source is re-classified as public-sector if its text names a ministry,
county government, commission, authority or state corporation — so government adverts
republished by an aggregator still land in the government section. Public-sector items are
then filtered down to genuine vacancies: procurement notices, annual reports and press
commentary about hiring are dropped, as is recruitment news from outside Kenya.

Listings are de-duplicated on employer + job title, so the same vacancy syndicated to
three boards under three URLs appears once.

Sources are deliberately fault-tolerant: if a site is down, returns 403 or changes its
HTML, that one source logs a warning and the run continues.

**Adzuna (optional):** register free at <https://developer.adzuna.com/> and add
`ADZUNA_APP_ID` / `ADZUNA_APP_KEY` to `.env` for direct Kenyan job-market coverage.
Leave them blank and the source is skipped silently.

---

## Tuning what you receive

Everything lives in **`config.yaml`** — no code changes needed.

| Setting | Effect |
|---|---|
| `keywords.must_any` | A job is dropped unless it matches one of these. Widens or narrows the funnel. |
| `keywords.weighted` | Scoring. Title matches count double. Raise `elixir` or `mikrotik` to push your niche skills to the top. |
| `keywords.exclude` | Title words that bin a job outright (sales, internships, roles too senior). |
| `search.queries` | Free-text queries sent to the searchable APIs. |
| `search.min_score` | Relevance cut-off for remote/international roles. **Too few results? Lower it. Too much noise? Raise it.** |
| `search.local_min_score` | Separate, lower cut-off for Kenya-based roles. |
| `search.max_per_section` | Maximum listings per section in one email. |
| `search.max_age_days` | Ignore postings older than this. |
| `government.min_score` | `0` means report every public-sector vacancy found. |
| `government.html` | Add any ministry or parastatal careers page here — name, URL, and link hints. |
| `runtime.remember_days` | How long a vacancy stays suppressed after being sent. |
| `runtime.send_even_if_empty` | Set `false` to stay silent on days with no new listings. |
| `delivery.channels` | Which channels receive the digest: `local`, `telegram`, `email`, `discord`. |

---

## The schedule

Times live in `config.yaml`, and `./install_cron.sh` turns them into crontab entries:

```yaml
schedule:
  timezone: "Africa/Nairobi"
  times:
    - "07:00"
    - "21:25"
```

```
0  7 * * * cd "<project>" && TZ=Africa/Nairobi "<project>/.venv/bin/python" run.py >> logs/cron.log 2>&1
25 21 * * * cd "<project>" && TZ=Africa/Nairobi "<project>/.venv/bin/python" run.py >> logs/cron.log 2>&1
```

`TZ` is pinned so the times mean Nairobi time whatever the machine's clock is set to.
To add, remove or move a run, edit `schedule.times` and re-run `./install_cron.sh` —
it replaces the previous set rather than accumulating duplicates.

Because vacancies are remembered for 45 days, the evening run reports only what
appeared since the morning one — you never see the same job twice.

```bash
crontab -l                                              # check it's installed
tail -f logs/cron.log                                   # watch the next run
crontab -l | grep -v job-seeker-daily-digest | crontab - # remove it
```

**The machine must be powered on at both times for cron to fire.** If it sleeps
overnight, use the GitHub Actions schedule below instead — it needs no machine
of your own.

---

## Running it on GitHub Actions (no machine of your own)

Pushing to GitHub does **not** by itself make anything run — GitHub stores code, it
doesn't execute it. But the included workflow at
[`.github/workflows/job-digest.yml`](.github/workflows/job-digest.yml) runs the search
on GitHub's servers on the same twice-daily schedule, free, with nothing to deploy.

### Setup

1. Create an **empty** repository at <https://github.com/new> — no README, no
   .gitignore, no licence — then run:

   ```bash
   ./deploy_github.sh https://github.com/<you>/<repo>.git
   ```

   It pushes the project, refuses to run if `.env` is not gitignored, and prints
   the exact secret names and values to paste in the next step.
2. In the repo: **Settings → Secrets and variables → Actions → New repository secret**.
   Add the ones for your channel:

   | Secret | Value |
   |---|---|
   | `TELEGRAM_BOT_TOKEN` | the token from @BotFather |
   | `TELEGRAM_CHAT_ID` | the id saved in your local `.env` |

   Email or Discord instead? Add `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`,
   `MAIL_FROM`, `MAIL_TO`, or `DISCORD_WEBHOOK_URL`.
3. Open the **Actions** tab and run **Job Digest** once by hand to confirm it works.

`.env` is gitignored and never leaves your machine — Actions reads the secrets instead.

### Things worth knowing

- **Times are UTC in the workflow.** GitHub cron ignores `schedule.timezone`. Kenya is
  UTC+3 year-round, so the workflow uses `04:00` and `18:25` UTC. If you change
  `schedule.times` in `config.yaml`, update the workflow's `cron:` lines too — subtract
  three hours.
- **`data/seen.db` is committed back after every run.** The runner is wiped between
  jobs, so without this you would be sent the same vacancies twice a day forever. The
  workflow commits with the built-in token, which by design does not re-trigger
  workflows, so there is no loop.
- **`digest.html` is committed too**, so you can read the latest digest straight from
  the repo. Each run also uploads it as a downloadable artifact for 14 days.
- **Scheduled runs can be late.** GitHub delays schedules under load, sometimes by
  30+ minutes. It is not a precise alarm clock.
- **GitHub disables scheduled workflows after ~60 days of repository inactivity.**
  You get an email and can re-enable in one click.
- **Cost:** public repos run Actions free. Private repos get 2,000 minutes/month free;
  at roughly 3 minutes a run, twice daily, this uses about 180.

---

## Project layout

```
config.yaml              profile, keywords, sources, thresholds  ← tune this
.env                     SMTP credentials and API keys           ← secrets, never commit
run.py                   CLI entry point
setup.sh                 one-time environment setup
install_cron.sh          installs the daily schedule from config.yaml
deploy_github.sh         pushes to GitHub and prints the secrets to add
.github/workflows/       GitHub Actions schedule (runs without your PC on)
jobseeker/
  models.py              Job dataclass, fingerprinting, text cleaning
  config.py              YAML + .env loading
  http.py                shared HTTP session with retries and failure tolerance
  matcher.py             CV relevance scoring and filtering
  store.py               SQLite memory of what has already been sent
  digest.py              Digest object, HTML + plain-text rendering
  notifiers/
    __init__.py          channel registry and dispatch
    local.py             writes digest.html, no credentials needed
    email_smtp.py        any SMTP provider
    telegram.py          bot messages, with length-safe chunking
    discord.py           incoming webhook
  sources/
    boards.py            job-board JSON APIs
    rss.py               RSS/Atom adapter + Google News sweeps
    scrape.py            generic careers-page link scraper
    gov.py               Kenyan government, parastatals, public-sector classifier
cv/EDGAH_KIPKEMOI_CV.md  your revised CV
data/seen.db             de-duplication database (auto-created)
logs/                    run logs and --dry-run digests
```

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `SMTP auth rejected` | With Gmail you used your account password — create an **App Password**. With Brevo/Resend, `SMTP_USER` must be the login they show you, not your signup email. |
| `not configured — needs ...` | That channel is listed in `config.yaml` but its `.env` values are blank. |
| Telegram: no chat ids found | You have not messaged the bot yet. Send it anything, then re-run `--telegram-chat-id`. |
| No email at 07:00 | Machine was off or asleep. Check `crontab -l` and `logs/cron.log`. |
| Very few matched roles | Lower `search.min_score`, or add keywords to `keywords.must_any`. |
| Too much irrelevant noise | Raise `search.min_score`, or add words to `keywords.exclude`. |
| A source logs `403` / `404` | That site changed or blocks bots. Every other source still runs — update or remove its entry in `config.yaml`. |
