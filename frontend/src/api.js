const API = '/api'

async function request(path, options = {}) {
  const response = await fetch(`${API}${path}`, options)

  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`)
  }

  return response.json()
}

export function getStats() {
  return request('/stats')
}

export function submitTask(task) {
  return request('/tasks', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(task),
  })
}