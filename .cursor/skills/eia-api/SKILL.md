---
name: eia-api
description: Queries the EIA Open Data API v2 (electricity, natural-gas, petroleum, coal, total-energy) with facets and pagination. Use when the user asks about EIA data, the EIA API, energy data API, api.eia.gov, or when implementing or changing the EIA client or data routes in this project.
---

# EIA Open Data API

## When to use this skill

Apply this skill when:

- The user asks about EIA data, the EIA API, energy data from EIA, or `api.eia.gov`
- Implementing or changing EIA client code, data routes, or API call logic
- Looking up EIA v2 endpoints, parameters, or response shapes

## Quick reference

- **Base URL:** `https://api.eia.gov/v2`
- **Authentication:** API key required. Pass as query parameter `api_key` (per EIA docs). Get a key from [EIA Open Data registration](https://www.eia.gov/opendata/register.php).
- **Routes:** `/electricity`, `/natural-gas`, `/petroleum`, `/coal`, `/total-energy`, with optional subpaths (e.g. `electricity/retail-sales/data`).
- **Parameters:** `length` (max 5000), `offset`, `sort`, and facet filters (e.g. `facets[stateid]=NY`, `facets[sectorid]=RES`). JSON is the default response format.

## Full API specification

For exact endpoints, parameters, and response shapes, read [eia-api-swagger.yaml](eia-api-swagger.yaml) in this skill directory.

**Canonical source:** [https://www.eia.gov/opendata/eia-api-swagger.zip](https://www.eia.gov/opendata/eia-api-swagger.zip). Download and replace the YAML in this skill periodically for the latest API documentation.

## This project

- Prefer the existing **EIAClient** and **EIAManager** in `src/energy_usa/eia/client.py` and `src/energy_usa/eia/manager.py` for EIA calls.
- Config (base URL, API key, timeouts) is in `src/energy_usa/config.py`; set `EIA_API_KEY` in the environment.
- Use the OpenAPI spec when adding new routes, subpaths, or parameters not yet supported by the client.
