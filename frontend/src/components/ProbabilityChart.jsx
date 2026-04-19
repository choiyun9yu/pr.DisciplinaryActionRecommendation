import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

export default function ProbabilityChart({ data }) {
  return (
    <section className="panel chart-panel">
      <h3>추천 조치 확률 분포</h3>
      <ResponsiveContainer width="100%" height={320}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="action" />
          <YAxis domain={[0, 1]} />
          <Tooltip formatter={(value) => `${(value * 100).toFixed(1)}%`} />
          <Bar dataKey="probability" />
        </BarChart>
      </ResponsiveContainer>
    </section>
  )
}
