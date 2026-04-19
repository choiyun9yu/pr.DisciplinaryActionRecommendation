const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api/v1'

function resolveApiUrl(path, params = {}) {
  const base = API_BASE_URL.startsWith('http://') || API_BASE_URL.startsWith('https://')
    ? API_BASE_URL
    : `${window.location.origin}${API_BASE_URL}`
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  const url = new URL(`${base}${normalizedPath}`)
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      url.searchParams.set(key, String(value))
    }
  })
  return url.toString()
}

async function request(path, options = {}, params = {}) {
  const headers = { ...(options.headers ?? {}) }
  const isFormData = options.body instanceof FormData
  if (!isFormData && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json'
  }

  const response = await fetch(resolveApiUrl(path, params), {
    ...options,
    headers,
  })

  const contentType = response.headers.get('content-type') || ''
  const data = contentType.includes('application/json')
    ? await response.json().catch(() => ({}))
    : await response.text().catch(() => '')

  if (!response.ok) {
    const detail = data?.detail || data?.message || data || `요청 실패 (${response.status})`
    throw new Error(detail)
  }
  return data
}

export function fetchHealth() {
  return request('/health')
}

export function fetchRecommendation(payload) {
  return request('/recommend', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function fetchTrainingSummary() {
  return request('/training/summary')
}

export function fetchTrainingCases(params) {
  return request('/training/cases', {}, params)
}

export function createTrainingCase(payload) {
  return request('/training/cases', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function updateTrainingCase(rowId, payload) {
  return request(`/training/cases/${rowId}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}

export function deleteTrainingCase(rowId) {
  return request(`/training/cases/${rowId}`, {
    method: 'DELETE',
  })
}

export function importTrainingCases(file, mode = 'append') {
  const form = new FormData()
  form.append('file', file)
  form.append('mode', mode)
  return request('/training/import', {
    method: 'POST',
    body: form,
  })
}

export function retrainArtifacts() {
  return request('/training/retrain', {
    method: 'POST',
  })
}

export async function downloadTrainingExport() {
  const response = await fetch(resolveApiUrl('/training/export'))
  if (!response.ok) {
    let detail = `요청 실패 (${response.status})`
    try {
      const data = await response.json()
      detail = data?.detail || data?.message || detail
    } catch {
      // ignore
    }
    throw new Error(detail)
  }
  const blob = await response.blob()
  const filename = response.headers.get('content-disposition')?.match(/filename="?([^\"]+)"?/)?.[1] || 'audit_cases.csv'
  return { blob, filename }
}
