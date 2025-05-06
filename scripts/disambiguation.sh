#!/bin/bash
#set -x

# Project directory
PROJECT_DIR="$HOME/projects/software-observatory/research-software-etl"

# File paths
SCRIPT_PATH="src/adapters/cli/integration/disambiguation.py"
BLOCKS_FILE="scripts/data/blocks.json"
CONFLICT_BLOCKS_FILE="scripts/data/conflict_blocks.json"
DISAMBIGUATED_BLOCKS_FILE="scripts/data/disambiguated_blocks.json"

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
  --blocks-file "$BLOCKS_FILE" \
  --conflict-blocks-file "$CONFLICT_BLOCKS_FILE" \
  --disambiguated-blocks-file "$DISAMBIGUATED_BLOCKS_FILE" \
  --env-file ".env" \
