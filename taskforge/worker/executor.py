from typing import Any
import time


# Compute Tasks
def add(a: float, b: float) -> float:
    return a + b


def subtract(a: float, b: float) -> float:
    return a - b


def multiply(a: float, b: float) -> float:
    return a * b


def divide(a: float, b: float) -> float:
    return a / b


# Notification / IO Tasks
def send_email(recipient: str) -> dict:
    """Simulate sending an email."""
    time.sleep(0.5)

    return {
        "recipient": recipient,
        "status": "sent"
    }


# File Processing Tasks
def count_words(text: str) -> int:
    """Count the number of words in a document."""
    return len(text.split())


# ML Tasks
def generate_embedding(text: str) -> dict:
    """Simulate embedding generation."""
    time.sleep(0.3)

    return {
        "dimension": 384,
        "status": "generated"
    }


TASK_REGISTRY = {
    # Compute
    "add": add,
    "subtract": subtract,
    "multiply": multiply,
    "divide": divide,

    # Notification / IO
    "send_email": send_email,

    # File
    "count_words": count_words,

    # ML
    "generate_embedding": generate_embedding,
}


def execute_task(payload: dict[str, Any]) -> Any:
    """Execute a task based on its payload."""

    function_name = payload.get("func")
    args = payload.get("args", [])

    if not function_name:
        raise ValueError("Task payload must contain 'func'")

    if function_name not in TASK_REGISTRY:
        raise ValueError(f"Unknown task function: {function_name}")

    function = TASK_REGISTRY[function_name]

    return function(*args)