# Documentation

Guides for setting up, running, and analyzing data with Energy USA.

Each doc is written for **both** audiences — it starts with a plain-English explanation of what something does and why, then goes into technical details and code examples.

## Guides

| Guide | What it covers |
|-------|---------------|
| [Getting Started](getting-started.md) | First-time setup: installing prerequisites, configuring your environment, starting the stack, and running your first data load |
| [Running Ingest](ingest-flows.md) | How EIA data gets into the database — local debugging vs Prefect, backfilling historical data, understanding what each dataset contains |
| [Analyzing Data](data-analysis.md) | Querying the database with DBeaver, writing Python in Jupyter, using Claude AI for analysis, and exporting data |
| [Building Dashboards](dashboards.md) | Creating Superset dashboards, using saved queries, version control, and the interactive visualize workflow |
| [Proxmox Deployment](../deploy/proxmox/README.md) | Step-by-step guide for deploying to a Proxmox on-prem server |
| [Architecture Design Spec](superpowers/specs/2026-04-10-markdown-driven-data-platform-design.md) | Architecture spec for the layered data platform (ingest → quality → transform) |

## Quick reference

```bash
make help              # All available commands

make backfill DATASET=retail_sales START=2020-01 END=2024-12   # Load historical data
make export TABLE=eia.retail_sales OUT=exports/retail.csv       # Export to CSV
make jupyter           # Start Jupyter Lab locally
```
