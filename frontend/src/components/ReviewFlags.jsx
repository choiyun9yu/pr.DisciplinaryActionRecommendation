export default function ReviewFlags({ flags }) {
  if (!flags || flags.length === 0) {
    return <div className="panel notice success">유사 사례 근거가 비교적 일관됩니다.</div>
  }

  return (
    <div className="panel notice warning">
      <strong>검토 포인트</strong>
      <ul>
        {flags.map((flag) => (
          <li key={flag}>{flag}</li>
        ))}
      </ul>
    </div>
  )
}
