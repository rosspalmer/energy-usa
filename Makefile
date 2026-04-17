# Energy USA — common development tasks.
# Run `make help` to see all targets.
# Install make on macOS: xcode-select --install

# ── Variables (override on the command line, e.g. make backfill DATASET=all) ──

DATASET   ?= retail_sales           # Dataset for backfill: retail_sales | electric_power_operational | state_source_disposition | state_summary | all
START     ?=                        # Start period YYYY-MM (blank = last calendar month)
END       ?=                        # End period YYYY-MM (blank = current month)
CHUNKS    ?= 1                      # Months per backfill chunk
SERVICE   ?=                        # Service name for `make logs` (blank = all)
TABLE     ?= eia.retail_sales       # Table for `make export` (schema.table format)
FILTER    ?=                        # Optional SQL WHERE clause for `make export` (e.g. "stateid='CA'")
OUT       ?= exports/$(TABLE).csv   # Output path for `make export`
SOURCE    ?= eia                    # Source for code generation
GDATASET  ?=                        # Dataset for single-dataset generation (blank = all)
VSOURCE   ?= eia                    # Source for validation
VDATASET  ?=                        # Dataset for validation (blank = all)
DOMAIN    ?= electricity            # Domain for transform
TTABLE    ?=                        # Table for single-table transform (blank = all)

.PHONY: help up down logs deploy \
        backfill backfill-prefect \
        jupyter \
        export \
        generate-ingest \
        validate audit generate-validate \
        transform \
        dashboard-list dashboard-export dashboard-import \
        evidence evidence-build evidence-logs evidence-publish

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

# ── Code generation ───────────────────────────────────────────────────────────
# Generate ingest artifacts (SQL, db module, flow) from markdown specs.
#
# Examples:
#   make generate-ingest SOURCE=eia
#   make generate-ingest SOURCE=eia GDATASET=retail_sales

generate-ingest:  ## Generate ingest code from specs/ingest/<SOURCE>.md
	uv run python scripts/generate.py ingest \
	  --source $(SOURCE) \
	  $(if $(GDATASET),--dataset $(GDATASET))

# ── Validation ────────────────────────────────────────────────────────────────

validate:  ## Run validation checks. Use VSOURCE, VDATASET (optional).
	uv run python scripts/validate.py run \
	  --source $(VSOURCE) \
	  $(if $(VDATASET),--dataset $(VDATASET))

audit:  ## Show audit results summary. Use VSOURCE, VDATASET (optional).
	uv run python scripts/validate.py audit \
	  --source $(VSOURCE) \
	  $(if $(VDATASET),--dataset $(VDATASET))

generate-validate:  ## Generate validate audit rules SQL from specs/validate/<VSOURCE>.md
	uv run python scripts/generate.py validate --source $(VSOURCE)

# ── Transform ─────────────────────────────────────────────────────────────────

transform:  ## Run transform for a domain. Use DOMAIN, TTABLE (optional).
	uv run python scripts/transform.py \
	  --domain $(DOMAIN) \
	  $(if $(TTABLE),--table $(TTABLE))

# ── Dashboards ────────────────────────────────────────────────────────────────

dashboard-list:  ## List Superset dashboards
	uv run python scripts/dashboards.py list

dashboard-export:  ## Export dashboards to docker/superset/dashboards/
	uv run python scripts/dashboards.py export

dashboard-import:  ## Import dashboards from docker/superset/dashboards/
	uv run python scripts/dashboards.py import

# ── Evidence docs ─────────────────────────────────────────────────────────────
# Evidence turns markdown + SQL into interactive static reports. Dev server at
# http://localhost:3000 once the stack is up. See docs/evidence.md.
#
# Examples:
#   make evidence                          # start just postgres + evidence
#   make evidence-build                    # build static site to evidence/build/
#   make evidence-logs                     # tail the container log
#   make evidence-publish DEST=/tmp/share  # sync build to a directory
#   make evidence-publish DEST=s3://bucket/path/

DEST ?= exports/evidence-build/

evidence:  ## Start just the Evidence service (+ postgres dependency)
	docker compose up -d postgres evidence
	@echo "Evidence available at http://localhost:3000"

evidence-build:  ## Build Evidence static site to evidence/build/
	docker compose run --rm evidence npm run build
	@echo "Built static site at evidence/build/"

evidence-logs:  ## Tail the evidence container logs
	docker compose logs -f evidence

evidence-publish:  ## Sync evidence/build/ to DEST (local dir or s3:// URI)
	@if [ ! -f evidence/build/index.html ]; then \
	    echo "evidence/build missing — running evidence-build first"; \
	    $(MAKE) evidence-build; \
	fi
	@case "$(DEST)" in \
	  s3://*) \
	    command -v aws >/dev/null 2>&1 || { \
	      echo "error: aws CLI not found on PATH; install it or pick a local DEST"; \
	      exit 1; \
	    }; \
	    echo "Publishing to $(DEST) via aws s3 sync"; \
	    aws s3 sync evidence/build/ "$(DEST)" --delete ;; \
	  *) \
	    mkdir -p "$(DEST)"; \
	    echo "Publishing to $(DEST) via rsync"; \
	    rsync -av --delete evidence/build/ "$(DEST)" ;; \
	esac
	@echo "Published to $(DEST)"
