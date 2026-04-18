<template>
  <section class="course-data-root">
    <div class="course-data-toolbar glass-panel">
      <label class="course-data-field">
        <span>课程</span>
        <select v-model.number="selectedCourseId">
          <option :value="null">请选择课程</option>
          <option v-for="course in courses" :key="course.id" :value="course.id">
            {{ course.name || `课程 ${course.id}` }}
          </option>
        </select>
      </label>

      <label class="course-data-field">
        <span>课堂</span>
        <select v-model.number="selectedSessionId" :disabled="!selectedCourseId || loadingSessions">
          <option :value="null">请选择课堂</option>
          <option v-for="session in sessions" :key="session.id" :value="session.id">
            {{ session.title || `课堂 ${session.id}` }}
          </option>
        </select>
      </label>

      <div class="course-data-toolbar__actions">
        <button class="course-data-btn" type="button" @click="refreshCurrentSelection">
          刷新
        </button>
      </div>
    </div>

    <div class="course-data-edit-grid">
      <section
        class="course-data-edit-card glass-panel"
        :class="{ 'is-disabled': !selectedCourseId }"
        role="button"
        tabindex="0"
        @click="openEditDialog('course')"
        @keyup.enter="openEditDialog('course')"
      >
        <header class="course-data-edit-card__head">
          <div>
            <p class="course-data-edit-card__title">课程信息</p>
            <span class="course-data-edit-card__desc">点击卡片弹出编辑框</span>
          </div>
          <span class="course-data-edit-card__badge">
            {{ selectedCourseId ? `ID ${selectedCourseId}` : '未选择' }}
          </span>
        </header>

        <div v-if="!selectedCourseId" class="course-data-edit-card__empty">
          先选择课程，再编辑课程信息。
        </div>

        <div v-else class="course-data-edit-card__display">
          <p><strong>课程编号：</strong>{{ selectedCourse?.code || '未设置' }}</p>
          <p><strong>课程名称：</strong>{{ selectedCourse?.name || '未设置' }}</p>
          <p><strong>授课教师：</strong>{{ selectedCourse?.teacher || '未设置' }}</p>
          <p><strong>课程简介：</strong>{{ selectedCourse?.description || '未设置' }}</p>

          <div class="course-data-edit-card__actions course-data-edit-card__actions--compact">
            <small v-if="courseSaveMessage" class="course-data-edit-card__tip course-data-edit-card__tip--success">
              {{ courseSaveMessage }}
            </small>
            <small v-if="courseSaveError" class="course-data-edit-card__tip course-data-edit-card__tip--error">
              {{ courseSaveError }}
            </small>
          </div>
        </div>
      </section>

      <section
        class="course-data-edit-card glass-panel"
        :class="{ 'is-disabled': !selectedSessionId }"
        role="button"
        tabindex="0"
        @click="openEditDialog('session')"
        @keyup.enter="openEditDialog('session')"
      >
        <header class="course-data-edit-card__head">
          <div>
            <p class="course-data-edit-card__title">课堂信息</p>
            <span class="course-data-edit-card__desc">点击卡片弹出编辑框</span>
          </div>
          <span class="course-data-edit-card__badge">
            {{ selectedSessionId ? `ID ${selectedSessionId}` : '未选择' }}
          </span>
        </header>

        <div v-if="!selectedSessionId" class="course-data-edit-card__empty">
          先选择课堂，再编辑课堂信息。
        </div>

        <div v-else class="course-data-edit-card__display">
          <p><strong>课堂标题：</strong>{{ selectedSession?.title || '未设置' }}</p>
          <p><strong>课堂序号：</strong>{{ selectedSession?.seq || '未设置' }}</p>
          <p><strong>开始时间：</strong>{{ formatTimestamp(selectedSession?.start_time, '未开始') }}</p>
          <p><strong>结束时间：</strong>{{ formatTimestamp(selectedSession?.end_time, '未结束') }}</p>

          <div class="course-data-edit-card__actions course-data-edit-card__actions--compact">
            <small v-if="sessionSaveMessage" class="course-data-edit-card__tip course-data-edit-card__tip--success">
              {{ sessionSaveMessage }}
            </small>
            <small v-if="sessionSaveError" class="course-data-edit-card__tip course-data-edit-card__tip--error">
              {{ sessionSaveError }}
            </small>
          </div>
        </div>
      </section>
    </div>

    <section class="course-data-chooser glass-panel">
      <div class="course-data-chooser__head">
        <div>
          <p>显示内容</p>
          <span>按需勾选要展示的课堂数据类型</span>
        </div>

        <div class="course-data-chooser__actions">
          <button class="course-data-btn course-data-btn--subtle" type="button" @click="selectAllSections">
            全选
          </button>
          <button class="course-data-btn course-data-btn--subtle" type="button" @click="clearSelectedSections">
            清空
          </button>
        </div>
      </div>

      <div class="course-data-section-switches">
        <button
          v-for="section in sectionDefinitions"
          :key="section.id"
          class="course-data-switch"
          :class="{ 'is-active': selectedSectionIds.includes(section.id) }"
          type="button"
          @click="toggleSection(section.id)"
        >
          <span class="course-data-switch__icon">{{ section.symbol }}</span>
          <span class="course-data-switch__label">{{ section.label }}</span>
          <small v-if="section.id !== 'timelineStats'" class="course-data-switch__count">{{ sectionCounts[section.id] || 0 }}</small>
        </button>
      </div>
    </section>

    <div v-if="error" class="course-data-state course-data-state--error glass-panel">
      {{ error }}
    </div>

    <div v-else-if="loading || loadingSessions" class="course-data-state glass-panel">
      课程内容加载中...
    </div>

    <div v-else-if="!selectedCourseId" class="course-data-state glass-panel">
      先选择课程，再选择课堂查看课堂数据。
    </div>

    <div v-else-if="!selectedSessionId" class="course-data-state glass-panel">
      已选课程，继续选择课堂。
    </div>

    <div v-else-if="visibleSections.length === 0" class="course-data-state glass-panel">
      先在上方选择要展示的内容类型。
    </div>

    <div v-else class="course-data-grid">
      <article
        v-for="section in displaySections"
        :key="section.id"
        class="course-data-card glass-panel"
        :class="{ 'course-data-card--timeline': section.id === 'timelineStats' }"
      >
        <header class="course-data-card__head">
          <div>
            <p class="course-data-card__label">{{ section.label }}</p>
            <span class="course-data-card__desc">{{ section.description }}</span>
          </div>
          <span v-if="section.id !== 'timelineStats'" class="course-data-card__count">{{ section.count }} 条</span>
        </header>

        <div v-if="section.id !== 'timelineStats' && section.items.length === 0" class="course-data-card__empty">
          暂无{{ section.label }}数据
        </div>

        <div v-else class="course-data-card__list" :class="{ 'course-data-card__list--timeline': section.id === 'timelineStats' }">
          <div v-if="section.id === 'timelineStats'" class="course-data-timeline">
            <div class="course-data-timeline__toolbar">
              <span class="course-data-timeline__hint">缩放</span>
              <input
                v-model.number="timelineZoom"
                class="course-data-timeline__zoom"
                type="range"
                min="1"
                max="8"
                step="0.5"
              />
              <span class="course-data-timeline__hint">{{ timelineBucketCount }} 个时间点</span>
              <button class="course-data-btn course-data-btn--subtle" type="button" @click="loadTimelineStats">
                刷新统计图
              </button>
              <button
                class="course-data-btn course-data-btn--subtle"
                type="button"
                :disabled="!timelineRangeChanged"
                @click="resetTimelineRange"
              >
                重置范围
              </button>
            </div>

            <div v-if="timelineLoading" class="course-data-card__empty">
              正在生成统计图...
            </div>

            <div
              v-else
              class="course-data-timeline__chart-wrap"
              @mousedown="handleTimelineMouseDown"
              @mousemove="handleTimelineMouseMove"
              @mouseup="handleTimelineMouseUp"
              @mouseleave="handleTimelineMouseLeave"
            >
              <svg
                class="course-data-timeline__chart"
                :viewBox="`0 0 ${TIMELINE_CHART_WIDTH} ${TIMELINE_CHART_HEIGHT}`"
                preserveAspectRatio="none"
                aria-hidden="true"
              >
                <line
                  v-for="tick in timelineYAxisTicks"
                  :key="`timeline-y-grid-${tick.value}`"
                  class="course-data-timeline__grid"
                  :x1="TIMELINE_CHART_PADDING.left"
                  :y1="tick.y"
                  :x2="TIMELINE_CHART_WIDTH - TIMELINE_CHART_PADDING.right"
                  :y2="tick.y"
                />

                <line
                  class="course-data-timeline__axis"
                  :x1="TIMELINE_CHART_PADDING.left"
                  :y1="TIMELINE_CHART_PADDING.top"
                  :x2="TIMELINE_CHART_PADDING.left"
                  :y2="TIMELINE_CHART_HEIGHT - TIMELINE_CHART_PADDING.bottom"
                />
                <line
                  class="course-data-timeline__axis"
                  :x1="TIMELINE_CHART_PADDING.left"
                  :y1="TIMELINE_CHART_HEIGHT - TIMELINE_CHART_PADDING.bottom"
                  :x2="TIMELINE_CHART_WIDTH - TIMELINE_CHART_PADDING.right"
                  :y2="TIMELINE_CHART_HEIGHT - TIMELINE_CHART_PADDING.bottom"
                />

                <text
                  v-for="tick in timelineYAxisTicks"
                  :key="`timeline-y-label-${tick.value}`"
                  class="course-data-timeline__axis-text"
                  :x="TIMELINE_CHART_PADDING.left - 8"
                  :y="tick.y"
                  text-anchor="end"
                  dominant-baseline="middle"
                >
                  {{ tick.value }}
                </text>

                <text
                  v-for="label in timelineBuckets.xLabels"
                  :key="`timeline-x-label-${label.label}-${label.x}`"
                  class="course-data-timeline__axis-text"
                  :x="label.x"
                  :y="TIMELINE_CHART_HEIGHT - 14"
                  text-anchor="middle"
                >
                  {{ label.label }}
                </text>

                <path
                  v-for="line in timelineVisibleLines"
                  :key="`timeline-line-${line.id}`"
                  class="course-data-timeline__line"
                  :stroke="line.color"
                  :d="timelineLinePath(line.points)"
                />

                <line
                  v-if="timelineCursorX != null"
                  class="course-data-timeline__cursor"
                  :x1="timelineCursorX"
                  :x2="timelineCursorX"
                  :y1="TIMELINE_CHART_PADDING.top"
                  :y2="TIMELINE_CHART_HEIGHT - TIMELINE_CHART_PADDING.bottom"
                />

                <rect
                  v-if="timelineDragRect"
                  class="course-data-timeline__brush"
                  :x="timelineDragRect.x"
                  :y="TIMELINE_CHART_PADDING.top"
                  :width="timelineDragRect.width"
                  :height="timelinePlotHeight"
                />
              </svg>

            </div>

            <p v-if="timelineError" class="course-data-timeline__warning">{{ timelineError }}</p>

            <div class="course-data-timeline__legend">
              <button
                v-for="line in timelineBuckets.lines"
                :key="`timeline-legend-${line.id}`"
                class="course-data-timeline__legend-item"
                :class="{ 'is-inactive': !isTimelineLineVisible(line.id) }"
                type="button"
                @click="toggleTimelineLine(line.id)"
              >
                <span class="course-data-timeline__legend-dot" :style="{ background: line.color }"></span>
                <span>{{ line.label }}</span>
              </button>
            </div>
          </div>

          <div v-else-if="sectionLoadingState[section.id]" class="course-data-card__empty">
            正在请求{{ section.label }}...
          </div>

          <template v-else-if="section.id === 'transcripts'">
            <article
              v-for="item in section.items"
              :key="item.id"
              class="course-data-item course-data-item--clickable"
              role="button"
              tabindex="0"
              @click="openDetail(section, item)"
              @keyup.enter="openDetail(section, item)"
            >
              <div class="course-data-item__meta">
                <strong>{{ item.displayTitle }}</strong>
                <span>{{ item.timeLabel }}</span>
              </div>
              <pre>{{ item.text }}</pre>
            </article>
          </template>

          <template v-else-if="section.id === 'questions'">
            <article
              v-for="item in section.items"
              :key="item.id"
              class="course-data-item course-data-item--clickable"
              role="button"
              tabindex="0"
              @click="openDetail(section, item)"
              @keyup.enter="openDetail(section, item)"
            >
              <div class="course-data-item__meta">
                <strong>{{ item.displayTitle }}</strong>
                <span>{{ item.timeLabel }}</span>
              </div>
              <div class="course-data-item__chips">
                <span class="course-data-mini-chip">{{ item.statusLabel }}</span>
                <span class="course-data-mini-chip">评分 {{ item.scoreLabel }}</span>
              </div>
              <pre>{{ item.text }}</pre>
            </article>
          </template>

          <template v-else-if="section.id === 'summaries'">
            <article
              v-for="item in section.items"
              :key="item.id"
              class="course-data-item course-data-item--clickable"
              role="button"
              tabindex="0"
              @click="openDetail(section, item)"
              @keyup.enter="openDetail(section, item)"
            >
              <div class="course-data-item__meta">
                <strong>{{ item.displayTitle }}</strong>
                <span>{{ item.timeLabel }}</span>
              </div>
              <pre>{{ item.text }}</pre>
            </article>
          </template>

          <template v-else-if="section.id === 'keywords'">
            <article
              v-for="item in section.items"
              :key="item.id"
              class="course-data-item course-data-item--clickable"
              role="button"
              tabindex="0"
              @click="openDetail(section, item)"
              @keyup.enter="openDetail(section, item)"
            >
              <div class="course-data-item__meta">
                <strong>{{ item.displayTitle }}</strong>
                <span>{{ item.timeLabel }}</span>
              </div>
              <div class="course-data-tag-cloud">
                <span v-for="keyword in item.keywords" :key="keyword" class="course-data-mini-chip">
                  {{ keyword }}
                </span>
              </div>
            </article>
          </template>

          <template v-else-if="section.id === 'quizItems'">
            <article
              v-for="item in section.items"
              :key="item.id"
              class="course-data-item course-data-item--clickable"
              role="button"
              tabindex="0"
              @click="openDetail(section, item)"
              @keyup.enter="openDetail(section, item)"
            >
              <div class="course-data-item__meta">
                <strong>{{ item.displayTitle }}</strong>
                <span>{{ item.timeLabel }}</span>
              </div>
              <p class="course-data-item__title">题目</p>
              <pre>{{ item.question }}</pre>
              <p v-if="item.answer" class="course-data-item__title">答案</p>
              <pre v-if="item.answer">{{ item.answer }}</pre>
              <p v-if="item.explanation" class="course-data-item__title">解释</p>
              <pre v-if="item.explanation">{{ item.explanation }}</pre>
            </article>
          </template>

          <template v-else-if="section.id === 'knowledgePoints'">
            <article
              v-for="item in section.items"
              :key="item.id"
              class="course-data-item course-data-item--clickable"
              role="button"
              tabindex="0"
              @click="openDetail(section, item)"
              @keyup.enter="openDetail(section, item)"
            >
              <div class="course-data-item__meta">
                <strong>{{ item.displayTitle }}</strong>
                <span>{{ item.timeLabel }}</span>
              </div>
              <div class="course-data-item__chips">
                <span class="course-data-mini-chip">难度 {{ item.difficultyLabel }}</span>
              </div>
              <pre>{{ item.description }}</pre>
            </article>
          </template>

          <template v-else-if="section.id === 'reports'">
            <article
              v-for="item in section.items"
              :key="item.id"
              class="course-data-item course-data-item--clickable"
              role="button"
              tabindex="0"
              @click="openDetail(section, item)"
              @keyup.enter="openDetail(section, item)"
            >
              <div class="course-data-item__meta">
                <strong>{{ item.displayTitle }}</strong>
                <span>{{ item.timeLabel }}</span>
              </div>
              <p v-if="item.filePath" class="course-data-item__subtitle">文件：{{ item.filePath }}</p>
              <p class="course-data-item__subtitle">预览：{{ item.contentPreview }}</p>
              <pre class="course-data-item__content">{{ item.content }}</pre>
            </article>
          </template>
        </div>
      </article>
    </div>

    <Teleport to="body">
      <div v-if="timelineTooltipDetail" class="course-data-timeline__tooltip" :style="timelineTooltipStyle">
        <p class="course-data-timeline__tooltip-time">{{ timelineTooltipDetail.timeLabel }}</p>
        <p class="course-data-timeline__tooltip-total">总计：{{ timelineTooltipDetail.total }}</p>
        <div
          v-for="line in timelineTooltipDetail.lines"
          :key="`timeline-tooltip-line-${line.id}`"
          class="course-data-timeline__tooltip-row"
        >
          <span class="course-data-timeline__tooltip-dot" :style="{ background: line.color }"></span>
          <span>{{ line.label }}</span>
          <strong>{{ line.value }}</strong>
        </div>
      </div>
    </Teleport>

    <Teleport to="body">
      <div v-if="detailVisible" class="course-data-detail-mask" @click.self="closeDetail">
        <div class="course-data-detail glass-panel">
          <header class="course-data-detail__head">
            <div>
              <p class="course-data-detail__eyebrow">{{ detailSectionLabel }}</p>
              <h3>{{ detailTitle }}</h3>
              <span class="course-data-detail__meta">{{ detailMeta }}</span>
            </div>
            <button class="course-data-detail__close" type="button" @click="closeDetail">
              ×
            </button>
          </header>

          <div class="course-data-detail__body">
            <p v-if="detailLoading">详情加载中...</p>
            <p v-else-if="detailError">{{ detailError }}</p>
            <div v-else-if="detailFieldEntries.length > 0" class="course-data-detail-fields">
              <div
                v-for="entry in detailFieldEntries"
                :key="entry.key"
                class="course-data-detail-field"
                :class="{ 'is-wide': isWideDetailField(entry) }"
              >
                <p class="course-data-detail-field__line">
                  <strong>{{ entry.key }}：</strong>
                  <span v-if="entry.kind === 'text'">{{ entry.displayValue }}</span>
                </p>
                <pre v-if="entry.kind === 'block'" class="course-data-detail-field__block">{{ entry.displayValue }}</pre>
              </div>
            </div>
            <p v-else>暂无详情字段</p>
          </div>
        </div>
      </div>
    </Teleport>

    <Teleport to="body">
      <div v-if="editDialogVisible" class="course-data-detail-mask" @click.self="closeEditDialog">
        <div class="course-data-edit-modal glass-panel">
          <header class="course-data-detail__head">
            <div>
              <p class="course-data-detail__eyebrow">信息修改</p>
              <h3>{{ editDialogType === 'course' ? '修改课程信息' : '修改课堂信息' }}</h3>
            </div>
            <button class="course-data-detail__close" type="button" @click="closeEditDialog">×</button>
          </header>

          <div class="course-data-edit-card__fields">
            <template v-if="editDialogType === 'course'">
              <label class="course-data-edit-field">
                <span>课程编号</span>
                <input v-model.trim="courseDraft.code" type="text" placeholder="例如：CS-101" />
              </label>

              <label class="course-data-edit-field">
                <span>课程名称</span>
                <input v-model.trim="courseDraft.name" type="text" placeholder="例如：计算机网络" />
              </label>

              <label class="course-data-edit-field course-data-edit-field--wide">
                <span>课程简介</span>
                <textarea v-model.trim="courseDraft.description" rows="3" placeholder="可选"></textarea>
              </label>

              <label class="course-data-edit-field">
                <span>授课教师</span>
                <input v-model.trim="courseDraft.teacher" type="text" placeholder="例如：张老师" />
              </label>
            </template>

            <template v-else>
              <label class="course-data-edit-field course-data-edit-field--wide">
                <span>课堂标题</span>
                <input v-model.trim="sessionDraft.title" type="text" placeholder="例如：第二讲" />
              </label>
            </template>

            <div class="course-data-edit-card__actions course-data-edit-card__actions--center">
              <button class="course-data-btn course-data-btn--subtle" type="button" @click="closeEditDialog">
                取消
              </button>
              <button
                class="course-data-btn"
                type="button"
                :disabled="editDialogType === 'course' ? courseSaving : sessionSaving"
                @click="submitEditDialog"
              >
                {{ (editDialogType === 'course' ? courseSaving : sessionSaving) ? '保存中...' : '保存' }}
              </button>
              <small v-if="courseSaveError && editDialogType === 'course'" class="course-data-edit-card__tip course-data-edit-card__tip--error">
                {{ courseSaveError }}
              </small>
              <small v-if="sessionSaveError && editDialogType === 'session'" class="course-data-edit-card__tip course-data-edit-card__tip--error">
                {{ sessionSaveError }}
              </small>
            </div>
          </div>
        </div>
      </div>
    </Teleport>
  </section>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import {
  fetchCourses,
  fetchKeywordById,
  fetchKnowledgePointById,
  fetchQuestionById,
  fetchSessionKnowledgePoints,
  fetchSessionKeywords,
  fetchSessionQuestions,
  fetchSessionQuizItems,
  fetchSessionReports,
  fetchSessionSummaries,
  fetchSessionTranscripts,
  fetchQuizItemById,
  fetchReportById,
  fetchSessionsByCourse,
  fetchSummaryById,
  fetchTranscriptById,
  patchCourse,
  patchSession
} from '../../api/api'
import { useCoursePage } from '../../composables/useCoursePage'

