# Energy USA

Energy USA is a Python ETL package for extracting, analyzing, and displaying US energy data from open sources like EIA, FERC, and EPA.

## Features
- **Extract**: Pulls raw data from EIA API, FERC forms, and EPA eGRID.
- **Transform**: Normalizes data into Production, Consumption, and Transmission categories.
- **Analyze/Display**: Provides structured access to energy metrics.

## Installation

1. **Prerequisites**:
   - Python 3.12+
   - `uv` (Project Manager)
   - Postgres (Local Database)

2. **Install Dependencies**:
   ```bash
   uv sync
   ```

3. **Install Package (Editable Mode)**:
   ```bash
   uv pip install -e .
   ```

## Local Development Setup

To run this project locally, you need a running Postgres instance.

### 1. Setup Database
We provide a script to install/configure Postgres on Mac/Linux:

```bash
./scripts/setup_dev.sh
```

This will:
- Install Postgres (if missing) via Homebrew (Mac) or apt (Linux).
- Create a user `user` with password `password`.
- Create two databases: `energyusa` (dev) and `energyusa_test` (test).

### 2. Environment Variables
Create a `.env` file in the root directory:

```bash
DATABASE_URL="postgresql://user:password@localhost:5432/energyusa"
EIA_API_KEY="your_eia_api_key_here"
NREL_API_KEY="your_nrel_api_key_here"
```

### 3. Initialize Database Schema
Run the setup command to create tables:

```bash
energyusa setup-db
```

## Usage

### CLI Commands

- **Extract Data**:
  ```bash
  energyusa extract eia --mode refresh
  ```

- **Run Analysis/Transformation**:
  ```bash
  energyusa analyze
  ```

- **View Data**:
  ```bash
  energyusa show-production
  ```

## Testing

Run the test suite using `pytest`. Requires the test database `energyusa_test` to be running.

```bash
uv run pytest
```

