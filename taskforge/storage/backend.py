import threading
from typing import Any


class ResultStore:
    def __init__(self):
        self._results: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()

    def store(
        self,
        task_id: str,
        result: Any,
        status: str,
        error: str | None = None
    ) -> None:
        """Store the result of a task."""

        with self._lock:
            self._results[task_id] = {
                "task_id": task_id,
                "status": status,
                "result": result,
                "error": error
            }

    def get(self, task_id: str) -> dict[str, Any] | None:
        """Retrieve a task result by ID."""

        with self._lock:
            return self._results.get(task_id)