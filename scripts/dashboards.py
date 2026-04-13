#!/usr/bin/env -S uv run python
"""Export and import Superset dashboards for version control.

Usage:
    uv run python scripts/dashboards.py export
    uv run python scripts/dashboards.py import
    uv run python scripts/dashboards.py list

Dashboards are exported as ZIP files to docker/superset/dashboards/.
Requires the Superset stack to be running (make up).
"""
import argparse
import sys
from pathlib import Path

import httpx

SUPERSET_URL = "http://localhost:8088"
DASHBOARDS_DIR = Path("docker/superset/dashboards")


def _get_session() -> httpx.Client:
    client = httpx.Client(base_url=SUPERSET_URL, timeout=30.0)
    resp = client.post("/api/v1/security/login", json={
        "username": "admin",
        "password": "admin",
        "provider": "db",
    })
    if resp.status_code != 200:
        print(f"ERROR: Login failed ({resp.status_code}). Is Superset running?")
        sys.exit(1)
    token = resp.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return client


def cmd_list(args):
    client = _get_session()
    resp = client.get("/api/v1/dashboard/", params={"page_size": 100})
    dashboards = resp.json().get("result", [])
    if not dashboards:
        print("No dashboards found.")
        return
    print(f"{'ID':<6} {'Title':<40} {'Status':<12} Charts")
    print("-" * 70)
    for d in dashboards:
        title = d.get("dashboard_title", "Untitled")
        status = d.get("status", "draft")
        chart_count = len(d.get("charts", []))
        print(f"{d['id']:<6} {title:<40} {status:<12} {chart_count}")


def cmd_export(args):
    client = _get_session()
    resp = client.get("/api/v1/dashboard/", params={"page_size": 100})
    dashboards = resp.json().get("result", [])
    if not dashboards:
        print("No dashboards to export.")
        return

    DASHBOARDS_DIR.mkdir(parents=True, exist_ok=True)
    ids = [d["id"] for d in dashboards]
    export_resp = client.get("/api/v1/dashboard/export/", params={"q": ids})
    if export_resp.status_code != 200:
        print(f"ERROR: Export failed ({export_resp.status_code})")
        sys.exit(1)

    out_path = DASHBOARDS_DIR / "dashboards_export.zip"
    out_path.write_bytes(export_resp.content)
    print(f"Exported {len(ids)} dashboard(s) to {out_path}")


def cmd_import(args):
    zip_path = DASHBOARDS_DIR / "dashboards_export.zip"
    if not zip_path.exists():
        print(f"ERROR: No export file at {zip_path}")
        print("Run 'make dashboard-export' first.")
        sys.exit(1)

    client = _get_session()
    with open(zip_path, "rb") as f:
        resp = client.post(
            "/api/v1/dashboard/import/",
            files={"formData": ("dashboards_export.zip", f, "application/zip")},
            data={"overwrite": "true"},
        )
    if resp.status_code == 200:
        print(f"Imported dashboards from {zip_path}")
    else:
        print(f"ERROR: Import failed ({resp.status_code}): {resp.text[:200]}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Manage Superset dashboards")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list", help="List dashboards")
    sub.add_parser("export", help="Export dashboards to docker/superset/dashboards/")
    sub.add_parser("import", help="Import dashboards from docker/superset/dashboards/")

    args = parser.parse_args()
    {"list": cmd_list, "export": cmd_export, "import": cmd_import}[args.command](args)


if __name__ == "__main__":
    main()