const {
  courses,
  sessions,
  selectedCourseId,
  selectedSessionId,
  selectedCourse,
  selectedSession,
  selectedSectionIds,
  sectionDefinitions,
  sectionCounts,
  visibleSections,
  sectionSummaryLabel,
  sectionLoadingState,
  loading,
  loadingSessions,
  error,
  hasSessionSelection,
  refreshCurrentSelection,
  toggleSection,
  selectAllSections,
  clearSelectedSections
} = useCoursePage()

const displaySections = computed(() => {
  const sections = [...visibleSections.value]
  sections.sort((left, right) => {
    if (left.id === 'timelineStats' && right.id !== 'timelineStats') {
      return -1
    }
    if (left.id !== 'timelineStats' && right.id === 'timelineStats') {
      return 1
    }
    return 0
  })
  return sections
})

const courseDraft = reactive({
  code: '',
  name: '',
  description: '',
  teacher: ''
})

const sessionDraft = reactive({
  title: ''
})

const courseSaving = ref(false)
const sessionSaving = ref(false)
const courseSaveMessage = ref('')
const sessionSaveMessage = ref('')
const courseSaveError = ref('')
const sessionSaveError = ref('')
const editDialogVisible = ref(false)
const editDialogType = ref('course')

const detailVisible = ref(false)
const detailSectionId = ref('')
const detailItem = ref(null)
const detailLoading = ref(false)
const detailError = ref('')
const detailPreviewTitle = ref('')

