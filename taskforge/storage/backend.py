import threading
from typing import Any
import sqlite3
import json

class ResultStore:
    def __init__(self, db_path: str = "taskforge.db"    ):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._initialize_database()
    def _connect(self) -> sqlite3.Connection:
        """Create a connection to the SQLite database."""
        return sqlite3.connect(self.db_path)

    def _initialize_database(self) -> None:
        """Create the results table if it does not already exist."""

        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS results (
                    task_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    result TEXT,
                    error TEXT
                )
                """
            )
    def store(
        self,
        task_id: str,
        result: Any,
        status: str,
        error: str | None = None
    ) -> None:
        """Store the result of a task."""

        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO results
                    (task_id, status, result, error)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        task_id,
                        status,
                        result,
                        error
                    )
                )

    def get(self, task_id: str) -> dict[str, Any] | None:
        """Retrieve a task result by ID."""
        with self._lock:
            with self._connect() as conn:
                row = conn.execute(
                    """
                    SELECT task_id, status, result, error
                    FROM results
                    WHERE task_id = ?
                    """,
                    (task_id,)
                ).fetchone()

        if row is None:
            return None

        return {
            "task_id": row[0],
            "status": row[1],
            "result": json.loads(row[2]),
            "error": row[3]
        }
class TaskStore:
    def __init__(self, db_path: str = "taskforge.db"):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._initialize_database()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _initialize_database(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    priority INTEGER NOT NULL,
                    task_type TEXT NOT NULL,
                    retries INTEGER NOT NULL,
                    status TEXT NOT NULL
                )
                """
            )

    def store(self, task) -> None:
        """Store or update a task."""

        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO tasks
                    (task_id, payload, priority, task_type, retries, status)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        task.id,
                        json.dumps(task.payload),
                        task.priority,
                        task.task_type,
                        task.retries,
                        task.status
                    )
                )

    def delete(self, task_id: str) -> None:
        """Delete a completed task."""

        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    "DELETE FROM tasks WHERE task_id = ?",
                    (task_id,)
                )

    def load_pending(self) -> list[dict]:
        """Load tasks that should be restored after broker restart."""

        with self._lock:
            with self._connect() as conn:
                rows = conn.execute(
                    """
                    SELECT task_id, payload, priority,
                           task_type, retries, status
                    FROM tasks
                    WHERE status IN ('queued', 'running')
                    """
                ).fetchall()

        return [
            {
                "id": row[0],
                "payload": json.loads(row[1]),
                "priority": row[2],
                "task_type": row[3],
                "retries": row[4],
                "status": row[5]
            }
            for row in rows
        ]