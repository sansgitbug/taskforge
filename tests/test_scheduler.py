from taskforge.broker.scheduler import TaskScheduler
from taskforge.common.models import Task


scheduler = TaskScheduler()

scheduler.enqueue(Task({"name": "low"}, priority=5))
scheduler.enqueue(Task({"name": "urgent"}, priority=1))
scheduler.enqueue(Task({"name": "medium"}, priority=3))

while scheduler.size() > 0:
    task = scheduler.dequeue()
    print(task.priority, task.payload)