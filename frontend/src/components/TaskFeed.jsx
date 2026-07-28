import { useState } from 'react'

function shortId(id) {
  return id ? `${id.slice(0, 8)}…` : '—'
}

function formatTime(timestamp) {
  if (!timestamp) return '—'

  return new Date(timestamp * 1000).toLocaleTimeString([], {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

function formatDuration(duration) {
  if (duration == null) return '—'
  if (duration < 1) return `${Math.round(duration * 1000)}ms`
  return `${duration.toFixed(2)}s`
}

export default function TaskFeed({ tasks = [] }) {
  const [expanded, setExpanded] = useState(null)

  return (
    <section className="panel tasks-panel">
      <div className="panel-header">
        <div>
          <span className="eyebrow">EXECUTION</span>
          <h2>Tasks</h2>
        </div>

        <span className="record-count">{tasks.length} records</span>
      </div>

      <div className="task-table-wrap">
        <table className="task-table">
          <thead>
            <tr>
              <th>TASK ID</th>
              <th>TYPE</th>
              <th>PRI</th>
              <th>STATUS</th>
              <th>SUBMITTED</th>
              <th>DURATION</th>
            </tr>
          </thead>

          <tbody>
            {tasks.length === 0 && (
              <tr>
                <td colSpan="6" className="empty">
                  No tasks recorded.
                </td>
              </tr>
            )}

            {tasks.map((task) => (
              <>
                <tr
                  key={task.task_id}
                  className="task-row"
                  onClick={() =>
                    setExpanded(
                      expanded === task.task_id ? null : task.task_id
                    )
                  }
                >
                  <td className="mono task-id" title={task.task_id}>
                    {shortId(task.task_id)}
                  </td>

                  <td>{task.task_type}</td>
                  <td className="mono">{task.priority}</td>

                  <td>
                    <span className={`status status-${task.status}`}>
                      {task.status}
                    </span>
                  </td>

                  <td className="mono">{formatTime(task.created_at)}</td>
                  <td className="mono">
                    {formatDuration(task.duration)}
                  </td>
                </tr>

                {expanded === task.task_id && (
                  <tr
                    className="task-detail-row"
                    key={`${task.task_id}-detail`}
                  >
                    <td colSpan="6">
                      <div className="task-detail">
                        <div>
                          <span className="detail-label">FULL ID</span>
                          <code>{task.task_id}</code>
                        </div>

                        <div>
                          <span className="detail-label">WORKER</span>
                          <code>{task.worker_id ?? 'unassigned'}</code>
                        </div>

                        <div>
                          <span className="detail-label">RETRIES</span>
                          <code>{task.retries ?? 0}</code>
                        </div>

                        <div className="detail-wide">
                          <span className="detail-label">PAYLOAD</span>
                          <pre>
                            {JSON.stringify(task.payload, null, 2)}
                          </pre>
                        </div>

                        <div className="detail-wide">
                          <span className="detail-label">
                            {task.error ? 'ERROR' : 'RESULT'}
                          </span>
                          <pre>
                            {task.error ??
                              JSON.stringify(task.result, null, 2)}
                          </pre>
                        </div>
                      </div>
                    </td>
                  </tr>
                )}
              </>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}