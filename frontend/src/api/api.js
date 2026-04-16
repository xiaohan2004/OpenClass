import { apiRequest } from './httpClient'

export function fetchCourses() {
  return apiRequest('/api/courses')
}

export function fetchCourseById(courseId) {
  return apiRequest(`/api/courses/${courseId}`)
}

export function fetchSessionsByCourse(courseId) {
  return apiRequest(`/api/courses/${courseId}/sessions`)
}

export function fetchSessions() {
  return apiRequest('/api/sessions')
}

export function fetchSessionById(sessionId) {
  return apiRequest(`/api/sessions/${sessionId}`)
}

export function fetchSessionTranscripts(sessionId) {
  return apiRequest(`/api/sessions/${sessionId}/transcripts`)
}

export function fetchTranscripts() {
  return apiRequest('/api/transcripts')
}

export function fetchTranscriptById(transcriptId) {
  return apiRequest(`/api/transcripts/${transcriptId}`)
}

export function fetchSessionSummaries(sessionId) {
  return apiRequest(`/api/sessions/${sessionId}/segment-summaries`)
}

export function fetchSummaries() {
  return apiRequest('/api/segment-summaries')
}

export function fetchSummaryById(summaryId) {
  return apiRequest(`/api/segment-summaries/${summaryId}`)
}

export function fetchSessionQuestions(sessionId) {
  return apiRequest(`/api/sessions/${sessionId}/questions`)
}

export function fetchQuestions() {
  return apiRequest('/api/questions')
}

export function fetchQuestionById(questionId) {
  return apiRequest(`/api/questions/${questionId}`)
}

export function fetchStatsTotals() {
  return apiRequest('/api/stats/totals')
}

export function fetchStatsTotalById(statsTotalId) {
  return apiRequest(`/api/stats/totals/${statsTotalId}`)
}

export function fetchStatsDailies() {
  return apiRequest('/api/stats/dailies')
}

export function fetchStatsHourlies() {
  return apiRequest('/api/stats/hourlies')
}

export function fetchRelayLogs(params = {}) {
  const query = new URLSearchParams()

  if (params.serviceType) {
    query.set('service_type', params.serviceType)
  }

  if (Number.isFinite(params.limit)) {
    query.set('limit', String(params.limit))
  }

  if (Number.isFinite(params.offset)) {
    query.set('offset', String(params.offset))
  }

  const queryString = query.toString()
  const path = queryString ? `/api/relay-logs?${queryString}` : '/api/relay-logs'
  return apiRequest(path)
}

export function fetchRelayLogById(relayLogId) {
  return apiRequest(`/api/relay-logs/${relayLogId}`)
}

export function createCourse(payload) {
  return apiRequest('/api/courses', {
    method: 'POST',
    body: JSON.stringify(payload)
  })
}

export function updateCourse(courseId, payload) {
  return apiRequest(`/api/courses/${courseId}`, {
    method: 'PUT',
    body: JSON.stringify(payload)
  })
}

export function patchCourse(courseId, payload) {
  return apiRequest(`/api/courses/${courseId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload)
  })
}

export function deleteCourse(courseId) {
  return apiRequest(`/api/courses/${courseId}`, {
    method: 'DELETE'
  })
}

export function createSession(payload) {
  return apiRequest('/api/sessions', {
    method: 'POST',
    body: JSON.stringify(payload)
  })
}

export function updateSession(sessionId, payload) {
  return apiRequest(`/api/sessions/${sessionId}`, {
    method: 'PUT',
    body: JSON.stringify(payload)
  })
}

export function patchSession(sessionId, payload) {
  return apiRequest(`/api/sessions/${sessionId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload)
  })
}

export function deleteSession(sessionId) {
  return apiRequest(`/api/sessions/${sessionId}`, {
    method: 'DELETE'
  })
}

export function startSession(sessionId, startTime) {
  return apiRequest(`/api/sessions/${sessionId}/start`, {
    method: 'POST',
    body: JSON.stringify({ start_time: startTime })
  })
}

export function pauseSession(sessionId) {
  return apiRequest(`/api/sessions/${sessionId}/pause`, {
    method: 'POST'
  })
}

export function endSession(sessionId, endTime) {
  return apiRequest(`/api/sessions/${sessionId}/end`, {
    method: 'POST',
    body: JSON.stringify({ end_time: endTime })
  })
}

export function patchQuestion(questionId, payload) {
  return apiRequest(`/api/questions/${questionId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload)
  })
}
