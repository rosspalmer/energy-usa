"""One-off script to inspect EIA state-electricity-profiles/summary API response.

Run from repo root with EIA_API_KEY set:
  uv run python scripts/debug_eia_state_summary.py

Prints the raw API response so we can see structure, keys, and why no rows might be returned.
"""
import asyncio
import json
import os
import sys

# Add src to path so we can import energy_usa
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from energy_usa.config import Settings
from energy_usa.eia.manager import EIAManager


async def main() -> None:
    settings = Settings()
    if not settings.eia_api_key:
        print("Set EIA_API_KEY and re-run.")
        return
    manager = EIAManager(
        base_url=settings.eia_base_url,
        api_key=settings.eia_api_key,
        timeout=settings.eia_ingest_timeout_seconds,
        max_concurrent=2,
        max_retries=1,
    )
    try:
        # 1) Facet endpoint to see available frequency options
        print("=== Summary facet (metadata) ===")
        facet = await manager.get_electricity(
            subpath="state-electricity-profiles/summary/facet",
        )
        # Redact api_key from output
        if "request" in facet and isinstance(facet["request"], dict) and "params" in facet["request"]:
            facet["request"]["params"] = {k: "..." if k == "api_key" else v for k, v in facet["request"]["params"].items()}
        print(json.dumps(facet, indent=2)[:3000])
        print()

        # 2) Data with frequency=annual, start=2024, end=2024
        print("=== Summary data: frequency=annual, start=2024, end=2024 ===")
        data_resp = await manager.get_electricity(
            subpath="state-electricity-profiles/summary/data",
            length=10,
            offset=0,
            frequency="annual",
            start="2024",
            end="2024",
        )
        print("Top-level keys:", list(data_resp.keys()))
        response_body = data_resp.get("response") if "response" in data_resp else data_resp
        if response_body:
            print("response_body keys:", list(response_body.keys()))
            print("total:", response_body.get("total"))
            data = response_body.get("data")
            print("data type:", type(data), "len:", len(data) if isinstance(data, list) else "n/a")
            if data and isinstance(data, list) and len(data) > 0:
                print("first row:", data[0])
            else:
                print("full response (truncated):", json.dumps(data_resp, indent=2)[:2000])
        else:
            print("full response:", json.dumps(data_resp, indent=2)[:2000])
    finally:
        await manager.aclose()


if __name__ == "__main__":
    asyncio.run(main())
