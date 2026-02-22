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
  logs [service]   Tail logs (optional: postgres, prefect-server, prefect-worker, pgweb, web)
  ps              List running services
  worker-pool     Create Prefect process work pool (idempotent; run once)
  deploy          Register Prefect ingest deployments (run after worker-pool)
  run <flow>      Trigger a deployment run (e.g. run ingest-eia-electricity-all)

Examples:
  $0 up
  $0 up 3
  PREFECT_WORKERS=4 $0 up
  $0 run ingest-eia-electricity-all
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
  $COMPOSE_CMD up -d --scale prefect-worker="$workers"
  echo "Stack up (prefect-worker x${workers}). Web: http://localhost:8000  Prefect: http://localhost:4200  pgweb: http://localhost:8080"
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
  local flow="${1:-ingest-eia-electricity-all}"
  # deployment name and flow name match in our deploy script
  echo "Triggering deployment run: $flow/$flow"
  PREFECT_API_URL="$PREFECT_API_URL" prefect deployment run "$flow/$flow"
}

case "${1:-}" in
  up)        cmd_up "$2" ;;
  down)      cmd_down ;;
  restart)   cmd_restart ;;
  logs)     cmd_logs "$2" ;;
  ps)       cmd_ps ;;
  worker-pool) cmd_worker_pool ;;
  deploy)   cmd_deploy ;;
  run)      cmd_run "$2" ;;
  -h|--help|help|"") usage ;;
  *)        echo "Unknown command: $1"; usage; exit 1 ;;
esac
