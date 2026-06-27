#!/usr/bin/env bash
# Weekly LOCAL ASN refresh (PRD 0012).
#
# aviation-safety.net (ASN) returns HTTP 403 to datacenter/cloud IPs, so it
# CANNOT run on GitHub Actions / Railway. This wrapper runs the ASN-only ingest
# from a residential IP (your Mac) on a launchd schedule and writes any new
# Boeing/Airbus incidents straight to the Railway Postgres (Postgres-cYEh).
#
# Secrets are NOT stored here. DATABASE_URL is sourced from a local env file
# OUTSIDE the repo (default: ~/.config/aircraft-safety/asn.env), so this script
# is safe to commit.
#
# Manual run:  bash "scripts/run_asn_refresh.sh"
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(dirname "$SCRIPT_DIR")"
PYTHON="${ASN_PYTHON:-/Users/Bhavesh/opt/anaconda3/bin/python}"
ENV_FILE="${ASN_ENV_FILE:-$HOME/.config/aircraft-safety/asn.env}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: env file not found: $ENV_FILE (must define DATABASE_URL=...)" >&2
  exit 1
fi
# shellcheck disable=SC1090
set -a; source "$ENV_FILE"; set +a

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "ERROR: DATABASE_URL not set after sourcing $ENV_FILE" >&2
  exit 1
fi

cd "$APP_DIR"
export PYTHONPATH=.
export FLASK_CONFIG="${FLASK_CONFIG:-production}"

echo "===== ASN refresh $(date '+%Y-%m-%d %H:%M:%S %Z') ====="
set +e
"$PYTHON" scripts/weekly_ingest.py --asn-only
status=$?
set -e
echo "===== ASN refresh exit=$status ====="
exit $status
