#!/usr/bin/env bash
# growth-reporter local installer: venv + deps + wizard + cron line.
# Uses uv (https://docs.astral.sh/uv/) when available; falls back to python3 -m venv + pip.
set -euo pipefail
cd "$(dirname "$0")"

echo "== growth-reporter installer =="

if command -v uv >/dev/null; then
  uv venv --quiet .venv
  uv pip install --quiet --python .venv/bin/python .
  echo "✓ installed into ./.venv (via uv)"
else
  if ! command -v python3 >/dev/null; then
    echo "Neither uv nor python3 found. Install uv: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
  fi
  python3 -m venv .venv
  ./.venv/bin/pip install --quiet --upgrade pip
  ./.venv/bin/pip install --quiet .
  echo "✓ installed into ./.venv (via pip — consider installing uv, it's much faster)"
fi

if [ ! -f reporter.yaml ]; then
  ./.venv/bin/growth-reporter init
else
  echo "✓ reporter.yaml already exists — skipping wizard"
fi

./.venv/bin/growth-reporter doctor || true

BIN="$(pwd)/.venv/bin/growth-reporter"
echo
echo "To get your report every Tuesday at 08:00, add this line to 'crontab -e':"
echo "  0 8 * * 2 cd $(pwd) && $BIN run >> $(pwd)/reporter.log 2>&1"
echo
echo "(Tuesday because Search Console data for the week ending Sunday is"
echo "finalized by then.) Or push this repo to GitHub, add the GA4_SA_JSON"
echo "secret, and enable the included Actions workflow instead."
