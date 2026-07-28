import socket
import threading

from taskforge.broker.scheduler import TaskScheduler
from taskforge.common.protocol import receive_message, send_message
from taskforge.common.models import Task


class Broker:
    def __init__(self, host: str = "127.0.0.1", port: int = 5555):
        self.host = host
        self.port = port

        self.scheduler = TaskScheduler()

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


if __name__ == "__main__":
    broker = Broker()
    broker.start()