"""Prefect flow: run all EIA electricity dataset ingests as subflows.

Runs ingest_eia_retail_sales, ingest_eia_electric_power_operational, and
ingest_eia_state_source_disposition. Each runs as a child flow run.
Requires EIA_API_KEY and DATABASE_URL.
"""

from prefect import flow
from prefect.logging import get_run_logger

from energy_usa.config import Settings
from energy_usa.flows.eia_electric_power_operational import ingest_eia_electric_power_operational
from energy_usa.flows.eia_retail_sales import ingest_eia_retail_sales
from energy_usa.flows.eia_state_source_disposition import ingest_eia_state_source_disposition


@flow(name="ingest-eia-electricity-all", retries=2)
async def ingest_eia_electricity_all() -> dict[str, int]:
    """Run all EIA electricity ingests (retail-sales, electric-power-operational, source-disposition).

    Each dataset ingest runs as a subflow. Returns a summary of rows upserted per dataset.

    :returns: Dict mapping dataset name to rows upserted.
    """
    logger = get_run_logger()
    settings = Settings()
    if not settings.eia_api_key:
        raise ValueError("EIA_API_KEY is required for ingest_eia_electricity_all")
    if not settings.database_url:
        raise ValueError("DATABASE_URL is required for ingest_eia_electricity_all")

    retail = await ingest_eia_retail_sales()
    operational = await ingest_eia_electric_power_operational()
    source_disp = await ingest_eia_state_source_disposition()

    summary = {
        "retail_sales": retail,
        "electric_power_operational": operational,
        "state_source_disposition": source_disp,
    }
    logger.info("Ingest all complete: %s", summary)
    return summary
