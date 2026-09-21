#!/usr/bin/env bash
# Pushes this project to GitHub and prints the exact secrets to paste there,
# so the digest runs on GitHub's servers instead of your own machine.
#
#   ./deploy_github.sh https://github.com/<you>/<repo>.git
set -euo pipefail
cd "$(dirname "$0")"

REMOTE="${1:-}"
if [ -z "$REMOTE" ]; then
  cat <<'USAGE'
Usage: ./deploy_github.sh <repository-url>

First create an EMPTY repository at https://github.com/new
(no README, no .gitignore, no licence), then run this with its URL, e.g.

  ./deploy_github.sh https://github.com/Edgahkipkemoi/job-seeker.git
USAGE
  exit 1
fi

if [ ! -f .env ]; then
  echo "ERROR: .env not found — run ./setup.sh first." >&2
  exit 1
fi

# Refuse to push if secrets would somehow be included.
if git check-ignore -q .env; then
  echo "✓ .env is gitignored — your credentials stay on this machine"
else
  echo "ERROR: .env is NOT gitignored. Refusing to push." >&2
  exit 1
fi

git add -A
git diff --staged --quiet || git commit -q -m "Update job seeker configuration"

if git remote | grep -qx origin; then
  git remote set-url origin "$REMOTE"
else
  git remote add origin "$REMOTE"
fi

echo "==> Pushing to $REMOTE"
git push -u origin HEAD

REPO_WEB="${REMOTE%.git}"
echo
echo "=============================================================="
echo " Pushed. Two things left, both in your browser."
echo "=============================================================="
echo
echo "1. Add these secrets at:"
echo "     $REPO_WEB/settings/secrets/actions"
echo
# Only the values your configured channels actually need. SMTP settings are
# skipped unless a username is set, since host/port alone send nothing.
HAS_SMTP=$(grep -c '^SMTP_USER=..*' .env || true)
while IFS='=' read -r key value; do
  [ -n "$value" ] || continue
  case "$key" in
    SMTP_*|MAIL_*)
      [ "$HAS_SMTP" = "0" ] && continue
      printf '     %-20s %s\n' "$key" "$value" ;;
    TELEGRAM_BOT_TOKEN|TELEGRAM_CHAT_ID|DISCORD_WEBHOOK_URL|ADZUNA_APP_ID|ADZUNA_APP_KEY)
      printf '     %-20s %s\n' "$key" "$value" ;;
  esac
done < .env
echo
echo "2. Run it once by hand to confirm, at:"
echo "     $REPO_WEB/actions/workflows/job-digest.yml"
echo "   -> 'Run workflow'"
echo
echo "   If that run fails on the commit step with a 403, go to"
echo "     $REPO_WEB/settings/actions"
echo "   and set Workflow permissions to 'Read and write permissions'."
echo
echo "After that it runs at 07:00 and 21:25 Nairobi time with your PC off."
