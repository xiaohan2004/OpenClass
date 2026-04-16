import { apiRequest } from './httpClient'

export function fetchCourses() {
  return apiRequest('/api/courses')
}

export function fetchSessionsByCourse(courseId) {
  return apiRequest(`/api/courses/${courseId}/sessions`)
}

export function fetchSessionTranscripts(sessionId) {
  return apiRequest(`/api/sessions/${sessionId}/transcripts`)
}

export function fetchSessionSummaries(sessionId) {
  return apiRequest(`/api/sessions/${sessionId}/segment-summaries`)
}

export function fetchSessionQuestions(sessionId) {
  return apiRequest(`/api/sessions/${sessionId}/questions`)
}

export function fetchStatsTotals() {
  return apiRequest('/api/stats/totals')
}

export function fetchRelayLogs() {
  return apiRequest('/api/relay-logs')
}

export function createCourse(payload) {
  return apiRequest('/api/courses', {
    method: 'POST',
    body: JSON.stringify(payload)
  })
}

export function createSession(payload) {
  return apiRequest('/api/sessions', {
    method: 'POST',
    body: JSON.stringify(payload)
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
