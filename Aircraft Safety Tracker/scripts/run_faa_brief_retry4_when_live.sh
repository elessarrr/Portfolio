#!/bin/bash
# Cron wrapper: probe ASIAS every 30m; start retry4 when liveness is true.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="$ROOT"
export PATH="/Users/Bhavesh/opt/anaconda3/bin:/usr/local/bin:/usr/bin:/bin"

PYTHON="${PYTHON:-/Users/Bhavesh/opt/anaconda3/bin/python}"
exec "$PYTHON" "$ROOT/scripts/run_faa_brief_retry4_when_live.py"
