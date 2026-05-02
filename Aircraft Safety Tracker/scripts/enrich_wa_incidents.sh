#!/bin/bash

# Daily WA press enrichment runner.
# Uses --max-queries to stay under Google CSE free-tier limits.

PROJECT_DIR="/Users/Bhavesh/Documents/GitHub/Portfoilo/Aircraft Safety Tracker"
LOG_FILE="$PROJECT_DIR/logs/enrich_wa_incidents.log"

mkdir -p "$PROJECT_DIR/logs"

{
  echo "========================================================"
  echo "Starting WA enrichment run: $(date)"
} >> "$LOG_FILE"

cd "$PROJECT_DIR" || {
  echo "Error: Could not change directory to $PROJECT_DIR" >> "$LOG_FILE"
  exit 1
}

if [ -f ".venv/bin/activate" ]; then
  source .venv/bin/activate
elif [ -f "venv/bin/activate" ]; then
  source venv/bin/activate
else
  echo "Error: Virtual environment not found at .venv/bin/activate or venv/bin/activate" >> "$LOG_FILE"
  exit 1
fi

PYTHONPATH=. flask import-data enrich-wa-incidents --max-queries 90 >> "$LOG_FILE" 2>&1
if [ $? -ne 0 ]; then
  echo "Error: WA enrichment command failed" >> "$LOG_FILE"
fi

{
  echo "Completed WA enrichment run: $(date)"
  echo "========================================================"
} >> "$LOG_FILE"
