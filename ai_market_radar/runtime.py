from __future__ import annotations

import json
import time
from contextlib import contextmanager
from typing import Any, Iterator

from ai_market_radar.postgres import PostgresConnectionFactory


class AdvisoryLockError(RuntimeError):
    pass


class RunnerRuntime:
    def __init__(self, connection_factory: PostgresConnectionFactory) -> None:
        self.connection_factory = connection_factory

    @contextmanager
    def advisory_lock(self, lock_key: int) -> Iterator[None]:
        with self.connection_factory.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("select pg_try_advisory_lock(%s)", (lock_key,))
                locked = cur.fetchone()[0]
                if not locked:
                    raise AdvisoryLockError(f"Runner already active for lock {lock_key}")
            try:
                yield
            finally:
                with conn.cursor() as cur:
                    cur.execute("select pg_advisory_unlock(%s)", (lock_key,))

    @contextmanager
    def transaction(self) -> Iterator[Any]:
        with self.connection_factory.connection() as conn:
            yield conn


def json_dumps(payload: dict[str, Any] | None) -> str:
    return json.dumps(payload or {})


@contextmanager
def timed() -> Iterator[list[float]]:
    marker = [time.monotonic()]
    yield marker
    marker.append(time.monotonic() - marker[0])
