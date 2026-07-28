function eventPrefix(type) {
  if (type === 'completed') return '✓'
  if (type === 'failed') return '✗'
  if (type === 'dispatched' || type === 'retry' || type === 'requeued') {
    return '→'
  }
  return '●'
}

function eventClass(type) {
  if (type === 'completed') return 'event-success'
  if (type === 'failed') return 'event-failed'
  if (type === 'retry') return 'event-warning'
  return ''
}

function formatTime(timestamp) {
  return new Date(timestamp * 1000).toLocaleTimeString([], {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

export default function EventLog({ events = [] }) {
  const ordered = [...events].reverse()

  return (
    <section className="panel event-panel">
      <div className="panel-header">
        <div>
          <span className="eyebrow">BROKER</span>
          <h2>System events</h2>
        </div>

        <span className="record-count">last {Math.min(events.length, 50)}</span>
      </div>

      <div className="event-log">
        {ordered.length === 0 && (
          <div className="empty">No system events.</div>
        )}

        {ordered.slice(0, 50).map((event, index) => (
          <div
            className="event-row"
            key={`${event.timestamp}-${index}`}
          >
            <time>{formatTime(event.timestamp)}</time>

            <span className={`event-prefix ${eventClass(event.type)}`}>
              {eventPrefix(event.type)}
            </span>

            <span>{event.message}</span>

            {event.task_id && (
              <code>{event.task_id.slice(0, 8)}</code>
            )}
          </div>
        ))}
      </div>
    </section>
  )
}