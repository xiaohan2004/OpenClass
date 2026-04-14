<template>
  <div class="app-shell">
    <div class="ambient ambient-left"></div>
    <div class="ambient ambient-right"></div>

    <header class="top-bar glass-panel">
      <div class="top-bar__left">
        <div class="top-selector-stack">
          <p class="eyebrow">实时课堂助手</p>

          <div class="top-selectors-inline">
            <div class="mini-selector-row">
              <button
                class="icon-action"
                type="button"
                title="新建课程"
                aria-label="新建课程"
                @click="openCourseModal"
              >
                +
              </button>
              <label class="mini-selector">
                <select v-model.number="selectedCourseId" @change="handleCourseChange">
                  <option :value="null">请选择课程</option>
                  <option v-for="course in courses" :key="course.id" :value="course.id">
                    {{ course.name || `课程 ${course.id}` }}
                  </option>
                </select>
              </label>
            </div>

            <div class="mini-selector-row">
              <button
                class="icon-action"
                type="button"
                title="新建课堂"
                aria-label="新建课堂"
                :disabled="!selectedCourseId"
                @click="openSessionModal"
              >
                +
              </button>
              <label class="mini-selector">
                <select
                  v-model.number="selectedSessionId"
                  :disabled="!selectedCourseId"
                  @change="handleSessionChange"
                >
                  <option :value="null">请选择课堂</option>
                  <option v-for="session in sessions" :key="session.id" :value="session.id">
                    {{ session.title || `第 ${session.seq || '-'} 讲` }}
                  </option>
                </select>
              </label>
            </div>
          </div>
        </div>
      </div>

      <div class="top-bar__center">
        <span class="status-pill" :class="`is-${sessionStatus}`">
          <span class="status-pill__dot"></span>
          {{ sessionStatusLabel }}
        </span>
        <span class="timer">{{ timerLabel }}</span>
      </div>

      <div class="top-bar__actions">
        <button class="ghost-button" type="button" @click="rightPanelOpen = !rightPanelOpen">
          {{ rightPanelOpen ? '收起队列' : '查看队列' }}
        </button>
      </div>
    </header>

    <main class="workspace">
      <aside class="left-sidebar">
        <section class="sidebar-group">
          <p class="sidebar-title">关键词</p>
          <div class="keyword-list">
            <span v-for="keyword in keywords" :key="keyword" class="keyword-chip">
              {{ keyword }}
            </span>
            <p v-if="keywords.length === 0" class="empty-text">暂无关键词</p>
          </div>
        </section>

        <section class="sidebar-group">
          <p class="sidebar-title">实时摘要</p>
          <div class="summary-list">
            <p v-for="summary in summaries" :key="summary.id" class="summary-item">
              <span>{{ summary.time }}</span>
              {{ summary.text }}
            </p>
            <p v-if="summaries.length === 0" class="empty-text">暂无摘要</p>
          </div>
        </section>
      </aside>

      <section class="main-stage">
        <div ref="transcriptFeed" class="transcript-feed glass-panel">
          <div class="feed-header">
            <p>课堂转录</p>
            <span>实时流式更新中</span>
          </div>

          <div class="transcript-list">
            <article
              v-for="(item, index) in transcriptItems"
              :key="item.id"
              class="transcript-item"
              :class="[
                `kind-${item.kind}`,
                { 'is-fresh': index >= transcriptItems.length - 2 }
              ]"
              :style="{ opacity: lineOpacity(index) }"
            >
              <span class="transcript-meta">
                {{ item.label }} · {{ item.time }}
              </span>
              <p>{{ item.text }}</p>
            </article>
            <p v-if="transcriptItems.length === 0" class="empty-text">暂无转录数据</p>
          </div>
        </div>

        <div class="floating-stack">
          <section class="control-bar glass-panel simple-actions">
            <button
              class="primary-button"
              type="button"
              :disabled="!canStartSession || actionLoading"
              @click="toggleStartPause"
            >
              {{ isRunning ? '暂停' : '开始' }}
            </button>
            <button
              class="ghost-button"
              type="button"
              :disabled="!canEndSession || actionLoading"
              @click="endCurrentSession"
            >
              结束
            </button>
          </section>
        </div>
      </section>

      <transition name="drawer">
        <aside v-if="rightPanelOpen" class="right-panel glass-panel">
          <section class="drawer-group">
            <div class="drawer-header">
              <p>问题队列</p>
              <span>{{ queuedQuestions.length }} 条</span>
            </div>

            <div class="queue-list">
              <article
                v-for="question in queuedQuestions"
                :key="question.id"
                class="queue-item"
              >
                <span>{{ question.order }}</span>
                <p>{{ question.text }}</p>
              </article>
              <p v-if="queuedQuestions.length === 0" class="empty-text">暂无待提问问题</p>
            </div>
          </section>

          <section class="drawer-group">
            <div class="drawer-header">
              <p>日志 / 统计</p>
              <span>实时概览</span>
            </div>

            <div class="stats-list">
              <div v-for="stat in stats" :key="stat.label" class="stat-row">
                <span>{{ stat.label }}</span>
                <strong>{{ stat.value }}</strong>
              </div>
            </div>

            <div class="log-list">
              <p v-for="log in logs" :key="log" class="log-item">
                {{ log }}
              </p>
              <p v-if="logs.length === 0" class="empty-text">暂无日志</p>
            </div>
          </section>
        </aside>
      </transition>
    </main>

    <transition name="drawer">
      <section v-if="showCreateCourseModal" class="modal-mask">
        <div class="modal-card glass-panel">
          <h3>新建课程</h3>
          <label>
            课程名称
            <input v-model.trim="courseForm.name" type="text" placeholder="例如：高级软件工程" />
          </label>
          <label>
            课程编号
            <input v-model.trim="courseForm.code" type="text" placeholder="例如：SE-06" />
          </label>
          <label>
            教师
            <input v-model.trim="courseForm.teacher" type="text" placeholder="例如：张老师" />
          </label>
          <label>
            简介
            <textarea v-model.trim="courseForm.description" rows="3" placeholder="可选"></textarea>
          </label>
          <div class="modal-actions">
            <button class="ghost-button" type="button" @click="showCreateCourseModal = false">取消</button>
            <button class="primary-button" type="button" @click="createCourseAction">创建</button>
          </div>
        </div>
      </section>
    </transition>

    <transition name="drawer">
      <section v-if="showCreateSessionModal" class="modal-mask">
        <div class="modal-card glass-panel">
          <h3>新建课堂</h3>
          <label>
            课堂标题
            <input v-model.trim="sessionForm.title" type="text" placeholder="例如：第 6 讲 · 一致性" />
          </label>
          <label>
            课程序号
            <input v-model.number="sessionForm.seq" type="number" min="1" placeholder="例如：6" />
          </label>
          <label>
            配置（JSON，可选）
            <textarea
              v-model.trim="sessionForm.configText"
              rows="4"
              placeholder='例如：{"autoAsk": true, "interval": 20}'
            ></textarea>
          </label>
          <div class="modal-actions">
            <button class="ghost-button" type="button" @click="showCreateSessionModal = false">取消</button>
            <button class="primary-button" type="button" @click="createSessionAction">创建</button>
          </div>
        </div>
      </section>
    </transition>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'

