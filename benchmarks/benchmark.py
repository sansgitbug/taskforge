import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import sys
from taskforge.client.client import Client


NUM_TASKS = int(sys.argv[1]) if len(sys.argv) > 1 else 100
SUBMIT_THREADS = 10
POLL_INTERVAL = 0.05

client = Client()


def submit_one(i):
    start = time.perf_counter()

    task_id = client.submit(
        payload={
            "func": "add",
            "args": [i, i + 1]
        },
        priority=5,
        task_type="compute"
    )

    return task_id, start


def percentile(values, p):
    index = int((len(values) - 1) * p)
    return values[index]


print(f"\nStarting benchmark with {NUM_TASKS} tasks...")

benchmark_start = time.perf_counter()

submitted = {}

with ThreadPoolExecutor(max_workers=SUBMIT_THREADS) as executor:
    futures = [
        executor.submit(submit_one, i)
        for i in range(NUM_TASKS)
    ]

    for future in as_completed(futures):
        task_id, start_time = future.result()
        submitted[task_id] = start_time

print(f"Submitted {len(submitted)} tasks.")

pending = set(submitted)
latencies = []
failed = 0

while pending:
    try:
        stats = client.get_stats()

        # Your broker stats has used "tasks" in the dashboard.
        # Fall back to task_history for compatibility.
        tasks = stats.get("tasks", stats.get("task_history", []))

        for task in tasks:
            task_id = task.get("task_id") or task.get("id")

            if task_id not in pending:
                continue

            status = task.get("status")

            if status in ("success", "failed"):
                end = time.perf_counter()

                latency_ms = (
                    end - submitted[task_id]
                ) * 1000

                latencies.append(latency_ms)

                if status == "failed":
                    failed += 1

                pending.remove(task_id)

    except Exception as exc:
        print(f"Polling error: {exc}")

    if pending:
        time.sleep(POLL_INTERVAL)


benchmark_end = time.perf_counter()

total_time = benchmark_end - benchmark_start
completed = len(latencies)
throughput = completed / total_time

latencies.sort()

print("\n========== TASKFORGE BENCHMARK ==========")
print(f"Tasks:       {NUM_TASKS}")
print(f"Completed:   {completed}")
print(f"Failed:      {failed}")
print(f"Total time:  {total_time:.2f} s")
print(f"Throughput:  {throughput:.2f} tasks/sec")

if latencies:
    print("\nEnd-to-end latency")
    print(f"p50:         {percentile(latencies, 0.50):.2f} ms")
    print(f"p95:         {percentile(latencies, 0.95):.2f} ms")
    print(f"p99:         {percentile(latencies, 0.99):.2f} ms")

print("=========================================\n")