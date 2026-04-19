import { useCallback, useEffect, useMemo, useState } from 'react'

import {
  createTrainingCase,
  deleteTrainingCase,
  downloadTrainingExport,
  fetchTrainingCases,
  fetchTrainingSummary,
  importTrainingCases,
  retrainArtifacts,
  updateTrainingCase,
} from '../api/client.js'
import LoadingOverlay from '../components/LoadingOverlay.jsx'

const EMPTY_FORM = {
  audit_source: '',
  finding_title: '',
  finding_detail: '',
  action: '',
}

export default function TrainingPage({ onArtifactsChanged }) {
  const [summary, setSummary] = useState(null)
  const [dataset, setDataset] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  const [searchInput, setSearchInput] = useState('')
  const [appliedSearch, setAppliedSearch] = useState('')
  const [actionFilter, setActionFilter] = useState('')
  const [auditSourceFilter, setAuditSourceFilter] = useState('')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)

  const [form, setForm] = useState(EMPTY_FORM)
  const [editingRowId, setEditingRowId] = useState(null)
  const [importMode, setImportMode] = useState('append')
  const [importFile, setImportFile] = useState(null)

  const refresh = useCallback(async () => {
    try {
      setLoading(true)
      setError('')
      const [summaryResponse, datasetResponse] = await Promise.all([
        fetchTrainingSummary(),
        fetchTrainingCases({
          search: appliedSearch,
          action_filter: actionFilter,
          audit_source_filter: auditSourceFilter,
          page,
          page_size: pageSize,
        }),
      ])
      setSummary(summaryResponse)
      setDataset(datasetResponse)
    } catch (requestError) {
      setError(requestError.message || '학습 데이터 로딩 중 오류가 발생했습니다.')
    } finally {
      setLoading(false)
    }
  }, [actionFilter, appliedSearch, auditSourceFilter, page, pageSize])

  useEffect(() => {
    refresh()
  }, [refresh])

  const availableActions = dataset?.available_actions ?? []
  const availableSources = dataset?.available_sources ?? []

  const handleFormChange = (key, value) => {
    setForm((current) => ({ ...current, [key]: value }))
  }

  const resetForm = () => {
    setForm(EMPTY_FORM)
    setEditingRowId(null)
  }

  const handleSaveCase = async () => {
    try {
      setLoading(true)
      setError('')
      setNotice('')
      if (editingRowId) {
        const response = await updateTrainingCase(editingRowId, form)
        setNotice(response.message)
      } else {
        const response = await createTrainingCase(form)
        setNotice(response.message)
      }
      resetForm()
      setPage(1)
      await refresh()
    } catch (requestError) {
      setError(requestError.message || '사례 저장 중 오류가 발생했습니다.')
    } finally {
      setLoading(false)
    }
  }

  const handleEdit = (row) => {
    setEditingRowId(row.row_id)
    setForm({
      audit_source: row.audit_source,
      finding_title: row.finding_title,
      finding_detail: row.finding_detail,
      action: row.action,
    })
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const handleDelete = async (rowId) => {
    const confirmed = window.confirm('이 사례를 삭제할까요? 삭제 후에는 재학습 전까지 기존 아티팩트가 유지됩니다.')
    if (!confirmed) return

    try {
      setLoading(true)
      setError('')
      setNotice('')
      const response = await deleteTrainingCase(rowId)
      setNotice(response.message)
      if (editingRowId === rowId) {
        resetForm()
      }
      await refresh()
    } catch (requestError) {
      setError(requestError.message || '사례 삭제 중 오류가 발생했습니다.')
    } finally {
      setLoading(false)
    }
  }

  const handleImport = async () => {
    if (!importFile) {
      setError('가져올 CSV 또는 Excel 파일을 선택해 주세요.')
      return
    }

    try {
      setLoading(true)
      setError('')
      setNotice('')
      const response = await importTrainingCases(importFile, importMode)
      setNotice(response.message)
      setImportFile(null)
      const input = document.getElementById('import-file-input')
      if (input) input.value = ''
      setPage(1)
      await refresh()
    } catch (requestError) {
      setError(requestError.message || '파일 가져오기 중 오류가 발생했습니다.')
    } finally {
      setLoading(false)
    }
  }

  const handleRetrain = async () => {
    try {
      setLoading(true)
      setError('')
      setNotice('')
      const response = await retrainArtifacts()
      setNotice(`${response.message} (${response.num_cases}건 / best_k=${response.best_k})`)
      await refresh()
      if (onArtifactsChanged) {
        await onArtifactsChanged()
      }
    } catch (requestError) {
      setError(requestError.message || '재학습 중 오류가 발생했습니다.')
    } finally {
      setLoading(false)
    }
  }

  const handleExport = async () => {
    try {
      setLoading(true)
      setError('')
      const { blob, filename } = await downloadTrainingExport()
      const url = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = filename
      document.body.appendChild(anchor)
      anchor.click()
      anchor.remove()
      URL.revokeObjectURL(url)
    } catch (requestError) {
      setError(requestError.message || '내보내기 중 오류가 발생했습니다.')
    } finally {
      setLoading(false)
    }
  }

  const artifactStatusLabel = useMemo(() => {
    if (!summary) return '-'
    if (!summary.artifact_ready) return '아티팩트 없음'
    if (summary.needs_retrain) return '재학습 필요'
    return '최신 상태'
  }, [summary])

  return (
    <div className="training-page">
      <LoadingOverlay show={loading} />

      {error ? <div className="panel notice error">{error}</div> : null}
      {notice ? <div className="panel notice success">{notice}</div> : null}

      <div className="metrics-grid training-metrics-grid">
        <div className="metric-card">
          <div className="metric-title">학습 데이터 건수</div>
          <div className="metric-value">{summary?.num_cases ?? 0}</div>
          <div className="metric-subtext">CSV 기준 전체 사례 수</div>
        </div>
        <div className="metric-card">
          <div className="metric-title">감사출처 수</div>
          <div className="metric-value">{summary?.unique_audit_sources ?? 0}</div>
          <div className="metric-subtext">서로 다른 감사 출처 개수</div>
        </div>
        <div className="metric-card">
          <div className="metric-title">아티팩트 상태</div>
          <div className="metric-value status-value">{artifactStatusLabel}</div>
          <div className="metric-subtext">{summary?.artifact_trained_at ? `마지막 학습: ${summary.artifact_trained_at}` : '아직 학습 이력이 없습니다.'}</div>
        </div>
      </div>

      <div className="panel training-toolbar">
        <div>
          <h2>학습 데이터 관리</h2>
          <p className="helper-text">
            audit_source, finding_title, finding_detail, action 컬럼을 직접 CSV로 만들지 않아도 여기서 사례를 추가·수정·삭제하고,
            원할 때 재학습을 실행할 수 있습니다.
          </p>
          <div className="helper-text small-text">데이터 파일: {summary?.dataset_path ?? '-'}</div>
        </div>
        <div className="toolbar-actions">
          <button type="button" className="secondary-button" onClick={refresh}>새로고침</button>
          <button type="button" className="secondary-button" onClick={handleExport}>CSV 내보내기</button>
          <button type="button" onClick={handleRetrain} disabled={(summary?.num_cases ?? 0) < 5}>재학습 실행</button>
        </div>
      </div>

      {summary?.needs_retrain ? (
        <div className="panel notice warning">
          학습 데이터가 변경되어 현재 추천 아티팩트가 최신이 아닙니다. 사례를 정리한 뒤 <strong>재학습 실행</strong>을 눌러 반영하세요.
        </div>
      ) : null}

      {summary?.message ? <div className="panel notice warning">{summary.message}</div> : null}

      <div className="training-layout">
        <div className="panel">
          <h3>{editingRowId ? `사례 수정 #${editingRowId}` : '사례 직접 입력'}</h3>
          <div className="field-grid">
            <label>
              감사출처
              <input value={form.audit_source} onChange={(event) => handleFormChange('audit_source', event.target.value)} placeholder="예: 2024 안동사업소 종합감사" />
            </label>
            <label>
              조치 방안
              <input value={form.action} onChange={(event) => handleFormChange('action', event.target.value)} placeholder="예: 시정, 경고, 시정(주의 1명)" />
            </label>
          </div>
          <label>
            지적 제목
            <input value={form.finding_title} onChange={(event) => handleFormChange('finding_title', event.target.value)} placeholder="예: 법인카드 부정집행" />
          </label>
          <label>
            지적 세부 설명
            <textarea rows="7" value={form.finding_detail} onChange={(event) => handleFormChange('finding_detail', event.target.value)} placeholder="실제 감사 지적 문장을 그대로 입력하세요." />
          </label>
          <div className="form-actions-row">
            {editingRowId ? <button type="button" className="secondary-button" onClick={resetForm}>수정 취소</button> : null}
            <button type="button" onClick={handleSaveCase}>{editingRowId ? '사례 수정 저장' : '사례 추가'}</button>
          </div>
        </div>

        <div className="panel">
          <h3>CSV / Excel 가져오기</h3>
          <p className="helper-text">기존에 가지고 있는 감사 사례 파일을 append 또는 replace 방식으로 반영할 수 있습니다.</p>
          <label>
            반영 방식
            <select value={importMode} onChange={(event) => setImportMode(event.target.value)}>
              <option value="append">기존 데이터에 추가</option>
              <option value="replace">기존 데이터를 완전히 교체</option>
            </select>
          </label>
          <label>
            파일 선택
            <input id="import-file-input" type="file" accept=".csv,.xlsx,.xls" onChange={(event) => setImportFile(event.target.files?.[0] ?? null)} />
          </label>
          <div className="helper-text small-text">필수 컬럼: audit_source, finding_title, finding_detail, action</div>
          <button type="button" onClick={handleImport}>파일 가져오기</button>
        </div>
      </div>

      <div className="panel">
        <h3>데이터셋 검색 및 필터</h3>
        <div className="filters-grid">
          <label>
            검색어
            <input value={searchInput} onChange={(event) => setSearchInput(event.target.value)} placeholder="감사출처, 지적 제목, 상세 설명, 조치" />
          </label>
          <label>
            조치 분류 미리보기
            <select value={actionFilter} onChange={(event) => { setActionFilter(event.target.value); setPage(1) }}>
              <option value="">전체</option>
              {availableActions.map((action) => <option key={action} value={action}>{action}</option>)}
            </select>
          </label>
          <label>
            감사출처
            <select value={auditSourceFilter} onChange={(event) => { setAuditSourceFilter(event.target.value); setPage(1) }}>
              <option value="">전체</option>
              {availableSources.map((source) => <option key={source} value={source}>{source}</option>)}
            </select>
          </label>
          <label>
            페이지 크기
            <select value={pageSize} onChange={(event) => { setPageSize(Number(event.target.value)); setPage(1) }}>
              <option value={10}>10</option>
              <option value={20}>20</option>
              <option value={50}>50</option>
            </select>
          </label>
        </div>
        <div className="form-actions-row compact-actions">
          <button type="button" className="secondary-button" onClick={() => { setSearchInput(''); setAppliedSearch(''); setActionFilter(''); setAuditSourceFilter(''); setPage(1) }}>필터 초기화</button>
          <button type="button" onClick={() => { setAppliedSearch(searchInput); setPage(1) }}>검색 적용</button>
        </div>
      </div>

      <div className="panel">
        <div className="table-toolbar">
          <div>
            <h3>학습 사례 목록</h3>
            <div className="helper-text small-text">총 {dataset?.total ?? 0}건 · 페이지 {dataset?.page ?? 1} / {dataset?.total_pages ?? 1}</div>
          </div>
          <div className="pagination-buttons">
            <button type="button" className="secondary-button" disabled={(dataset?.page ?? 1) <= 1} onClick={() => setPage((current) => Math.max(1, current - 1))}>이전</button>
            <button type="button" className="secondary-button" disabled={(dataset?.page ?? 1) >= (dataset?.total_pages ?? 1)} onClick={() => setPage((current) => Math.min(dataset?.total_pages ?? current, current + 1))}>다음</button>
          </div>
        </div>

        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>#</th>
                <th>감사출처</th>
                <th>지적 제목</th>
                <th>세부 설명</th>
                <th>원문 조치</th>
                <th>정규화 미리보기</th>
                <th>작업</th>
              </tr>
            </thead>
            <tbody>
              {(dataset?.items ?? []).length === 0 ? (
                <tr>
                  <td colSpan="7">조건에 맞는 사례가 없습니다.</td>
                </tr>
              ) : (
                dataset.items.map((row) => (
                  <tr key={row.row_id}>
                    <td>{row.row_id}</td>
                    <td>{row.audit_source}</td>
                    <td>{row.finding_title}</td>
                    <td className="multiline-cell">{row.finding_detail}</td>
                    <td>{row.action}</td>
                    <td>{row.action_norm_preview || '-'}</td>
                    <td>
                      <div className="row-actions">
                        <button type="button" className="secondary-button small-button" onClick={() => handleEdit(row)}>수정</button>
                        <button type="button" className="danger-button small-button" onClick={() => handleDelete(row.row_id)}>삭제</button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
