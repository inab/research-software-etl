#!/bin/bash
# Script to generate statistics for all collections using the CLI adapter
# Usage: ./generate_all_stats.sh [--env-file ENV] [--loglevel LEVEL]


# Project directory
PROJECT_DIR="$HOME/projects/software-observatory/research-software-etl"


ENV_FILE=".env"
LOGLEVEL="INFO"
#COLLECTIONS="all"
COLLECTIONS="EUCAIM"

# Set the PYTHONPATH environment variable
export PYTHONPATH="$PROJECT_DIR"

python3 src/adapters/cli/generate_stats.py --collections "$COLLECTIONS" --env-file "$ENV_FILE" --loglevel "$LOGLEVEL" 