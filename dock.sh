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
  up              Start all services (detached)
  down            Stop and remove containers
  restart         Restart all services
  logs [service]   Tail logs (optional: postgres, prefect-server, prefect-worker, api, pgweb)
  ps              List running services
  worker-pool     Create Prefect process work pool (idempotent; run once)
  deploy          Register Prefect ingest deployments (run after worker-pool)
  run <flow>      Trigger a deployment run (e.g. run ingest-eia-electricity-all)

Examples:
  $0 up
  $0 worker-pool && $0 deploy
  $0 run ingest-eia-electricity-all
  $0 logs prefect-worker
EOF
}

cmd_up() {
  $COMPOSE_CMD up -d
  echo "Stack up. API: http://localhost:8000  Prefect: http://localhost:4200  pgweb: http://localhost:8080"
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
  up)        cmd_up ;;
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
