#!/bin/bash

# Configuration
PROJECT_DIR="/Users/Bhavesh/Documents/GitHub/Portfoilo/Portfolio/Aircraft Safety Tracker"
LOG_FILE="$PROJECT_DIR/logs/update_data.log"

# Ensure log directory exists
mkdir -p "$PROJECT_DIR/logs"

# Start logging
echo "========================================================" >> "$LOG_FILE"
echo "Starting weekly data update: $(date)" >> "$LOG_FILE"

# Navigate to project directory
cd "$PROJECT_DIR" || {
    echo "Error: Could not change directory to $PROJECT_DIR" >> "$LOG_FILE"
    exit 1
}

# Activate virtual environment
# Assuming venv is in the project root
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
else
    echo "Error: Virtual environment not found at venv/bin/activate" >> "$LOG_FILE"
    exit 1
fi

# Run Boeing Scraper
echo "Running Boeing scraper..." >> "$LOG_FILE"
python scripts/scrape_boeing.py >> "$LOG_FILE" 2>&1
if [ $? -ne 0 ]; then
    echo "Error: Boeing scraper failed" >> "$LOG_FILE"
fi

# Run Airbus Scraper
echo "Running Airbus scraper..." >> "$LOG_FILE"
python scripts/scrape_airbus.py >> "$LOG_FILE" 2>&1
if [ $? -ne 0 ]; then
    echo "Error: Airbus scraper failed" >> "$LOG_FILE"
fi

# Run Data Import
echo "Running Data Import..." >> "$LOG_FILE"
python scripts/import_data.py >> "$LOG_FILE" 2>&1
if [ $? -ne 0 ]; then
    echo "Error: Data import failed" >> "$LOG_FILE"
fi

echo "Weekly update completed: $(date)" >> "$LOG_FILE"
echo "========================================================" >> "$LOG_FILE"
