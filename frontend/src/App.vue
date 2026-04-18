<template>
  <div class="app-shell">
    <div class="ambient ambient-left"></div>
    <div class="ambient ambient-right"></div>

    <header class="top-bar glass-panel">
      <div class="top-bar__left">
        <div class="top-selector-stack">
          <p class="eyebrow">课堂模拟学生提问助手</p>

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
                    {{ `第${session.seq || '-'}讲 · ${session.title || '未命名课堂'}` }}
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
            <span v-for="keyword in latestSessionKeywords" :key="keyword" class="keyword-chip">
              {{ keyword }}
            </span>
            <p v-if="latestSessionKeywords.length === 0" class="empty-text">暂无关键词</p>
          </div>
        </section>

        <section class="sidebar-group">
          <p class="sidebar-title">课堂摘要</p>
          <div ref="summaryFeed" class="summary-list">
            <p v-for="summary in summaries" :key="summary.id" class="summary-item">
              <span>{{ summary.time }}</span>
              {{ summary.text }}
            </p>
            <p v-if="summaries.length === 0" class="empty-text">暂无摘要</p>
          </div>
        </section>
      </aside>

      <section class="main-stage">
        <div class="transcript-stage" :class="{ 'is-question-history-open': isQuestionHistoryExpanded }">
          <div ref="transcriptFeed" class="transcript-feed glass-panel">
            <div class="feed-header">
              <p>课堂转录</p>
              <span>实时流式更新中</span>
            </div>

            <div ref="transcriptListFeed" class="transcript-list">
              <article
                v-for="(item, index) in transcriptItems"
                :key="item.id"
                class="transcript-item"
                :class="[
                  `kind-${item.kind}`,
                  {
                    'is-fresh-1': freshLevel(index) === 1,
                    'is-fresh-2': freshLevel(index) === 2,
                    'is-fresh-3': freshLevel(index) === 3
                  }
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

            <section class="question-history-stack">
              <section
                class="transcript-ask-bar"
                :class="{ 'is-asking': isQuestionAsking, 'is-expanded': isQuestionHistoryExpanded }"
                @mousedown.prevent
                @click="toggleQuestionHistoryExpanded"
              >
                <span class="transcript-ask-bar__state">
                  <span class="transcript-ask-bar__dot"></span>
                  {{ isQuestionAsking ? '提问中' : '未提问' }}
                </span>
                <span class="transcript-ask-bar__text">{{ currentAskingQuestionText }}</span>
              </section>

              <transition name="knowledge-rise">
                <section v-if="isQuestionHistoryExpanded" class="question-history-overlay">
                  <div class="question-history-header">
                    <span>提问历史</span>
                    <span>{{ askedQuestionsHistory.length }} 条</span>
                  </div>
                  <div ref="questionHistoryListRef" class="question-history-list">
                    <article
                      v-for="item in askedQuestionsHistory"
                      :key="item.id"
                      class="question-history-item"
                      :class="{ 'is-current': isQuestionAsking && item.id === currentAskingHistoryId }"
                    >
                      <span class="question-history-time">{{ item.askedAtLabel }}</span>
                      <p>{{ item.text }}</p>
                    </article>
                    <p v-if="askedQuestionsHistory.length === 0" class="empty-text">暂无提问历史</p>
                  </div>
                </section>
              </transition>
            </section>
          </div>

          <button
            class="quiz-toggle-button"
            type="button"
            :disabled="!selectedSessionId"
            @click="toggleQuizPanel"
          >
            {{ isQuizPanelOpen ? '收起小测' : '展开小测' }}
          </button>

          <aside class="quiz-drawer glass-panel" :class="{ 'is-open': isQuizPanelOpen }">
            <div class="quiz-drawer__header">
              <p>课堂小测</p>
              <span>{{ quizIndexLabel }}</span>
            </div>

            <div class="quiz-drawer__body" v-if="currentQuizItem">
                <p class="quiz-row"><strong>题目：</strong>{{ currentQuizItem.question }}</p>
                <template v-if="showQuizAnswer">
                  <p class="quiz-row" v-if="currentQuizItem.answer">
                    <strong>答案：</strong>{{ currentQuizItem.answer }}
                  </p>
                  <p class="quiz-row" v-if="currentQuizItem.explanation">
                    <strong>解释：</strong>{{ currentQuizItem.explanation }}</p>
                </template>
                <button
                  v-if="currentQuizItem.answer || currentQuizItem.explanation"
                  class="primary-button"
                  style="margin-top: 12px;"
                  @click="showQuizAnswer = !showQuizAnswer"
                >{{ showQuizAnswer ? '收起答案' : '显示答案' }}</button>
            </div>
            <p v-else class="empty-text">暂无小测题目</p>

            <div class="quiz-drawer__actions">
              <button class="ghost-button" type="button" :disabled="!canShowPrevQuiz" @click="showPrevQuiz">
                上一题
              </button>
              <button class="ghost-button" type="button" :disabled="!canShowNextQuiz" @click="showNextQuiz">
                下一题
              </button>
            </div>
          </aside>
        </div>

        <div class="floating-stack">
          <section class="mic-inline glass-panel">
            <label class="mic-select">
              <span>麦克风</span>
              <select v-model="selectedMicrophoneId" @change="handleMicrophoneChange">
                <option value="default">系统默认麦克风</option>
                <option v-for="mic in availableMicrophones" :key="mic.id" :value="mic.id">
                  {{ mic.label }}
                </option>
              </select>
            </label>
            <div class="level-meter">
              <div class="level-meter__bar">
                <div class="level-meter__fill" :style="{ width: `${micLevelPercent}%` }"></div>
              </div>
              <span class="level-meter__value">{{ micLevelPercent }}%</span>
            </div>
          </section>

          <section class="knowledge-stack">
            <section
              class="ask-status-bar glass-panel"
              :class="{ 'is-expanded': isKnowledgeExpanded }"
                @mousedown.prevent
              @click="toggleKnowledgeExpanded"
            >
              <div class="knowledge-main-row">
                <span class="difficulty-tag" :class="`level-${currentDifficultyLevel}`">
                  {{ currentDifficultyLabel }}
                </span>
                <strong>{{ currentKnowledgePoint }}</strong>
              </div>
            </section>

            <transition name="knowledge-rise">
              <section v-if="isKnowledgeExpanded" class="knowledge-overlay glass-panel">
                <div class="knowledge-extra">
                  {{ currentKnowledgeDescription }}
                </div>
              </section>
            </transition>
          </section>

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

            <div ref="queueFeed" class="queue-list">
              <article
                v-for="question in queuedQuestions"
                :key="question.id"
                class="queue-item"
              >
                <span>{{ question.order }}</span>
                <div class="queue-item__content">
                  <p>{{ question.text }}</p>
                  <small class="queue-item__time">{{ question.time || '--:--:--' }}</small>
                </div>
              </article>
              <p v-if="queuedQuestions.length === 0" class="empty-text">暂无待提问问题</p>
            </div>
          </section>
        </aside>
      </transition>
    </main>

    <section class="debug-dock">
      <button class="ghost-button more-toggle" type="button" @click="moreOverlayOpen = !moreOverlayOpen">
        {{ moreOverlayOpen ? '主页' : '更多' }}
      </button>
      <button v-if="showDebugToggle" class="ghost-button debug-toggle" type="button" @click="debugPanelOpen = !debugPanelOpen">
        {{ debugPanelOpen ? '收起' : '调试' }}
      </button>

      <transition name="drawer">
        <div v-if="showDebugToggle && debugPanelOpen" class="debug-panel glass-panel">
          <p class="debug-title">调试工具</p>
          <div class="debug-header-row">
            <p class="debug-meta">WS 收发记录（共 {{ wsTrafficLogs.length }} 条）</p>
            <div class="debug-actions">
              <button class="ghost-button debug-action-button" type="button" @click="copyWsTrafficLogs">{{ copyButtonText }}</button>
              <button class="ghost-button debug-action-button" type="button" @click="clearWsTrafficLogs">清空</button>
            </div>
          </div>
          <div ref="debugWsListRef" class="debug-ws-list" @scroll="handleDebugWsScroll">
            <p v-for="(item, index) in wsTrafficLogs" :key="`${index}-${item}`" class="debug-ws-item">
              {{ item }}
            </p>
            <p v-if="wsTrafficLogs.length === 0" class="debug-ws-empty">暂无 WS 日志</p>
          </div>
        </div>
      </transition>
    </section>

    <transition name="overlay-fade">
      <MoreLayout v-if="moreOverlayOpen" />
    </transition>

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
            <input v-model.trim="sessionForm.title" type="text" placeholder="例如：Web and HTTP" />
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
import { nextTick, onMounted, onUnmounted, ref, watch } from 'vue'

