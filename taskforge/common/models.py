from dataclasses import dataclass, field
from typing import Any
import time
import uuid


@dataclass
class Task:
    payload: dict[str, Any]

    priority: int = 5
    task_type: str = "default"

    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    status: str = "queued"

    retries: int = 0
    max_retries: int = 3

    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    completed_at: float | None = None

    result: Any = None
    error: str | None = None