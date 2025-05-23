#!/bin/bash
#set -x

# Project directory
PROJECT_DIR="$HOME/projects/software-observatory/research-software-etl"

# File paths
SCRIPT_PATH="src/adapters/cli/integration/disambiguation.py"
BLOCKS_FILE="scripts/data/blocks.jsonl"
CONFLICT_BLOCKS_FILE="scripts/data/conflict_blocks.jsonl"
DISAMBIGUATED_BLOCKS_FILE="scripts/data/disambiguated_blocks.jsonl"

# Change to the project directory
cd "$PROJECT_DIR" || {
  echo "❌ Failed to change directory to $PROJECT_DIR" | tee -a rs-disambiguation-08052025.log
  exit 1
}


# Set the PYTHONPATH environment variable
export PYTHONPATH="$PROJECT_DIR"

echo "ℹ️  Running the disambiguation script..." | tee -a rs-disambiguation-08052025.log

# Run the Python script
python3 -u "$SCRIPT_PATH" \
  --blocks-file "$BLOCKS_FILE" \
  --conflict-blocks-file "$CONFLICT_BLOCKS_FILE" \
  --disambiguated-blocks-file "$DISAMBIGUATED_BLOCKS_FILE" \
  --env-file ".env" 2>&1 | tee -a rs-disambiguation-08052025.log
