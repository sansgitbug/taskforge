import threading
from typing import Any
import sqlite3
import json
import time 
class ResultStore:
    def __init__(self, db_path: str = "taskforge.db"    ):
        self.db_path = db_path
        self._lock = threading.Lock()
        self.conn = sqlite3.connect(
            self.db_path,
            check_same_thread=False
        )

        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.execute("PRAGMA temp_store=MEMORY")
        self.conn.execute("PRAGMA busy_timeout=5000")
        self._initialize_database()

    def _initialize_database(self) -> None:
        """Create the results table if it does not already exist."""

        with self._lock:
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS results (
                    task_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    result TEXT,
                    error TEXT
                )
                """
            )
            self.conn.commit()
    def store(
        self,
        task_id: str,
        result: Any,
        status: str,
        error: str | None = None
    ) -> None:
        """Store the result of a task."""
        #start = time.perf_counter()
        with self._lock:
            self.conn.execute(
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
            self.conn.commit()
        #elapsed = (time.perf_counter() - start) * 1000

        #if elapsed > 50:
            #print(f"[STORAGE] ResultStore.store took {elapsed:.1f} ms") 
    def get(self, task_id: str) -> dict[str, Any] | None:
        """Retrieve a task result by ID."""
        with self._lock:
            row = self.conn.execute(
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
        self.conn = sqlite3.connect(
            self.db_path,
            check_same_thread=False
        )

        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.execute("PRAGMA temp_store=MEMORY")
        self.conn.execute("PRAGMA busy_timeout=5000")

        self._initialize_database()


    def _initialize_database(self) -> None:
        with self._lock:
            self.conn.execute(
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
            self.conn.commit()
    def store(self, task) -> None:
        """Store or update a task."""
        #start = time.perf_counter()


        with self._lock:
    
            self.conn.execute(
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
            self.conn.commit()
        #elapsed = (time.perf_counter() - start) * 1000

        #if elapsed > 50:
            #print(f"[STORAGE] TaskStore.store took {elapsed:.1f} ms")
    def delete(self, task_id: str) -> None:
        """Delete a completed task."""
        #start = time.perf_counter()

        with self._lock:
            
            self.conn.execute(
                    "DELETE FROM tasks WHERE task_id = ?",
                    (task_id,)
                )
            self.conn.commit()
        #elapsed = (time.perf_counter() - start) * 1000

        #if elapsed > 50:
            #print(
                #f"[STORAGE] TaskStore.delete took "
                #f"{elapsed:.1f} ms"
            #)

    def load_pending(self) -> list[dict]:
        """Load tasks that should be restored after broker restart."""

        with self._lock:

            rows = self.conn.execute(
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
    