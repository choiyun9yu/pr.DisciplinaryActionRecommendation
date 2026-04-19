export default function NeighborTable({ rows }) {
  return (
    <section className="panel">
      <h3>최근접 유사사례</h3>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Case ID</th>
              <th>순위</th>
              <th>유사도</th>
              <th>정규화 조치</th>
              <th>조치 그룹</th>
              <th>원본 조치</th>
              <th>감사출처</th>
              <th>지적 제목</th>
              <th>세부 설명</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={`${row.case_id}-${row.rank}`}>
                <td>{row.case_id}</td>
                <td>{row.rank}</td>
                <td>{row.similarity.toFixed(3)}</td>
                <td>{row.action_norm}</td>
                <td>{row.action_group}</td>
                <td>{row.action_raw}</td>
                <td>{row.audit_source}</td>
                <td>{row.finding_title}</td>
                <td>{row.finding_detail}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}
