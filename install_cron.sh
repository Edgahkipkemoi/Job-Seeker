#!/usr/bin/env bash
# Installs (or refreshes) the daily cron entries.
#
# The times come from `schedule.times` in config.yaml — edit that list and
# re-run this script. Every entry is tagged with a marker so re-running
# replaces the previous set rather than piling up duplicates.
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON="$PROJECT_DIR/.venv/bin/python"
MARKER="# job-seeker-daily-digest"

if [ ! -x "$PYTHON" ]; then
  echo "ERROR: $PYTHON not found. Run ./setup.sh first." >&2
  exit 1
fi

# Turn the schedule in config.yaml into crontab lines.
ENTRIES="$("$PYTHON" - "$PROJECT_DIR" "$MARKER" <<'PYEOF'
import sys, yaml, pathlib
project, marker = sys.argv[1], sys.argv[2]
cfg = yaml.safe_load(pathlib.Path(project, "config.yaml").read_text(encoding="utf-8"))
sched = cfg.get("schedule") or {}
tz = sched.get("timezone", "Africa/Nairobi")
times = sched.get("times") or ["07:00"]
python = f"{project}/.venv/bin/python"
log = f"{project}/logs/cron.log"
for t in times:
    hour, minute = str(t).strip().split(":")
    print(f'{int(minute)} {int(hour)} * * * cd "{project}" && TZ={tz} '
          f'"{python}" run.py >> "{log}" 2>&1 {marker}')
PYEOF
)"

if [ -z "$ENTRIES" ]; then
  echo "ERROR: no times found under schedule.times in config.yaml" >&2
  exit 1
fi

# grep exits 1 when the crontab is empty or has no match, which would trip
# `set -e`, so tolerate it explicitly.
{ crontab -l 2>/dev/null | grep -v -F "$MARKER" || true; echo "$ENTRIES"; } | crontab -

echo "Installed. Your crontab now contains:"
crontab -l | grep -F "$MARKER" || echo "  (could not read back crontab)"
echo
echo "To change the schedule: edit schedule.times in config.yaml, re-run this script."
echo "To remove it:  crontab -l | grep -v job-seeker-daily-digest | crontab -"
