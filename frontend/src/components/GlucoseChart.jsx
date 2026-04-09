import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceArea,
  ResponsiveContainer, Legend,
} from 'recharts'

export default function GlucoseChart({ data, xKey = 'day', lines, height = 300, yDomain = [40, 300] }) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#eef0f4" />
        <XAxis dataKey={xKey} tick={{ fontSize: 11 }} />
        <YAxis domain={yDomain} tick={{ fontSize: 11 }} label={{ value: 'mg/dL', angle: -90, position: 'insideLeft', fontSize: 11 }} />
        <Tooltip />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <ReferenceArea y1={70} y2={180} fill="#16a34a" fillOpacity={0.06} label={{ value: 'Target 70-180', fontSize: 10, fill: '#16a34a' }} />
        {lines.map((l) => (
          <Line
            key={l.key}
            type="monotone"
            dataKey={l.key}
            name={l.name}
            stroke={l.color}
            strokeWidth={2}
            dot={l.dot ?? false}
            connectNulls
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  )
}
