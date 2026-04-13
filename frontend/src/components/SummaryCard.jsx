export default function SummaryCard({ label, value, hint, accent }) {
  return (
    <div className={`card${accent ? ` accent-${accent}` : ''}`}>
      <div className="label">{label}</div>
      <div className="value">{value ?? '—'}</div>
      {hint && <div className="hint">{hint}</div>}
    </div>
  )
}
