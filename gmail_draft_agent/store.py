from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass(frozen=True)
class ProcessedMessage:
    message_id: str
    thread_id: str | None
    draft_id: str | None
    status: str
    reason: str | None
    created_at: str


class Store:
    """Small SQLite store for idempotency and audit logs."""

    def __init__(self, database_path: Path):
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_db(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS processed_messages (
                    message_id TEXT PRIMARY KEY,
                    thread_id TEXT,
                    draft_id TEXT,
                    status TEXT NOT NULL,
                    reason TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_processed_messages_created_at
                ON processed_messages(created_at)
                """
            )

    def has_processed(self, message_id: str) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT 1 FROM processed_messages WHERE message_id = ? LIMIT 1",
                (message_id,),
            ).fetchone()
        return row is not None

    def record(
        self,
        *,
        message_id: str,
        thread_id: str | None,
        draft_id: str | None,
        status: str,
        reason: str | None,
    ) -> None:
        now = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO processed_messages
                (message_id, thread_id, draft_id, status, reason, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (message_id, thread_id, draft_id, status, reason, now),
            )

    def recent(self, limit: int = 20) -> list[ProcessedMessage]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT message_id, thread_id, draft_id, status, reason, created_at
                FROM processed_messages
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [ProcessedMessage(**dict(row)) for row in rows]
