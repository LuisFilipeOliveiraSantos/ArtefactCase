"""Conversation history persistence in a local SQLite file.

One row per session, holding the full message list as JSON. This is enough for a
prototype: a customer (identified by a session id, e.g. their phone number in a real
WhatsApp integration) can come back later and the agent remembers the conversation.
"""

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from emporio_agent.config import ROOT_DIR

DEFAULT_DB_PATH = ROOT_DIR / ".sessions" / "conversations.db"


class HistoryStore:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path or os.getenv("EMPORIO_DB_PATH") or DEFAULT_DB_PATH)
        if not self.path.is_absolute():
            self.path = ROOT_DIR / self.path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS sessions ("
                " id TEXT PRIMARY KEY, messages TEXT NOT NULL, updated_at TEXT NOT NULL)"
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def load(self, session_id: str) -> list[dict[str, Any]]:
        with self._connect() as db:
            row = db.execute("SELECT messages FROM sessions WHERE id = ?", (session_id,)).fetchone()
        return json.loads(row[0]) if row else []

    def save(self, session_id: str, messages: list[dict[str, Any]]) -> None:
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._connect() as db:
            db.execute(
                "INSERT INTO sessions (id, messages, updated_at) VALUES (?, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET messages = excluded.messages, updated_at = excluded.updated_at",
                (session_id, json.dumps(messages, ensure_ascii=False, default=str), now),
            )

    def delete(self, session_id: str) -> None:
        with self._connect() as db:
            db.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
