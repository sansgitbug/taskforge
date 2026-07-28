#part of broker that decides which queued task gets executed next
#uses heapq which is a minheap- smaller num = higher priority, priority queue 

import heapq
import threading

from taskforge.common.models import Task

class TaskScheduler:
    def __init__(self):
        self._queue = []
        self._counter = 0
        self._lock = threading.Lock()

    def enqueue(self, task: Task) -> None:
        """Add a task to the priority queue."""
        with self._lock:
            heapq.heappush(
                self._queue,
                (task.priority, self._counter, task)
            )
            self._counter += 1

    def dequeue(self) -> Task | None:
        """Remove and return the highest-priority task."""
        with self._lock:
            if not self._queue:
                return None

            _, _, task = heapq.heappop(self._queue)
            return task

    def size(self) -> int:
        """Return the number of queued tasks."""
        with self._lock:
            return len(self._queue)