const detailFetcherMap = {
  transcripts: fetchTranscriptById,
  questions: fetchQuestionById,
  summaries: fetchSummaryById,
  keywords: fetchKeywordById,
  quizItems: fetchQuizItemById,
  knowledgePoints: fetchKnowledgePointById,
  reports: fetchReportById
}

const TIMELINE_SERIES_META = [
  {
    id: 'transcripts',
    label: '转写分段',
    color: '#8de6a9',
    fetcher: fetchSessionTranscripts,
    timeResolver: (item) => item?.created_at
  },
  {
    id: 'questions',
    label: '问题',
    color: '#ffd27b',
    fetcher: fetchSessionQuestions,
    timeResolver: (item) => item?.created_at
  },
  {
    id: 'askedQuestions',
    label: '已提问',
    color: '#ff8fd1',
    fetcher: fetchSessionQuestions,
    timeResolver: (item) => item?.asked_at
  },
  {
    id: 'summaries',
    label: '分段小结',
    color: '#9fd5ff',
    fetcher: fetchSessionSummaries,
    timeResolver: (item) => item?.created_at
  },
  {
    id: 'keywords',
    label: '关键词',
    color: '#cdb4ff',
    fetcher: fetchSessionKeywords,
    timeResolver: (item) => item?.created_at
  },
  {
    id: 'quizItems',
    label: '小测题目',
    color: '#ff9f9f',
    fetcher: fetchSessionQuizItems,
    timeResolver: (item) => item?.created_at
  },
  {
    id: 'knowledgePoints',
    label: '知识点',
    color: '#86efe1',
    fetcher: fetchSessionKnowledgePoints,
    timeResolver: (item) => item?.created_at
  },
  {
    id: 'reports',
    label: '课后报告',
    color: '#ffb77a',
    fetcher: fetchSessionReports,
    timeResolver: (item) => item?.created_at
  }
]

