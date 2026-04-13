import { useEffect, useState } from 'react'
import { api } from '../api'
import UploadForm from '../components/UploadForm.jsx'

function StatusPill({ status }) {
  const s = status?.toLowerCase()
  let cls = 'pending'
  if (s === 'done' || s === 'completed') cls = 'done'
  else if (s === 'error' || s === 'failed') cls = 'error'
  else if (s === 'processing') cls = 'processing'
  return <span className={`status-pill ${cls}`}>{status}</span>
}

export default function Upload() {
  const [jobs, setJobs] = useState([])
  const [err, setErr] = useState(null)

  const load = async () => {
    try { setJobs(await api.listJobs()) } catch (e) { setErr(e.message) }
  }
  useEffect(() => { load() }, [])

  return (
    <div>
      <h2 className="page-title">Upload Glucose Data</h2>
      <p className="page-sub">
        Upload a FreeStyle Libre CSV export or a generic glucose CSV/JSON file.
        The system handles duplicates automatically.
      </p>

      <div className="panel">
        <UploadForm onUploaded={load} />
      </div>

      <div className="panel">
        <h3>Import History</h3>
        {err && <div className="alert error">{err}</div>}
        {jobs.length === 0 ? (
          <div className="loading">No uploads yet.</div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>When</th>
                  <th>File</th>
                  <th>Format</th>
                  <th>Status</th>
                  <th>Parsed</th>
                  <th>Inserted</th>
                  <th>Skipped</th>
                </tr>
              </thead>
              <tbody>
                {jobs.map((j) => (
                  <tr key={j.id}>
                    <td style={{ color: 'var(--muted)', whiteSpace: 'nowrap' }}>
                      {new Date(j.created_at).toLocaleString()}
                    </td>
                    <td style={{ fontWeight: 500 }}>{j.filename}</td>
                    <td style={{ color: 'var(--muted)' }}>{j.source_format}</td>
                    <td><StatusPill status={j.status} /></td>
                    <td>{j.rows_parsed}</td>
                    <td>{j.rows_inserted}</td>
                    <td style={{ color: 'var(--muted)' }}>{j.rows_skipped}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
