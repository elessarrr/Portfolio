#!/bin/bash
echo "Starting Aircraft Safety Tracker in Development Mode..."

# Ensure we are in the project root
cd "$(dirname "$0")"

# Absolute path to venv python
PYTHON_EXEC="$(pwd)/venv/bin/python"

if [ ! -f "$PYTHON_EXEC" ]; then
    echo "ERROR: Virtual environment python not found at $PYTHON_EXEC"
    echo "Please run: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

echo "Using Python: $PYTHON_EXEC"

# Run Flask using the venv python directly
export FLASK_APP=run.py
export FLASK_ENV=development
export FLASK_DEBUG=1
"$PYTHON_EXEC" -m flask run
