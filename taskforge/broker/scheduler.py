#part of broker that decides which queued task gets executed next
#uses heapq which is a minheap- smaller num = higher priority, priority queue 

import heapq
import threading
import time

from taskforge.common.models import Task

class TaskScheduler:
    def __init__(self):
        self._queue = []
        self._counter = 0
        self._lock = threading.Lock()

    def enqueue(self, task: Task, delay: float = 0) -> None:
        """Add a task to the queue, optionally delaying its availability"""
        available_at = time.time() + delay

        with self._lock:
            heapq.heappush(
                self._queue,
                (available_at, task.priority, self._counter, task)
            )
            self._counter += 1

    def dequeue(self, capabilities: list[str] | None = None) -> Task | None:
        """Return the next available task supported by the worker"""
        with self._lock:
            if not self._queue:
                return None

            available_at, _, _, task = self._queue[0]
            if available_at > time.time():
                return None

            current_time = time.time()

            skipped = []
            selected_task = None

            while self._queue:
                available_at, priority, counter, task = heapq.heappop(
                    self._queue
                )
                if available_at > current_time:
                    heapq.heappush(
                        self._queue,
                        (available_at, priority, counter, task)
                    )
                    break

            # Worker cannot execute this task type.
                if (
                    capabilities is not None
                    and task.task_type not in capabilities
                ):
                    skipped.append(
                        (available_at, priority, counter, task)
                    )
                    continue

                selected_task = task
                break

            # Put incompatible tasks back.
            for item in skipped:
                heapq.heappush(self._queue, item)

            return selected_task

    def size(self) -> int:
        """Return the number of queued tasks."""
        with self._lock:
            return len(self._queue)

    def snapshot(self) -> list[Task]:
        """Return queued tasks without removing them."""

        with self._lock:
            return [
                item[3]
                for item in sorted(self._queue)
            ]