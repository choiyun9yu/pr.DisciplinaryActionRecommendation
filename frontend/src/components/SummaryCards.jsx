function Card({ title, value, subtext }) {
  return (
    <div className="metric-card">
      <div className="metric-title">{title}</div>
      <div className="metric-value">{value}</div>
      {subtext ? <div className="metric-subtext">{subtext}</div> : null}
    </div>
  )
}

export default function SummaryCards({ result }) {
  if (!result) return null

  return (
    <section className="metrics-grid">
      <Card title="추천 조치" value={result.predicted_action} subtext={result.predicted_group} />
      <Card
        title="추천 확률"
        value={`${(result.predicted_probability * 100).toFixed(1)}%`}
        subtext={result.confidence_band}
      />
      <Card title="최상위 유사도" value={result.top_similarity.toFixed(3)} subtext="최근접 사례 기준" />
    </section>
  )
}
