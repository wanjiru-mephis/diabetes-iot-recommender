// Thin fetch wrapper around the FastAPI backend.
// Vite proxies /api/* to http://localhost:8000 in dev.

const BASE = ''

async function request(path, opts = {}) {
  const res = await fetch(`${BASE}${path}`, opts)
  if (!res.ok) {
    let detail
    try {
      const body = await res.json()
      detail = body.detail || JSON.stringify(body)
    } catch {
      detail = await res.text()
    }
    throw new Error(`HTTP ${res.status}: ${detail}`)
  }
  return res.json()
}

export const api = {
  getSummary:        () => request('/api/dashboard/summary'),
  getDailyFeatures:  (limit = 30) => request(`/api/features/daily?limit=${limit}`),
  getRawEvents:      (hours = 48) => request(`/api/features/raw?hours=${hours}`),
  getRecommendations:() => request('/api/recommendations'),
  regenerate:        () => request('/api/recommendations/regenerate', { method: 'POST' }),
  listJobs:          () => request('/api/ingest/jobs'),
  uploadFile: (file) => {
    const fd = new FormData()
    fd.append('file', file)
    return request('/api/ingest/upload', { method: 'POST', body: fd })
  },
}
