# TaskForge

![TaskForge Dashboard](docs/dashboard.png)

TaskForge is a distributed task queue built in Python. It has a central broker that accepts tasks, schedules them to compatible workers, tracks worker health, and stores task results.

I built it to understand what happens underneath task queue systems instead of starting with an existing framework such as Celery. The communication between the broker, workers, and Python client uses a custom TCP protocol built with Python sockets.

A FastAPI layer exposes the system over HTTP, and a React dashboard provides a live view of tasks, workers, and broker events.

## How it works

A task submitted to TaskForge contains three main pieces of information:

```json
{
  "payload": {
    "func": "add",
    "args": [10, 20]
  },
  "priority": 5,
  "task_type": "compute"
}
```

The broker adds the task to its queue and waits for a worker that can execute its task type.

Workers register themselves with a list of capabilities. For example:

```text
worker-1 -> compute
worker-2 -> notification
worker-3 -> file
worker-4 -> ML
```

A task is only dispatched to a worker whose advertised capabilities match the task's task_type. For example, compute tasks are routed to compute workers, while notification, file, and ml tasks are dispatched to their respective worker pools.

Once a worker receives a task, it executes the payload and sends the result back to the broker. The broker records the result and makes it available to clients and the dashboard.

For the example above:

```text
submit task
    |
    v
broker queues task
    |
    v
broker finds compute worker
    |
    v
worker-1 executes add(10, 20)
    |
    v
result = 30
    |
    v
broker stores result
```

## Architecture

```text
                         HTTP
                  +----------------+
                  | React Dashboard|
                  +-------+--------+
                          |
                          v
                  +----------------+
                  |    FastAPI     |
                  +-------+--------+
                          |
                          | TCP
                          v
                  +----------------+
                  |     Broker     |
                  |                |
                  | priority queue |
                  | worker registry|
                  | task routing   |
                  +---+--------+---+
                      |        |
                  TCP |        | TCP
                      v        v
               +----------+ +----------+
               | Worker 1 | | Worker 2 |
               | compute  | |    io    |
               +----------+ +----------+

                         |
                         v
                  +----------------+
                  |     SQLite     |
                  | tasks/results  |
                  +----------------+
```

The broker is the central coordinator. It owns the task queue, keeps track of registered workers, decides which worker should receive a task, and records execution events.

## Scheduling

Tasks have priorities from 1 to 10 and are stored in a priority queue.

Scheduling also takes worker capabilities into account. A worker only receives tasks whose `task_type` matches one of its registered capabilities.

This means adding more workers does not require changing the client. Workers advertise what they can handle when they register with the broker.

## Supported task types

TaskForge currently supports multiple categories of workloads.

| Task type | Example functions |
|-----------|-------------------|
| Compute | add, subtract, multiply, divide |
| Notification | send_email |
| File | count_words |
| ML | generate_embedding |

Additional task types can be introduced by registering new worker capabilities and task handlers.

## Worker health

Workers send heartbeats to the broker while they are running.

The broker records the last heartbeat received from every worker. Workers that stop sending heartbeats are marked as stale by the broker and displayed as unhealthy in the dashboard. This allows inactive workers to be identified without inspecting broker logs.

The dashboard exposes this information so worker state can be inspected without looking through broker logs.

## Failure handling

Task execution happens inside the worker.

If execution succeeds, the worker sends the result back to the broker with a successful status.

If execution raises an exception, the worker reports the failure instead. Tasks also keep track of their retry count and maximum retry limit.

The task model records:

```text
status
retries
max_retries
created_at
started_at
completed_at
result
error
```

This makes the execution lifecycle visible instead of treating a task as only an input and output.

## Persistence and recovery

Task results are stored in SQLite rather than existing only in broker memory.

The broker also persists enough task information to recover pending work after a restart. When the broker starts again, pending tasks can be restored to the queue instead of being silently lost.

SQLite keeps the project self-contained and makes it possible to run the complete system locally without another database service.

## API

FastAPI provides an HTTP interface over the Python client.

Current endpoints include:

```text
GET  /health
POST /tasks
GET  /tasks/{task_id}
GET  /stats
GET  /workers
```

For example, a task can be submitted with:

```json
{
  "payload": {
    "func": "add",
    "args": [10, 20]
  },
  "priority": 5,
  "task_type": "compute"
}
```

FastAPI's interactive API documentation is available at:

```text
http://127.0.0.1:8000/docs
```

## Dashboard

The React dashboard acts as a small control plane for TaskForge.

It polls the API every 1.5 seconds and displays:

- queue depth and task counts
- queued, running, completed, and failed tasks
- task priority and execution duration
- registered workers and their capabilities
- worker heartbeat status
- broker dispatch and completion events

Tasks can be expanded directly in the table to inspect their full payload, assigned worker, retry count, and result.

Tasks can also be submitted directly from the dashboard.

## Running locally

### 1. Install the Python dependencies

Create and activate a virtual environment, then install the dependencies:

```bash
pip install -r requirements.txt
```

### 2. Start the broker

From the project root:

```bash
python -m taskforge.broker.broker
```

The broker listens on:

```text
127.0.0.1:5555
```

### 3. Start a worker

Open another terminal:

```bash
python -m taskforge.worker.worker worker-1 compute
```

The final argument specifies the worker capability.

Another worker can be started with a different capability:

```bash
python -m taskforge.worker.worker worker-2 io
```

### 4. Start the API

Open another terminal:

```bash
python -m uvicorn api.main:app --reload
```

The API runs at:

```text
http://127.0.0.1:8000
```

### 5. Start the dashboard

From the `frontend` directory:

```bash
npm install
npm run dev
```

Then open:

```text
http://localhost:5173
```

## Project structure

```text
taskforge/
|
|-- api/
|   `-- main.py
|
|-- frontend/
|   `-- src/
|       |-- components/
|       |-- api.js
|       |-- App.jsx
|       `-- styles.css
|
|-- taskforge/
|   |-- broker/
|   |-- client/
|   |-- common/
|   |-- storage/
|   `-- worker/
|
|-- tests/
|-- requirements.txt
|-- pyproject.toml
`-- README.md
```

## Tech stack

**Backend:** Python, TCP sockets, threading, SQLite, FastAPI

**Frontend:** React, Vite, JavaScript, CSS

**Concepts:** Distributed task scheduling, capability-aware routing, heartbeat monitoring, retry with exponential backoff, dead-letter queues

## Performance

The persistence layer was optimized by replacing per-operation SQLite connections with persistent connections configured in WAL mode.

Benchmark results:

| Workload | Throughput |
|----------|-----------:|
| 100 tasks | ~115 tasks/sec |
| 1000 tasks | ~95 tasks/sec |

The benchmark measures end-to-end latency from task submission until completion across multiple workers.
