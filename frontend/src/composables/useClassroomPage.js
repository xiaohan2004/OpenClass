import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import {
  createCourse,
  createSession,
  endSession,
  generateSessionReport,
  fetchCourses,
  fetchSessionById,
  fetchSessionKnowledgePoints,
  fetchSessionKeywords,
  fetchRelayLogs,
  fetchSessionQuestions,
  fetchSessionQuizItems,
  fetchSessionsByCourse,
  fetchSessionSummaries,
  fetchSessionTranscripts,
  fetchStatsTotals,
  pauseSession,
  startSession
} from '../api/api'

const AUDIO_CHUNK_MS = 5000
const RECEIVE_DRAIN_MS = 12000
const KEYWORD_SOURCE_FILTER_STORAGE_KEY = 'openclass.keyword.sourceFilter'
const KEYWORD_SOURCE_FILTER_VALUES = ['llm', 'algorithm', 'all']

export function useClassroomPage() {
  const sessionStatus = ref('idle')
  const rightPanelOpen = ref(false)
  const debugPanelOpen = ref(false)
  const isRunning = ref(false)
  const actionLoading = ref(false)
  const nowTimestamp = ref(Math.floor(Date.now() / 1000))
  const availableMicrophones = ref([])
  const selectedMicrophoneId = ref('default')

  const courses = ref([])
  const sessions = ref([])
  const selectedCourseId = ref(null)
  const selectedSessionId = ref(null)

  const showCreateCourseModal = ref(false)
  const showCreateSessionModal = ref(false)

  const courseForm = ref({
    code: '',
    name: '',
    description: '',
    teacher: ''
  })

  const sessionForm = ref({
    title: ''
  })

  const transcriptFeed = ref(null)
  const transcriptListFeed = ref(null)
  const summaryFeed = ref(null)
  const queueFeed = ref(null)
  let timerTick = null
  let wsCloseTimer = null
  let chunkStopTimer = null
  let chunkLoopActive = false
  let chunkLoopTask = null
  const wsRef = ref(null)
  const activeWsSessionId = ref(null)
  const mediaStreamRef = ref(null)
  const mediaRecorderRef = ref(null)
  const localFileRecorderRef = ref(null)
  const localFileChunksRef = ref([])
  const localFileMimeType = ref('audio/webm')
  const dataDirHandleRef = ref(null)
  const audioContextRef = ref(null)
  const analyserRef = ref(null)
  const analyserDataRef = ref(null)
  const levelAnimationRef = ref(null)
  const micLevel = ref(0)
  const recordingChunks = ref([])
  const recordingMimeType = ref('audio/webm')
  const lastChunkBytes = ref(0)
  const sessionRuntimeState = ref({})

  const transcriptItems = ref([])
  const summaries = ref([])
  const queuedQuestions = ref([])
  const askedQuestionsHistory = ref([])
  const isQuestionAsking = ref(false)
  const activeTtsPlayCount = ref(0)
  const currentAskingQuestion = ref('')
  const currentAskingHistoryId = ref(null)
  const keywordSnapshots = ref([])
  const keywordSourceFilter = ref('llm')
  const knowledgePoints = ref([])
  const quizItems = ref([])
  const isKnowledgeExpanded = ref(false)
  const isQuizPanelOpen = ref(false)
  const currentQuizIndex = ref(-1)
  const stats = ref([])
  const logs = ref([])
  const wsTrafficLogs = ref([])
  const reportToast = ref(null)
  let reportToastTimer = null
  const onDeviceChange = () => {
    void refreshMicrophones()
  }

  function showReportToast(type, message) {
    reportToast.value = {
      type,
      message
    }
    if (reportToastTimer) {
      window.clearTimeout(reportToastTimer)
    }
    reportToastTimer = window.setTimeout(() => {
      reportToast.value = null
      reportToastTimer = null
    }, 3200)
  }

  function appendWsTrafficLog(direction, content) {
    const now = formatTime(Math.floor(Date.now() / 1000))
    const safeDirection = direction === 'send' ? 'SEND' : direction === 'recv' ? 'RECV' : 'INFO'
    wsTrafficLogs.value = [...wsTrafficLogs.value, `${now} [${safeDirection}] ${content}`]
  }

  function clearWsTrafficLogs() {
    wsTrafficLogs.value = []
  }

  function getSessionRuntime(sessionId) {
    return (
      sessionRuntimeState.value[sessionId] || {
        status: 'idle',
        elapsedSeconds: 0,
        runningSince: null
      }
    )
  }

  function setSessionRuntime(sessionId, patch) {
    sessionRuntimeState.value = {
      ...sessionRuntimeState.value,
      [sessionId]: {
        ...getSessionRuntime(sessionId),
        ...patch
      }
    }
  }

  function resetSessionRuntime(sessionId) {
    if (!sessionId) {
      return
    }

    const nextState = { ...sessionRuntimeState.value }
    delete nextState[sessionId]
    sessionRuntimeState.value = nextState
  }

  const sessionStatusLabel = computed(() => {
    const currentRuntime = selectedSessionId.value
      ? getSessionRuntime(selectedSessionId.value)
      : { status: 'idle' }

    if (currentRuntime.status === 'paused') {
      return '已暂停'
    }
    if (currentRuntime.status === 'recording') {
      return '录制中'
    }
    return '空闲中'
  })

  const selectedSession = computed(() =>
    sessions.value.find((item) => item.id === selectedSessionId.value) || null
  )

  const canStartSession = computed(() =>
    Boolean(selectedCourseId.value && selectedSessionId.value)
  )

  const canEndSession = computed(() => {
    if (!canStartSession.value || !selectedSessionId.value) {
      return false
    }

    const runtime = getSessionRuntime(selectedSessionId.value)
    return runtime.status === 'recording' || runtime.status === 'paused'
  })

  const timerLabel = computed(() => {
    const sessionId = selectedSessionId.value
    if (!sessionId) {
      return '00:00:00'
    }

    const runtime = getSessionRuntime(sessionId)
    const runningElapsed =
      runtime.status === 'recording' && runtime.runningSince
        ? Math.max(0, nowTimestamp.value - runtime.runningSince)
        : 0
    const seconds = Math.max(0, runtime.elapsedSeconds + runningElapsed)
    const hh = String(Math.floor(seconds / 3600)).padStart(2, '0')
    const mm = String(Math.floor((seconds % 3600) / 60)).padStart(2, '0')
    const ss = String(seconds % 60).padStart(2, '0')
    return `${hh}:${mm}:${ss}`
  })

  const latestSessionKeywords = computed(() => {
    const snapshots =
      keywordSourceFilter.value === 'all'
        ? keywordSnapshots.value
        : keywordSnapshots.value.filter((item) => item.source === keywordSourceFilter.value)
    const latest = snapshots[snapshots.length - 1] || null
    return Array.isArray(latest?.keywords) ? latest.keywords : []
  })

  const bufferedChunkCount = computed(() => recordingChunks.value.length)

  const bufferedAudioSizeLabel = computed(() => {
    const totalBytes = recordingChunks.value.reduce((sum, chunk) => sum + (chunk?.size || 0), 0)
    if (totalBytes < 1024) {
      return `${totalBytes} B`
    }
    if (totalBytes < 1024 * 1024) {
      return `${(totalBytes / 1024).toFixed(1)} KB`
    }
    return `${(totalBytes / (1024 * 1024)).toFixed(2)} MB`
  })

  const micLevelPercent = computed(() => Math.max(0, Math.min(100, Math.round(micLevel.value * 100))))

  const currentAskingQuestionText = computed(() => {
    if (!isQuestionAsking.value) {
      return '当前暂未提问'
    }

    const text = String(currentAskingQuestion.value || '').trim()
    return text || '当前暂未提问'
  })

  const latestKnowledgePoint = computed(
    () => knowledgePoints.value[knowledgePoints.value.length - 1] || null
  )

  const currentKnowledgePoint = computed(
    () => latestKnowledgePoint.value?.name || '暂无知识点'
  )

  const currentKnowledgeDescription = computed(
    () => latestKnowledgePoint.value?.description || '暂无简要说明'
  )

  const currentDifficultyLevel = computed(() => {
    const latestItem = latestKnowledgePoint.value
    if (!latestItem) {
      return 'unknown'
    }

    const rawDifficulty = String(latestItem.difficulty || '').trim().toLowerCase()
    if (!rawDifficulty) {
      return 'unknown'
    }
    if (rawDifficulty.includes('hard') || rawDifficulty.includes('难')) {
      return 'hard'
    }
    if (rawDifficulty.includes('easy') || rawDifficulty.includes('易')) {
      return 'easy'
    }
    return 'medium'
  })

  const currentDifficultyLabel = computed(() => {
    if (currentDifficultyLevel.value === 'hard') {
      return '难'
    }
    if (currentDifficultyLevel.value === 'easy') {
      return '易'
    }
    if (currentDifficultyLevel.value === 'unknown') {
      return '未知'
    }
    return '中'
  })

  const currentQuizItem = computed(() => {
    if (currentQuizIndex.value < 0 || currentQuizIndex.value >= quizItems.value.length) {
      return null
    }
    return quizItems.value[currentQuizIndex.value]
  })

  const quizIndexLabel = computed(() => {
    if (quizItems.value.length === 0 || currentQuizIndex.value < 0) {
      return '0/0'
    }
    return `${currentQuizIndex.value + 1}/${quizItems.value.length}`
  })

  const canShowPrevQuiz = computed(() => currentQuizIndex.value > 0)
  const canShowNextQuiz = computed(
    () => currentQuizIndex.value >= 0 && currentQuizIndex.value < quizItems.value.length - 1
  )

  function normalizeKeywordSource(source) {
    const normalized = String(source || 'llm').trim().toLowerCase()
    return normalized === 'algorithm' ? 'algorithm' : 'llm'
  }

  function normalizeKeywordSourceFilter(value) {
    const normalized = String(value || '').trim().toLowerCase()
    return KEYWORD_SOURCE_FILTER_VALUES.includes(normalized) ? normalized : 'llm'
  }

  function loadKeywordSourceFilter() {
    try {
      keywordSourceFilter.value = normalizeKeywordSourceFilter(
        window.localStorage.getItem(KEYWORD_SOURCE_FILTER_STORAGE_KEY)
      )
    } catch {
      keywordSourceFilter.value = 'llm'
    }
  }

  function handleLocalSettingsUpdated(event) {
    if (event?.detail?.keywordSourceFilter) {
      keywordSourceFilter.value = normalizeKeywordSourceFilter(event.detail.keywordSourceFilter)
      return
    }
    loadKeywordSourceFilter()
  }

  function handleLocalStorageUpdated(event) {
    if (event?.key === KEYWORD_SOURCE_FILTER_STORAGE_KEY) {
      keywordSourceFilter.value = normalizeKeywordSourceFilter(event.newValue)
    }
  }

  function parseKeywordSet(rawKeywordSets) {
    if (!rawKeywordSets) {
      return []
    }

    if (Array.isArray(rawKeywordSets)) {
      return rawKeywordSets.map((item) => String(item).trim()).filter(Boolean)
    }

    if (typeof rawKeywordSets === 'string') {
      try {
        const parsed = JSON.parse(rawKeywordSets)
        if (Array.isArray(parsed)) {
          return parsed.map((item) => String(item).trim()).filter(Boolean)
        }
      } catch {
        return rawKeywordSets
          .split(/[、,，\s]+/)
          .map((item) => item.trim())
          .filter(Boolean)
      }
    }

    return []
  }

  function normalizeKnowledgePoint(item) {
    if (!item || typeof item !== 'object') {
      return null
    }

    const name = String(item.name || '').trim()
    if (!name) {
      return null
    }

    return {
      id: item.id ?? createTransientId('knowledge'),
      name,
      description: String(item.description || '').trim(),
      difficulty: String(item.difficulty || '').trim().toLowerCase(),
      createdAt: toUnixSeconds(item.created_at || item.start_time || Date.now())
    }
  }

  function normalizeQuizItem(item) {
    if (!item || typeof item !== 'object') {
      return null
    }

    const question = String(item.question || '')
    if (!question.trim()) {
      return null
    }

    return {
      id: item.id ?? createTransientId('quiz'),
      type: String(item.type || '').trim() || 'short_answer',
      question,
      answer: String(item.answer || '').trim(),
      explanation: String(item.explanation || '').trim(),
      createdAt: toUnixSeconds(item.created_at || item.start_time || Date.now())
    }
  }

  function toggleKnowledgeExpanded() {
    isKnowledgeExpanded.value = !isKnowledgeExpanded.value
  }

  function toggleQuizPanel() {
    isQuizPanelOpen.value = !isQuizPanelOpen.value
  }

  function showPrevQuiz() {
    if (!canShowPrevQuiz.value) {
      return
    }
    currentQuizIndex.value -= 1
  }

  function showNextQuiz() {
    if (!canShowNextQuiz.value) {
      return
    }
    currentQuizIndex.value += 1
  }

  function toUnixSeconds(ts) {
    if (typeof ts === 'number' && Number.isFinite(ts)) {
      return ts > 1e12 ? Math.floor(ts / 1000) : Math.floor(ts)
    }
    if (typeof ts === 'string' && ts.trim()) {
      const numeric = Number(ts)
      if (Number.isFinite(numeric)) {
        return numeric > 1e12 ? Math.floor(numeric / 1000) : Math.floor(numeric)
      }
      const parsedMs = Date.parse(ts)
      if (Number.isFinite(parsedMs)) {
        return Math.floor(parsedMs / 1000)
      }
    }
    return 0
  }

  function formatTime(ts) {
    const seconds = toUnixSeconds(ts)
    if (!seconds) {
      return '--:--:--'
    }
    const d = new Date(seconds * 1000)
    const hh = String(d.getHours()).padStart(2, '0')
    const mm = String(d.getMinutes()).padStart(2, '0')
    const ss = String(d.getSeconds()).padStart(2, '0')
    return `${hh}:${mm}:${ss}`
  }

  function scrollQueueToBottom() {
    if (queueFeed.value) {
      queueFeed.value.scrollTop = queueFeed.value.scrollHeight
    }
  }

  function scrollSummaryToBottom() {
    if (summaryFeed.value) {
      summaryFeed.value.scrollTop = summaryFeed.value.scrollHeight
    }
  }

  function createTransientId(prefix = 'temp') {
    return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
  }

  function appendLog(message) {
    logs.value = [message, ...logs.value].slice(0, 80)
  }

  function appendAskedQuestionHistory(questionText, askedAtTs, questionId = null) {
    const text = String(questionText || '').trim()
    if (!text) {
      return null
    }

    const askedAt = toUnixSeconds(askedAtTs || Math.floor(Date.now() / 1000))
    const stableId = questionId ?? `asked-live-${askedAt}-${Math.random().toString(36).slice(2, 8)}`
    const nextItem = {
      id: stableId,
      askedAt,
      askedAtLabel: formatTime(askedAt),
      text
    }

    const exists = askedQuestionsHistory.value.some((item) => item.id === stableId)
    const merged = exists
      ? askedQuestionsHistory.value.map((item) => (item.id === stableId ? nextItem : item))
      : [...askedQuestionsHistory.value, nextItem]

    askedQuestionsHistory.value = merged.sort((a, b) => {
      if (a.askedAt !== b.askedAt) {
        return a.askedAt - b.askedAt
      }
      return String(a.id).localeCompare(String(b.id))
    })

    return stableId
  }

  function beginQuestionAsking(questionText, askedAtTs) {
    const text = String(questionText || '').trim()
    if (text) {
      currentAskingQuestion.value = text
      currentAskingHistoryId.value = appendAskedQuestionHistory(text, askedAtTs)
    }

    activeTtsPlayCount.value += 1
    isQuestionAsking.value = activeTtsPlayCount.value > 0
  }

  function finishQuestionAsking() {
    activeTtsPlayCount.value = Math.max(0, activeTtsPlayCount.value - 1)
    isQuestionAsking.value = activeTtsPlayCount.value > 0
    if (!isQuestionAsking.value) {
      currentAskingQuestion.value = ''
      currentAskingHistoryId.value = null
    }
  }

  async function refreshMicrophones() {
    if (!navigator.mediaDevices?.enumerateDevices) {
      availableMicrophones.value = []
      return
    }

    const devices = await navigator.mediaDevices.enumerateDevices()
    const mics = devices.filter((device) => device.kind === 'audioinput')
    availableMicrophones.value = mics.map((device, index) => ({
      id: device.deviceId || 'default',
      label: device.label || `麦克风 ${index + 1}`
    }))

    if (
      selectedMicrophoneId.value !== 'default' &&
      !availableMicrophones.value.some((item) => item.id === selectedMicrophoneId.value)
    ) {
      selectedMicrophoneId.value = 'default'
    }
  }

  async function handleMicrophoneChange() {
    try {
      await refreshMicrophones()
      const wasRunning = isRunning.value

      if (wasRunning) {
        await stopRecordingLoop()
      }

      stopMicrophone()
      await ensureMediaStream()

      if (wasRunning) {
        await startRecordingLoop()
        appendLog(`${formatTime(Math.floor(Date.now() / 1000))} 麦克风已即时切换并继续录制`) 
      } else {
        appendLog(`${formatTime(Math.floor(Date.now() / 1000))} 麦克风已切换`) 
      }
    } catch (error) {
      window.alert(error instanceof Error ? error.message : '切换麦克风失败')
    }
  }

  function stopMicLevelMonitor() {
    if (levelAnimationRef.value) {
      window.cancelAnimationFrame(levelAnimationRef.value)
      levelAnimationRef.value = null
    }
    analyserRef.value = null
    analyserDataRef.value = null
    if (audioContextRef.value) {
      void audioContextRef.value.close()
      audioContextRef.value = null
    }
    micLevel.value = 0
  }

  function startMicLevelMonitor(stream) {
    if (typeof window === 'undefined' || !window.AudioContext) {
      return
    }

    stopMicLevelMonitor()

    const audioContext = new window.AudioContext()
    const source = audioContext.createMediaStreamSource(stream)
    const analyser = audioContext.createAnalyser()
    analyser.fftSize = 2048
    analyser.smoothingTimeConstant = 0.82

    source.connect(analyser)

    const buffer = new Uint8Array(analyser.fftSize)
    audioContextRef.value = audioContext
    analyserRef.value = analyser
    analyserDataRef.value = buffer

    const loop = () => {
      const activeAnalyser = analyserRef.value
      const activeBuffer = analyserDataRef.value
      if (!activeAnalyser || !activeBuffer) {
        return
      }

      activeAnalyser.getByteTimeDomainData(activeBuffer)
      let sumSquares = 0
      for (let i = 0; i < activeBuffer.length; i += 1) {
        const normalized = (activeBuffer[i] - 128) / 128
        sumSquares += normalized * normalized
      }
      const rms = Math.sqrt(sumSquares / activeBuffer.length)
      micLevel.value = Math.min(1, rms * 3.2)

      levelAnimationRef.value = window.requestAnimationFrame(loop)
    }

    levelAnimationRef.value = window.requestAnimationFrame(loop)
  }

  async function chooseDataDirectory() {
    if (!('showDirectoryPicker' in window)) {
      return false
    }
    const dataDirHandle = await window.showDirectoryPicker({ mode: 'readwrite' })
    dataDirHandleRef.value = dataDirHandle
    return true
  }

  async function toggleLocalBackup() {
    if (localBackupEnabled.value) {
      localBackupEnabled.value = false
      await stopLocalFileRecorder(false)
      appendLog(`${formatTime(Math.floor(Date.now() / 1000))} 已关闭本地录音备份`) 
      return
    }

    try {
      if ('showDirectoryPicker' in window && !dataDirHandleRef.value) {
        await chooseDataDirectory()
      }
      localBackupEnabled.value = true
      if (isRunning.value && mediaStreamRef.value) {
        startLocalFileRecorder(mediaStreamRef.value)
      }
      appendLog(`${formatTime(Math.floor(Date.now() / 1000))} 已开启本地录音备份`) 
    } catch {
      localBackupEnabled.value = false
      window.alert('未选择目录，本地录音备份未开启')
    }
  }

  function getRecordingFileExtension(mimeType) {
    if (mimeType.includes('mp4')) {
      return 'm4a'
    }
    if (mimeType.includes('ogg')) {
      return 'ogg'
    }
    if (mimeType.includes('wav')) {
      return 'wav'
    }
    return 'webm'
  }

  function buildRecordingBlob() {
    if (recordingChunks.value.length === 0) {
      return null
    }
    return new Blob(recordingChunks.value, {
      type: recordingMimeType.value || 'audio/webm'
    })
  }

  function getRecordingFileName() {
    const sessionPart = selectedSessionId.value ? `session-${selectedSessionId.value}` : 'session-unknown'
    const timePart = new Date().toISOString().replace(/[:.]/g, '-')
    const ext = getRecordingFileExtension(localFileMimeType.value || recordingMimeType.value || '')
    return `${sessionPart}-${timePart}.${ext}`
  }

  async function saveBlobToLocalDataDir(blob) {
    if (!blob || blob.size === 0 || debugSaving.value) {
      return
    }

    debugSaving.value = true
    try {
      const fileName = getRecordingFileName()
      if (!('showDirectoryPicker' in window)) {
        const url = URL.createObjectURL(blob)
        const anchor = document.createElement('a')
        anchor.href = url
        anchor.download = fileName
        anchor.click()
        URL.revokeObjectURL(url)
        appendLog(`${formatTime(Math.floor(Date.now() / 1000))} 浏览器不支持目录写入，已下载录音文件`) 
        window.alert('当前浏览器不支持直接写入目录，已转为下载文件')
        return
      }

      let dataDirHandle = dataDirHandleRef.value
      if (!dataDirHandle) {
        await chooseDataDirectory()
        dataDirHandle = dataDirHandleRef.value
      }

      const fileHandle = await dataDirHandle.getFileHandle(fileName, { create: true })
      const writable = await fileHandle.createWritable()
      await writable.write(blob)
      await writable.close()

      appendLog(`${formatTime(Math.floor(Date.now() / 1000))} 已保存录音文件: ${fileName}`) 
    } catch (error) {
      const errMsg = error instanceof Error ? error.message : '保存录音失败'
      window.alert(errMsg)
    } finally {
      debugSaving.value = false
    }
  }

  async function saveRecordingToLocalDataDir() {
    const blob = buildRecordingBlob()
    if (!blob) {
      window.alert('当前没有可保存的录音片段')
      return
    }
    await saveBlobToLocalDataDir(blob)
  }

  function clearRecordingBuffer() {
    recordingChunks.value = []
    lastChunkBytes.value = 0
    appendLog(`${formatTime(Math.floor(Date.now() / 1000))} 已清空本地录音缓存`) 
  }

  function getWsBase() {
    const envBase = import.meta.env.VITE_WS_BASE
    if (envBase && envBase.trim()) {
      return envBase.replace(/\/$/, '')
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    return `${protocol}//${window.location.host}`
  }

  function getSessionWsUrl(sessionId) {
    return `${getWsBase()}/ws/session/${sessionId}`
  }

  function clearWsCloseTimer() {
    if (wsCloseTimer) {
      window.clearTimeout(wsCloseTimer)
      wsCloseTimer = null
    }
  }

  function clearChunkStopTimer() {
    if (chunkStopTimer) {
      window.clearTimeout(chunkStopTimer)
      chunkStopTimer = null
    }
  }

  function scheduleWsClose() {
    clearWsCloseTimer()
    wsCloseTimer = window.setTimeout(() => {
      closeSessionWebSocket()
    }, RECEIVE_DRAIN_MS)
  }

  function blobToBase64(blob) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.onloadend = () => {
        const result = typeof reader.result === 'string' ? reader.result : ''
        const marker = 'base64,'
        const markerIndex = result.indexOf(marker)
        if (markerIndex < 0) {
          reject(new Error('录音编码失败'))
          return
        }
        resolve(result.slice(markerIndex + marker.length))
      }
      reader.onerror = () => reject(new Error('录音读取失败'))
      reader.readAsDataURL(blob)
    })
  }

  function handleWsMessage(payload) {
    if (!payload || typeof payload !== 'object') {
      return
    }

    const payloadPreview = JSON.stringify(payload)
    appendWsTrafficLog(
      'recv',
      payloadPreview.length > 240 ? `${payloadPreview.slice(0, 240)}...` : payloadPreview
    )

    const { type, data } = payload
    const now = Math.floor(Date.now() / 1000)

    if (type === 'transcript') {
      const transcriptId = data?.id ?? createTransientId('transcript')
      const transcriptText = data?.text || ''
      if (transcriptText) {
        transcriptItems.value = [
          ...transcriptItems.value,
          {
            id: transcriptId,
            kind: 'teacher',
            label: '转录',
            time: formatTime(now),
            text: transcriptText
          }
        ]
      }
    }

    if (type === 'summary') {
      const summaryId = data?.id ?? createTransientId('summary')
      const summaryText = data?.text || ''
      if (summaryText) {
        summaries.value = [
          ...summaries.value,
          {
            id: summaryId,
            time: formatTime(now),
            text: summaryText
          }
        ]
      }
    }

    if (type === 'question') {
      const items = Array.isArray(data?.items) ? data.items : []
      if (items.length > 0) {
        const existingIds = new Set(queuedQuestions.value.map((item) => item.id))
        const nextItems = items
          .filter((item) => !existingIds.has(item.id))
          .map((item) => ({
            id: item.id,
            order: '',
            text: item.text,
            time: formatTime(item.start_time || item.created_at || now),
            score: item.score
          }))

        const merged = [...queuedQuestions.value, ...nextItems]
        queuedQuestions.value = merged.map((item, index) => ({
          ...item,
          order: `Q${index + 1}`
        }))

        void nextTick().then(() => {
          scrollQueueToBottom()
        })
      }
    }

    if (type === 'keywords') {
      const incomingKeywords = Array.isArray(data?.keywords)
        ? data.keywords.map((item) => String(item).trim()).filter(Boolean)
        : []

      if (incomingKeywords.length > 0) {
        keywordSnapshots.value = [
          ...keywordSnapshots.value,
          {
            id: createTransientId('keyword-set'),
            createdAt: now,
            keywords: incomingKeywords,
            source: normalizeKeywordSource(data?.source)
          }
        ]
      }
    }

    if (type === 'knowledge') {
      const nextKnowledgePoint = normalizeKnowledgePoint(data)
      if (nextKnowledgePoint) {
        knowledgePoints.value = [...knowledgePoints.value, nextKnowledgePoint]
      }
    }

    if (type === 'quiz') {
      const nextQuizItem = normalizeQuizItem(data)
      if (nextQuizItem) {
        const mergedQuizItems = [...quizItems.value, nextQuizItem]
        quizItems.value = mergedQuizItems
        currentQuizIndex.value = mergedQuizItems.length - 1
      }
    }

    if (type === 'tts_out') {
      const ttsText = String(data?.text || '').trim()
      if (data?.audio_url) {
        beginQuestionAsking(ttsText, now)

        const audio = new Audio(data.audio_url)
        let finished = false
        const fallbackTimer = window.setTimeout(() => {
          if (finished) {
            return
          }
          finished = true
          finishQuestionAsking()
        }, 30000)

        const finalizeAsking = () => {
          if (finished) {
            return
          }
          finished = true
          window.clearTimeout(fallbackTimer)
          finishQuestionAsking()
        }

        audio.addEventListener('ended', finalizeAsking, { once: true })
        audio.addEventListener('error', finalizeAsking, { once: true })

        void audio.play().catch(() => {
          appendLog(`${formatTime(now)} 音频自动播放失败`) 
          finalizeAsking()
        })
      }

      if (ttsText) {
        appendLog(`${formatTime(now)} 提问播报：${ttsText}`)
      }
    }

    if (type === 'error') {
      appendLog(`${formatTime(now)} WS错误：${data?.message || '未知错误'}`)
    }

    void nextTick().then(() => {
      if (transcriptListFeed.value) {
        transcriptListFeed.value.scrollTop = transcriptListFeed.value.scrollHeight
      }
      scrollSummaryToBottom()
    })
  }

  async function connectSessionWebSocket(sessionId) {
    if (!sessionId) {
      return
    }

    const existingWs = wsRef.value
    if (
      existingWs &&
      activeWsSessionId.value === sessionId &&
      (existingWs.readyState === WebSocket.OPEN || existingWs.readyState === WebSocket.CONNECTING)
    ) {
      return
    }

    await closeSessionWebSocket()

    await new Promise((resolve, reject) => {
      const ws = new WebSocket(getSessionWsUrl(sessionId))
      wsRef.value = ws
      activeWsSessionId.value = sessionId

      ws.onopen = () => {
        appendLog(`${formatTime(Math.floor(Date.now() / 1000))} WS连接成功`) 
        appendWsTrafficLog('info', `WS connected: session ${sessionId}`)
        resolve()
      }

      ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data)
          handleWsMessage(payload)
        } catch {
          appendLog(`${formatTime(Math.floor(Date.now() / 1000))} WS消息解析失败`)
          const rawData = typeof event.data === 'string' ? event.data : '[binary data]'
          appendWsTrafficLog('recv', `Invalid JSON: ${rawData.slice(0, 240)}`)
        }
      }

      ws.onerror = () => {
        appendLog(`${formatTime(Math.floor(Date.now() / 1000))} WS连接异常`)
        appendWsTrafficLog('info', 'WS error')
      }

      ws.onclose = () => {
        wsRef.value = null
        activeWsSessionId.value = null
        appendWsTrafficLog('info', 'WS closed')
      }

      window.setTimeout(() => {
        if (ws.readyState === WebSocket.CONNECTING) {
          reject(new Error('WS连接超时'))
        }
      }, 8000)
    })
  }

  async function closeSessionWebSocket() {
    clearWsCloseTimer()
    await stopRecordingLoop()

    const ws = wsRef.value
    if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
      ws.close(1000, 'client-close')
    }
    wsRef.value = null
    activeWsSessionId.value = null
  }

  async function ensureMediaStream() {
    if (mediaStreamRef.value) {
      return mediaStreamRef.value
    }

    const audioConstraints =
      selectedMicrophoneId.value && selectedMicrophoneId.value !== 'default'
        ? { deviceId: { exact: selectedMicrophoneId.value } }
        : true
    const stream = await navigator.mediaDevices.getUserMedia({ audio: audioConstraints })
    mediaStreamRef.value = stream
    startMicLevelMonitor(stream)
    await refreshMicrophones()
    return stream
  }

  function getRecorderOptions() {
    const mimeCandidates = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4']
    for (const mimeType of mimeCandidates) {
      if (typeof MediaRecorder !== 'undefined' && MediaRecorder.isTypeSupported(mimeType)) {
        return { mimeType }
      }
    }
    return {}
  }

  function startLocalFileRecorder(stream) {
    if (!localBackupEnabled.value) {
      return
    }

    if (localFileRecorderRef.value && localFileRecorderRef.value.state === 'recording') {
      return
    }

    const recorder = new MediaRecorder(stream, getRecorderOptions())
    localFileRecorderRef.value = recorder
    localFileChunksRef.value = []
    localFileMimeType.value = recorder.mimeType || 'audio/webm'

    recorder.ondataavailable = (event) => {
      const chunk = event.data
      if (!chunk || chunk.size === 0) {
        return
      }
      localFileChunksRef.value = [...localFileChunksRef.value, chunk]
    }

    recorder.start()
    appendLog(`${formatTime(Math.floor(Date.now() / 1000))} 本地备份录音已启动`) 
  }

  async function stopLocalFileRecorder(saveFile) {
    const recorder = localFileRecorderRef.value
    if (!recorder) {
      return
    }

    if (recorder.state !== 'inactive') {
      await new Promise((resolve) => {
        recorder.addEventListener('stop', () => resolve(), { once: true })
        recorder.stop()
      })
    }

    localFileRecorderRef.value = null
    const localBlob = new Blob(localFileChunksRef.value, {
      type: localFileMimeType.value || 'audio/webm'
    })
    localFileChunksRef.value = []

    if (saveFile) {
      await saveBlobToLocalDataDir(localBlob)
    }
  }

  async function startRecordingLoop() {
    const ws = wsRef.value
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      throw new Error('WS未连接，无法发送录音')
    }

    if (chunkLoopActive) {
      return
    }

    const stream = await ensureMediaStream()
    chunkLoopActive = true
    appendLog(`${formatTime(Math.floor(Date.now() / 1000))} 开始录音并每5秒发送`) 

    chunkLoopTask = (async () => {
      while (chunkLoopActive) {
        const chunkStartTime = Math.floor(Date.now() / 1000)
        const recorder = new MediaRecorder(stream, getRecorderOptions())
        mediaRecorderRef.value = recorder
        recordingMimeType.value = recorder.mimeType || 'audio/webm'

        try {
          const chunk = await new Promise((resolve, reject) => {
            let chunkBlob = null

            recorder.ondataavailable = (event) => {
              if (event.data && event.data.size > 0) {
                chunkBlob = event.data
              }
            }

            recorder.onerror = () => {
              reject(new Error('录音器异常'))
            }

            recorder.onstop = () => {
              resolve(chunkBlob)
            }

            recorder.start()
            clearChunkStopTimer()
            chunkStopTimer = window.setTimeout(() => {
              if (recorder.state !== 'inactive') {
                recorder.stop()
              }
            }, AUDIO_CHUNK_MS)
          })

          if (!chunkLoopActive) {
            break
          }

          if (!chunk || chunk.size === 0) {
            continue
          }

          lastChunkBytes.value = chunk.size

          const activeWs = wsRef.value
          if (!activeWs || activeWs.readyState !== WebSocket.OPEN) {
            continue
          }

          const endTime = Math.floor(Date.now() / 1000)
          const audioBase64 = await blobToBase64(chunk)

          const outboundPayload = {
            type: 'audio_in',
            data: {
              audio: audioBase64,
              start_time: chunkStartTime,
              end_time: endTime
            }
          }

          activeWs.send(JSON.stringify(outboundPayload))
          appendWsTrafficLog(
            'send',
            `audio_in ${Math.round(chunk.size / 1024)}KB [${outboundPayload.data.start_time}-${outboundPayload.data.end_time}]`
          )
          appendLog(`${formatTime(Math.floor(Date.now() / 1000))} 录音分片已发送 ${Math.round(chunk.size / 1024)}KB`) 
        } catch {
          appendLog(`${formatTime(Math.floor(Date.now() / 1000))} 发送录音失败`) 
          appendWsTrafficLog('info', 'Send audio chunk failed')
        } finally {
          clearChunkStopTimer()
          mediaRecorderRef.value = null
        }
      }
    })()
  }

  async function stopRecordingLoop() {
    chunkLoopActive = false
    clearChunkStopTimer()

    const recorder = mediaRecorderRef.value
    if (recorder && recorder.state !== 'inactive') {
      await new Promise((resolve) => {
        recorder.addEventListener('stop', () => resolve(), { once: true })
        recorder.stop()
      })
    }
    mediaRecorderRef.value = null
    if (chunkLoopTask) {
      await chunkLoopTask.catch(() => {})
      chunkLoopTask = null
    }
  }

  function stopMicrophone() {
    const stream = mediaStreamRef.value
    if (stream) {
      stream.getTracks().forEach((track) => track.stop())
    }
    mediaStreamRef.value = null
    stopMicLevelMonitor()
  }

  async function loadCourses() {
    const data = await fetchCourses()
    courses.value = Array.isArray(data) ? data : []
  }

  async function loadSessions(courseId, options = {}) {
    const { preserveSelection = false } = options
    const previousSessionId = selectedSessionId.value

    if (!courseId) {
      sessions.value = []
      selectedSessionId.value = null
      return
    }

    const data = await fetchSessionsByCourse(courseId)
    sessions.value = Array.isArray(data) ? data : []

    if (
      preserveSelection &&
      previousSessionId &&
      sessions.value.some((item) => item.id === previousSessionId)
    ) {
      selectedSessionId.value = previousSessionId
      return
    }

    selectedSessionId.value = null
  }

  async function loadSessionData(sessionId) {
    if (!sessionId) {
      transcriptItems.value = []
      summaries.value = []
      queuedQuestions.value = []
      askedQuestionsHistory.value = []
      isQuestionAsking.value = false
      activeTtsPlayCount.value = 0
      currentAskingQuestion.value = ''
      currentAskingHistoryId.value = null
      keywordSnapshots.value = []
      knowledgePoints.value = []
      quizItems.value = []
      currentQuizIndex.value = -1
      isKnowledgeExpanded.value = false
      isQuizPanelOpen.value = false
      stats.value = []
      logs.value = []
      isRunning.value = false
      sessionStatus.value = 'idle'
      return
    }

    const currentRuntime = getSessionRuntime(sessionId)

    const [sessionData, transcriptsData, summariesData, questionsData, keywordsData, knowledgeData, quizData, statsData, relayLogsData] = await Promise.all([
      fetchSessionById(sessionId),
      fetchSessionTranscripts(sessionId),
      fetchSessionSummaries(sessionId),
      fetchSessionQuestions(sessionId),
      fetchSessionKeywords(sessionId),
      fetchSessionKnowledgePoints(sessionId),
      fetchSessionQuizItems(sessionId),
      fetchStatsTotals(),
      fetchRelayLogs()
    ])

    const transcriptList = Array.isArray(transcriptsData) ? transcriptsData : []
    transcriptItems.value = transcriptList.map((item) => ({
      id: item.id,
      kind: 'teacher',
      label: '转录',
      time: formatTime(item.start_time || item.created_at),
      text: item.text
    }))

    const summaryList = Array.isArray(summariesData) ? summariesData : []
    summaries.value = summaryList.map((item) => ({
      id: item.id,
      time: formatTime(item.start_time || item.created_at),
      text: item.text
    }))

    const questionList = Array.isArray(questionsData) ? questionsData : []
    const sortedQuestionList = [...questionList].sort((a, b) => {
      const tsA = toUnixSeconds(a?.start_time || a?.created_at) || 0
      const tsB = toUnixSeconds(b?.start_time || b?.created_at) || 0
      if (tsA !== tsB) {
        return tsA - tsB
      }
      return Number(a?.id || 0) - Number(b?.id || 0)
    })

    queuedQuestions.value = sortedQuestionList
      .filter((item) => item.status !== 'asked')
      .map((item, index) => ({
        id: item.id,
        order: `Q${index + 1}`,
        text: item.text,
        time: formatTime(item.start_time || item.created_at),
        score: item.score
      }))

    askedQuestionsHistory.value = sortedQuestionList
      .filter((item) => item.status === 'asked')
      .map((item) => {
        const askedAt = toUnixSeconds(item.asked_at || item.start_time || item.created_at)
        return {
          id: item.id,
          askedAt,
          askedAtLabel: formatTime(askedAt),
          text: String(item.text || '').trim()
        }
      })
      .filter((item) => item.text)
      .sort((a, b) => {
        if (a.askedAt !== b.askedAt) {
          return a.askedAt - b.askedAt
        }
        return Number(a.id || 0) - Number(b.id || 0)
      })

    isQuestionAsking.value = false
    activeTtsPlayCount.value = 0
    currentAskingQuestion.value = ''
    currentAskingHistoryId.value = null

    const keywordList = Array.isArray(keywordsData) ? keywordsData : []
    const sortedKeywordList = [...keywordList].sort((a, b) => {
      const tsA = toUnixSeconds(a?.created_at) || 0
      const tsB = toUnixSeconds(b?.created_at) || 0
      if (tsA !== tsB) {
        return tsA - tsB
      }
      return Number(a?.id || 0) - Number(b?.id || 0)
    })
    keywordSnapshots.value = sortedKeywordList
      .map((item) => ({
        id: item.id,
        createdAt: toUnixSeconds(item.created_at),
        keywords: parseKeywordSet(item.keyword_sets),
        source: normalizeKeywordSource(item.source)
      }))
      .filter((item) => item.keywords.length > 0)

    const knowledgeList = Array.isArray(knowledgeData) ? knowledgeData : []
    const sortedKnowledgeList = [...knowledgeList].sort((a, b) => {
      const tsA = toUnixSeconds(a?.created_at) || 0
      const tsB = toUnixSeconds(b?.created_at) || 0
      if (tsA !== tsB) {
        return tsA - tsB
      }
      return Number(a?.id || 0) - Number(b?.id || 0)
    })
    knowledgePoints.value = sortedKnowledgeList
      .map((item) => normalizeKnowledgePoint(item))
      .filter(Boolean)
    isKnowledgeExpanded.value = false

    const quizList = Array.isArray(quizData) ? quizData : []
    const sortedQuizList = [...quizList].sort((a, b) => {
      const tsA = toUnixSeconds(a?.created_at) || 0
      const tsB = toUnixSeconds(b?.created_at) || 0
      if (tsA !== tsB) {
        return tsA - tsB
      }
      return Number(a?.id || 0) - Number(b?.id || 0)
    })
    quizItems.value = sortedQuizList
      .map((item) => normalizeQuizItem(item))
      .filter(Boolean)
    currentQuizIndex.value = quizItems.value.length > 0 ? quizItems.value.length - 1 : -1
    isQuizPanelOpen.value = false

    const totalList = Array.isArray(statsData) ? statsData : []
    stats.value = totalList.map((item) => ({
      label: `${item.service_type.toUpperCase()} 成功`,
      value: `${item.request_success || 0}`
    }))

    const relayList = Array.isArray(relayLogsData) ? relayLogsData : []
    logs.value = relayList
      .slice(-6)
      .reverse()
      .map((item) => `${formatTime(item.time)} ${item.service_type.toUpperCase()} ${item.status || 'unknown'}`)

    const latestSession = sessionData || sessions.value.find((item) => item.id === sessionId)
    const hasStarted = Boolean(latestSession?.start_time && !latestSession?.end_time)

    if (currentRuntime.status === 'paused') {
      sessionStatus.value = 'paused'
      isRunning.value = false
    } else if (currentRuntime.status === 'recording') {
      sessionStatus.value = 'recording'
      isRunning.value = true
    } else if (latestSession?.end_time) {
      sessionStatus.value = 'idle'
      isRunning.value = false
      setSessionRuntime(sessionId, {
        status: 'idle',
        elapsedSeconds: 0,
        runningSince: null
      })
    } else if (hasStarted) {
      sessionStatus.value = 'recording'
      isRunning.value = true
      if (!currentRuntime.runningSince) {
        setSessionRuntime(sessionId, {
          status: 'recording',
          elapsedSeconds: 0,
          runningSince: latestSession.start_time
        })
      }
    } else {
      sessionStatus.value = 'idle'
      isRunning.value = false
      setSessionRuntime(sessionId, {
        status: 'idle',
        elapsedSeconds: 0,
        runningSince: null
      })
    }

    await nextTick()
    if (transcriptListFeed.value) {
      transcriptListFeed.value.scrollTop = transcriptListFeed.value.scrollHeight
    }
    scrollSummaryToBottom()
    scrollQueueToBottom()
  }

  function openCourseModal() {
    showCreateCourseModal.value = true
  }

  function openSessionModal() {
    if (!selectedCourseId.value) {
      return
    }
    showCreateSessionModal.value = true
  }

  async function createCourseAction() {
    try {
      if (!courseForm.value.name) {
        window.alert('请输入课程名称')
        return
      }

      const payload = {
        name: courseForm.value.name,
        code: courseForm.value.code || null,
        description: courseForm.value.description || null,
        teacher: courseForm.value.teacher || null
      }

      const created = await createCourse(payload)

      showCreateCourseModal.value = false
      courseForm.value = {
        code: '',
        name: '',
        description: '',
        teacher: ''
      }
      await loadCourses()
      selectedCourseId.value = created.id
    } catch (error) {
      window.alert(error instanceof Error ? error.message : '创建课程失败')
    }
  }

  async function createSessionAction() {
    try {
      if (!selectedCourseId.value) {
        return
      }
      if (!sessionForm.value.title) {
        window.alert('请输入课堂标题')
        return
      }

      const payload = {
        course_id: selectedCourseId.value,
        title: sessionForm.value.title
      }

      const created = await createSession(payload)

      showCreateSessionModal.value = false
      sessionForm.value = {
        title: ''
      }

      await loadSessions(selectedCourseId.value)
      selectedSessionId.value = created.id
    } catch (error) {
      window.alert(error instanceof Error ? error.message : '创建课堂失败')
    }
  }

  async function handleCourseChange() {
    try {
      await loadSessions(selectedCourseId.value)
    } catch (error) {
      window.alert(error instanceof Error ? error.message : '加载课堂失败')
    }
  }

  async function handleSessionChange() {
    try {
      await closeSessionWebSocket()
      await loadSessionData(selectedSessionId.value)
    } catch (error) {
      window.alert(error instanceof Error ? error.message : '加载课堂数据失败')
    }
  }

  async function toggleStartPause() {
    if (!canStartSession.value || !selectedSessionId.value || actionLoading.value) {
      return
    }
    actionLoading.value = true
    try {
      const buttonClickTs = Math.floor(Date.now() / 1000)
      const currentRuntime = getSessionRuntime(selectedSessionId.value)
      if (isRunning.value) {
        await pauseSession(selectedSessionId.value)
        const now = buttonClickTs
        const runningSince = currentRuntime.runningSince || now
        const elapsedSeconds = Math.max(0, currentRuntime.elapsedSeconds + (now - runningSince))
        setSessionRuntime(selectedSessionId.value, {
          status: 'paused',
          elapsedSeconds,
          runningSince: null
        })
        await stopRecordingLoop()
        scheduleWsClose()
        isRunning.value = false
        sessionStatus.value = 'paused'
        appendLog(`${formatTime(Math.floor(Date.now() / 1000))} 已暂停发送录音，延迟关闭接收`) 
      } else {
        clearWsCloseTimer()
        const now = buttonClickTs
        await startSession(selectedSessionId.value, now)
        const nextElapsedSeconds = currentRuntime.status === 'paused' ? currentRuntime.elapsedSeconds : 0
        setSessionRuntime(selectedSessionId.value, {
          status: 'recording',
          elapsedSeconds: nextElapsedSeconds,
          runningSince: now
        })
        await connectSessionWebSocket(selectedSessionId.value)
        await startRecordingLoop()
        isRunning.value = true
        sessionStatus.value = 'recording'
        appendLog(`${formatTime(Math.floor(Date.now() / 1000))} 已开始课堂并启动实时上传`) 
      }
      await loadSessions(selectedCourseId.value, { preserveSelection: true })
      if (isRunning.value) {
        await loadSessionData(selectedSessionId.value)
      }
    } catch (error) {
      window.alert(error instanceof Error ? error.message : '课堂控制失败')
    } finally {
      actionLoading.value = false
    }
  }

  async function endCurrentSession() {
    if (!canEndSession.value || !selectedSessionId.value || actionLoading.value) {
      return
    }
    actionLoading.value = true
    try {
      const buttonClickTs = Math.floor(Date.now() / 1000)
      await endSession(selectedSessionId.value, buttonClickTs)

      await stopRecordingLoop()
      scheduleWsClose()
      isRunning.value = false
      sessionStatus.value = 'idle'
      setSessionRuntime(selectedSessionId.value, {
        status: 'idle',
        elapsedSeconds: 0,
        runningSince: null
      })
      appendLog(`${formatTime(Math.floor(Date.now() / 1000))} 课堂结束，延迟关闭接收`) 

      generateSessionReport(selectedSessionId.value)
        .then(() => {
          appendLog(`${formatTime(Math.floor(Date.now() / 1000))} 已触发课后报告生成`) 
          showReportToast('success', '课后报告生成任务已提交')
        })
        .catch((reportError) => {
          const errorMessage = reportError instanceof Error ? reportError.message : '未知错误'
          appendLog(
            `${formatTime(Math.floor(Date.now() / 1000))} 课后报告触发失败：${errorMessage}`
          )
          showReportToast('error', `课后报告生成任务提交失败：${errorMessage}`)
        })

      await loadSessions(selectedCourseId.value, { preserveSelection: true })
      await loadSessionData(selectedSessionId.value)
    } catch (error) {
      window.alert(error instanceof Error ? error.message : '结束课堂失败')
    } finally {
      actionLoading.value = false
    }
  }

  const lineOpacity = (index) => {
    const total = transcriptItems.value.length
    const distance = total - index - 1
    return Math.max(0.4, 1 - distance * 0.11)
  }

  const freshLevel = (index) => {
    const distance = transcriptItems.value.length - index - 1
    if (distance < 0 || distance > 2) {
      return 0
    }
    return distance + 1
  }

  watch(selectedCourseId, async (newValue) => {
    if (!newValue) {
      await closeSessionWebSocket()
      await loadSessionData(null)
    }
  })

  watch(selectedSessionId, async (newValue, oldValue) => {
    if (oldValue && oldValue !== newValue) {
      await closeSessionWebSocket()
      recordingChunks.value = []
    }

    if (!newValue) {
      await loadSessionData(null)
      sessionStatus.value = 'idle'
      isRunning.value = false
      lastChunkBytes.value = 0
      micLevel.value = 0
    }
  })

  watch(rightPanelOpen, async (isOpen) => {
    if (!isOpen) {
      return
    }
    await nextTick()
    scrollQueueToBottom()
  })

  onMounted(async () => {
    loadKeywordSourceFilter()
    window.addEventListener('openclass:local-settings-updated', handleLocalSettingsUpdated)
    window.addEventListener('storage', handleLocalStorageUpdated)

    timerTick = window.setInterval(() => {
      nowTimestamp.value = Math.floor(Date.now() / 1000)
    }, 1000)

    try {
      await loadCourses()
      await refreshMicrophones()
      await ensureMediaStream()
      navigator.mediaDevices?.addEventListener?.('devicechange', onDeviceChange)
    } catch (error) {
      window.alert(error instanceof Error ? error.message : '加载课程失败')
    }
  })

  onUnmounted(() => {
    if (timerTick) {
      window.clearInterval(timerTick)
    }
    if (reportToastTimer) {
      window.clearTimeout(reportToastTimer)
      reportToastTimer = null
    }
    navigator.mediaDevices?.removeEventListener?.('devicechange', onDeviceChange)
    window.removeEventListener('openclass:local-settings-updated', handleLocalSettingsUpdated)
    window.removeEventListener('storage', handleLocalStorageUpdated)
    void closeSessionWebSocket()
    stopMicrophone()
  })

  return {
    sessionStatus,
    rightPanelOpen,
    debugPanelOpen,
    isRunning,
    actionLoading,
    courses,
    sessions,
    selectedCourseId,
    selectedSessionId,
    showCreateCourseModal,
    showCreateSessionModal,
    courseForm,
    sessionForm,
    transcriptFeed,
    transcriptListFeed,
    summaryFeed,
    queueFeed,
    transcriptItems,
    summaries,
    queuedQuestions,
    askedQuestionsHistory,
    isQuestionAsking,
    currentAskingQuestionText,
    currentAskingHistoryId,
    stats,
    logs,
    wsTrafficLogs,
    reportToast,
    sessionStatusLabel,
    canStartSession,
    canEndSession,
    timerLabel,
    latestSessionKeywords,
    currentKnowledgePoint,
    currentKnowledgeDescription,
    currentDifficultyLevel,
    currentDifficultyLabel,
    isKnowledgeExpanded,
    toggleKnowledgeExpanded,
    isQuizPanelOpen,
    toggleQuizPanel,
    currentQuizItem,
    quizIndexLabel,
    canShowPrevQuiz,
    canShowNextQuiz,
    showPrevQuiz,
    showNextQuiz,
    availableMicrophones,
    selectedMicrophoneId,
    micLevelPercent,
    lineOpacity,
    freshLevel,
    openCourseModal,
    openSessionModal,
    createCourseAction,
    createSessionAction,
    handleCourseChange,
    handleSessionChange,
    handleMicrophoneChange,
    toggleStartPause,
    endCurrentSession,
    refreshMicrophones,
    clearWsTrafficLogs
  }
}
