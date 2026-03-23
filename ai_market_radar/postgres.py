from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Iterator


class PostgresNotAvailableError(RuntimeError):
    pass


def _import_driver() -> Any:
    try:
        import psycopg  # type: ignore

        return psycopg
    except ImportError:
        try:
            import psycopg2  # type: ignore

            return psycopg2
        except ImportError as exc:
            raise PostgresNotAvailableError(
                "Postgres driver not installed. Install `psycopg` or `psycopg2` to use repository adapters."
            ) from exc


def get_database_url() -> str:
    database_url = os.getenv("AI_MARKET_RADAR_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not database_url:
        raise PostgresNotAvailableError(
            "Set AI_MARKET_RADAR_DATABASE_URL or DATABASE_URL before running Postgres-backed runners."
        )
    return database_url


class PostgresConnectionFactory:
    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url or get_database_url()
        self.driver = _import_driver()

    def connect(self) -> Any:
        return self.driver.connect(self.database_url)

    @contextmanager
    def connection(self) -> Iterator[Any]:
        conn = self.connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