const TIMELINE_CHART_WIDTH = 980
const TIMELINE_CHART_HEIGHT = 340
const TIMELINE_TOOLTIP_WIDTH = 260
const TIMELINE_TOOLTIP_MARGIN = 12
const TIMELINE_TOOLTIP_BASE_HEIGHT = 56
const TIMELINE_TOOLTIP_ROW_HEIGHT = 24
const TIMELINE_CHART_PADDING = {
  left: 56,
  right: 20,
  top: 16,
  bottom: 40
}

const timelineLoading = ref(false)
const timelineError = ref('')
const timelineZoom = ref(2)
const timelineRawSeries = ref({})
const timelineFullRange = ref({
  startMs: 0,
  endMs: 0
})
const timelineRange = ref({
  startMs: 0,
  endMs: 0
})
const timelineTooltip = ref(null)
const timelineDrag = ref({
  active: false,
  startX: 0,
  currentX: 0
})
const hiddenTimelineLineIds = ref([])

const timelinePlotWidth = computed(() => TIMELINE_CHART_WIDTH - TIMELINE_CHART_PADDING.left - TIMELINE_CHART_PADDING.right)
const timelinePlotHeight = computed(() => TIMELINE_CHART_HEIGHT - TIMELINE_CHART_PADDING.top - TIMELINE_CHART_PADDING.bottom)

const timelineBucketCount = computed(() => {
  const base = Math.round(24 * timelineZoom.value)
  return Math.max(24, Math.min(320, base))
})

const timelineHasSelection = computed(() => selectedSectionIds.value.includes('timelineStats'))

const timelineRangeChanged = computed(() => {
  const full = timelineFullRange.value
  const current = timelineRange.value
  if (!Number.isFinite(full.startMs) || !Number.isFinite(full.endMs)) {
    return false
  }

  return Math.abs(full.startMs - current.startMs) > 1000 || Math.abs(full.endMs - current.endMs) > 1000
})

const formatCompactTime = (timestampMs) => {
  if (!Number.isFinite(timestampMs)) {
    return '--'
  }
  const date = new Date(timestampMs)
  if (Number.isNaN(date.getTime())) {
    return '--'
  }

  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hour = String(date.getHours()).padStart(2, '0')
  const minute = String(date.getMinutes()).padStart(2, '0')
  return `${month}-${day} ${hour}:${minute}`
}

const toTimestampMs = (value) => {
  if (value == null || value === '') {
    return null
  }

  const numericValue = Number(value)
  let timestampMs = Number.isFinite(numericValue) ? numericValue : Date.parse(String(value))
  if (!Number.isFinite(timestampMs)) {
    return null
  }

  if (timestampMs < 1e12) {
    timestampMs *= 1000
  }

  return timestampMs
}

const resolveSessionRange = (allSeriesValues) => {
  const sessionStartMs = toTimestampMs(selectedSession.value?.start_time)
  const sessionEndMs = toTimestampMs(selectedSession.value?.end_time)

  let minMs = Number.isFinite(sessionStartMs) ? sessionStartMs : Number.POSITIVE_INFINITY
  let maxMs = Number.isFinite(sessionEndMs) ? sessionEndMs : Number.NEGATIVE_INFINITY

  Object.values(allSeriesValues).forEach((timestamps) => {
    timestamps.forEach((timestamp) => {
      if (timestamp < minMs) {
        minMs = timestamp
      }
      if (timestamp > maxMs) {
        maxMs = timestamp
      }
    })
  })

  if (!Number.isFinite(minMs) || !Number.isFinite(maxMs)) {
    const now = Date.now()
    return {
      startMs: now - 30 * 60 * 1000,
      endMs: now + 30 * 60 * 1000
    }
  }

  if (maxMs <= minMs) {
    maxMs = minMs + 60 * 1000
  }

  const paddingMs = Math.max((maxMs - minMs) * 0.05, 5 * 60 * 1000)
  return {
    startMs: minMs - paddingMs,
    endMs: maxMs + paddingMs
  }
}

const buildTimelineCounts = (timestamps, startMs, bucketMs, bucketCount) => {
  const counts = new Array(bucketCount).fill(0)
  if (!Array.isArray(timestamps) || bucketCount <= 0) {
    return counts
  }

  timestamps.forEach((timestamp) => {
    const index = Math.round((timestamp - startMs) / bucketMs)
    if (index >= 0 && index < bucketCount) {
      counts[index] += 1
    }
  })
  return counts
}

const timelineBuckets = computed(() => {
  const startMs = timelineRange.value.startMs
  const endMs = timelineRange.value.endMs
  const bucketCount = timelineBucketCount.value
  if (!Number.isFinite(startMs) || !Number.isFinite(endMs) || endMs <= startMs) {
    return {
      xLabels: [],
      timeAt: () => null,
      lines: [],
      maxY: 1
    }
  }

  const durationMs = endMs - startMs
  const bucketMs = durationMs / Math.max(bucketCount - 1, 1)
  const xAt = (index) => {
    if (bucketCount <= 1) {
      return TIMELINE_CHART_PADDING.left + timelinePlotWidth.value / 2
    }
    return TIMELINE_CHART_PADDING.left + (index / (bucketCount - 1)) * timelinePlotWidth.value
  }
  const timeAt = (index) => startMs + index * bucketMs

  const lines = TIMELINE_SERIES_META.map((meta) => {
    const timestamps = timelineRawSeries.value[meta.id] || []
    const counts = buildTimelineCounts(timestamps, startMs, bucketMs, bucketCount)
    return {
      ...meta,
      counts
    }
  })

  const maxY = Math.max(
    ...lines.flatMap((line) => line.counts),
    1
  )

  const yAt = (count) => TIMELINE_CHART_PADDING.top + ((maxY - count) / maxY) * timelinePlotHeight.value

  const xLabels = [0, 1, 2, 3].map((position) => {
    const ratio = position / 3
    const index = Math.round(ratio * (bucketCount - 1))
    return {
      x: xAt(index),
      label: formatCompactTime(timeAt(index))
    }
  })

  return {
    lines: lines.map((line) => ({
      ...line,
      points: line.counts.map((count, index) => ({
        x: xAt(index),
        y: yAt(count),
        count
      }))
    })),
    maxY,
    xLabels,
    timeAt,
    bucketCount
  }
})

const timelineYAxisTicks = computed(() => {
  const maxY = timelineBuckets.value.maxY || 1
  const half = Math.ceil(maxY / 2)
  return [
    { value: maxY, y: TIMELINE_CHART_PADDING.top },
    { value: half, y: TIMELINE_CHART_PADDING.top + timelinePlotHeight.value / 2 },
    { value: 0, y: TIMELINE_CHART_HEIGHT - TIMELINE_CHART_PADDING.bottom }
  ]
})

const timelineTooltipDetail = computed(() => {
  if (!timelineTooltip.value) {
    return null
  }

  const index = timelineTooltip.value.index
  const lines = timelineBuckets.value.lines
    .filter((line) => !hiddenTimelineLineIds.value.includes(line.id))
    .map((line) => ({
    id: line.id,
    label: line.label,
    color: line.color,
    value: line.counts[index] || 0
    }))

  const total = lines.reduce((sum, line) => sum + line.value, 0)
  return {
    timeLabel: formatTimestamp(timelineBuckets.value.timeAt(index), '--'),
    lines,
    total
  }
})

