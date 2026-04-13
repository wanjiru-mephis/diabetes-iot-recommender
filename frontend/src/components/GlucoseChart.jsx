import {
  ComposedChart, Line, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ReferenceArea, ResponsiveContainer, Legend,
} from 'recharts'

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div style={{
      background: '#1e293b',
      border: 'none',
      borderRadius: 10,
      padding: '10px 14px',
      boxShadow: '0 8px 24px rgba(0,0,0,0.18)',
      color: '#f1f5f9',
      fontSize: 12,
      minWidth: 140,
    }}>
      <div style={{ marginBottom: 8, fontWeight: 600, color: '#94a3b8', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
        {label}
      </div>
      {payload.map((p) => (
        p.value != null && (
          <div key={p.dataKey} style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 4 }}>
            <div style={{ width: 8, height: 8, borderRadius: '50%', background: p.color, flexShrink: 0 }} />
            <span style={{ color: '#94a3b8', flex: 1 }}>{p.name}</span>
            <span style={{ fontWeight: 600 }}>
              {typeof p.value === 'number' ? p.value.toFixed(0) : p.value}
            </span>
            <span style={{ color: '#64748b', fontSize: 10 }}>mg/dL</span>
          </div>
        )
      ))}
    </div>
  )
}

export default function GlucoseChart({ data, xKey = 'day', lines, height = 300, yDomain = [40, 300] }) {
  const firstLine = lines[0]

  return (
    <ResponsiveContainer width="100%" height={height}>
      <ComposedChart data={data} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
        <defs>
          {lines.map((l) => (
            <linearGradient key={`grad-${l.key}`} id={`grad-${l.key}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={l.color} stopOpacity={0.15} />
              <stop offset="95%" stopColor={l.color} stopOpacity={0} />
            </linearGradient>
          ))}
        </defs>

        <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
        <XAxis
          dataKey={xKey}
          tick={{ fontSize: 11, fill: '#94a3b8' }}
          axisLine={{ stroke: '#e2e8f0' }}
          tickLine={false}
        />
        <YAxis
          domain={yDomain}
          tick={{ fontSize: 11, fill: '#94a3b8' }}
          axisLine={false}
          tickLine={false}
          label={{ value: 'mg/dL', angle: -90, position: 'insideLeft', fontSize: 11, fill: '#94a3b8' }}
        />
        <Tooltip content={<CustomTooltip />} />
        <Legend
          wrapperStyle={{ fontSize: 12, paddingTop: 12 }}
          iconType="circle"
          iconSize={8}
        />
        <ReferenceArea
          y1={70} y2={180}
          fill="#16a34a"
          fillOpacity={0.05}
          label={{ value: 'Target 70–180', fontSize: 10, fill: '#16a34a', position: 'insideTopRight' }}
        />

        {lines.map((l, i) => (
          i === 0 ? (
            <Area
              key={l.key}
              type="monotone"
              dataKey={l.key}
              name={l.name}
              stroke={l.color}
              strokeWidth={2.5}
              fill={`url(#grad-${l.key})`}
              dot={false}
              connectNulls
            />
          ) : (
            <Line
              key={l.key}
              type="monotone"
              dataKey={l.key}
              name={l.name}
              stroke={l.color}
              strokeWidth={2}
              dot={l.dot ?? false}
              strokeDasharray={i > 1 ? '5 3' : undefined}
              connectNulls
            />
          )
        ))}
      </ComposedChart>
    </ResponsiveContainer>
  )
}
