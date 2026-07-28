import socket
import time

from taskforge.common.protocol import receive_message, send_message
from taskforge.worker.executor import execute_task

class Worker:
    def __init__(
        self,
        worker_id: str,
        host: str = "127.0.0.1",
        port: int = 5555
    ):
        self.worker_id = worker_id
        self.host = host
        self.port = port

    def request_task(self) -> dict | None:
        """Request the next available task from the broker."""

        sock = socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM
        )

        try:
            sock.connect((self.host, self.port))

            send_message(
                sock,
                {
                    "op": "GET_TASK",
                    "worker_id": self.worker_id
                }
            )

            response = receive_message(sock)

            return response.get("task")

        finally:
            sock.close()

    def run(self) -> None:
        """Continuously request and execute tasks."""

        print(f"[WORKER {self.worker_id}] Started")

        while True:
            task = self.request_task()

            if task is None:
                time.sleep(1)
                continue

            print(
                f"[WORKER {self.worker_id}] "
                f"Executing task {task['id']}: {task['payload']}"
            )

            try:
                result = execute_task(task["payload"])

                print(
                    f"[WORKER {self.worker_id}] "
                    f"Task {task['id']} completed → {result}"
                )
                
                self.submit_result(
                    task_id=task["id"],
                    result=result,
                    status="success"
                )

            except Exception as exc:
                print(
                    f"[WORKER {self.worker_id}] "
                    f"Task {task['id']} failed → {exc}"
                )
                self.submit_result(
                    task_id=task["id"],
                    result=None,
                    status="failed",
                    error=str(exc)
                )
    def submit_result(
        self,
        task_id: str,
        result,
        status: str,
        error: str | None = None
    ) -> None:
        """Send a task result back to the broker."""

        sock = socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM
        )

        try:
            sock.connect((self.host, self.port))

            send_message(
                sock,
                {
                    "op": "SUBMIT_RESULT",
                    "task_id": task_id,
                    "result": result,
                    "status": status,
                    "error": error
                }
            )

            receive_message(sock)

        finally:
            sock.close()

if __name__ == "__main__":
    worker = Worker("worker-1")
    worker.run()