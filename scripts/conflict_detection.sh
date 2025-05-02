#!/bin/bash

# Project directory
PROJECT_DIR="$HOME/projects/software-observatory/research-software-etl"

# File paths
SCRIPT_PATH="src/adapters/cli/integration/conflict_detection.py"
GROUPED_ENTRIES_FILE="scripts/data/grouped_entries_no_opeb.json"
DISCONNECTED_ENTRIES_FILE="scripts/data/disconnected_entries.json"

# Change to the project directory
cd "$PROJECT_DIR" || {
  echo "❌ Failed to change directory to $PROJECT_DIR" | tee -a rs-integration-25042025.log
  exit 1
}

# Set the PYTHONPATH environment variable
export PYTHONPATH="$PROJECT_DIR"

echo "ℹ️ Running the conflict detection script..." | tee -a rs-integration-28042025.log
# Run the Python script
python3 "$SCRIPT_PATH" \
  --grouped-entries-file "$GROUPED_ENTRIES_FILE" \
  --disconnected-entries-file "$DISCONNECTED_ENTRIES_FILE" 2>&1 | tee -a rs-integration-28042025.log