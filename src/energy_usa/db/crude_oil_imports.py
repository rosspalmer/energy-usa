"""Upsert EIA crude-oil-imports into ingest.eia_crude_oil_imports.

Monthly crude oil imports by origin, destination, grade, and refiner type.
Period stored as DATE (first of month). Unique key: (period, origin_id, destination_id, grade_id, refiner_type).
"""

from typing import Any

import psycopg

from energy_usa.db.period import normalize_period


def upsert_crude_oil_imports(conn: psycopg.Connection, rows: list[dict[str, Any]]) -> int:
    """Upsert EIA crude oil import rows.

    :param conn: Open psycopg connection.
    :param rows: List of dicts with EIA crude-oil-imports keys.
    :returns: Number of rows upserted.
    """
    if not rows:
        return 0
    sql = """
    INSERT INTO ingest.eia_crude_oil_imports
        (period, origin_id, origin_name, destination_id, destination_name,
         grade_id, grade_name, refiner_type, quantity, quantity_units, ingested_at)
    VALUES
        (%(period)s, %(origin_id)s, %(origin_name)s, %(destination_id)s, %(destination_name)s,
         %(grade_id)s, %(grade_name)s, %(refiner_type)s, %(quantity)s, %(quantity_units)s, now())
    ON CONFLICT (period, origin_id, destination_id, grade_id, refiner_type)
    DO UPDATE SET
        origin_name = EXCLUDED.origin_name,
        destination_name = EXCLUDED.destination_name,
        grade_name = EXCLUDED.grade_name,
        quantity = EXCLUDED.quantity,
        quantity_units = EXCLUDED.quantity_units,
        ingested_at = now()
    """
    normalized = []
    for r in rows:
        period_date = normalize_period(r.get("period"), "monthly")
        if period_date is None:
            continue
        normalized.append({
            "period": period_date,
            "origin_id": r.get("originId") or r.get("origin_id") or r.get("originCode") or "UNK",
            "origin_name": r.get("originName") or r.get("origin_name"),
            "destination_id": r.get("destinationId") or r.get("destination_id") or r.get("destinationCode") or "UNK",
            "destination_name": r.get("destinationName") or r.get("destination_name"),
            "grade_id": r.get("gradeId") or r.get("grade_id") or r.get("gradeCode") or "UNK",
            "grade_name": r.get("gradeName") or r.get("grade_name"),
            "refiner_type": r.get("refinerType") or r.get("refiner_type") or r.get("refinerTypeId") or "UNK",
            "quantity": r.get("quantity"),
            "quantity_units": r.get("quantity-units") or "thousand barrels",
        })
    if not normalized:
        return 0
    with conn.cursor() as cur:
        cur.executemany(sql, normalized)
    conn.commit()
    return len(normalized)
