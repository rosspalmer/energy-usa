# Data Product Specs

Markdown specifications that drive code generation. Each layer has its own
directory, format, and automation level.

| Layer | Automation | Directory | What Claude does |
|-------|-----------|-----------|-----------------|
| Ingest | A (full generation) | `ingest/` | Reads spec, runs generator, produces all code |
| Validate | A (full generation) | `validate/` | Generates validation flows and audit rules |
| Transform | B (scaffold + fill) | `transform/` | Generates skeleton, fills business logic with review |
| Visualize | C (interactive) | `visualize/` | Reads spec as conversation starter, builds interactively |

## Quick Start

```bash
# Generate ingest code for all EIA datasets
make generate-ingest SOURCE=eia

# Generate a single dataset
make generate-ingest SOURCE=eia GDATASET=retail_sales
```

## Spec Format Reference

Each `_template.md` file in a layer's directory shows the expected format
with comments explaining each field. Copy it to create a new spec.

## Design Spec

See `docs/superpowers/specs/2026-04-10-markdown-driven-data-platform-design.md`
for the full architecture and rationale.
