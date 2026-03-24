"""Upsert EIA International into ingest.eia_international.

Annual international energy production/consumption/trade by country and product.
Period stored as DATE (Jan 1 of year).
Unique key: (period, activity_id, product_id, country_region_id, unit).
"""

from typing import Any

import psycopg

from energy_usa.db.period import normalize_period


def upsert_international(conn: psycopg.Connection, rows: list[dict[str, Any]]) -> int:
    """Upsert EIA international energy rows.

    :param conn: Open psycopg connection.
    :param rows: List of dicts with EIA international keys.
    :returns: Number of rows upserted.
    """
    if not rows:
        return 0
    sql = """
    INSERT INTO ingest.eia_international
        (period, activity_id, activity_name, product_id, product_name,
         country_region_id, country_region_name, unit, value, ingested_at)
    VALUES
        (%(period)s, %(activity_id)s, %(activity_name)s, %(product_id)s, %(product_name)s,
         %(country_region_id)s, %(country_region_name)s, %(unit)s, %(value)s, now())
    ON CONFLICT (period, activity_id, product_id, country_region_id, unit)
    DO UPDATE SET
        activity_name = EXCLUDED.activity_name,
        product_name = EXCLUDED.product_name,
        country_region_name = EXCLUDED.country_region_name,
        value = EXCLUDED.value,
        ingested_at = now()
    """
    normalized = []
    for r in rows:
        period_date = normalize_period(r.get("period"), "yearly")
        if period_date is None:
            continue
        normalized.append({
            "period": period_date,
            "activity_id": r.get("activityId") or r.get("activity_id") or r.get("activity") or "NA",
            "activity_name": r.get("activityName") or r.get("activity_name"),
            "product_id": r.get("productId") or r.get("product_id") or r.get("product") or "NA",
            "product_name": r.get("productName") or r.get("product_name"),
            "country_region_id": r.get("countryRegionId") or r.get("country_region_id") or r.get("countryId") or "WORL",
            "country_region_name": r.get("countryRegionName") or r.get("country_region_name") or r.get("countryName"),
            "unit": r.get("unit") or r.get("units") or "NA",
            "value": r.get("value"),
        })
    if not normalized:
        return 0
    with conn.cursor() as cur:
        cur.executemany(sql, normalized)
    conn.commit()
    return len(normalized)
