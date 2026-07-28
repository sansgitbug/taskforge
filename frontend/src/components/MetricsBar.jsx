export default function MetricsBar({ stats }) {
  const metrics = [
    ['QUEUE', stats?.queued_tasks ?? 0],
    ['RUNNING', stats?.active_tasks ?? 0],
    ['COMPLETED', stats?.completed_tasks ?? 0],
    ['FAILED', stats?.failed_tasks ?? 0],
  ]

  return (
    <section className="metrics-bar">
      {metrics.map(([label, value]) => (
        <div className="metric" key={label}>
          <span>{label}</span>
          <strong>{value}</strong>
        </div>
      ))}
    </section>
  )
}