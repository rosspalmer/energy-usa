"""Shared database connection helper for all layers."""

import psycopg
from psycopg.rows import dict_row


def get_connection(database_url: str) -> psycopg.Connection:
    """Open a sync connection to Postgres with dict row factory.

    :param database_url: PostgreSQL connection URL.
    :returns: An open connection; caller must close it.
    """
    return psycopg.connect(database_url, row_factory=dict_row)