const timelineTooltipStyle = computed(() => {
  if (!timelineTooltip.value || !timelineTooltipDetail.value) {
    return null
  }

  const viewportWidth = window.innerWidth || 0
  const viewportHeight = window.innerHeight || 0
  const estimatedHeight = TIMELINE_TOOLTIP_BASE_HEIGHT + timelineTooltipDetail.value.lines.length * TIMELINE_TOOLTIP_ROW_HEIGHT

  let left = timelineTooltip.value.clientX + TIMELINE_TOOLTIP_MARGIN
  if (left + TIMELINE_TOOLTIP_WIDTH > viewportWidth - 8) {
    left = viewportWidth - TIMELINE_TOOLTIP_WIDTH - 8
  }
  if (left < 8) {
    left = 8
  }

  let top = timelineTooltip.value.clientY + TIMELINE_TOOLTIP_MARGIN
  if (top + estimatedHeight > viewportHeight - 8) {
    top = timelineTooltip.value.clientY - estimatedHeight - TIMELINE_TOOLTIP_MARGIN
  }
  if (top < 8) {
    top = 8
  }

  return {
    left: `${left}px`,
    top: `${top}px`
  }
})

const timelineLinePath = (points) => {
  if (!Array.isArray(points) || points.length === 0) {
    return ''
  }
  return points
    .map((point, index) => `${index === 0 ? 'M' : 'L'}${point.x.toFixed(2)},${point.y.toFixed(2)}`)
    .join(' ')
}

const isTimelineLineVisible = (lineId) => !hiddenTimelineLineIds.value.includes(lineId)

const timelineVisibleLines = computed(() => (
  timelineBuckets.value.lines.filter((line) => isTimelineLineVisible(line.id))
))

const toggleTimelineLine = (lineId) => {
  if (hiddenTimelineLineIds.value.includes(lineId)) {
    hiddenTimelineLineIds.value = hiddenTimelineLineIds.value.filter((id) => id !== lineId)
    return
  }
  hiddenTimelineLineIds.value = [...hiddenTimelineLineIds.value, lineId]
}

const timelineCursorX = computed(() => {
  if (!timelineTooltip.value || !timelineBuckets.value.bucketCount) {
    return null
  }
  const denominator = Math.max(timelineBuckets.value.bucketCount - 1, 1)
  return TIMELINE_CHART_PADDING.left + (timelineTooltip.value.index / denominator) * timelinePlotWidth.value
})

const timelineDragRect = computed(() => {
  if (!timelineDrag.value.active) {
    return null
  }
  const startX = Math.min(timelineDrag.value.startX, timelineDrag.value.currentX)
  const endX = Math.max(timelineDrag.value.startX, timelineDrag.value.currentX)
  return {
    x: TIMELINE_CHART_PADDING.left + startX,
    width: Math.max(0, endX - startX)
  }
})

const clampTimelineRelativeX = (value) => {
  return Math.min(Math.max(value, 0), timelinePlotWidth.value)
}

const getTimelineRelativeX = (event) => {
  const rect = event.currentTarget.getBoundingClientRect()
  return clampTimelineRelativeX(event.clientX - rect.left - TIMELINE_CHART_PADDING.left)
}

const resetTimelineRange = () => {
  timelineRange.value = {
    ...timelineFullRange.value
  }
  timelineTooltip.value = null
}

const loadTimelineStats = async () => {
  if (!selectedSessionId.value || !timelineHasSelection.value) {
    return
  }

  timelineLoading.value = true
  timelineError.value = ''
  timelineTooltip.value = null

  try {
    const results = await Promise.allSettled(
      TIMELINE_SERIES_META.map((meta) => meta.fetcher(selectedSessionId.value))
    )

    const rawSeries = {}
    const failedLabels = []

    results.forEach((result, index) => {
      const meta = TIMELINE_SERIES_META[index]
      if (result.status !== 'fulfilled') {
        rawSeries[meta.id] = []
        failedLabels.push(meta.label)
        return
      }

      const list = Array.isArray(result.value) ? result.value : []
      rawSeries[meta.id] = list
        .map((item) => toTimestampMs(meta.timeResolver(item)))
        .filter((timestamp) => Number.isFinite(timestamp))
        .sort((left, right) => left - right)
    })

    timelineRawSeries.value = rawSeries
    const resolvedRange = resolveSessionRange(rawSeries)
    timelineFullRange.value = resolvedRange
    timelineRange.value = resolvedRange

    if (failedLabels.length > 0) {
      timelineError.value = `部分数据加载失败：${failedLabels.join('、')}`
    }
  } catch (loadError) {
    timelineError.value = loadError instanceof Error ? loadError.message : '统计图加载失败'
    timelineRawSeries.value = {}
  } finally {
    timelineLoading.value = false
  }
}

const handleTimelineMouseMove = (event) => {
  if (timelineDrag.value.active) {
    timelineDrag.value.currentX = getTimelineRelativeX(event)
    timelineTooltip.value = null
    return
  }

  if (!timelineBuckets.value.bucketCount) {
    timelineTooltip.value = null
    return
  }

  const rect = event.currentTarget.getBoundingClientRect()
  const rawX = event.clientX - rect.left - TIMELINE_CHART_PADDING.left
  const clampedX = Math.min(Math.max(rawX, 0), timelinePlotWidth.value)
  const ratio = timelinePlotWidth.value > 0 ? clampedX / timelinePlotWidth.value : 0
  const index = Math.round(ratio * Math.max(timelineBuckets.value.bucketCount - 1, 0))

  timelineTooltip.value = {
    index,
    clientX: event.clientX,
    clientY: event.clientY
  }
}

const handleTimelineMouseDown = (event) => {
  if (!timelineBuckets.value.bucketCount) {
    return
  }
  timelineDrag.value = {
    active: true,
    startX: getTimelineRelativeX(event),
    currentX: getTimelineRelativeX(event)
  }
  timelineTooltip.value = null
}

const applyTimelineBrushRange = () => {
  if (!timelineDrag.value.active) {
    return
  }

  const leftX = Math.min(timelineDrag.value.startX, timelineDrag.value.currentX)
  const rightX = Math.max(timelineDrag.value.startX, timelineDrag.value.currentX)
  const brushWidth = rightX - leftX

  timelineDrag.value = {
    active: false,
    startX: 0,
    currentX: 0
  }

  if (brushWidth < 8) {
    return
  }

  const currentStart = timelineRange.value.startMs
  const currentEnd = timelineRange.value.endMs
  if (!Number.isFinite(currentStart) || !Number.isFinite(currentEnd) || currentEnd <= currentStart) {
    return
  }

  const duration = currentEnd - currentStart
  const nextStart = currentStart + (leftX / timelinePlotWidth.value) * duration
  const nextEnd = currentStart + (rightX / timelinePlotWidth.value) * duration

  if (nextEnd - nextStart < 1000) {
    return
  }

  timelineRange.value = {
    startMs: nextStart,
    endMs: nextEnd
  }
}

const handleTimelineMouseUp = () => {
  applyTimelineBrushRange()
}

const handleTimelineMouseLeave = () => {
  if (timelineDrag.value.active) {
    applyTimelineBrushRange()
    return
  }
  timelineTooltip.value = null
}

watch(
  () => [selectedSessionId.value, timelineHasSelection.value],
  ([sessionId, hasSelection]) => {
    if (!sessionId || !hasSelection) {
      timelineRawSeries.value = {}
      timelineFullRange.value = {
        startMs: 0,
        endMs: 0
      }
      timelineError.value = ''
      timelineTooltip.value = null
      timelineDrag.value = {
        active: false,
        startX: 0,
        currentX: 0
      }
      hiddenTimelineLineIds.value = []
      return
    }
    void loadTimelineStats()
  },
  { immediate: true }
)

watch(timelineZoom, () => {
  timelineTooltip.value = null
})

const detailSectionLabel = computed(() => {
  const section = sectionDefinitions.find((item) => item.id === detailSectionId.value)
  return section?.label || '详情'
})

const detailTitle = computed(() => {
  if (detailPreviewTitle.value) {
    return detailPreviewTitle.value
  }

  return detailSectionLabel.value || '详情'
})

const detailMeta = computed(() => {
  if (!detailItem.value) {
    return ''
  }

  return (
    formatTimestamp(detailItem.value.created_at, '')
  )
})

