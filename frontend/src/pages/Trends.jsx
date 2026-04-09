import { useEffect, useState } from 'react'
import { api } from '../api'
import GlucoseChart from '../components/GlucoseChart.jsx'

export default function Trends() {
  const [daily, setDaily] = useState([])
  const [raw, setRaw] = useState([])
  const [err, setErr] = useState(null)

  useEffect(() => {
    (async () => {
      try {
        const [d, r] = await Promise.all([api.getDailyFeatures(60), api.getRawEvents(72)])
        setDaily(d); setRaw(r)
      } catch (e) { setErr(e.message) }
    })()
  }, [])

  const dailyChart = daily.map((d) => ({
    day: d.day,
    mean: d.mean_glucose,
    min: d.min_glucose,
    max: d.max_glucose,
    rolling_3d: d.rolling_3d_mean,
    rolling_7d: d.rolling_7d_mean,
  }))

  const rawChart = raw.map((e) => ({
    ts: new Date(e.timestamp).toLocaleString([], { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' }),
    glucose: e.glucose_mgdl,
  }))

  return (
    <div>
      <h2 className="page-title">Trends</h2>
      <p className="page-sub">Rolling averages, daily ranges, and recent raw readings.</p>
      {err && <div className="alert error">{err}</div>}

      <div className="panel">
        <h3>Daily Min / Mean / Max</h3>
        <GlucoseChart
          data={dailyChart}
          xKey="day"
          lines={[
            { key: 'max', name: 'Daily max', color: '#dc2626' },
            { key: 'mean', name: 'Daily mean', color: '#2563eb' },
            { key: 'min', name: 'Daily min', color: '#16a34a' },
          ]}
        />
      </div>

      <div className="panel">
        <h3>Rolling Averages</h3>
        <GlucoseChart
          data={dailyChart}
          xKey="day"
          yDomain={[80, 250]}
          lines={[
            { key: 'mean', name: 'Daily mean', color: '#94a3b8' },
            { key: 'rolling_3d', name: '3-day rolling', color: '#2563eb' },
            { key: 'rolling_7d', name: '7-day rolling', color: '#d97706' },
          ]}
        />
      </div>

      <div className="panel">
        <h3>Recent Raw Readings</h3>
        {rawChart.length === 0 ? (
          <div className="loading">No raw readings available.</div>
        ) : (
          <GlucoseChart
            data={rawChart}
            xKey="ts"
            height={260}
            lines={[{ key: 'glucose', name: 'Glucose (mg/dL)', color: '#2563eb' }]}
          />
        )}
      </div>

      <div className="panel">
        <h3>Daily Features Table</h3>
        <table>
          <thead>
            <tr>
              <th>Day</th><th>Readings</th><th>Mean</th><th>Min</th><th>Max</th>
              <th>CV%</th><th>TIR%</th><th>7d mean</th><th>eA1c</th>
            </tr>
          </thead>
          <tbody>
            {[...daily].reverse().map((d) => (
              <tr key={d.day}>
                <td>{d.day}</td>
                <td>{d.readings_count}</td>
                <td>{d.mean_glucose?.toFixed(0)}</td>
                <td>{d.min_glucose?.toFixed(0)}</td>
                <td>{d.max_glucose?.toFixed(0)}</td>
                <td>{d.cv_glucose?.toFixed(1)}</td>
                <td>{d.time_in_range_pct?.toFixed(0)}</td>
                <td>{d.rolling_7d_mean?.toFixed(0)}</td>
                <td>{d.estimated_a1c?.toFixed(1)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
