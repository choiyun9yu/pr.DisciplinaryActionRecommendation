import { useState } from 'react'

import { fetchRecommendation } from '../api/client.js'
import ActionDistributionChart from '../components/ActionDistributionChart'
import EmptyState from '../components/EmptyState'
import LoadingOverlay from '../components/LoadingOverlay'
import NeighborTable from '../components/NeighborTable'
import ProbabilityChart from '../components/ProbabilityChart'
import ReviewFlags from '../components/ReviewFlags'
import ScatterPlot from '../components/ScatterPlot'
import SearchForm from '../components/SearchForm'
import SourceChart from '../components/SourceChart'
import SummaryCards from '../components/SummaryCards'

export default function RecommendationPage() {
  const [query, setQuery] = useState('')
  const [topK, setTopK] = useState(5)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')

  const handleSubmit = async () => {
    try {
      setLoading(true)
      setError('')
      const response = await fetchRecommendation({ query, top_k: topK })
      setResult(response)
    } catch (requestError) {
      setError(requestError.message || '추천 요청 중 오류가 발생했습니다.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <LoadingOverlay show={loading} />
      <SearchForm
        query={query}
        setQuery={setQuery}
        topK={topK}
        setTopK={setTopK}
        onSubmit={handleSubmit}
        loading={loading}
      />

      {error ? <div className="panel notice error">{error}</div> : null}

      <SummaryCards result={result} />
      {result ? <ReviewFlags flags={result.review_flags} /> : null}

      {result ? (
        <>
          <div className="charts-grid">
            <ActionDistributionChart data={result.count_distribution} />
            <ProbabilityChart data={result.probability_distribution} />
          </div>
          <SourceChart data={result.source_distribution} />
          <ScatterPlot data={result.scatter} />
          <NeighborTable rows={result.neighbors} />
        </>
      ) : (
        <EmptyState />
      )}
    </>
  )
}