const isTimeLikeField = (key) => (
  key === 'created_at'
  || key === 'asked_at'
  || key === 'start_time'
  || key === 'end_time'
)

const formatDetailFieldValue = (key, value) => {
  if (value === null || value === undefined || value === '') {
    return {
      kind: 'text',
      displayValue: 'null'
    }
  }

  if (isTimeLikeField(key)) {
    return {
      kind: 'text',
      displayValue: formatTimestamp(value, 'null')
    }
  }

  if (typeof value === 'string') {
    if (value.includes('\n') || value.length > 120) {
      return {
        kind: 'block',
        displayValue: value
      }
    }
    return {
      kind: 'text',
      displayValue: value
    }
  }

  if (typeof value === 'number' || typeof value === 'boolean') {
    return {
      kind: 'text',
      displayValue: String(value)
    }
  }

  try {
    return {
      kind: 'block',
      displayValue: JSON.stringify(value, null, 2)
    }
  } catch {
    return {
      kind: 'text',
      displayValue: String(value)
    }
  }
}

const detailFieldEntries = computed(() => {
  if (!detailItem.value || typeof detailItem.value !== 'object') {
    return []
  }

  const transcriptHiddenKeys = new Set(['transcript_ids', 'transcript_segments'])

  const entries = Object.entries(detailItem.value)
    .filter(([key]) => !key.endsWith('Label') && !transcriptHiddenKeys.has(key))
    .map(([key, value]) => {
      const formatted = formatDetailFieldValue(key, value)
      return {
        key,
        kind: formatted.kind,
        displayValue: formatted.displayValue
      }
    })

  const joinedTextEntries = entries.filter((entry) => entry.key === 'transcript_joined_text')
  const normalEntries = entries.filter((entry) => entry.key !== 'transcript_joined_text')
  return [...normalEntries, ...joinedTextEntries]
})

const isWideDetailField = (entry) => {
  if (entry.kind === 'block') {
    return true
  }
  return entry.displayValue.length > 26
}

const formatTimestamp = (value, fallback = '--') => {
  if (value == null || value === '') {
    return fallback
  }

  const numericValue = Number(value)
  let timestampMs = Number.isFinite(numericValue) ? numericValue : Date.parse(String(value))

  if (!Number.isFinite(timestampMs)) {
    return fallback
  }

  if (timestampMs < 1e12) {
    timestampMs *= 1000
  }

  const date = new Date(timestampMs)
  if (Number.isNaN(date.getTime())) {
    return fallback
  }

  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hour = String(date.getHours()).padStart(2, '0')
  const minute = String(date.getMinutes()).padStart(2, '0')
  const second = String(date.getSeconds()).padStart(2, '0')
  return `${year}-${month}-${day} ${hour}:${minute}:${second}`
}

const syncCourseDraft = (course) => {
  courseDraft.code = course?.code || ''
  courseDraft.name = course?.name || ''
  courseDraft.description = course?.description || ''
  courseDraft.teacher = course?.teacher || ''
}

const syncSessionDraft = (session) => {
  sessionDraft.title = session?.title || ''
}

watch(selectedCourse, (course) => {
  syncCourseDraft(course)
  courseSaveMessage.value = ''
  courseSaveError.value = ''
}, { immediate: true })

watch(selectedSession, (session) => {
  syncSessionDraft(session)
  sessionSaveMessage.value = ''
  sessionSaveError.value = ''
}, { immediate: true })

const openDetail = async (section, item) => {
  detailSectionId.value = section.id
  detailPreviewTitle.value = item?.displayTitle || section.label || '详情'
  detailItem.value = null
  detailError.value = ''
  detailVisible.value = true

  const detailFetcher = detailFetcherMap[section.id]
  if (!detailFetcher || item?.id == null) {
    return
  }

  detailLoading.value = true
  try {
    const latest = await detailFetcher(item.id)
    if (latest && typeof latest === 'object') {
      detailItem.value = latest
    }
  } catch (loadError) {
    detailError.value = loadError instanceof Error ? loadError.message : '详情加载失败'
  } finally {
    detailLoading.value = false
  }
}

const closeDetail = () => {
  detailVisible.value = false
  detailLoading.value = false
  detailError.value = ''
  detailPreviewTitle.value = ''
}

const openEditDialog = (type) => {
  if (type === 'course' && !selectedCourseId.value) {
    return
  }
  if (type === 'session' && !selectedSessionId.value) {
    return
  }

  editDialogType.value = type
  if (type === 'course') {
    syncCourseDraft(selectedCourse.value)
    courseSaveError.value = ''
  } else {
    syncSessionDraft(selectedSession.value)
    sessionSaveError.value = ''
  }
  editDialogVisible.value = true
}

const closeEditDialog = () => {
  editDialogVisible.value = false
}

const submitEditDialog = async () => {
  if (editDialogType.value === 'course') {
    await saveCourseInfo()
    if (!courseSaveError.value) {
      closeEditDialog()
    }
    return
  }

  await saveSessionInfo()
  if (!sessionSaveError.value) {
    closeEditDialog()
  }
}

const reloadCourseAndSessionOptions = async ({ keepSessionSelection = true } = {}) => {
  const currentCourseId = selectedCourseId.value
  const currentSessionId = selectedSessionId.value

  const latestCourses = await fetchCourses()
  courses.value = Array.isArray(latestCourses) ? latestCourses : []

  if (!currentCourseId) {
    return
  }

  const matchedCourse = courses.value.find((course) => course.id === currentCourseId) || null
  if (!matchedCourse) {
    selectedCourseId.value = null
    selectedSessionId.value = null
    sessions.value = []
    return
  }

  const latestSessions = await fetchSessionsByCourse(currentCourseId)
  sessions.value = Array.isArray(latestSessions) ? latestSessions : []

  if (
    keepSessionSelection &&
    currentSessionId &&
    sessions.value.some((session) => session.id === currentSessionId)
  ) {
    selectedSessionId.value = currentSessionId
    return
  }

  if (!sessions.value.some((session) => session.id === selectedSessionId.value)) {
    selectedSessionId.value = null
  }
}

const saveCourseInfo = async () => {
  if (!selectedCourseId.value || !selectedCourse.value) {
    return
  }

  courseSaving.value = true
  courseSaveMessage.value = ''
  courseSaveError.value = ''

  try {
    const payload = {
      code: courseDraft.code.trim(),
      name: courseDraft.name.trim(),
      description: courseDraft.description.trim(),
      teacher: courseDraft.teacher.trim()
    }
    const updatedCourse = await patchCourse(selectedCourseId.value, payload)
    if (updatedCourse && updatedCourse.id != null) {
      courses.value = courses.value.map((course) => (
        course.id === updatedCourse.id ? { ...course, ...updatedCourse } : course
      ))
    }

    await reloadCourseAndSessionOptions({ keepSessionSelection: true })
    const latestCourse = courses.value.find((course) => course.id === selectedCourseId.value) || null
    syncCourseDraft(latestCourse)

    courseSaveMessage.value = '课程信息已保存'
  } catch (saveError) {
    courseSaveError.value = saveError instanceof Error ? saveError.message : '课程保存失败'
  } finally {
    courseSaving.value = false
  }
}

const saveSessionInfo = async () => {
  if (!selectedSessionId.value || !selectedSession.value) {
    return
  }

  sessionSaving.value = true
  sessionSaveMessage.value = ''
  sessionSaveError.value = ''

  try {
    const payload = {
      title: sessionDraft.title.trim()
    }
    const updatedSession = await patchSession(selectedSessionId.value, payload)
    if (updatedSession && updatedSession.id != null) {
      sessions.value = sessions.value.map((session) => (
        session.id === updatedSession.id ? { ...session, ...updatedSession } : session
      ))
    }

    await reloadCourseAndSessionOptions({ keepSessionSelection: true })
    const latestSession = sessions.value.find((session) => session.id === selectedSessionId.value) || null
    syncSessionDraft(latestSession)

    sessionSaveMessage.value = '课堂信息已保存'
  } catch (saveError) {
    sessionSaveError.value = saveError instanceof Error ? saveError.message : '课堂保存失败'
  } finally {
    sessionSaving.value = false
  }
}
</script>

