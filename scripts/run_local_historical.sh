#!/bin/bash

# Script to run a historical backfill locally using an isolated database.
# Uses 'energyusa_historical' database to avoid polluting main dev DB (energyusa).

set -e

HISTORICAL_DB_NAME="energyusa_historical"
DB_USER="user" # As setup by setup_dev.sh
DB_PASS="password"

echo "==============================================="
echo "Starting Local Historical Backfill"
echo "Target DB: $HISTORICAL_DB_NAME"
echo "==============================================="

# Check if historical DB exists, create if not
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS check (user is often superuser for brew postgres)
    if ! psql -d postgres -lqt | cut -d \| -f 1 | grep -qw $HISTORICAL_DB_NAME; then
        echo "Creating database $HISTORICAL_DB_NAME..."
        createdb $HISTORICAL_DB_NAME -O "$DB_USER"
    fi
else
    # Linux check
    if ! sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw $HISTORICAL_DB_NAME; then
        echo "Creating database $HISTORICAL_DB_NAME..."
        sudo -u postgres createdb -O "$DB_USER" $HISTORICAL_DB_NAME
    fi
fi

# Prompt for dates if not provided
START_DATE=${1:-"2020-01-01"}
END_DATE=${2:-"2020-12-31"}

echo "Backfill Range: $START_DATE to $END_DATE"

# Export env var to point to historical DB
export DATABASE_URL="postgresql://$DB_USER:$DB_PASS@localhost:5432/$HISTORICAL_DB_NAME"

# Initialize DB (Schemas/Tables)
echo "Initializing Database Schema (Resetting)..."
energyusa setup-db --reset

# Run Extraction
echo "Extracting EIA Data..."
energyusa extract eia --mode historical --start-date "$START_DATE" --end-date "$END_DATE"

echo "Extracting File-based Data (FERC/EPA)..."
energyusa extract files --mode historical --start-date "$START_DATE"

# Run Analysis
echo "Running Analysis..."
energyusa analyze

echo "==============================================="
echo "Historical Backfill Complete!"
echo "Data is in $HISTORICAL_DB_NAME"
echo "==============================================="
