#!/bin/bash
#set -x

# Project directory
PROJECT_DIR="$HOME/projects/software-observatory/research-software-etl"

# File paths
SCRIPT_PATH="src/adapters/cli/integration/merge_entries.py"
DISAMBIGUATED_BLOCKS_FILE="scripts/data/disambiguated_blocks.jsonl"

# Change to the project directory
cd "$PROJECT_DIR" || {
  echo "❌ Failed to change directory to $PROJECT_DIR" | tee -a rs-merging-09092025.log
  exit 1
}


# Set the PYTHONPATH environment variable
export PYTHONPATH="$PROJECT_DIR"

echo "ℹ️  Running the merging script..." | tee -a rs-merging-09092025.log

# Run the Python script
python3 -u "$SCRIPT_PATH" \
  --disambiguated-blocks-file "$DISAMBIGUATED_BLOCKS_FILE" \
  --env-file ".env" 2>&1 | tee -a rs-merging-09092025.log
