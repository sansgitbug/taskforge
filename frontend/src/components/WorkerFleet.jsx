function shortId(id) {
  return id ? `${id.slice(0, 8)}…` : 'IDLE'
}

export default function WorkerFleet({ workers = [], now }) {
  return (
    <section className="panel workers-panel">
      <div className="panel-header">
        <div>
          <span className="eyebrow">INFRASTRUCTURE</span>
          <h2>Worker fleet</h2>
        </div>

        <span className="record-count">{workers.length} online</span>
      </div>

      <div className="worker-list">
        {workers.length === 0 && (
          <div className="empty">No workers registered.</div>
        )}

        {workers.map((worker) => {
          const heartbeat = Math.max(
            0,
            now / 1000 - worker.last_heartbeat
          )

          const stale = heartbeat >= 4

          return (
            <div className="worker-row" key={worker.worker_id}>
              <div className="worker-heading">
                <div className={`health-dot ${stale ? 'stale' : ''}`} />
                <span className="mono">{worker.worker_id}</span>

                <span className={stale ? 'heartbeat stale-text' : 'heartbeat'}>
                  {heartbeat.toFixed(1)}s
                </span>
              </div>

              <div className="worker-meta">
                <span>
                  {worker.capabilities?.join(', ') || 'default'}
                </span>

                <code>{shortId(worker.current_task)}</code>
              </div>
            </div>
          )
        })}
      </div>
    </section>
  )
}