
Here’s what you need to start the project and build the core multithreaded API call manager.

---

## 1. Starting the Python project with `uv`

**One-time setup:**

- **Create the project** (from repo root):
  - `uv init` – creates `pyproject.toml` and a default package layout, or  
  - `uv project init` – same idea; use whichever your `uv` version supports.

- **Add dependencies** (examples; adjust names if your `uv` uses different commands):
  - `uv add fastapi uvicorn[standard]`
  - `uv add httpx` – for calling the EIA API (async-friendly).
  - Optional: `uv add python-dotenv` for config, `pydantic-settings` for typed settings.

- **EIA API key**  
  EIA API v2 requires an API key. Get one from [EIA’s registration page](https://www.eia.gov/opendata/register.php) and keep it out of code (env vars or secrets).

**Resulting layout (conceptual):**

- `pyproject.toml` – project metadata and dependencies.
- `src/energy_usa/` (or a single `app/`) – package root.
- `src/energy_usa/main.py` – FastAPI app and `uvicorn` entrypoint.

---

## 2. Basic FastAPI service framework

You’ll need:

- **App entrypoint** – `FastAPI()` instance, include routers, run with `uvicorn ...:app`.
- **Routers** – e.g. `routers/` for “live/historical data” endpoints that will use the EIA manager.
- **Config** – base URL for EIA API v2, API key, timeouts, concurrency limits (from env or `pydantic-settings`).
- **Health/readiness** – e.g. `GET /health` that doesn’t call EIA; useful for Docker/load balancers.

No database or UI needed for this first step; focus on the API and the manager that will back it.

---

## 3. Core multithreaded API call manager (from PROJECT.md)

PROJECT.md asks for a **multithreaded API call manager** that makes connections to EIA for:

- `/electricity`
- `/natural-gas`
- `/petroleum`
- `/coal`
- `/total-energy`

Below is a design that fits that and the EIA API doc you have.

### Responsibilities of the manager

1. **Single place** that talks to the EIA API (v2 base URL + path, API key in headers).
2. **Concurrency control** – “multithreaded” can mean:
   - **Thread pool**: `concurrent.futures.ThreadPoolExecutor` with a fixed max workers (e.g. 4–8) so you don’t overwhelm EIA or open too many connections.
   - **Async alternative**: `asyncio` + `httpx.AsyncClient` with a limit on concurrent requests (same idea, often better for many small I/O-bound calls). FastAPI is async, so an async client fits well.
3. **Rate limiting** – EIA may have rate limits; the manager should throttle (e.g. max N requests per second or a simple queue).
4. **Retries** – transient failures (timeouts, 5xx); backoff (e.g. exponential) and a max number of retries.
5. **Timeouts** – on every request so a hung call doesn’t block the pool.
6. **Route abstraction** – one method per EIA “route” (electricity, natural_gas, petroleum, coal, total_energy) that builds the correct path and query params (and optionally facets), so the rest of the app doesn’t deal with URLs.

### Suggested layout

- **`eia_client.py`** (or `eia/client.py`)  
  - Holds base URL, API key, timeouts.  
  - Defines methods like `get_electricity(...)`, `get_natural_gas(...)`, etc., each building path and query params and calling the core fetcher.

- **`api_call_manager.py`** (or `eia/manager.py`)  
  - **If thread-based**: uses a `ThreadPoolExecutor`; `submit()` or `map()` to run `eia_client` calls; you can add a small wrapper that applies rate limiting (e.g. a token bucket or a queue that releases one request per interval).  
  - **If async**: uses an `httpx.AsyncClient` (or similar) with a semaphore or a bounded queue to cap concurrency; the same `eia_client` methods would be `async` and use that client.  
  - This layer handles retries, timeouts, and (optionally) logging or metrics.

- **FastAPI integration**  
  - Depends on the manager (or the EIA client) via a dependency (e.g. `get_api_manager()` that returns the shared manager instance).  
  - Endpoints call the manager’s methods (e.g. “get electricity data for these params”) and return the parsed response (or a transformed subset).

### EIA API v2 details to respect

From your API doc:

- **Hierarchy** – parent routes like `/electricity`, `/natural-gas`, etc.; you may need to discover or hardcode child dataset paths (e.g. retail sales under electricity).
- **Facets** – query params like `facets[stateid]=NY`, `facets[sectorid]=RES`; the manager or client should accept these and pass them through.
- **Pagination** – `length` (e.g. up to 5,000 rows), `offset`, `sort`; the manager can accept these and forward to the client so callers can page.

So “what’s needed” for the manager is: **config (base URL, key, limits)** + **concurrency (thread pool or async + semaphore)** + **retries/timeouts** + **route-oriented methods** that speak EIA v2 (paths + facets + pagination).

---

## 4. Minimal dependency list (for `pyproject.toml`)

- `fastapi`
- `uvicorn[standard]`
- `httpx` (for EIA calls; use async if you go async)
- Optional: `python-dotenv`, `pydantic-settings`

You don’t need a database or front-end stack to build and test the multithreaded API call manager; that can come later per PROJECT.md.

---

## 5. Order of work

1. **`uv init`** (or `uv project init`) and add the dependencies above.  
2. **Config** – env vars for EIA base URL and API key; load in the app and in the manager.  
3. **EIA client** – base URL + key, one method per EIA route (electricity, natural_gas, petroleum, coal, total_energy), with path and query params (facets, length, offset).  
4. **API call manager** – thread pool (or async) + concurrency limit + retries + timeouts; calls into the EIA client.  
5. **FastAPI app** – create app, wire a “data” router that depends on the manager and exposes endpoints that delegate to the manager.  
6. **Run** – `uv run uvicorn energy_usa.main:app --reload` (adjust module path to your layout).

If you want, next step can be a concrete sketch of `eia_client` and `api_call_manager` (e.g. function signatures and where threads/async and retries go) tailored to your chosen threading vs async approach. I'm in **Ask mode**, so I can only outline and suggest code; if you switch to **Agent mode**, I can add the files and wiring in your repo.