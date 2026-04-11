#!/bin/bash
# Run SQL files for the ingest and transform databases.
# Walks subdirectories recursively. Within each directory, 00-*.sql files run
# first (schema creation), then the rest in alphabetical order.
set -e

PG_USER="${POSTGRES_USER:-postgres}"
INIT_DIR="/docker-entrypoint-initdb.d"

run_sql_dir() {
  local db="$1"
  local dir="$2"
  [ -d "$dir" ] || return 0

  # Run 00-*.sql files first (schema setup)
  for f in "$dir"/00-*.sql; do
    [ -f "$f" ] || continue
    echo "  [$db] $f"
    psql -v ON_ERROR_STOP=1 -U "$PG_USER" -d "$db" -f "$f"
  done

  # Run remaining SQL files (skip 00-*)
  for f in "$dir"/*.sql; do
    [ -f "$f" ] || continue
    case "$(basename "$f")" in 00-*) continue ;; esac
    echo "  [$db] $f"
    psql -v ON_ERROR_STOP=1 -U "$PG_USER" -d "$db" -f "$f"
  done

  # Recurse into subdirectories
  for subdir in "$dir"/*/; do
    [ -d "$subdir" ] || continue
    run_sql_dir "$db" "$subdir"
  done
}

echo "=== Initializing ingest database ==="
run_sql_dir "ingest" "$INIT_DIR/ingest"

echo "=== Initializing transform database ==="
run_sql_dir "transform" "$INIT_DIR/transform"

echo "=== Database initialization complete ==="
