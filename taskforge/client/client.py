import socket

from taskforge.common.protocol import receive_message, send_message


class Client:
    def __init__(self, host: str = "127.0.0.1", port: int = 5555):
        self.host = host
        self.port = port

    def send(self, message: dict) -> dict:
        """Send a request to the broker and return its response."""

        sock = socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM
        )

        try:
            sock.connect((self.host, self.port))

            send_message(sock, message)

            response = receive_message(sock)

            return response

        finally:
            sock.close()

    def submit(
        self,
        payload: dict,
        priority: int = 5,
        task_type: str = "default"
    ) -> str:
        """Submit a task to the broker and return its task ID."""

        response = self.send({
            "op": "SUBMIT_TASK",
            "payload": payload,
            "priority": priority,
            "task_type": task_type
        })

        if response.get("status") != "ok":
            raise RuntimeError(
                response.get("message", "Task submission failed")
            )

        return response["task_id"]

    def get_result(self, task_id: str) -> dict | None:
        """Retrieve a task result from the broker."""

        response = self.send({
            "op": "GET_RESULT",
            "task_id": task_id
        })

        if response.get("status") != "ok":
            raise RuntimeError(
                response.get("message", "Failed to retrieve result")
            )

        return response.get("result")


if __name__ == "__main__":
    import time

    client = Client()

    task_id = client.submit(
        payload={
            "func": "add",
            "args": [10, 20]
        },
        priority=1
    )

    print(f"[CLIENT] Submitted task: {task_id}")

    time.sleep(2)

    result = client.get_result(task_id)

    print(f"[CLIENT] Result: {result}")