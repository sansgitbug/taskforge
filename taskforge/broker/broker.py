import socket
import threading
import time

from taskforge.broker.scheduler import TaskScheduler
from taskforge.common.protocol import receive_message, send_message
from taskforge.common.models import Task
from taskforge.storage.backend import ResultStore


class Broker:
    def __init__(self, host: str = "127.0.0.1", port: int = 5555):
        self.host = host
        self.port = port

        self.scheduler = TaskScheduler()
        self.result_store = ResultStore()
        self.active_tasks: dict[str, Task] = {}
        self.dead_letter_queue: list[Task] = []
        self.max_retries = 3
        self.workers: dict[str,dict] = {}
        self.worker_timeout = 5

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
        task = self.scheduler.dequeue()

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
        self.active_tasks[task.id] = task
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
            self.result_store.store(
                task_id=task_id,
                result=result,
                status="success"
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

                    print(
                        f"[BROKER] Task {task_id} moved to DLQ"
                    )

                else:
                    task.status = "queued"
                    retry_delay = 2 ** (task.retries - 1)

                    self.scheduler.enqueue(task, delay = retry_delay)

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
            "current_task": None
        }

        print(f"[BROKER] Worker registered: {worker_id}")

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
                    task_id = worker_info.get("current_task")

                    if task_id:
                        task = self.active_tasks.pop(task_id, None)

                        if task:
                            task.status = "queued"
                            self.scheduler.enqueue(task)

                            print(
                                f"[BROKER] Requeued task {task_id} "
                                f"after worker failure"
                            )

                    del self.workers[worker_id]
if __name__ == "__main__":
    broker = Broker()
    broker.start()