<style scoped>
.course-data-root {
  display: grid;
  gap: 14px;
}

.course-data-toolbar {
  border-radius: 20px;
  padding: 14px 16px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) auto;
  gap: 12px;
  align-items: end;
  background: linear-gradient(180deg, rgba(39, 69, 57, 0.82), rgba(28, 50, 42, 0.9));
  border: 1px solid rgba(132, 178, 150, 0.18);
}

.course-data-field {
  display: grid;
  gap: 8px;
}

.course-data-field span {
  color: rgba(223, 242, 231, 0.92);
  font-size: 0.9rem;
  font-weight: 700;
}

.course-data-field select {
  width: 100%;
  border: 1px solid rgba(127, 169, 143, 0.28);
  background: rgba(251, 253, 249, 0.88);
  border-radius: 14px;
  padding: 10px 12px;
  color: #1f2b22;
}

.course-data-field select:disabled {
  opacity: 0.58;
  cursor: not-allowed;
}

.course-data-toolbar__actions {
  display: flex;
  align-items: end;
}

.course-data-btn {
  border-radius: 14px;
  padding: 10px 14px;
  font-size: 0.84rem;
  font-weight: 800;
  color: #0f3a24;
  background: linear-gradient(180deg, rgba(144, 229, 168, 0.96), rgba(98, 199, 122, 0.94));
  box-shadow: inset 0 1px 0 rgba(244, 255, 246, 0.46);
}

.course-data-btn--subtle {
  color: rgba(225, 245, 232, 0.92);
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(161, 219, 178, 0.2);
  box-shadow: none;
}

.course-data-chooser,
.course-data-state,
.course-data-card,
.course-data-edit-card {
  border-radius: 20px;
  border: 1px solid rgba(132, 178, 150, 0.18);
}

.course-data-chooser__head p,
.course-data-card__label,
.course-data-item__title {
  margin: 0;
}

.course-data-mini-chip,
.course-data-card__count {
  border-radius: 999px;
  border: 1px solid rgba(165, 217, 181, 0.2);
  background: rgba(255, 255, 255, 0.08);
  color: rgba(233, 248, 237, 0.92);
}

.course-data-chooser {
  padding: 16px;
  background: linear-gradient(180deg, rgba(36, 61, 50, 0.82), rgba(25, 42, 35, 0.9));
}

.course-data-chooser__head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  margin-bottom: 14px;
}

.course-data-chooser__head p {
  color: #ecf8ef;
  font-weight: 800;
}

.course-data-chooser__head span {
  color: rgba(194, 226, 206, 0.82);
  font-size: 0.84rem;
}

.course-data-chooser__actions {
  display: flex;
  gap: 8px;
}

.course-data-edit-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.course-data-edit-card {
  padding: 14px;
  background: linear-gradient(180deg, rgba(36, 61, 51, 0.84), rgba(25, 41, 35, 0.92));
  transition: border-color 160ms ease, background 160ms ease;
}

.course-data-edit-card.is-disabled {
  opacity: 0.72;
  cursor: not-allowed;
}

.course-data-edit-card.is-disabled:hover {
  transform: none;
  border-color: rgba(132, 178, 150, 0.18);
}

.course-data-edit-card__head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
  margin-bottom: 14px;
}

.course-data-edit-card__title {
  margin: 0;
  color: #effaf2;
  font-size: 1.08rem;
  font-weight: 800;
}

.course-data-edit-card__desc {
  display: inline-block;
  margin-top: 4px;
  color: rgba(192, 225, 205, 0.8);
  font-size: 0.84rem;
}

.course-data-edit-card__badge {
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid rgba(165, 217, 181, 0.2);
  background: rgba(255, 255, 255, 0.08);
  color: rgba(233, 248, 237, 0.92);
  font-size: 0.84rem;
  white-space: nowrap;
}

.course-data-edit-card__empty {
  color: rgba(194, 226, 206, 0.84);
  font-size: 0.86rem;
}

.course-data-edit-card__fields {
  display: grid;
  gap: 10px;
}

.course-data-edit-card__display {
  display: grid;
  gap: 8px;
}

.course-data-edit-card__display p {
  margin: 0;
  color: rgba(230, 244, 235, 0.9);
  font-size: 0.86rem;
  line-height: 1.6;
}

.course-data-edit-field {
  display: grid;
  gap: 6px;
}

.course-data-edit-field span {
  color: rgba(223, 242, 231, 0.92);
  font-size: 0.84rem;
  font-weight: 700;
}

.course-data-edit-field input,
.course-data-edit-field textarea {
  width: 100%;
  border: 1px solid rgba(127, 169, 143, 0.28);
  background: rgba(251, 253, 249, 0.88);
  border-radius: 14px;
  padding: 10px 12px;
  color: #1f2b22;
}

.course-data-edit-field textarea {
  resize: vertical;
}

.course-data-edit-field--wide {
  grid-column: 1 / -1;
}

.course-data-edit-card__actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  margin-top: 4px;
}

.course-data-edit-card__actions--compact {
  justify-content: flex-start;
}

.course-data-edit-card__actions--center {
  justify-content: center;
}

.course-data-edit-card__tip {
  font-size: 0.84rem;
}

.course-data-edit-card__hint {
  color: rgba(194, 226, 206, 0.8);
  font-size: 0.84rem;
}

.course-data-edit-card__tip--success {
  color: rgba(187, 255, 203, 0.9);
}

.course-data-edit-card__tip--error {
  color: rgba(255, 188, 188, 0.92);
}

.course-data-section-switches {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.course-data-switch {
  min-width: 132px;
  display: inline-flex;
  align-items: center;
  gap: 9px;
  padding: 11px 12px;
  border-radius: 16px;
  border: 1px solid rgba(160, 210, 176, 0.18);
  background: rgba(255, 255, 255, 0.06);
  color: rgba(224, 241, 230, 0.9);
  transition: transform 180ms ease, border-color 180ms ease, background 180ms ease, box-shadow 180ms ease;
}

.course-data-switch:hover {
  transform: translateY(-1px);
  border-color: rgba(168, 233, 190, 0.48);
  box-shadow: 0 10px 22px rgba(7, 24, 16, 0.2);
}

.course-data-switch.is-active {
  color: #0f3b26;
  background: linear-gradient(180deg, rgba(144, 229, 168, 0.96), rgba(98, 199, 122, 0.94));
  border-color: rgba(145, 226, 174, 0.72);
}

.course-data-switch__icon {
  width: 28px;
  height: 28px;
  border-radius: 999px;
  display: grid;
  place-items: center;
  font-size: 0.78rem;
  font-weight: 800;
  background: rgba(255, 255, 255, 0.08);
}

.course-data-switch.is-active .course-data-switch__icon {
  background: rgba(255, 255, 255, 0.14);
}

.course-data-switch__label {
  font-size: 0.84rem;
  font-weight: 800;
}

.course-data-switch__count {
  margin-left: auto;
  font-size: 0.72rem;
  padding: 3px 8px;
}

.course-data-state {
  padding: 16px;
  color: rgba(230, 244, 235, 0.9);
  background: linear-gradient(180deg, rgba(35, 57, 47, 0.78), rgba(27, 41, 35, 0.88));
}

.course-data-state--error {
  border-color: rgba(255, 124, 124, 0.28);
  background: linear-gradient(180deg, rgba(86, 31, 31, 0.82), rgba(68, 25, 25, 0.9));
}

.course-data-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 14px;
}

.course-data-card {
  padding: 14px;
  background: linear-gradient(180deg, rgba(36, 61, 51, 0.84), rgba(25, 41, 35, 0.92));
}

.course-data-card--timeline {
  grid-column: 1 / -1;
}

.course-data-card__head {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  align-items: start;
  margin-bottom: 12px;
}

.course-data-card__label {
  color: #effaf2;
  font-size: 1rem;
  font-weight: 800;
}

.course-data-card__desc {
  color: rgba(192, 225, 205, 0.8);
  font-size: 0.84rem;
}

.course-data-card__count {
  padding: 5px 10px;
  font-size: 0.84rem;
}

