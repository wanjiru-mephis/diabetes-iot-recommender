export default function RecommendationList({ items }) {
  if (!items || items.length === 0) {
    return <div className="loading">No recommendations yet. Upload some data first.</div>
  }

  const order = { high: 0, medium: 1, low: 2, info: 3 }
  const sorted = [...items].sort((a, b) => (order[a.severity] ?? 9) - (order[b.severity] ?? 9))

  return (
    <div>
      {sorted.map((r) => {
        const pct = Math.round(r.confidence * 100)
        return (
          <div key={r.id} className={`rec ${r.severity}`}>
            <div className="title">
              <span>{r.title}</span>
              <span className="badge">{r.severity}</span>
            </div>
            <div className="message">{r.message}</div>
            <div className="explanation">
              <strong>Why:</strong> {r.explanation}
              <span style={{ marginLeft: 8, opacity: 0.55, fontSize: 11 }}>[{r.rule_id}]</span>
            </div>
            <div className="confidence-row">
              <span className="confidence-label">Confidence</span>
              <div className="confidence-bar">
                <div className="confidence-fill" style={{ width: `${pct}%` }} />
              </div>
              <span className="confidence-pct">{pct}%</span>
            </div>
          </div>
        )
      })}
    </div>
  )
}
