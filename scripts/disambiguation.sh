#!/bin/bash
#set -x

# Project directory
PROJECT_DIR="$HOME/projects/software-observatory/research-software-etl"

# File paths
SCRIPT_PATH="src/adapters/cli/integration/disambiguation.py"
GROUPED_ENTRIES_FILE="scripts/data/grouped_entries.json"
DISCONNECTED_ENTRIES_FILE="scripts/data/disconnected_entries_test.json"
NEW_GROUPED_ENTRIES_FILE="scripts/data/new_grouped_entries_test.json"
RESULTS_FILE="scripts/data/disambiguation_results_test.jsonl"

# Change to the project directory
cd "$PROJECT_DIR" || {
  echo "❌ Failed to change directory to $PROJECT_DIR" | tee -a rs-disambiguation-test.log
  exit 1
}


# Set the PYTHONPATH environment variable
export PYTHONPATH="$PROJECT_DIR"

echo "ℹ️  Running the disambiguation script..." | tee -a rs-disambiguation-test.log

# Run the Python script
python3 -u "$SCRIPT_PATH" \
  --grouped-entries-file "$GROUPED_ENTRIES_FILE" \
  --disconnected-entries-file "$DISCONNECTED_ENTRIES_FILE" \
  --new-grouped-entries-file "$NEW_GROUPED_ENTRIES_FILE" \
  --env-file ".env" \
  --results-file "$RESULTS_FILE" 2>&1 | tee -a rs-disambiguation-test.log