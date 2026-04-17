#!/usr/bin/env bash
# CLI for managing the docker-compose environment: compose, workers, and Prefect job deployment.
# Run from repo root. Uses docker compose (Compose V2).

set -e

COMPOSE_CMD="${COMPOSE_CMD:-docker compose}"
PREFECT_API_URL="${PREFECT_API_URL:-http://localhost:4200/api}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

usage() {
  cat <<EOF
Usage: $0 <command> [options]

Commands:
  up [workers]    Start all services (detached), create work pool, and register deployments.
                  Optional workers = number of prefect-worker replicas (default: 1, or PREFECT_WORKERS)
  down            Stop and remove containers
  restart         Restart all services
  logs [service]   Tail logs (optional: postgres, prefect-server, prefect-worker, jupyter, pgweb)
  ps              List running services
  worker-pool     Create Prefect process work pool (idempotent; run once)
  deploy          Register Prefect ingest deployments (run after worker-pool)
  run <flow>      Trigger a deployment run (e.g. run ingest-eia-electricity-all)
  cancel <id>     Cancel a flow run by ID (use when stuck in AwaitingRetry)
  ensure-ingest-db  Create ingest database and tables (run if you see "database ingest does not exist")

Examples:
  $0 up
  $0 up 3
  PREFECT_WORKERS=4 $0 up
  $0 run ingest-eia-electricity-all
  $0 cancel 1a2b3c4d-5e6f-7890-abcd-ef1234567890
  $0 logs prefect-worker
EOF
}

# Wait for Prefect server API to accept connections (avoids ConnectError when creating work pool).
wait_for_prefect() {
  local url="${PREFECT_API_URL:-http://localhost:4200/api}"
  local max_attempts=30
  local attempt=1
  echo "Waiting for Prefect server at $url..."
  while [ "$attempt" -le "$max_attempts" ]; do
    if curl -s --connect-timeout 2 -o /dev/null "$url" 2>/dev/null; then
      echo "Prefect server ready."
      return 0
    fi
    sleep 2
    attempt=$((attempt + 1))
  done
  echo "Warning: Prefect server did not become ready in time. Work pool create and deploy may fail."
  return 1
}

cmd_up() {
  local workers="${1:-${PREFECT_WORKERS:-1}}"
  $COMPOSE_CMD up -d --scale prefect-worker="$workers" --build
  echo "Stack up (prefect-worker x${workers}). Prefect: http://localhost:4200  Jupyter: http://localhost:8888  pgweb: http://localhost:8080  Superset: http://localhost:8088"
  wait_for_prefect || true
  cmd_worker_pool
  cmd_deploy
}

cmd_down() {
  $COMPOSE_CMD down
}

cmd_restart() {
  $COMPOSE_CMD restart
}

cmd_logs() {
  $COMPOSE_CMD logs -f "${1:-}"
}

cmd_ps() {
  $COMPOSE_CMD ps
}

cmd_worker_pool() {
  echo "Creating process work pool (ignore error if it already exists)..."
  $COMPOSE_CMD run --rm prefect-worker prefect work-pool create process-pool --type process 2>/dev/null || true
  echo "Work pool ready."
}

cmd_deploy() {
  echo "Registering Prefect deployments (PREFECT_API_URL=$PREFECT_API_URL)..."
  PREFECT_API_URL="$PREFECT_API_URL" uv run python scripts/deploy_ingest.py
}

cmd_run() {
  local flow="${1:?Usage: $0 run <flow> [--param key=value ...]}"
  shift
  # deployment name and flow name match in our deploy script.
  # Forward any remaining args (e.g. --param date_start=2020-01) to the prefect CLI.
  echo "Triggering deployment run: $flow/$flow $*"
  PREFECT_API_URL="$PREFECT_API_URL" prefect deployment run "$flow/$flow" "$@"
}

cmd_cancel() {
  local run_id="${1:?Usage: $0 cancel <flow-run-id>}"
  echo "Cancelling flow run: $run_id"
  PREFECT_API_URL="${PREFECT_API_URL}" prefect flow-run cancel "$run_id"
}

cmd_ensure_ingest_db() {
  echo "Creating ingest database and tables (idempotent)..."
  $COMPOSE_CMD exec postgres bash -c '
    export PGPASSWORD="$POSTGRES_PASSWORD"
    psql -U "$POSTGRES_USER" -d postgres -c "CREATE DATABASE ingest;" 2>/dev/null || true
    psql -U "$POSTGRES_USER" -d postgres -c "CREATE DATABASE transform;" 2>/dev/null || true
    find /docker-entrypoint-initdb.d/ingest -name "*.sql" | sort | while read f; do
      psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d ingest -f "$f"
    done
    echo "Ingest database ready."
  '
}

subcommand="${1:-}"
shift || true
case "$subcommand" in
  up)        cmd_up "$@" ;;
  down)      cmd_down ;;
  restart)   cmd_restart ;;
  logs)     cmd_logs "$@" ;;
  ps)       cmd_ps ;;
  worker-pool) cmd_worker_pool ;;
  deploy)   cmd_deploy ;;
  run)      cmd_run "$@" ;;
  cancel)   cmd_cancel "$@" ;;
  ensure-ingest-db) cmd_ensure_ingest_db ;;
  -h|--help|help|"") usage ;;
  *)        echo "Unknown command: $subcommand"; usage; exit 1 ;;
esac
