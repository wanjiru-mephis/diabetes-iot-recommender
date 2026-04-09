import { useEffect, useState } from 'react'
import { api } from '../api'
import RecommendationList from '../components/RecommendationList.jsx'

export default function Recommendations() {
  const [recs, setRecs] = useState([])
  const [err, setErr] = useState(null)
  const [busy, setBusy] = useState(false)

  const load = async () => {
    try { setRecs(await api.getRecommendations()) } catch (e) { setErr(e.message) }
  }
  useEffect(() => { load() }, [])

  const regenerate = async () => {
    setBusy(true); setErr(null)
    try { setRecs(await api.regenerate()) }
    catch (e) { setErr(e.message) }
    finally { setBusy(false) }
  }

  return (
    <div>
      <h2 className="page-title">Recommendations</h2>
      <p className="page-sub">
        Rule-based treatment-support messages. Every recommendation includes an
        explanation and confidence score. Always confirm major changes with your care team.
      </p>

      <div className="disclaimer">
        <strong>Non-diagnostic.</strong> These are educational suggestions, not medical advice.
        In a medical emergency, contact emergency services immediately.
      </div>

      <div className="panel">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <h3 style={{ margin: 0 }}>Active Recommendations</h3>
          <button onClick={regenerate} disabled={busy}>
            {busy ? 'Regenerating…' : 'Regenerate'}
          </button>
        </div>
        {err && <div className="alert error">{err}</div>}
        <RecommendationList items={recs} />
      </div>
    </div>
  )
}
