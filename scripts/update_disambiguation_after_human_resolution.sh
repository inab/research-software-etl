#!/bin/bash
#set -x

# Project directory
PROJECT_DIR="$HOME/projects/software-observatory/research-software-etl"

# File paths
SCRIPT_PATH="src/adapters/cli/integration/update_disambiguation_after_human_resolution.py"
CONFLICT_BLOCKS_FILE="scripts/data/conflict_blocks.jsonl"
DISAMBIGUATED_BLOCKS_FILE="scripts/data/disambiguated_blocks.jsonl"

# Change to the project directory
cd "$PROJECT_DIR" || {
  echo "❌ Failed to change directory to $PROJECT_DIR" | tee -a rs-after-human-16052025.log
  exit 1
}


# Set the PYTHONPATH environment variable
export PYTHONPATH="$PROJECT_DIR"

echo "ℹ️  Running the update of disambiguation ofter human resolution script..." | tee -a rs-after-human-16052025.log

# Run the Python script
python3 -u "$SCRIPT_PATH" \
  --conflict-blocks-file "$CONFLICT_BLOCKS_FILE" \
  --disambiguated-blocks-file "$DISAMBIGUATED_BLOCKS_FILE" 2>&1 | tee -a rs-after-human-16052025.log

# ...
# Updating record with key: beagle/cmd
# Updated disambiguated record for conflict ID: beagle/cmd
# Total conflicts updated: 107
# Disambiguation process finished!