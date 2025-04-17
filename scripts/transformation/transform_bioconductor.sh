#!/bin/bash

# Project directory
PROJECT_DIR="$HOME/projects/software-observatory/research-software-etl"

# File paths
SCRIPT_PATH="src/adapters/cli/transformation/transformation.py"
ENV_FILE=".env"

# Sources to transform 
#SOURCES="bioconda bioconda_recipes github biotools bioconductor galaxy_metadata toolshed galaxy sourceforge opeb_metrics"

# Change to the project directory
cd "$PROJECT_DIR" || {
  echo "❌ Failed to change directory to $PROJECT_DIR" | tee -a rs-transformation-bioconductor-02042025.log
  exit 1
}

# Set the PYTHONPATH environment variable
export PYTHONPATH="$PROJECT_DIR"

echo "ℹ️ Running the transformation script..." | tee -a rs-transformation-bioconductor-02042025.log

# Run the Python script
python3 "$SCRIPT_PATH" --env-file "$ENV_FILE" --sources bioconductor 2>&1 | tee -a rs-transformation-bioconductor-02042025.log






  



    