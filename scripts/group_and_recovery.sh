#!/bin/bash

# Project directory
PROJECT_DIR="$HOME/projects/software-observatory/research-software-etl"

# File paths
SCRIPT_PATH="src/adapters/cli/integration/group_and_recovery.py"
GROUPED_ENTRIES_FILE="scripts/data/grouped_entries.json"
ENV_FILE=".env"

# Change to the project directory
cd "$PROJECT_DIR" || {
  echo "❌ Failed to change directory to $PROJECT_DIR" | tee -a rs-integration.log
  exit 1
}

# Set the PYTHONPATH environment variable
export PYTHONPATH="$PROJECT_DIR"

echo "ℹ️ Running the group and recovery script..." | tee -a rs-integration.log
# Run the Python script
python3 "$SCRIPT_PATH" \
  --grouped-entries-file "$GROUPED_ENTRIES_FILE" \
  --env-file "$ENV_FILE" 2>&1 | tee -a rs-integration.log