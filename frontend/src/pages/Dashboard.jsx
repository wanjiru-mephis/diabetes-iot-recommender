import { useEffect, useState } from 'react'
import { api } from '../api'
import SummaryCard from '../components/SummaryCard.jsx'
import GlucoseChart from '../components/GlucoseChart.jsx'
import RecommendationList from '../components/RecommendationList.jsx'

export default function Dashboard() {
  const [summary, setSummary] = useState(null)
  const [daily, setDaily] = useState([])
  const [recs, setRecs] = useState([])
  const [err, setErr] = useState(null)
  const [loading, setLoading] = useState(true)

  const load = async () => {
    setLoading(true); setErr(null)
    try {
      const [s, d, r] = await Promise.all([
        api.getSummary(), api.getDailyFeatures(30), api.getRecommendations(),
      ])
      setSummary(s); setDaily(d); setRecs(r)
    } catch (e) { setErr(e.message) }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  const chartData = daily.map((d) => ({
    day: d.day,
    mean: d.mean_glucose,
    rolling_7d: d.rolling_7d_mean,
    tir: d.time_in_range_pct,
  }))

  return (
    <div>
      <h2 className="page-title">Dashboard</h2>
      <p className="page-sub">Non-diagnostic overview of your recent glucose patterns.</p>

      <div className="disclaimer">
        <strong>Disclaimer:</strong> This system is for treatment-support and education only.
        It does not diagnose, prescribe, or replace advice from your healthcare team.
      </div>

      {err && <div className="alert error">{err}</div>}
      {loading && <div className="loading">Loading…</div>}

      {summary && (
        <div className="cards">
          <SummaryCard label="Total Readings" value={summary.total_readings} hint={`${summary.days_covered} days covered`} />
          <SummaryCard label="Latest Mean" value={summary.latest_mean_glucose ? `${summary.latest_mean_glucose.toFixed(0)} mg/dL` : '—'} hint={summary.latest_day ?? ''} />
          <SummaryCard label="7-Day Average" value={summary.rolling_7d_mean ? `${summary.rolling_7d_mean.toFixed(0)} mg/dL` : '—'} />
          <SummaryCard label="Latest Time in Range" value={summary.latest_tir_pct != null ? `${summary.latest_tir_pct.toFixed(0)}%` : '—'} hint="Target: ≥ 70%" />
          <SummaryCard label="Estimated A1c" value={summary.estimated_a1c ? `${summary.estimated_a1c.toFixed(1)}%` : '—'} hint="ADAG formula" />
          <SummaryCard label="Open Recommendations" value={summary.open_recommendations} />
        </div>
      )}

      {chartData.length > 0 && (
        <div className="panel">
          <h3>Daily Mean Glucose (last 30 days)</h3>
          <GlucoseChart
            data={chartData}
            xKey="day"
            lines={[
              { key: 'mean', name: 'Daily mean', color: '#2563eb' },
              { key: 'rolling_7d', name: '7-day rolling', color: '#d97706' },
            ]}
          />
        </div>
      )}

      <div className="panel">
        <h3>Top Recommendations</h3>
        <RecommendationList items={recs.slice(0, 5)} />
      </div>
    </div>
  )
}
