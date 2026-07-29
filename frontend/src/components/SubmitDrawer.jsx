import { useEffect, useState } from 'react'
import { submitTask } from '../api'

const DEFAULT_PAYLOADS = {
    compute: `{
    "func": "add",
    "args": [10, 20]
}`,

    notification: `{
    "func": "send_email",
    "args": ["alice@example.com"]
}`,

    file: `{
    "func": "count_words",
    "args": ["TaskForge is a distributed scheduler"]
}`,

    ml: `{
    "func": "generate_embedding",
    "args": ["TaskForge uses capability-aware scheduling"]
}`
}
    

export default function SubmitDrawer({ capabilities, onSubmitted }) {
  const [open, setOpen] = useState(false)
  const [payload, setPayload] = useState(DEFAULT_PAYLOADS[capabilities[0]] ?? DEFAULT_PAYLOADS.compute)
  const [priority, setPriority] = useState(5)
  const [taskType, setTaskType] = useState(
    capabilities[0] ?? 'default'
  )
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  // Capabilities arrive asynchronously from the API.
  // Keep the selected task type in sync once they are available.
  
  async function handleSubmit(event) {
    event.preventDefault()
    setError('')

    let parsedPayload

    try {
      parsedPayload = JSON.parse(payload)
    } catch {
      setError('Payload must be valid JSON.')
      return
    }

    try {
      setSubmitting(true)

      await submitTask({
        payload: parsedPayload,
        priority: Number(priority),
        task_type: taskType,
      })

      setOpen(false)
      onSubmitted?.()
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className={`submit-drawer ${open ? 'drawer-open' : ''}`}>
      <button
        className="drawer-toggle"
        onClick={() => setOpen(!open)}
      >
        <span>{open ? 'CLOSE' : 'SUBMIT TASK'}</span>
        <span>{open ? '×' : '+'}</span>
      </button>

      {open && (
        <form className="submit-form" onSubmit={handleSubmit}>
          <div className="form-field payload-field">
            <label>PAYLOAD</label>

            <textarea
              value={payload}
              onChange={(e) => setPayload(e.target.value)}
              spellCheck="false"
            />
          </div>

          <div className="form-field">
            <label>
              PRIORITY <span>{priority}</span>
            </label>

            <input
              type="range"
              min="1"
              max="10"
              value={priority}
              onChange={(e) => setPriority(e.target.value)}
            />
          </div>

          <div className="form-field">
            <label>TASK TYPE</label>

            <select
              value={taskType}
              onChange={(e) => {
                const type = e.target.value 
                setTaskType(type) 
                setPayload(DEFAULT_PAYLOADS[type])
              }}
            >
              {(capabilities.length
                ? capabilities
                : ['default']
              ).map((capability) => (
                <option key={capability} value={capability}>
                  {capability}
                </option>
              ))}
            </select>
          </div>

          {error && (
            <div className="form-error">
              {error}
            </div>
          )}

          <button
            className="submit-button"
            disabled={submitting}
            type="submit"
          >
            {submitting ? 'SUBMITTING…' : 'EXECUTE TASK'}
          </button>
        </form>
      )}
    </div>
  )
}