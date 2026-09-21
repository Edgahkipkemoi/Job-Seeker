#!/usr/bin/env bash
# One-time setup: virtualenv + dependencies + .env scaffold
set -euo pipefail
cd "$(dirname "$0")"

echo "==> Creating virtualenv (.venv)"
python3 -m venv .venv
./.venv/bin/pip install --quiet --upgrade pip
echo "==> Installing dependencies"
./.venv/bin/pip install --quiet -r requirements.txt

if [ ! -f .env ]; then
  cp .env.example .env
  echo "==> Created .env — EDIT IT NOW and fill in ONE delivery channel."
else
  echo "==> .env already exists, leaving it alone."
fi

mkdir -p data logs
echo
echo "Setup complete. Next steps:"
echo "  1. nano .env             # fill in Telegram, SMTP or Discord (see comments)"
echo "  2. nano config.yaml      # set delivery.channels to match"
echo "  3. ./.venv/bin/python run.py --test"
echo "  4. ./install_cron.sh     # schedule the 07:00 daily run"
