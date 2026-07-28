import socket
import threading
import time

from taskforge.broker.scheduler import TaskScheduler
from taskforge.common.protocol import receive_message, send_message
from taskforge.common.models import Task
from taskforge.storage.backend import ResultStore, TaskStore


class Broker:
    def __init__(self, host: str = "127.0.0.1", port: int = 5555):
        self.host = host
        self.port = port

        self.scheduler = TaskScheduler()
        self.result_store = ResultStore()
        self.task_store = TaskStore()
        self.active_tasks: dict[str, Task] = {}
        self.dead_letter_queue: list[Task] = []
        self.max_retries = 3
        self.workers: dict[str,dict] = {}
        self.worker_timeout = 5
        self.task_history: list[dict] = []
        self.events: list[dict] = []
        self.completed_count = 0
        self.failed_count = 0
        self.server_socket = socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM
        )

    def start(self) -> None:
        """Start the broker and listen for incoming connections."""

        self.server_socket.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_REUSEADDR,
            1
        )

        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen()
        self.restore_pending_tasks()
        print(f"[BROKER] Listening on {self.host}:{self.port}")
        monitor_thread = threading.Thread(
            target=self.monitor_workers,
            daemon=True
        )

        monitor_thread.start()
        while True:
            client_socket, address = self.server_socket.accept()

            print(f"[BROKER] Connection from {address}")

            thread = threading.Thread(
                target=self.handle_connection,
                args=(client_socket, address),
                daemon=True
            )

            thread.start()

    def handle_connection(
        self,
        client_socket: socket.socket,
        address
    ) -> None:
        """Handle one connected client or worker."""

        try:
            message = receive_message(client_socket)

            print(f"[BROKER] Received from {address}: {message}")

            operation = message.get("op")

            if operation == "SUBMIT_TASK":
                self.handle_submit_task(client_socket, message)

            elif operation == "GET_TASK":
                self.handle_get_task(client_socket, message)

            elif operation == "SUBMIT_RESULT":
                self.handle_submit_result(client_socket, message)

            elif operation == "GET_RESULT":
                self.handle_get_result(client_socket, message)
            elif operation == "REGISTER_WORKER":
                 self.handle_register_worker(client_socket, message)

            elif operation == "HEARTBEAT":
                self.handle_heartbeat(client_socket, message)
            elif operation == "GET_STATS":
                self.handle_get_stats(client_socket)
            else:
                send_message(
                    client_socket,
                    {
                        "status": "error",
                        "message": f"Unknown operation: {operation}"
                    }
                )

        except Exception as exc:
            print(f"[BROKER] Error handling {address}: {exc}")

        finally:
            client_socket.close()

    def handle_submit_task(
        self,
        client_socket: socket.socket,
        message: dict
    ) -> None:
        """Create a Task and add it to the scheduler."""

        payload = message.get("payload")
        priority = message.get("priority", 5)
        task_type = message.get("task_type", "default")

        if payload is None:
            send_message(
                client_socket,
                {
                    "status": "error",
                    "message": "Task payload is required"
                }
            )
            return

        task = Task(
            payload=payload,
            priority=priority,
            task_type=task_type
        )

        self.scheduler.enqueue(task)
        self.task_store.store(task)
        print(
            f"[BROKER] Task {task.id} queued "
            f"with priority {task.priority}"
        )

        send_message(
            client_socket,
            {
                "status": "ok",
                "task_id": task.id
            }
        )

    def handle_get_task(
        self,
        client_socket: socket.socket,
        message: dict
    ) -> None:
        """Give the next queued task to a worker."""
        worker_id = message.get("worker_id")
        worker = self.workers.get(worker_id)
        if worker is None:
            send_message(
                client_socket,
                {
                    "status": "error",
                    "message": "Worker is not registered"
                }
            )
            return

        capabilities = worker["capabilities"]
        task = self.scheduler.dequeue(capabilities = capabilities)

        if task is None:
            send_message(
                client_socket,
                {
                    "status": "ok",
                    "task": None
                }
            )
            return

        task.status = "running"
        task.started_at = time.time()
        self.add_event(
            event_type="dispatched",
            message=f"Task dispatched to {worker_id}",
            task_id=task.id,
            worker_id=worker_id
)
        self.active_tasks[task.id] = task
        self.task_store.store(task)
        if worker_id in self.workers:
            self.workers[worker_id]["current_task"] = task.id

        send_message(
            client_socket,
            {
                "status": "ok",
                "task": {
                    "id": task.id,
                    "payload": task.payload,
                    "priority": task.priority,
                    "task_type": task.task_type,
                    "retries": task.retries
                }
            }
        )

        print(f"[BROKER] Dispatched task {task.id}")

    def handle_submit_result(
        self,
        client_socket: socket.socket,
        message: dict
    ) -> None:
        """Store a result reported by a worker."""

        task_id = message.get("task_id")
        result = message.get("result")
        status = message.get("status")
        error = message.get("error")
        worker_id = message.get("worker_id")

        if not task_id or not status:
            send_message(
                client_socket,
                {
                    "status": "error",
                    "message": "task_id and status are required"
                }
            )
            return
        task = self.active_tasks.pop(task_id, None)
        if worker_id in self.workers:
            self.workers[worker_id]["current_task"] = None
        if status == "success":
            self.task_store.delete(task_id)
            self.result_store.store(
                task_id=task_id,
                result=result,
                status="success"
            )
            if task is not None:
                task.status = "success"
                task.completed_at = time.time()
                task.result = result

                duration = (
                    task.completed_at - task.started_at
                    if task.started_at
                    else None
                )

                self.task_history.append({
                    "task_id": task.id,
                    "task_type": task.task_type,
                    "priority": task.priority,
                    "status": "success",
                    "worker_id": worker_id,
                    "retries": task.retries,
                    "created_at": task.created_at,
                    "started_at": task.started_at,
                    "completed_at": task.completed_at,
                    "duration": duration,
                    "payload": task.payload,
                    "result": result,
                    "error": None
                })

                self.task_history = self.task_history[-100:]

            self.completed_count += 1

            self.add_event(
                event_type="completed",
                message="Task completed successfully",
                task_id=task_id,
                worker_id=worker_id
            )
            print(f"[BROKER] Task {task_id} succeeded")

        elif status == "failed":

            if task is None:
                print(f"[BROKER] Unknown failed task {task_id}")

            else:
                task.retries += 1

                print(
                    f"[BROKER] Task {task_id} failed "
                    f"(attempt {task.retries}/{self.max_retries})"
                )

                if task.retries >= self.max_retries:
                    task.status = "failed"

                    self.dead_letter_queue.append(task)

                    self.result_store.store(
                        task_id=task_id,
                        result=None,
                        status="failed",
                        error=error
                    )
                    self.task_store.delete(task_id)
                    task.completed_at = time.time()
                    task.error = error

                    duration = (
                        task.completed_at - task.started_at
                        if task.started_at
                        else None
                    )

                    self.task_history.append({
                        "task_id": task.id,
                        "task_type": task.task_type,
                        "priority": task.priority,
                        "status": "failed",
                        "worker_id": worker_id,
                        "retries": task.retries,
                        "created_at": task.created_at,
                        "started_at": task.started_at,
                        "completed_at": task.completed_at,
                        "duration": duration,
                        "payload": task.payload,
                        "result": None,
                        "error": error
                    })

                    self.task_history = self.task_history[-100:]

                    self.failed_count += 1

                    self.add_event(
                        event_type="failed",
                        message=f"Task moved to DLQ: {error}",
                        task_id=task_id,
                        worker_id=worker_id
                    )

                    print(
                        f"[BROKER] Task {task_id} moved to DLQ"
                    )

                else:
                    task.status = "queued"
                    self.task_store.store(task)
                    retry_delay = 2 ** (task.retries - 1)

                    self.scheduler.enqueue(task, delay = retry_delay)
                    self.add_event(
                        event_type="retry",
                        message=f"Retry {task.retries}/{self.max_retries} scheduled in {retry_delay}s",
                        task_id=task_id,
                        worker_id=worker_id
                    )

                    print(
                        f"[BROKER] Task {task_id} requeued"
                        f"with {retry_delay}s backoff"
                    )

        send_message(
            client_socket,
            {"status": "ok"}
        )


    def handle_get_result(
        self,
        client_socket: socket.socket,
        message: dict
    ) -> None:
        """Return the stored result for a task."""

        task_id = message.get("task_id")

        result = self.result_store.get(task_id)

        send_message(
            client_socket,
            {
                "status": "ok",
                "result": result
            }
        )
    
    def handle_register_worker(
        self,
        client_socket: socket.socket,
        message: dict
    ) -> None:
        """Register a worker with the broker."""
        capabilities = message.get("capabilities", ["default"])
        worker_id = message.get("worker_id")

        if not worker_id:
            send_message(
                client_socket,
                {
                    "status": "error",
                    "message": "worker_id is required"
                }
            )
            return

        self.workers[worker_id] = {
            "last_heartbeat": time.time(),
            "current_task": None,
            "capabilities": capabilities

        }

        print(f"[BROKER] Worker registered: {worker_id} "
            f"capabilities={capabilities}"
        )

        send_message(
            client_socket,
            {"status": "ok"}
        )


    def handle_heartbeat(
        self,
        client_socket: socket.socket,
        message: dict
    ) -> None:
        """Update a worker's last heartbeat time."""

        worker_id = message.get("worker_id")

        if worker_id not in self.workers:
            send_message(
                client_socket,
                {
                    "status": "error",
                    "message": "Worker is not registered"
                }
            )
            return

        self.workers[worker_id]["last_heartbeat"] = time.time()

        send_message(
            client_socket,
            {"status": "ok"}
        )
    def monitor_workers(self) -> None:
        """Detect workers that have stopped sending heartbeats."""

        while True:
            time.sleep(1)

            current_time = time.time()

            for worker_id, worker_info in list(self.workers.items()):
                last_heartbeat = worker_info["last_heartbeat"]

                if current_time - last_heartbeat > self.worker_timeout:
                    print(
                        f"[BROKER] Worker {worker_id} timed out"
                    )
                    self.add_event(
                        event_type="worker_timeout",
                        message=f"{worker_id} stopped responding",
                        worker_id=worker_id
                    )
                    task_id = worker_info.get("current_task")

                    if task_id:
                        task = self.active_tasks.pop(task_id, None)

                        if task:
                            task.status = "queued"
                            self.scheduler.enqueue(task)
                            self.task_store.store(task)

                            self.add_event(
                                event_type="requeued",
                                message=f"Task recovered after {worker_id} failure",
                                task_id=task_id,
                                worker_id=worker_id
                            )


                            print(
                                f"[BROKER] Requeued task {task_id} "
                                f"after worker failure"
                            )

                    del self.workers[worker_id]


    def restore_pending_tasks(self) -> None:
        """Restore unfinished tasks from persistent storage."""

        pending_tasks = self.task_store.load_pending()

        for saved_task in pending_tasks:
            task = Task(
                payload=saved_task["payload"],
                priority=saved_task["priority"],
                task_type=saved_task["task_type"],
                id=saved_task["id"],
                retries=saved_task["retries"],
                status="queued"
            )

            # A task that was "running" when the broker died
            # must be treated as queued again.
            self.task_store.store(task)
            self.scheduler.enqueue(task)

            print(f"[BROKER] Restored task {task.id}")

        if pending_tasks:
            print(
                f"[BROKER] Restored {len(pending_tasks)} "
                f"pending task(s)"
            )
    def handle_get_stats(
        self,
        client_socket: socket.socket
    ) -> None:
        """Return broker statistics and worker information."""
        queued_tasks = []

        for task in self.scheduler.snapshot():
            queued_tasks.append({
                "task_id": task.id,
                "task_type": task.task_type,
                "priority": task.priority,
                "status": "queued",
                "worker_id": None,
                "retries": task.retries,
                "created_at": task.created_at,
                "started_at": None,
                "completed_at": None,
                "duration": None,
                "payload": task.payload,
                "result": None,
                "error": None
            })
        running_tasks = []

        for task in self.active_tasks.values():
            worker_id = None

            for wid, info in self.workers.items():
                if info.get("current_task") == task.id:
                    worker_id = wid
                    break

            running_tasks.append({
                "task_id": task.id,
                "task_type": task.task_type,
                "priority": task.priority,
                "status": "running",
                "worker_id": worker_id,
                "retries": task.retries,
                "created_at": task.created_at,
                "started_at": task.started_at,
                "completed_at": None,
                "duration": (
                    time.time() - task.started_at
                    if task.started_at
                    else None
                ),
                "payload": task.payload,
                "result": None,
                "error": None
            })
        workers = []

        for worker_id, info in self.workers.items():
            workers.append({
                "worker_id": worker_id,
                "capabilities": info["capabilities"],
                "current_task": info["current_task"],
                "last_heartbeat": info["last_heartbeat"]
            })

        send_message(
            client_socket,
            {
                "status": "ok",
                "stats": {
                    "queued_tasks": self.scheduler.size(),
                    "active_tasks": len(self.active_tasks),
                    "workers": workers,
                    "worker_count": len(workers),
                    "dlq_size": len(self.dead_letter_queue),
                    "completed_tasks": self.completed_count,
                    "failed_tasks": self.failed_count,
                    "task_history": self.task_history[-50:],
                    "events": self.events[-50:],
                    "tasks": (
                        running_tasks
                        + queued_tasks
                        + list(reversed(self.task_history[-50:]))
                    ),
                }
            }
        )
    def add_event(
        self,
        event_type: str,
        message: str,
        task_id: str | None = None,
        worker_id: str | None = None
    ) -> None:
        """Record a recent system event."""

        self.events.append({
            "timestamp": time.time(),
            "type": event_type,
            "message": message,
            "task_id": task_id,
            "worker_id": worker_id
        })

        # Don't let this grow forever.
        self.events = self.events[-100:]
if __name__ == "__main__":
    broker = Broker()
    broker.start()