<template>
  <div class="app-shell">
    <div class="ambient ambient-left"></div>
    <div class="ambient ambient-right"></div>

    <header class="top-bar glass-panel">
      <div class="top-bar__left">
        <div>
          <p class="eyebrow">实时课堂助手</p>
          <h1>高级软件工程 · 第 6 讲</h1>
        </div>
      </div>

      <div class="top-bar__center">
        <span class="status-pill" :class="`is-${sessionStatus}`">
          <span class="status-pill__dot"></span>
          {{ sessionStatusLabel }}
        </span>
        <span class="timer">{{ timerLabel }}</span>
      </div>

      <button
        class="ghost-button"
        type="button"
        @click="rightPanelOpen = !rightPanelOpen"
      >
        {{ rightPanelOpen ? '收起队列' : '查看队列' }}
      </button>
    </header>

    <main class="workspace">
      <aside class="left-sidebar">
        <section class="sidebar-group">
          <p class="sidebar-title">关键词</p>
          <div class="keyword-list">
            <span
              v-for="keyword in keywords"
              :key="keyword"
              class="keyword-chip"
            >
              {{ keyword }}
            </span>
          </div>
        </section>

        <section class="sidebar-group">
          <p class="sidebar-title">实时摘要</p>
          <div class="summary-list">
            <p
              v-for="summary in summaries"
              :key="summary.time"
              class="summary-item"
            >
              <span>{{ summary.time }}</span>
              {{ summary.text }}
            </p>
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
          </div>
        </div>

        <div class="floating-stack">
          <section class="state-panel glass-panel">
            <div class="state-indicator">
              <span class="pulse-ring" :class="`mode-${systemState}`"></span>
              <div>
                <p class="eyebrow">当前状态</p>
                <h2>{{ systemStateLabel }}</h2>
              </div>
            </div>

            <div class="question-preview">
              <p class="eyebrow">当前生成问题</p>
              <p>{{ currentQuestion }}</p>
            </div>
          </section>

          <section class="control-bar glass-panel">
            <button class="primary-button" type="button">
              {{ isRunning ? '暂停' : '开始' }}
            </button>

            <label class="toggle-control">
              <span>自动提问</span>
              <button
                class="toggle-switch"
                :class="{ 'is-on': autoAskEnabled }"
                type="button"
                @click="autoAskEnabled = !autoAskEnabled"
              >
                <span></span>
              </button>
            </label>

            <label class="compact-slider">
              <span>频率</span>
              <input v-model="frequency" type="range" min="1" max="10" />
              <strong>{{ frequency }}</strong>
            </label>

            <label class="compact-slider volume">
              <span>音量</span>
              <input v-model="volume" type="range" min="0" max="100" />
              <strong>{{ volume }}%</strong>
            </label>
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
            </div>
          </section>
        </aside>
      </transition>
    </main>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref } from 'vue'

const sessionStatus = ref('recording')
const rightPanelOpen = ref(false)
const autoAskEnabled = ref(true)
const isRunning = ref(true)
const frequency = ref(4)
const volume = ref(68)
const systemState = ref('thinking')

const transcriptFeed = ref(null)

const transcriptItems = ref([
  {
    id: 1,
    kind: 'status',
    label: '系统',
    time: '00:02',
    text: '音频流已连接，正在进行课堂内容解析。'
  },
  {
    id: 2,
    kind: 'teacher',
    label: '教师',
    time: '00:08',
    text: '今天我们会讨论事件驱动架构中消息一致性的问题。'
  },
  {
    id: 3,
    kind: 'teacher',
    label: '教师',
    time: '00:23',
    text: '如果消费者处理失败，系统需要怎样保证重试过程不会造成重复副作用？'
  },
  {
    id: 4,
    kind: 'question',
    label: '生成问题',
    time: '00:29',
    text: '为什么幂等性通常是消息队列消费端设计里的关键要求？'
  },
  {
    id: 5,
    kind: 'status',
    label: '系统',
    time: '00:34',
    text: '已提取到主题词：消息投递、幂等性、补偿事务。'
  },
  {
    id: 6,
    kind: 'teacher',
    label: '教师',
    time: '00:41',
    text: '我们稍后会把 Saga 模式和两阶段提交做一个非常实际的对比。'
  },
  {
    id: 7,
    kind: 'question',
    label: '生成问题',
    time: '00:49',
    text: '在教学案例里，Saga 模式相比两阶段提交更适合分布式课堂作业系统的原因是什么？'
  }
])

const keywords = [
  '事件驱动',
  '消息一致性',
  '幂等性',
  '重试机制',
  'Saga',
  '补偿事务'
]

const summaries = [
  {
    time: '00:15',
    text: '教师引入消息一致性主题，聚焦消费者失败后的处理方式。'
  },
  {
    time: '00:33',
    text: '系统已识别课堂重点围绕幂等性、重试与副作用控制展开。'
  },
  {
    time: '00:46',
    text: '课程正在从基础概念过渡到 Saga 与 2PC 的工程对比。'
  }
]

const queuedQuestions = [
  {
    id: 1,
    order: 'Q1',
    text: '如果消息顺序被打乱，会怎样影响补偿事务的正确性？'
  },
  {
    id: 2,
    order: 'Q2',
    text: '课堂示例中哪些业务操作最适合设计成天然幂等？'
  },
  {
    id: 3,
    order: 'Q3',
    text: '为什么有些场景宁可接受最终一致性，也不选择强一致事务？'
  }
]

const stats = [
  { label: '转录速率', value: '142 字/分' },
  { label: '问题生成', value: '3 条待发' },
  { label: '摘要段数', value: '3 段' },
  { label: '关键词数', value: '6 个' }
]

const logs = [
  '00:34 提取到新关键词集合',
  '00:41 完成段落级摘要更新',
  '00:49 问题生成器输出一条高相关问题'
]

const currentQuestion = computed(
  () => transcriptItems.value.filter((item) => item.kind === 'question').at(-1)?.text ?? '等待生成中'
)

const sessionStatusLabel = computed(() =>
  sessionStatus.value === 'recording' ? '录制中' : '空闲中'
)

const systemStateLabel = computed(() => {
  if (systemState.value === 'thinking') {
    return 'Thinking'
  }
  if (systemState.value === 'speaking') {
    return 'Speaking'
  }
  return 'Ready'
})

const timerLabel = computed(() => '00:52:18')

const lineOpacity = (index) => {
  const total = transcriptItems.value.length
  const distance = total - index - 1
  return Math.max(0.4, 1 - distance * 0.11)
}

onMounted(async () => {
  await nextTick()
  if (transcriptFeed.value) {
    transcriptFeed.value.scrollTop = transcriptFeed.value.scrollHeight
  }
})
</script>
