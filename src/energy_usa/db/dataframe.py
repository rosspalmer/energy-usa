"""Load SQL query results from Postgres into a Pandas DataFrame."""

from typing import Any

from energy_usa.db.retail_sales import get_connection


def query_to_dataframe(
    database_url: str,
    sql: str,
    params: dict[str, Any] | None = None,
):
    """Execute a parameterized SQL query and return the result as a DataFrame.

    Uses a short-lived connection; suitable for read-only queries in notebooks
    or scripts. Prefer parameterized SQL (e.g. ``%(name)s``) and pass values
    via ``params`` to avoid injection.

    :param database_url: PostgreSQL connection URL (e.g. postgresql://user:pass@host:5432/db).
    :param sql: SQL query string; use ``%(key)s`` placeholders when passing ``params``.
    :param params: Optional dict of parameters for the query.
    :returns: A pandas DataFrame of the query result.
    """
    import pandas as pd

    with get_connection(database_url) as conn:
        return pd.read_sql_query(sql, conn, params=params)
