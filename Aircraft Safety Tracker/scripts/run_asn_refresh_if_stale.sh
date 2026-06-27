#!/usr/bin/env bash
# ASN refresh WATCHDOG (PRD 0012 failsafe).
#
# The primary launchd job runs the ASN refresh weekly (Monday 09:00). launchd
# only catches up a missed run on the next wake — if the Mac is off across the
# whole window, or the run fails, nothing retries. This watchdog (run DAILY by
# com.aircraftsafety.asnrefresh.watchdog.plist) fills that gap, anacron-style:
#
#   if the last SUCCESSFUL refresh is older than ASN_MAX_AGE_DAYS (default 6),
#   run it now; otherwise do nothing.
#
# So a healthy week is silent (Monday run stamps the marker, watchdog skips),
# and a missed/failed week self-heals within a day.
#
# Manual run:  bash "scripts/run_asn_refresh_if_stale.sh"
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATE_DIR="${ASN_STATE_DIR:-$HOME/.local/state/aircraft-safety}"
MARKER="$STATE_DIR/asn-last-success"
MAX_AGE_DAYS="${ASN_MAX_AGE_DAYS:-6}"

now=$(date +%s)
if [[ -f "$MARKER" ]]; then
  # BSD/macOS stat: %m = mtime as epoch seconds.
  last=$(stat -f %m "$MARKER" 2>/dev/null || echo 0)
  age_days=$(( (now - last) / 86400 ))
else
  age_days=99999
fi

echo "ASN watchdog $(date '+%Y-%m-%d %H:%M:%S %Z'): last success age=${age_days}d (threshold ${MAX_AGE_DAYS}d)"

if (( age_days > MAX_AGE_DAYS )); then
  echo "Stale (or never run) — triggering ASN refresh now."
  exec bash "$SCRIPT_DIR/run_asn_refresh.sh"
fi

echo "Fresh — nothing to do."