.course-data-card__empty {
  color: rgba(192, 225, 205, 0.82);
  font-size: 0.88rem;
  padding: 14px 0 4px;
}

.course-data-card__list {
  display: grid;
  gap: 10px;
  max-height: min(58vh, 780px);
  overflow: auto;
  padding-right: 2px;
}

.course-data-card__list--timeline {
  max-height: none;
  overflow: visible;
}

.course-data-item {
  border-radius: 16px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(160, 210, 176, 0.12);
}

.course-data-item--clickable {
  cursor: pointer;
  transition: transform 160ms ease, border-color 160ms ease, background 160ms ease;
}

.course-data-item--clickable:hover {
  transform: translateY(-1px);
  border-color: rgba(168, 233, 190, 0.46);
  background: rgba(255, 255, 255, 0.08);
}

.course-data-item__meta {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  align-items: center;
  color: rgba(232, 247, 236, 0.9);
  margin-bottom: 10px;
}

.course-data-item__meta strong {
  font-size: 0.88rem;
}

.course-data-item__meta span,
.course-data-item__subtitle {
  color: rgba(187, 220, 200, 0.82);
  font-size: 0.84rem;
}

.course-data-item__subtitle {
  margin: 0 0 8px;
}

.course-data-item__chips,
.course-data-tag-cloud {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 10px;
}

.course-data-mini-chip {
  padding: 5px 9px;
  font-size: 0.84rem;
}

.course-data-item pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  color: #ecf8ef;
  font-family: inherit;
  font-size: 0.86rem;
  line-height: 1.6;
}

.course-data-item__content {
  max-height: 260px;
  overflow: auto;
}

.course-data-timeline {
  display: grid;
  gap: 10px;
}

.course-data-timeline__toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}

.course-data-timeline__hint {
  color: rgba(194, 226, 206, 0.82);
  font-size: 0.82rem;
}

.course-data-timeline__zoom {
  width: min(320px, 58vw);
}

.course-data-timeline__chart-wrap {
  position: relative;
  border-radius: 14px;
  border: 1px solid rgba(160, 210, 176, 0.16);
  background: rgba(255, 255, 255, 0.04);
  overflow: visible;
}

.course-data-timeline__chart {
  width: 100%;
  height: 320px;
  display: block;
}

.course-data-timeline__grid {
  stroke: rgba(205, 234, 216, 0.14);
  stroke-width: 1;
}

.course-data-timeline__axis {
  stroke: rgba(205, 234, 216, 0.35);
  stroke-width: 1;
}

.course-data-timeline__axis-text {
  fill: rgba(198, 228, 210, 0.9);
  font-size: 11px;
}

.course-data-timeline__line {
  fill: none;
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.course-data-timeline__cursor {
  stroke: rgba(255, 255, 255, 0.54);
  stroke-width: 1;
  stroke-dasharray: 4 4;
}

.course-data-timeline__brush {
  fill: rgba(141, 230, 169, 0.2);
  stroke: rgba(141, 230, 169, 0.72);
  stroke-width: 1;
}

.course-data-timeline__tooltip {
  position: fixed;
  min-width: 210px;
  max-width: 260px;
  width: 260px;
  z-index: 1200;
  pointer-events: none;
  border-radius: 12px;
  border: 1px solid rgba(170, 219, 187, 0.28);
  background: rgba(12, 29, 21, 0.9);
  color: rgba(237, 249, 241, 0.94);
  padding: 10px;
  box-shadow: 0 14px 28px rgba(4, 20, 14, 0.42);
}

.course-data-timeline__tooltip-time,
.course-data-timeline__tooltip-total {
  margin: 0;
  font-size: 0.82rem;
}

.course-data-timeline__tooltip-total {
  margin-top: 4px;
  color: rgba(190, 232, 205, 0.9);
}

.course-data-timeline__tooltip-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 5px;
  font-size: 0.82rem;
}

.course-data-timeline__tooltip-row strong {
  margin-left: auto;
}

.course-data-timeline__tooltip-dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  flex-shrink: 0;
}

.course-data-timeline__legend {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 12px;
}

.course-data-timeline__legend-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: rgba(220, 241, 229, 0.9);
  font-size: 0.82rem;
  border: 1px solid rgba(160, 210, 176, 0.2);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.04);
  padding: 4px 10px;
  cursor: pointer;
  transition: opacity 140ms ease, border-color 140ms ease, background 140ms ease;
}

.course-data-timeline__legend-item:hover {
  border-color: rgba(168, 233, 190, 0.5);
  background: rgba(255, 255, 255, 0.08);
}

.course-data-timeline__legend-item.is-inactive {
  opacity: 0.45;
  border-color: rgba(160, 210, 176, 0.12);
}

.course-data-timeline__legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 999px;
}

.course-data-timeline__warning {
  margin: 0;
  color: rgba(255, 196, 196, 0.92);
  font-size: 0.82rem;
}

.course-data-detail-mask {
  position: fixed;
  inset: 0;
  z-index: 80;
  display: grid;
  place-items: center;
  padding: 20px;
  background: rgba(4, 14, 10, 0.56);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
}

.course-data-detail {
  width: min(760px, calc(100vw - 32px));
  max-height: min(80vh, 820px);
  overflow: auto;
  border-radius: 22px;
  padding: 18px;
  background: linear-gradient(180deg, rgba(36, 61, 51, 0.96), rgba(25, 42, 35, 0.98));
  border: 1px solid rgba(132, 178, 150, 0.22);
}

.course-data-edit-modal {
  width: min(640px, calc(100vw - 32px));
  max-height: min(80vh, 820px);
  overflow: auto;
  border-radius: 22px;
  padding: 18px;
  background: linear-gradient(180deg, rgba(36, 61, 51, 0.96), rgba(25, 42, 35, 0.98));
  border: 1px solid rgba(132, 178, 150, 0.22);
}

.course-data-detail__head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
  margin-bottom: 16px;
}

.course-data-detail__eyebrow {
  margin: 0 0 4px;
  color: rgba(186, 225, 201, 0.8);
  font-size: 0.84rem;
}

.course-data-detail__head h3 {
  margin: 0;
  color: #effaf2;
  font-size: 1.3rem;
}

.course-data-detail__meta {
  display: inline-block;
  margin-top: 4px;
  color: rgba(194, 226, 206, 0.8);
  font-size: 0.92rem;
}

.course-data-detail__close {
  width: 36px;
  height: 36px;
  border-radius: 999px;
  border: 1px solid rgba(165, 217, 181, 0.2);
  color: rgba(239, 250, 242, 0.94);
  background: rgba(255, 255, 255, 0.08);
  font-size: 1.4rem;
  line-height: 1;
}

.course-data-detail__body {
  display: grid;
  gap: 10px;
  color: rgba(236, 248, 240, 0.92);
  line-height: 1.75;
  font-size: 0.98rem;
}

.course-data-detail-fields {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px 16px;
}

.course-data-detail-field {
  min-width: 0;
}

.course-data-detail-field.is-wide {
  grid-column: 1 / -1;
}

.course-data-detail-field__line {
  margin: 0;
  color: rgba(230, 244, 235, 0.9);
  font-size: 0.98rem;
  line-height: 1.6;
}

.course-data-detail-field__line strong {
  color: rgba(194, 226, 206, 0.92);
}

.course-data-detail-field__block {
  margin: 4px 0 0;
  white-space: pre-wrap;
  word-break: break-word;
  color: rgba(236, 248, 240, 0.94);
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
  font-size: 0.9rem;
  line-height: 1.55;
}

@media (max-width: 960px) {
  .course-data-toolbar {
    grid-template-columns: 1fr;
  }

  .course-data-edit-grid {
    grid-template-columns: 1fr;
  }

  .course-data-summary {
    flex-direction: column;
    align-items: flex-start;
  }

  .course-data-summary__meta {
    justify-content: flex-start;
  }

  .course-data-chooser__head {
    flex-direction: column;
    align-items: flex-start;
  }
}

@media (max-width: 560px) {
  .course-data-grid {
    grid-template-columns: 1fr;
  }

  .course-data-detail-fields {
    grid-template-columns: 1fr;
  }

  .course-data-switch {
    min-width: 100%;
  }
}
</style>