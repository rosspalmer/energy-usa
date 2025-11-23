#!/bin/bash

# Setup script for local development environment (Postgres)
# Supports macOS (Homebrew) and Linux (apt)

set -e

DB_NAME="energyusa"
TEST_DB_NAME="energyusa_test"
DB_USER="user"
DB_PASS="password"

echo "Setting up local development environment..."

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# install postgres if missing
if ! command_exists psql; then
    echo "Postgres not found. Installing..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        if command_exists brew; then
            brew install postgresql@14
            brew services start postgresql@14
        else
            echo "Homebrew not found. Please install Homebrew first."
            exit 1
        fi
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if command_exists apt-get; then
            sudo apt-get update
            sudo apt-get install -y postgresql postgresql-contrib
            sudo service postgresql start
        else
             echo "apt-get not found. Manual installation required."
             exit 1
        fi
    else
        echo "Unsupported OS. Please install Postgres manually."
    fi
else
    echo "Postgres is already installed."
fi

# Wait for Postgres to start
sleep 3

echo "Configuring Database..."

# Create User if not exists
# Note: syntax varies slightly by OS/setup
if [[ "$OSTYPE" == "darwin"* ]]; then
    # On macOS/Homebrew, default superuser is $(whoami), and 'postgres' role might not exist.
    SUPERUSER=$(whoami)
    # Connect to 'postgres' db (usually exists) or 'template1'
    DB_TO_CONNECT="postgres"
else
    # On Linux/apt, 'postgres' is the system user and db role
    SUPERUSER="postgres"
    DB_TO_CONNECT="postgres"
fi

# Check if user exists
# We use "postgres" or current user to connect. 
if [[ "$OSTYPE" == "darwin"* ]]; then
    EXISTS_CMD="psql -d $DB_TO_CONNECT -tAc \"SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'\""
else
    EXISTS_CMD="sudo -u postgres psql -tAc \"SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'\""
fi

if ! eval "$EXISTS_CMD" | grep -q 1; then
    echo "Creating user $DB_USER..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
         # Use quotes around user to handle reserved keywords like "user"
         psql -d $DB_TO_CONNECT -c "CREATE USER \"$DB_USER\" WITH PASSWORD '$DB_PASS';"
         psql -d $DB_TO_CONNECT -c "ALTER USER \"$DB_USER\" CREATEDB;"
    else
         sudo -u postgres psql -c "CREATE USER \"$DB_USER\" WITH PASSWORD '$DB_PASS';"
         sudo -u postgres psql -c "ALTER USER \"$DB_USER\" CREATEDB;"
    fi
    echo "User $DB_USER created."
else
    echo "User $DB_USER already exists."
fi

# Create Databases
create_db_if_missing() {
    local DBNAME=$1
    # Check if DB exists
    if [[ "$OSTYPE" == "darwin"* ]]; then
        if ! psql -d postgres -lqt | cut -d \| -f 1 | grep -qw $DBNAME; then
            createdb $DBNAME -O "$DB_USER"
            echo "Database $DBNAME created."
        else
            echo "Database $DBNAME already exists."
        fi
    else
        if ! sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw $DBNAME; then
            sudo -u postgres createdb -O "$DB_USER" $DBNAME
            echo "Database $DBNAME created."
        else
            echo "Database $DBNAME already exists."
        fi
    fi
}

if [[ "$OSTYPE" == "darwin"* ]]; then
    create_db_if_missing $DB_NAME
    create_db_if_missing $TEST_DB_NAME
else
    # Linux typically requires sudo to switch to postgres user for creation
    if ! sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw $DB_NAME; then
        sudo -u postgres createdb -O $DB_USER $DB_NAME
        echo "Database $DB_NAME created."
    fi
    if ! sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw $TEST_DB_NAME; then
        sudo -u postgres createdb -O $DB_USER $TEST_DB_NAME
        echo "Database $TEST_DB_NAME created."
    fi
fi

echo "=================================================="
echo "Setup Complete!"
echo "Connection String: postgresql://$DB_USER:$DB_PASS@localhost:5432/$DB_NAME"
echo "Test DB String:    postgresql://$DB_USER:$DB_PASS@localhost:5432/$TEST_DB_NAME"
echo "=================================================="

