"""Upsert EIA petroleum/pri/gnd into eia.petroleum_prices.

Weekly retail gasoline and diesel prices by area and product.
Period stored as DATE. Unique key: (period, series).
"""

from typing import Any

import psycopg

from energy_usa.db.period import normalize_period, safe_numeric


def upsert_petroleum_prices(conn: psycopg.Connection, rows: list[dict[str, Any]]) -> int:
    """Upsert EIA petroleum retail price rows.

    :param conn: Open psycopg connection.
    :param rows: List of dicts with EIA petroleum/pri/gnd keys.
    :returns: Number of rows upserted.
    """
    if not rows:
        return 0
    sql = """
    INSERT INTO eia.petroleum_prices
        (period, duoarea, area_name, product, product_name,
         process, process_name, series, series_description, value, units, ingested_at)
    VALUES
        (%(period)s, %(duoarea)s, %(area_name)s, %(product)s, %(product_name)s,
         %(process)s, %(process_name)s, %(series)s, %(series_description)s,
         %(value)s, %(units)s, now())
    ON CONFLICT (period, series)
    DO UPDATE SET
        duoarea = EXCLUDED.duoarea,
        area_name = EXCLUDED.area_name,
        product = EXCLUDED.product,
        product_name = EXCLUDED.product_name,
        process = EXCLUDED.process,
        process_name = EXCLUDED.process_name,
        series_description = EXCLUDED.series_description,
        value = EXCLUDED.value,
        units = EXCLUDED.units,
        ingested_at = now()
    """
    normalized = []
    for r in rows:
        period_date = normalize_period(r.get("period"), "daily")
        if period_date is None:
            continue
        normalized.append({
            "period": period_date,
            "duoarea": r.get("duoarea") or r.get("area") or "NA",
            "area_name": r.get("area-name") or r.get("areaName") or r.get("area_name"),
            "product": r.get("product") or r.get("productId") or "NA",
            "product_name": r.get("product-name") or r.get("productName") or r.get("product_name"),
            "process": r.get("process") or r.get("processId") or "NA",
            "process_name": r.get("process-name") or r.get("processName") or r.get("process_name"),
            "series": r.get("series") or r.get("seriesId") or "NA",
            "series_description": r.get("series-description") or r.get("seriesDescription") or r.get("series_description"),
            "value": safe_numeric(r.get("value")),
            "units": r.get("units") or r.get("unit"),
        })
    if not normalized:
        return 0
    with conn.cursor() as cur:
        cur.executemany(sql, normalized)
    conn.commit()
    return len(normalized)
