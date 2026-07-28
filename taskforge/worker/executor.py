from typing import Any
import time

def add(a: float, b: float) -> float:
    return a + b


def subtract(a: float, b: float) -> float:
    return a - b


def multiply(a: float, b: float) -> float:
    return a * b

def divide(a: float, b: float) -> float:
    return a / b

def slow_task(seconds: int) -> str:
    time.sleep(seconds)
    return f"Slept for {seconds} seconds"

    
TASK_REGISTRY = {
    "add": add,
    "subtract": subtract,
    "multiply": multiply,
    "divide": divide,
    "slow_task": slow_task
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