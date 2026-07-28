from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any

from taskforge.client.client import Client


app = FastAPI(
    title="TaskForge API",
    description="HTTP API for the TaskForge distributed task queue",
    version="1.0.0"
)

client = Client()


class TaskRequest(BaseModel):
    payload: dict[str, Any]
    priority: int = 5
    task_type: str = "default"


@app.get("/health")
def health():
    """Check whether the API is running."""
    return {
        "status": "ok",
        "service": "taskforge-api"
    }


@app.post("/tasks")
def submit_task(request: TaskRequest):
    """Submit a task to the TaskForge broker."""

    try:
        task_id = client.submit(
            payload=request.payload,
            priority=request.priority,
            task_type=request.task_type
        )

        return {
            "status": "queued",
            "task_id": task_id
        }

    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Broker unavailable: {exc}"
        )


@app.get("/tasks/{task_id}")
def get_task_result(task_id: str):
    """Retrieve the result of a submitted task."""

    try:
        result = client.get_result(task_id)

    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Broker unavailable: {exc}"
        )

    if result is None:
        return {
            "task_id": task_id,
            "status": "pending"
        }

    return result

@app.get("/stats")
def get_stats():
    """Return TaskForge system statistics."""

    try:
        return client.get_stats()

    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Broker unavailable: {exc}"
        )


@app.get("/workers")
def get_workers():
    """Return currently registered workers."""

    try:
        stats = client.get_stats()

        return {
            "workers": stats["workers"],
            "count": stats["worker_count"]
        }

    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Broker unavailable: {exc}"
        )