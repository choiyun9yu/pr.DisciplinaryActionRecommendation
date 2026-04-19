import {
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

function formatSimilarity(value) {
  return typeof value === 'number' ? value.toFixed(3) : '-'
}

function CustomTooltip({ active, payload }) {
  if (!active || !payload || payload.length === 0) {
    return null
  }

  const item = payload[0]?.payload
  if (!item) {
    return null
  }

  return (
    <div className="scatter-tooltip">
      <div className="scatter-tooltip-title">
        {item.kind === 'query' ? '입력 질의' : `유사사례 ${item.rank}위`}
      </div>
      <div><strong>조치:</strong> {item.action_norm}</div>
      <div><strong>감사출처:</strong> {item.audit_source}</div>
      {item.case_id ? <div><strong>Case ID:</strong> {item.case_id}</div> : null}
      {item.kind !== 'query' ? <div><strong>유사도:</strong> {formatSimilarity(item.similarity)}</div> : null}
      <div><strong>지적 제목:</strong> {item.finding_title || '-'}</div>
      <div><strong>세부 설명:</strong> {item.finding_detail || item.text || '-'}</div>
    </div>
  )
}

export default function ScatterPlot({ data }) {
  const neighbors = data.filter((item) => item.kind === 'neighbor')
  const query = data.filter((item) => item.kind === 'query')

  return (
    <section className="panel chart-panel">
      <h3>질의문과 kNN 이웃의 2차원 분포</h3>
      <p className="helper-text">입력 질의는 마름모, 유사사례는 원형으로 표시됩니다. 마커 위에 마우스를 올리면 사례 설명을 볼 수 있습니다.</p>
      <ResponsiveContainer width="100%" height={380}>
        <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
          <CartesianGrid />
          <XAxis type="number" dataKey="x" name="PCA-1" />
          <YAxis type="number" dataKey="y" name="PCA-2" />
          <Tooltip cursor={{ strokeDasharray: '3 3' }} content={<CustomTooltip />} />
          <Legend />
          <Scatter name="유사사례" data={neighbors} shape="circle" />
          <Scatter name="입력 질의" data={query} shape="diamond" />
        </ScatterChart>
      </ResponsiveContainer>
    </section>
  )
}
