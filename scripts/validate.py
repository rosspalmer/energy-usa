#!/usr/bin/env -S uv run python
"""CLI for running validation flows and viewing audit results."""
import argparse
import sys

from energy_usa.config import Settings
from energy_usa.db.connection import get_connection


def cmd_run(args):
    from energy_usa.flows.validate.eia import validate_eia
    datasets = [args.dataset] if args.dataset else None
    summary = validate_eia(datasets=datasets)
    total = summary.get("total", sum(v for k, v in summary.items() if k in ("pass", "fail", "warn", "error")))
    print(f"\nValidation complete: {total} checks")
    for status in ("pass", "fail", "warn", "error"):
        count = summary.get(status, 0)
        if count > 0:
            print(f"  {status}: {count}")
    if summary.get("fail", 0) > 0:
        sys.exit(1)


def cmd_audit(args):
    settings = Settings()
    conn = get_connection(settings.ingest_database_url)
    try:
        if args.dataset:
            sql = """
            SELECT ar.rule_id, ar.status, ar.detail, ar.checked_at
            FROM quality.audit_results ar
            JOIN quality.audit_rules rl ON ar.rule_id = rl.rule_id
            WHERE rl.source = %(source)s AND rl.dataset = %(dataset)s
            ORDER BY ar.checked_at DESC LIMIT 50
            """
            params = {"source": args.source, "dataset": args.dataset}
        else:
            sql = """
            SELECT rl.dataset,
                   count(*) FILTER (WHERE ar.status = 'pass') AS pass,
                   count(*) FILTER (WHERE ar.status = 'fail') AS fail,
                   count(*) FILTER (WHERE ar.status = 'warn') AS warn,
                   count(*) FILTER (WHERE ar.status = 'error') AS error,
                   max(ar.checked_at) AS last_run
            FROM quality.audit_results ar
            JOIN quality.audit_rules rl ON ar.rule_id = rl.rule_id
            WHERE rl.source = %(source)s
            GROUP BY rl.dataset ORDER BY rl.dataset
            """
            params = {"source": args.source}

        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()

        if not rows:
            print("No audit results found.")
            return

        if args.dataset:
            for row in rows:
                print(f"  [{row['status'].upper()}] {row['rule_id']}  {row['detail'] or ''}")
        else:
            print(f"{'Dataset':<30} {'Pass':>5} {'Fail':>5} {'Warn':>5} {'Error':>6}  Last Run")
            print("-" * 85)
            for row in rows:
                print(f"{row['dataset']:<30} {row['pass']:>5} {row['fail']:>5} {row['warn']:>5} {row['error']:>6}  {row['last_run']}")
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Run validation and view audit results")
    sub = parser.add_subparsers(dest="command", required=True)
    run_p = sub.add_parser("run", help="Run validation checks")
    run_p.add_argument("--source", default="eia")
    run_p.add_argument("--dataset", help="Single dataset (optional)")
    audit_p = sub.add_parser("audit", help="View audit results")
    audit_p.add_argument("--source", default="eia")
    audit_p.add_argument("--dataset", help="Single dataset (optional)")
    args = parser.parse_args()
    {"run": cmd_run, "audit": cmd_audit}[args.command](args)

if __name__ == "__main__":
    main()
