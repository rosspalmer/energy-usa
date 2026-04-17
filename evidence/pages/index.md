---
title: Energy USA — Data Reports
---

Narrative reports backed by the Energy USA transform database. These pages
are hand-authored markdown with embedded SQL — every number and chart on
every page refreshes the moment the underlying data changes.

## Reports

- [State Monthly Electricity Balance](/electricity/state-monthly-balance) —
  generation, trade, and consumption for a single state, month by month.
  Filterable by state and date range.

## Adding a report

See [docs/evidence.md](https://github.com/) for the workflow. Short version:
copy an existing page in `evidence/pages/`, rewrite the SQL queries and
narrative, and save — the dev server hot-reloads automatically.