import { useCallback, useEffect, useMemo, useState } from 'react'

import { fetchHealth } from './api/client'
import RecommendationPage from './pages/RecommendationPage'
import TrainingPage from './pages/TrainingPage'

const ROUTES = {
  recommend: '#/recommend',
  training: '#/training',
}

function resolveRoute(hashValue) {
  if (hashValue === ROUTES.training) return 'training'
  return 'recommend'
}

export default function App() {
  const [health, setHealth] = useState(null)
  const [error, setError] = useState('')
  const [route, setRoute] = useState(resolveRoute(window.location.hash))

  const loadHealth = useCallback(async () => {
    try {
      const response = await fetchHealth()
      setHealth(response)
    } catch (requestError) {
      setError(requestError.message || '백엔드 연결에 실패했습니다.')
    }
  }, [])

  useEffect(() => {
    if (!window.location.hash) {
      window.location.hash = ROUTES.recommend
    }
    const onHashChange = () => setRoute(resolveRoute(window.location.hash))
    window.addEventListener('hashchange', onHashChange)
    return () => window.removeEventListener('hashchange', onHashChange)
  }, [])

  useEffect(() => {
    loadHealth()
  }, [loadHealth])

  const activeTitle = useMemo(() => {
    return route === 'training' ? '학습 데이터 관리' : '추천 실행'
  }, [route])

  return (
    <div className="app-shell">
      <header className="app-header">
        <div>
          <h1>감사 지적 내용 기반 조치 추천기</h1>
          <p>추천 화면과 학습 전용 관리 화면을 분리한 React View + Python MVCS 구조</p>
          <div className="nav-pills">
            <a className={`nav-pill ${route === 'recommend' ? 'active' : ''}`} href={ROUTES.recommend}>추천 페이지</a>
            <a className={`nav-pill ${route === 'training' ? 'active' : ''}`} href={ROUTES.training}>학습 데이터 관리</a>
          </div>
        </div>

        <div className="health-card">
          <div className="health-title">백엔드 상태</div>
          {health ? (
            <>
              <div>상태: {health.status}</div>
              <div>데이터: {health.num_cases}건</div>
              <div>best k: {health.best_k}</div>
              <div className="truncate">모델: {health.model_name || '-'}</div>
              <div className="truncate">현재 화면: {activeTitle}</div>
              <div>스키마: {health.required_columns?.join(', ') || '-'}</div>
            </>
          ) : (
            <div>확인 중...</div>
          )}
        </div>
      </header>

      {health?.status === 'not_ready' ? (
        <div className="panel notice warning">
          <strong>아티팩트가 아직 없습니다.</strong>
          <div>{health.message}</div>
          <div className="small-text">먼저 학습 데이터 관리 화면에서 사례를 넣고 재학습을 실행하면 됩니다.</div>
        </div>
      ) : null}

      {error ? <div className="panel notice error">{error}</div> : null}

      {route === 'training' ? <TrainingPage onArtifactsChanged={loadHealth} /> : <RecommendationPage />}
    </div>
  )
}
