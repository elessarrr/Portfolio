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

# State dir holds the success marker (mtime = last successful run) and the lock
# used by the watchdog (run_asn_refresh_if_stale.sh) to avoid concurrent runs.
STATE_DIR="${ASN_STATE_DIR:-$HOME/.local/state/aircraft-safety}"
MARKER="$STATE_DIR/asn-last-success"
LOCK="$STATE_DIR/asn-refresh.lock"
mkdir -p "$STATE_DIR"

# Atomic lock: mkdir succeeds only if the dir does not already exist.
if ! mkdir "$LOCK" 2>/dev/null; then
  echo "ASN refresh: another run holds $LOCK — skipping this invocation." >&2
  exit 0
fi
trap 'rmdir "$LOCK" 2>/dev/null || true' EXIT

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

# Record success so the watchdog knows the job ran this week. We only stamp the
# marker on a clean exit, so a failed run stays "stale" and gets retried.
if [[ "$status" -eq 0 ]]; then
  date '+%Y-%m-%dT%H:%M:%S%z' > "$MARKER"
fi

echo "===== ASN refresh exit=$status ====="
exit $status