// 小测答案显示控制
const showQuizAnswer = ref(false)
import MoreLayout from './components/MoreLayout.vue'
import { useClassroomPage } from './composables/useClassroomPage'

const moreOverlayOpen = ref(false)
const showDebugToggle = ref(true)
const DEBUG_TOGGLE_STORAGE_KEY = 'openclass.ui.showDebugToggle'
const debugWsListRef = ref(null)
const questionHistoryListRef = ref(null)
const wsAutoFollow = ref(true)
const copyButtonText = ref('复制')
const isQuestionHistoryExpanded = ref(false)
let copyFeedbackTimer = null

const toggleQuestionHistoryExpanded = () => {
  isQuestionHistoryExpanded.value = !isQuestionHistoryExpanded.value
}

const syncDebugToggleFromStorage = () => {
  let visible = true
  try {
    const raw = window.localStorage.getItem(DEBUG_TOGGLE_STORAGE_KEY)
    if (raw != null) {
      visible = String(raw).toLowerCase() !== 'false'
    }
  } catch {
    visible = true
  }

  showDebugToggle.value = visible
}

const handleStorageEvent = (event) => {
  if (event?.key !== DEBUG_TOGGLE_STORAGE_KEY) {
    return
  }
  syncDebugToggleFromStorage()
}

