"""Native PostgreSQL connections; all queries use psycopg placeholders."""
from datetime import date, datetime

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import JsonbLoader


class JSONTextLoader(JsonbLoader):
    """Keep repository payloads serialized until their boundary mapping."""
    def load(self, data):
        return bytes(data).decode("utf-8")


def record_row(cursor):
    factory = dict_row(cursor)

    def normalize(values):
        row = factory(values)
        return {key: value.isoformat() if isinstance(value, (date, datetime)) else value for key, value in row.items()}
    return normalize


class Connection(psycopg.Connection):
    def executemany(self, query, params):
        cursor = self.cursor()
        cursor.executemany(query, params)
        return cursor


def connect(database_url: str):
    dsn = database_url.replace("postgresql+psycopg://", "postgresql://", 1)
    connection = Connection.connect(dsn, row_factory=record_row, options="-csearch_path=homate,public")
    connection.adapters.register_loader("jsonb", JSONTextLoader)
    return connection
