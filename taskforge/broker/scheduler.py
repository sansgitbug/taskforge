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

    def dequeue(self) -> Task | None:
        """Return the next task if it is ready for execution"""
        with self._lock:
            if not self._queue:
                return None

            available_at, _, _, task = self._queue[0]
            if available_at > time.time():
                return None
            
            heapq.heappop(self._queue)
            return task


    def size(self) -> int:
        """Return the number of queued tasks."""
        with self._lock:
            return len(self._queue)