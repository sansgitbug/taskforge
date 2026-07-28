import { useCallback, useEffect, useMemo, useState } from 'react'
import { getStats } from './api'
import MetricsBar from './components/MetricsBar'
import TaskFeed from './components/TaskFeed'
import WorkerFleet from './components/WorkerFleet'
import EventLog from './components/EventLog'
import SubmitDrawer from './components/SubmitDrawer'

export default function App() {
  const [stats, setStats] = useState(null)
  const [error, setError] = useState('')
  const [now, setNow] = useState(Date.now())

  const refresh = useCallback(async () => {
    try {
      const data = await getStats()
      setStats(data)
      setError('')
    } catch {
      setError('Broker telemetry unavailable')
    }
  }, [])

  useEffect(() => {
    refresh()

    const polling = setInterval(refresh, 1500)
    const clock = setInterval(() => setNow(Date.now()), 500)

    return () => {
      clearInterval(polling)
      clearInterval(clock)
    }
  }, [refresh])

  const capabilities = useMemo(() => {
    const values = new Set()

    stats?.workers?.forEach((worker) => {
      worker.capabilities?.forEach((capability) => {
        values.add(capability)
      })
    })

    return [...values]
  }, [stats])

  const operational = !error

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <div className="brand">
            <span className="brand-mark">TF</span>
            <h1>TASKFORGE</h1>
            <span className="version">CONTROL PLANE</span>
          </div>

          <p>Distributed task execution</p>
        </div>

        <div className={`system-state ${operational ? '' : 'down'}`}>
          <span className="health-dot" />
          {operational ? 'OPERATIONAL' : 'DEGRADED'}
        </div>
      </header>

      {error && <div className="connection-error">{error}</div>}

      <MetricsBar stats={stats} />

      <div className="primary-grid">
        <TaskFeed tasks={stats?.tasks ?? []} />
        <WorkerFleet
          workers={stats?.workers ?? []}
          now={now}
        />
      </div>

      <EventLog events={stats?.events ?? []} />

      <SubmitDrawer
        capabilities={capabilities}
        onSubmitted={refresh}
      />
    </main>
  )
}