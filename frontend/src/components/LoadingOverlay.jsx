export default function LoadingOverlay({ show }) {
  if (!show) return null

  return (
    <div className="loading-overlay" role="status" aria-live="polite">
      <div className="loading-card">
        <div className="spinner" />
        <div className="loading-title">유사사례를 검색하고 있습니다</div>
        <div className="loading-subtext">임베딩 생성 → 최근접 사례 검색 → 조치 확률 계산</div>
      </div>
    </div>
  )
}
