# Energy USA — common development tasks.
# Run `make help` to see all targets.
# Install make on macOS: xcode-select --install

# ── Variables (override on the command line, e.g. make backfill DATASET=all) ──

DATASET   ?= retail_sales           # Dataset for backfill: retail_sales | electric_power_operational | state_source_disposition | state_summary | all
START     ?=                        # Start period YYYY-MM (blank = last calendar month)
END       ?=                        # End period YYYY-MM (blank = current month)
CHUNKS    ?= 1                      # Months per backfill chunk
SERVICE   ?=                        # Service name for `make logs` (blank = all)
TABLE     ?= eia_retail_sales       # Table for `make export`
FILTER    ?=                        # Optional SQL WHERE clause for `make export` (e.g. "stateid='CA'")
OUT       ?= exports/$(TABLE).csv   # Output path for `make export`

.PHONY: help up down logs deploy \
        backfill backfill-prefect \
        jupyter \
        export

# ── Help ──────────────────────────────────────────────────────────────────────

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	  | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'

# ── Docker stack ──────────────────────────────────────────────────────────────

up:  ## Start the full Docker Compose stack (builds images if needed)
	./dock.sh up

down:  ## Stop and remove all stack containers
	./dock.sh down

logs:  ## Tail logs (SERVICE=web|prefect-worker|jupyter|postgres|...)
	./dock.sh logs $(SERVICE)

deploy:  ## Register Prefect ingest deployments (run after `make up`)
	./dock.sh deploy

# ── Ingest — local (no Prefect server required) ───────────────────────────────
# This is the fastest way to build a historical dataset.
# Full Python tracebacks appear in the terminal.
#
# Examples:
#   make backfill DATASET=retail_sales START=2020-01 END=2024-12
#   make backfill DATASET=all START=2015-01 END=2024-12 CHUNKS=6

backfill:  ## Run ingest locally (no Prefect server). Use DATASET, START, END, CHUNKS.
	uv run python scripts/run_local.py \
	  --dataset $(DATASET) \
	  $(if $(START),--start $(START)) \
	  $(if $(END),--end $(END)) \
	  --chunks $(CHUNKS)

# ── Ingest — via Prefect (requires `make up` first) ───────────────────────────

backfill-prefect:  ## Trigger a backfill through the Prefect server. Use DATASET, START, END.
	./dock.sh run backfill-eia \
	  $(if $(START),--param date_start=$(START)) \
	  $(if $(END),--param date_end=$(END)) \
	  --param chunk_months=$(CHUNKS) \
	  --param dataset=$(DATASET)

# ── Local services (no Docker) ────────────────────────────────────────────────

jupyter:  ## Start Jupyter Lab locally (needs DATABASE_URL in .env)
	uv sync --extra notebook
	INGEST_DATABASE_URL=$${INGEST_DATABASE_URL} \
	  uv run jupyter lab --notebook-dir=notebooks

# ── Data export ───────────────────────────────────────────────────────────────
# Exports a table (or filtered slice) to CSV for analysis in DBeaver or Claude.ai.
#
# Examples:
#   make export TABLE=eia_retail_sales
#   make export TABLE=eia_retail_sales FILTER="stateid='TX'" OUT=exports/tx.csv
#   make export TABLE=eia_electric_power_operational FILTER="period > '2020-01-01'"

export:  ## Export a table to CSV. Use TABLE, FILTER (optional), OUT (optional).
	uv run python scripts/export_table.py \
	  --table $(TABLE) \
	  $(if $(FILTER),--filter '$(FILTER)') \
	  --out $(OUT)