const API_BASE = import.meta.env.VITE_API_BASE || ''

const sessionStatus = ref('idle')
const rightPanelOpen = ref(false)
const isRunning = ref(false)
const actionLoading = ref(false)
const nowTimestamp = ref(Math.floor(Date.now() / 1000))

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
  title: '',
  seq: null,
  configText: ''
})

const transcriptFeed = ref(null)
let timerTick = null

const transcriptItems = ref([])
const summaries = ref([])
const queuedQuestions = ref([])
const stats = ref([])
const logs = ref([])

const sessionStatusLabel = computed(() =>
  sessionStatus.value === 'recording' ? '录制中' : '空闲中'
)

const selectedCourse = computed(() =>
  courses.value.find((item) => item.id === selectedCourseId.value) || null
)

const selectedSession = computed(() =>
  sessions.value.find((item) => item.id === selectedSessionId.value) || null
)

const canStartSession = computed(() => Boolean(selectedCourseId.value && selectedSessionId.value))

const canEndSession = computed(() => Boolean(canStartSession.value && isRunning.value))

const timerLabel = computed(() => {
  const currentSession = selectedSession.value
  if (!currentSession?.start_time) {
    return '00:00:00'
  }

  const endTs = currentSession.end_time || nowTimestamp.value
  const seconds = Math.max(0, endTs - currentSession.start_time)
  const hh = String(Math.floor(seconds / 3600)).padStart(2, '0')
  const mm = String(Math.floor((seconds % 3600) / 60)).padStart(2, '0')
  const ss = String(seconds % 60).padStart(2, '0')
  return `${hh}:${mm}:${ss}`
})

const keywords = computed(() => {
  const text = transcriptItems.value.map((item) => item.text).join(' ')
  if (!text) {
    return []
  }
  const words = text
    .replace(/[，。！？；：、“”‘’（）()\-]/g, ' ')
    .split(/\s+/)
    .filter((word) => word.length >= 2)

  const countMap = words.reduce((acc, word) => {
    const nextValue = (acc[word] || 0) + 1
    return { ...acc, [word]: nextValue }
  }, {})

  return Object.entries(countMap)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 8)
    .map(([word]) => word)
})

async function apiRequest(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json'
    },
    ...options
  })

  if (!response.ok) {
    throw new Error(`请求失败: ${response.status}`)
  }

  const result = await response.json()
  if (result.code !== 0) {
    throw new Error(result.msg || '服务返回错误')
  }
  return result.data
}

