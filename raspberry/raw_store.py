"""SQLite persistence for immutable RAW attendance marks."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RawMark:
    """A RAW RFID/NFC attendance mark stored locally before synchronization."""

    id: int
    tag_uid: str
    worker_id: str | None
    device_id: str
    obra: str
    marked_at: str
    synced: bool
    sync_attempts: int
    last_sync_error: str | None
    created_at: str


class RawStore:
    """Stores RAW marks in SQLite and tracks synchronization state."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS raw_marks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tag_uid TEXT NOT NULL,
                    worker_id TEXT,
                    device_id TEXT NOT NULL,
                    obra TEXT NOT NULL,
                    marked_at TEXT NOT NULL,
                    synced INTEGER NOT NULL DEFAULT 0,
                    sync_attempts INTEGER NOT NULL DEFAULT 0,
                    last_sync_error TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_raw_marks_pending
                ON raw_marks (synced, id)
                """
            )

    def add_mark(
        self,
        *,
        tag_uid: str,
        worker_id: str | None,
        device_id: str,
        obra: str,
        marked_at: datetime | None = None,
    ) -> RawMark:
        """Persist a new RAW mark and return it."""

        now = datetime.now(UTC)
        effective_marked_at = marked_at or now
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO raw_marks (
                    tag_uid, worker_id, device_id, obra, marked_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    tag_uid,
                    worker_id,
                    device_id,
                    obra,
                    _to_iso(effective_marked_at),
                    _to_iso(now),
                ),
            )
            mark_id = int(cursor.lastrowid)
        return self.get_mark(mark_id)

    def get_mark(self, mark_id: int) -> RawMark:
        """Return a RAW mark by id."""

        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM raw_marks WHERE id = ?",
                (mark_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"RAW mark not found: {mark_id}")
        return _row_to_mark(row)

    def list_pending(self, *, limit: int = 100) -> list[RawMark]:
        """Return unsynchronized marks ordered by insertion id."""

        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM raw_marks WHERE synced = 0 ORDER BY id ASC LIMIT ?",
                (limit,),
            ).fetchall()
        return [_row_to_mark(row) for row in rows]

    def mark_synced(self, mark_id: int) -> None:
        """Mark a RAW entry as synchronized."""

        with self._connect() as connection:
            connection.execute(
                """
                UPDATE raw_marks
                SET synced = 1, last_sync_error = NULL
                WHERE id = ?
                """,
                (mark_id,),
            )

    def record_sync_failure(self, mark_id: int, error: str) -> None:
        """Increment sync attempts and store the last synchronization error."""

        with self._connect() as connection:
            connection.execute(
                """
                UPDATE raw_marks
                SET sync_attempts = sync_attempts + 1, last_sync_error = ?
                WHERE id = ?
                """,
                (error, mark_id),
            )

    def purge_older_than(self, *, retention_days: int) -> int:
        """Delete RAW marks older than the retention window and return row count."""

        cutoff = datetime.now(UTC) - timedelta(days=retention_days)
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM raw_marks WHERE marked_at < ?",
                (_to_iso(cutoff),),
            )
            return int(cursor.rowcount)


def _to_iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat()


def _row_to_mark(row: sqlite3.Row | dict[str, Any]) -> RawMark:
    return RawMark(
        id=int(row["id"]),
        tag_uid=str(row["tag_uid"]),
        worker_id=row["worker_id"],
        device_id=str(row["device_id"]),
        obra=str(row["obra"]),
        marked_at=str(row["marked_at"]),
        synced=bool(row["synced"]),
        sync_attempts=int(row["sync_attempts"]),
        last_sync_error=row["last_sync_error"],
        created_at=str(row["created_at"]),
    )