const handleDebugToggleUpdated = (event) => {
  const visible = event?.detail?.visible
  if (typeof visible === 'boolean') {
    showDebugToggle.value = visible
    return
  }
  syncDebugToggleFromStorage()
}

const {
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
  wsTrafficLogs,
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
  clearWsTrafficLogs
} = useClassroomPage()

// 切换题目时自动隐藏答案
watch(currentQuizItem, () => {
  showQuizAnswer.value = false
})

watch(selectedSessionId, () => {
  isQuestionHistoryExpanded.value = false
})

watch(isQuestionHistoryExpanded, async (isOpen) => {
  if (!isOpen) {
    return
  }
  await nextTick()
  const listEl = questionHistoryListRef.value
  if (!listEl) {
    return
  }
  listEl.scrollTop = listEl.scrollHeight
})

watch(
  () => askedQuestionsHistory.value.length,
  async () => {
    if (!isQuestionHistoryExpanded.value) {
      return
    }
    await nextTick()
    const listEl = questionHistoryListRef.value
    if (!listEl) {
      return
    }
    listEl.scrollTop = listEl.scrollHeight
  }
)

async function copyWsTrafficLogs() {
  const content = wsTrafficLogs.value.join('\n')
  if (!content) {
    copyButtonText.value = '暂无内容'
    if (copyFeedbackTimer) {
      window.clearTimeout(copyFeedbackTimer)
    }
    copyFeedbackTimer = window.setTimeout(() => {
      copyButtonText.value = '复制'
    }, 500)
    return
  }

  try {
    await navigator.clipboard.writeText(content)
  } catch {
    const textarea = document.createElement('textarea')
    textarea.value = content
    textarea.setAttribute('readonly', 'true')
    textarea.style.position = 'fixed'
    textarea.style.top = '-9999px'
    document.body.appendChild(textarea)
    textarea.select()
    document.execCommand('copy')
    document.body.removeChild(textarea)
  }

  copyButtonText.value = '复制成功'
  if (copyFeedbackTimer) {
    window.clearTimeout(copyFeedbackTimer)
  }
  copyFeedbackTimer = window.setTimeout(() => {
    copyButtonText.value = '复制'
  }, 700)
}

function handleDebugWsScroll() {
  const listEl = debugWsListRef.value
  if (!listEl) {
    return
  }

  const threshold = 8
  wsAutoFollow.value = listEl.scrollTop + listEl.clientHeight >= listEl.scrollHeight - threshold
}

watch(wsTrafficLogs, async () => {
  await nextTick()
  const listEl = debugWsListRef.value
  if (!listEl || !wsAutoFollow.value) {
    return
  }
  listEl.scrollTop = listEl.scrollHeight
})

watch(debugPanelOpen, async (isOpen) => {
  if (!isOpen) {
    return
  }
  await nextTick()
  const listEl = debugWsListRef.value
  if (!listEl) {
    return
  }
  listEl.scrollTop = listEl.scrollHeight
  wsAutoFollow.value = true
})

onMounted(() => {
  syncDebugToggleFromStorage()
  window.addEventListener('storage', handleStorageEvent)
  window.addEventListener('openclass:debug-toggle-updated', handleDebugToggleUpdated)
})

onUnmounted(() => {
  if (copyFeedbackTimer) {
    window.clearTimeout(copyFeedbackTimer)
    copyFeedbackTimer = null
  }
  window.removeEventListener('storage', handleStorageEvent)
  window.removeEventListener('openclass:debug-toggle-updated', handleDebugToggleUpdated)
})
</script>
