import { computed, onMounted, ref } from 'vue'
import { fetchRelayLogs } from '../api/api'

const serviceMetaMap = {
  llm: {
    label: 'LLM',
    symbol: '⚡',
    color: 'rgba(255, 138, 89, 0.18)',
    badgeColor: '#ff9b6e'
  },
  asr: {
    label: 'ASR',
    symbol: '🎙️',
    color: 'rgba(96, 182, 255, 0.18)',
    badgeColor: '#7dc8ff'
  },
  tts: {
    label: 'TTS',
    symbol: '🔊',
    color: 'rgba(182, 125, 255, 0.18)',
    badgeColor: '#c99aff'
  }
}

const statusMetaMap = {
  success: { label: '成功', className: 'is-success' },
  ok: { label: '成功', className: 'is-success' },
  done: { label: '成功', className: 'is-success' },
  warn: { label: '警告', className: 'is-warn' },
  warning: { label: '警告', className: 'is-warn' },
  error: { label: '失败', className: 'is-error' },
  failed: { label: '失败', className: 'is-error' }
}

const toNumber = (value) => {
  const numberValue = Number(value)
  return Number.isFinite(numberValue) ? numberValue : 0
}

const normalizeServiceType = (value) => String(value || '').trim().toLowerCase()

const pad = (value) => String(value).padStart(2, '0')

const formatTimeLabel = (timestamp) => {
  const date = new Date(toNumber(timestamp) * 1000)
  if (Number.isNaN(date.getTime())) {
    return '--'
  }

  return `${pad(date.getMonth() + 1)}/${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
}

const formatDuration = (milliseconds) => {
  const value = Math.max(0, toNumber(milliseconds))
  if (value >= 3600000) {
    return `${(value / 3600000).toFixed(2)} h`
  }
  if (value >= 60000) {
    return `${(value / 60000).toFixed(2)} min`
  }
  if (value >= 1000) {
    return `${(value / 1000).toFixed(2)} s`
  }
  return `${Math.round(value)} ms`
}

const formatCount = (value) => {
  const numberValue = toNumber(value)
  if (Math.abs(numberValue) >= 1000000) {
    return `${(numberValue / 1000000).toFixed(2)} M`
  }
  if (Math.abs(numberValue) >= 1000) {
    return `${(numberValue / 1000).toFixed(2)} K`
  }
  return String(Math.round(numberValue))
}

const safeParseContent = (value) => {
  if (value == null || value === '') {
    return ''
  }

  const text = typeof value === 'string' ? value.trim() : String(value)
  if (!text) {
    return ''
  }

  try {
    const parsed = JSON.parse(text)
    return JSON.stringify(parsed, null, 2)
  } catch {
    return text
  }
}

const previewContent = (value, maxLength = 140) => {
  const text = safeParseContent(value)
  if (!text) {
    return '（无内容）'
  }

  return text.length > maxLength ? `${text.slice(0, maxLength)}…` : text
}

const buildRelayLogItem = (entry) => {
  const serviceType = normalizeServiceType(entry.service_type)
  const serviceMeta = serviceMetaMap[serviceType] || {
    label: String(entry.service_type || 'LOG').toUpperCase(),
    symbol: '●',
    color: 'rgba(132, 230, 148, 0.16)',
    badgeColor: '#84e694'
  }

  const statusValue = String(entry.status || '').trim().toLowerCase()
  const statusMeta = statusMetaMap[statusValue] || {
    label: entry.status ? String(entry.status) : '未知',
    className: 'is-info'
  }

  return {
    ...entry,
    serviceType,
    serviceLabel: serviceMeta.label,
    serviceSymbol: serviceMeta.symbol,
    serviceColor: serviceMeta.color,
    serviceBadgeColor: serviceMeta.badgeColor,
    timeLabel: formatTimeLabel(entry.time),
    statusLabel: statusMeta.label,
    statusClassName: statusMeta.className,
    latencyLabel: formatDuration(entry.latency),
    firstResponseLabel: formatDuration(entry.first_response_time),
    inputValueLabel: formatCount(entry.input_value),
    outputValueLabel: formatCount(entry.output_value),
    totalAttemptsLabel: entry.total_attempts != null
      ? `${formatCount(entry.total_attempts)} 次尝试`
      : entry.attempts || '',
    requestContentText: safeParseContent(entry.request_content),
    responseContentText: safeParseContent(entry.response_content),
    requestPreview: previewContent(entry.request_content),
    responsePreview: previewContent(entry.response_content),
    hasError: Boolean(entry.error),
    errorText: entry.error || ''
  }
}

const PAGE_SIZE = 20

const logs = ref([])
const loading = ref(false)
const loadingMore = ref(false)
const error = ref('')
const selectedLogId = ref(null)
const isDetailOpen = ref(false)
const hasMore = ref(true)
const selectedServiceType = ref('all')

export function useLogsPage() {
  const logItems = computed(() => logs.value.map((entry) => buildRelayLogItem(entry)))

  const selectedLog = computed(() => {
    if (selectedLogId.value == null) {
      return null
    }

    return logItems.value.find((entry) => entry.id === selectedLogId.value) || null
  })

  const loadLogs = async ({ append = false } = {}) => {
    const offset = append ? logs.value.length : 0

    if (append) {
      loadingMore.value = true
    } else {
      loading.value = true
      error.value = ''
    }

    try {
      const result = await fetchRelayLogs({
        serviceType: selectedServiceType.value === 'all' ? undefined : selectedServiceType.value,
        limit: PAGE_SIZE,
        offset
      })
      const items = Array.isArray(result) ? result : []
      logs.value = append ? [...logs.value, ...items] : items
      hasMore.value = items.length === PAGE_SIZE
    } catch (loadError) {
      error.value = loadError instanceof Error ? loadError.message : '日志加载失败'
      if (!append) {
        logs.value = []
      }
    } finally {
      loading.value = false
      loadingMore.value = false
    }
  }

  const loadMoreLogs = () => {
    if (loading.value || loadingMore.value || !hasMore.value) {
      return
    }
    loadLogs({ append: true })
  }

  const changeServiceType = (serviceType) => {
    selectedServiceType.value = serviceType
    hasMore.value = true
    loadLogs()
  }

  const openLogDetail = (entry) => {
    selectedLogId.value = entry.id
    isDetailOpen.value = true
  }

  const closeLogDetail = () => {
    isDetailOpen.value = false
  }

  const reloadLogs = () => {
    hasMore.value = true
    loadLogs()
  }

  onMounted(() => {
    loadLogs()
  })

  return {
    logItems,
    loading,
    loadingMore,
    error,
    hasMore,
    selectedServiceType,
    selectedLog,
    isDetailOpen,
    openLogDetail,
    closeLogDetail,
    reloadLogs,
    loadMoreLogs,
    changeServiceType
  }
}