function formatTime(ts) {
  if (!ts) {
    return '--:--:--'
  }
  const d = new Date(ts * 1000)
  const hh = String(d.getHours()).padStart(2, '0')
  const mm = String(d.getMinutes()).padStart(2, '0')
  const ss = String(d.getSeconds()).padStart(2, '0')
  return `${hh}:${mm}:${ss}`
}

async function loadCourses() {
  const data = await apiRequest('/api/courses')
  courses.value = Array.isArray(data) ? data : []
}

async function loadSessions(courseId) {
  if (!courseId) {
    sessions.value = []
    selectedSessionId.value = null
    return
  }

  const data = await apiRequest(`/api/courses/${courseId}/sessions`)
  sessions.value = Array.isArray(data) ? data : []
  selectedSessionId.value = null
}

async function loadSessionData(sessionId) {
  if (!sessionId) {
    transcriptItems.value = []
    summaries.value = []
    queuedQuestions.value = []
    stats.value = []
    logs.value = []
    isRunning.value = false
    sessionStatus.value = 'idle'
    return
  }

  const [transcriptsData, summariesData, questionsData, statsData, relayLogsData] = await Promise.all([
    apiRequest(`/api/sessions/${sessionId}/transcripts`),
    apiRequest(`/api/sessions/${sessionId}/segment-summaries`),
    apiRequest(`/api/sessions/${sessionId}/questions`),
    apiRequest('/api/stats/totals'),
    apiRequest('/api/relay-logs')
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
  queuedQuestions.value = questionList
    .filter((item) => item.status !== 'asked')
    .map((item, index) => ({
      id: item.id,
      order: `Q${index + 1}`,
      text: item.text
    }))

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

  const latestSession = sessions.value.find((item) => item.id === sessionId)
  isRunning.value = Boolean(latestSession?.start_time && !latestSession?.end_time)
  sessionStatus.value = isRunning.value ? 'recording' : 'idle'

  await nextTick()
  if (transcriptFeed.value) {
    transcriptFeed.value.scrollTop = transcriptFeed.value.scrollHeight
  }
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

    const created = await apiRequest('/api/courses', {
      method: 'POST',
      body: JSON.stringify(payload)
    })

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

    let parsedConfig = null
    if (sessionForm.value.configText) {
      try {
        parsedConfig = JSON.parse(sessionForm.value.configText)
      } catch {
        window.alert('配置 JSON 格式不正确')
        return
      }
    }

    const payload = {
      course_id: selectedCourseId.value,
      title: sessionForm.value.title,
      seq: sessionForm.value.seq || null,
      config: parsedConfig
    }

    const created = await apiRequest('/api/sessions', {
      method: 'POST',
      body: JSON.stringify(payload)
    })

    showCreateSessionModal.value = false
    sessionForm.value = {
      title: '',
      seq: null,
      configText: ''
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
    if (isRunning.value) {
      await apiRequest(`/api/sessions/${selectedSessionId.value}/pause`, {
        method: 'POST'
      })
      isRunning.value = false
      sessionStatus.value = 'idle'
    } else {
      await apiRequest(`/api/sessions/${selectedSessionId.value}/start`, {
        method: 'POST',
        body: JSON.stringify({ start_time: Math.floor(Date.now() / 1000) })
      })
      isRunning.value = true
      sessionStatus.value = 'recording'
    }
    await loadSessions(selectedCourseId.value)
    await loadSessionData(selectedSessionId.value)
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
    await apiRequest(`/api/sessions/${selectedSessionId.value}/end`, {
      method: 'POST',
      body: JSON.stringify({ end_time: Math.floor(Date.now() / 1000) })
    })
    isRunning.value = false
    sessionStatus.value = 'idle'
    await loadSessions(selectedCourseId.value)
    await loadSessionData(selectedSessionId.value)
  } catch (error) {
    window.alert(error instanceof Error ? error.message : '结束课堂失败')
  } finally {
    actionLoading.value = false
  }
}

watch(selectedCourseId, async (newValue) => {
  if (!newValue) {
    await loadSessionData(null)
  }
})

watch(selectedSessionId, async (newValue) => {
  if (!newValue) {
    await loadSessionData(null)
  }
})

const lineOpacity = (index) => {
  const total = transcriptItems.value.length
  const distance = total - index - 1
  return Math.max(0.4, 1 - distance * 0.11)
}

onMounted(async () => {
  timerTick = window.setInterval(() => {
    nowTimestamp.value = Math.floor(Date.now() / 1000)
  }, 1000)

  try {
    await loadCourses()
  } catch (error) {
    window.alert(error instanceof Error ? error.message : '加载课程失败')
  }
})

onUnmounted(() => {
  if (timerTick) {
    window.clearInterval(timerTick)
  }
})
</script>
