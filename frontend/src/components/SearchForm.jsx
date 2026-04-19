export default function SearchForm({ query, setQuery, topK, setTopK, onSubmit, loading }) {
  return (
    <section className="panel">
      <h2>지적 내용 입력</h2>
      <p className="helper-text">
        입력 형식은 자유 자연어입니다. 예: “인사위원회 개최 절차 검토를 소홀히 하여 규정 위반이 발생하고,
        관리감독 책임도 인정되는 사안”
      </p>
      <textarea
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        placeholder="지적 내용을 자연어로 입력하세요."
        rows={7}
      />
      <div className="form-row">
        <label className="number-field">
          <span>유사사례 수</span>
          <input
            type="number"
            min="3"
            max="20"
            value={topK}
            onChange={(event) => {
              const nextValue = Number(event.target.value)
              setTopK(Number.isNaN(nextValue) ? 5 : nextValue)
            }}
          />
        </label>
        <button onClick={onSubmit} disabled={loading || !query.trim()}>
          {loading ? '추천 중...' : '추천 실행'}
        </button>
      </div>
    </section>
  )
}
