import { computed, onMounted, reactive, ref, watch } from 'vue'
import {
	fetchCourses,
	fetchSessionKnowledgePoints,
	fetchSessionKeywords,
	fetchSessionQuestions,
	fetchSessionQuizItems,
	fetchSessionReports,
	fetchSessionsByCourse,
	fetchSessionSummaries,
	fetchSessionTranscripts
} from '../api/api'

const SECTION_DEFINITIONS = [
	{
		id: 'timelineStats',
		label: '统计图',
		symbol: '📈',
		description: '课堂时间轴上的多类型数量趋势'
	},
	{
		id: 'transcripts',
		label: '转写分段',
		symbol: 'T',
		description: '课堂转写原文的分段流'
	},
	{
		id: 'questions',
		label: '问题',
		symbol: 'Q',
		description: '课堂提问记录'
	},
	{
		id: 'summaries',
		label: '分段小结',
		symbol: 'S',
		description: '课堂阶段性小结'
	},
	{
		id: 'keywords',
		label: '关键词',
		symbol: 'K',
		description: '当前课堂的关键词集合'
	},
	{
		id: 'quizItems',
		label: '小测题目',
		symbol: 'Z',
		description: '课堂小测与题目答案'
	},
	{
		id: 'knowledgePoints',
		label: '知识点',
		symbol: 'N',
		description: '抽取出的核心知识点'
	},
	{
		id: 'reports',
		label: '课后报告',
		symbol: 'R',
		description: '课堂结束后的报告内容'
	}
]

const SECTION_DEFINITION_MAP = SECTION_DEFINITIONS.reduce((accumulator, section) => {
	accumulator[section.id] = section
	return accumulator
}, {})

const DEFAULT_VISIBLE_SECTION_IDS = []

const EMPTY_SECTION_DATA = () => ({
	transcripts: [],
	questions: [],
	summaries: [],
	keywords: [],
	quizItems: [],
	knowledgePoints: [],
	reports: [],
	timelineStats: []
})

const courses = ref([])
const sessions = ref([])
const selectedCourseId = ref(null)
const selectedSessionId = ref(null)
const selectedSectionIds = ref([...DEFAULT_VISIBLE_SECTION_IDS])
const loading = ref(false)
const loadingSessions = ref(false)
const error = ref('')
const sectionData = ref(EMPTY_SECTION_DATA())
const sectionLoadingState = reactive({
	transcripts: false,
	questions: false,
	summaries: false,
	keywords: false,
	quizItems: false,
	knowledgePoints: false,
	reports: false,
	timelineStats: false
})

const toNumber = (value) => {
	const numberValue = Number(value)
	return Number.isFinite(numberValue) ? numberValue : 0
}

const toUnixSeconds = (value) => {
	if (typeof value === 'number' && Number.isFinite(value)) {
		return value > 1e12 ? Math.floor(value / 1000) : Math.floor(value)
	}

	if (typeof value === 'string' && value.trim()) {
		const numericValue = Number(value)
		if (Number.isFinite(numericValue)) {
			return numericValue > 1e12 ? Math.floor(numericValue / 1000) : Math.floor(numericValue)
		}

		const parsedValue = Date.parse(value)
		if (Number.isFinite(parsedValue)) {
			return Math.floor(parsedValue / 1000)
		}
	}

	return 0
}

const pad = (value) => String(value).padStart(2, '0')

const formatTimeLabel = (timestamp) => {
	const date = new Date(toUnixSeconds(timestamp) * 1000)
	if (Number.isNaN(date.getTime())) {
		return '--'
	}

	return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
}

const formatDateTimeLabel = (timestamp) => {
	const date = new Date(toUnixSeconds(timestamp) * 1000)
	if (Number.isNaN(date.getTime())) {
		return '--'
	}

	return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
}

const parseKeywordSets = (rawKeywordSets) => {
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

const stripHtml = (text) => String(text || '')
	.replace(/<[^>]*>/g, ' ')
	.replace(/\s+/g, ' ')
	.trim()

const previewText = (text, maxLength = 180) => {
	const normalizedText = stripHtml(text)
	if (!normalizedText) {
		return '（无内容）'
	}

	return normalizedText.length > maxLength ? `${normalizedText.slice(0, maxLength)}…` : normalizedText
}

const formatSectionText = (text) => String(text || '').trim() || '（无内容）'

const sortByCreatedAt = (items) => [...items].sort((left, right) => {
	const leftTime = toUnixSeconds(left?.created_at)
	const rightTime = toUnixSeconds(right?.created_at)

	if (leftTime !== rightTime) {
		return leftTime - rightTime
	}

	return toNumber(left?.id) - toNumber(right?.id)
})

const normalizeTranscript = (item) => ({
	id: item.id,
	seqLabel: item.seq != null ? `分段 ${item.seq}` : '分段',
	timeLabel: formatTimeLabel(item.created_at),
	text: formatSectionText(item.text)
})

const normalizeQuestion = (item) => ({
	id: item.id,
	timeLabel: formatTimeLabel(item.created_at),
	statusLabel: String(item.status || 'generated'),
	scoreLabel: item.score != null ? Number(item.score).toFixed(1) : '未评分',
	text: formatSectionText(item.text)
})

const normalizeSummary = (item) => ({
	id: item.id,
	timeLabel: formatTimeLabel(item.created_at),
	rangeLabel: item.start_time || item.end_time
		? `${formatTimeLabel(item.start_time || item.created_at)} - ${formatTimeLabel(item.end_time || item.created_at)}`
		: '完整课堂',
	text: formatSectionText(item.text)
})

const normalizeKeyword = (item) => ({
	id: item.id,
	timeLabel: formatTimeLabel(item.created_at),
	keywords: parseKeywordSets(item.keyword_sets)
})

const normalizeQuizItem = (item) => ({
	id: item.id,
	typeLabel: String(item.type || '题目'),
	timeLabel: formatTimeLabel(item.created_at),
	question: formatSectionText(item.question),
	answer: formatSectionText(item.answer),
	explanation: formatSectionText(item.explanation)
})

const normalizeKnowledgePoint = (item) => ({
	id: item.id,
	timeLabel: formatTimeLabel(item.created_at),
	name: formatSectionText(item.name),
	description: formatSectionText(item.description),
	difficultyLabel: String(item.difficulty || '中').trim() || '中'
})

const normalizeReport = (item) => ({
	id: item.id,
	timeLabel: formatDateTimeLabel(item.created_at),
	filePath: String(item.file_path || '').trim(),
	content: formatSectionText(item.content),
	contentPreview: previewText(item.content, 240)
})

const sectionLoaderMap = {
	transcripts: fetchSessionTranscripts,
	questions: fetchSessionQuestions,
	summaries: fetchSessionSummaries,
	keywords: fetchSessionKeywords,
	quizItems: fetchSessionQuizItems,
	knowledgePoints: fetchSessionKnowledgePoints,
	reports: fetchSessionReports
}

const sectionNormalizerMap = {
	transcripts: normalizeTranscript,
	questions: normalizeQuestion,
	summaries: normalizeSummary,
	keywords: normalizeKeyword,
	quizItems: normalizeQuizItem,
	knowledgePoints: normalizeKnowledgePoint,
	reports: normalizeReport
}

const emptySectionDataMap = {
	transcripts: [],
	questions: [],
	summaries: [],
	keywords: [],
	quizItems: [],
	knowledgePoints: [],
	reports: [],
	timelineStats: []
}

export function useCoursePage() {
	const selectedCourse = computed(
		() => courses.value.find((item) => item.id === selectedCourseId.value) || null
	)

	const selectedSession = computed(
		() => sessions.value.find((item) => item.id === selectedSessionId.value) || null
	)

	const sectionCounts = computed(() => ({
		transcripts: sectionData.value.transcripts.length,
		questions: sectionData.value.questions.length,
		summaries: sectionData.value.summaries.length,
		keywords: sectionData.value.keywords.length,
		quizItems: sectionData.value.quizItems.length,
		knowledgePoints: sectionData.value.knowledgePoints.length,
		reports: sectionData.value.reports.length,
		timelineStats: selectedSessionId.value ? 1 : 0
	}))

	const visibleSections = computed(() => {
		const activeSectionSet = new Set(selectedSectionIds.value)

		return SECTION_DEFINITIONS.filter((section) => activeSectionSet.has(section.id)).map((section) => ({
			...section,
			count: sectionCounts.value[section.id] || 0,
			items: sectionData.value[section.id] || []
		}))
	})

	const hasSessionSelection = computed(() => Boolean(selectedSessionId.value))

	const sectionSummaryLabel = computed(() => `${selectedSectionIds.value.length} 项已选`)

	const selectedSectionLabels = computed(() =>
		SECTION_DEFINITIONS.filter((section) => selectedSectionIds.value.includes(section.id)).map((section) => section.label)
	)

	const resetSectionData = () => {
		sectionData.value = EMPTY_SECTION_DATA()
		Object.keys(sectionLoadingState).forEach((key) => {
			sectionLoadingState[key] = false
		})
	}

	const ensureSectionLoaded = async (sectionId) => {
		if (!selectedSessionId.value || !selectedSectionIds.value.includes(sectionId)) {
			return
		}

		if (sectionLoadingState[sectionId]) {
			return
		}

		if ((sectionData.value[sectionId] || []).length > 0) {
			return
		}

		const loader = sectionLoaderMap[sectionId]
		const normalizer = sectionNormalizerMap[sectionId]
		if (!loader || !normalizer) {
			return
		}

		sectionLoadingState[sectionId] = true
		try {
			const data = await loader(selectedSessionId.value)
			const sectionLabel = SECTION_DEFINITION_MAP[sectionId]?.label || '记录'
			const items = sortByCreatedAt(Array.isArray(data) ? data : [])
				.map(normalizer)
				.map((item, index) => ({
					...item,
					sequenceNo: index + 1,
					displayTitle: `${sectionLabel}${index + 1}`
				}))
			sectionData.value = {
				...sectionData.value,
				[sectionId]: items
			}
		} catch (loadError) {
			error.value = loadError instanceof Error ? loadError.message : '课堂数据加载失败'
		} finally {
			sectionLoadingState[sectionId] = false
		}
	}

	const loadCourses = async () => {
		error.value = ''

		try {
			const data = await fetchCourses()
			courses.value = Array.isArray(data) ? data : []
		} catch (loadError) {
			error.value = loadError instanceof Error ? loadError.message : '课程列表加载失败'
			courses.value = []
		}
	}

	const loadSessions = async (courseId) => {
		loadingSessions.value = true
		error.value = ''

		try {
			if (!courseId) {
				sessions.value = []
				selectedSessionId.value = null
				resetSectionData()
				return
			}

			const data = await fetchSessionsByCourse(courseId)
			sessions.value = Array.isArray(data) ? data : []
			selectedSessionId.value = null
			resetSectionData()
		} catch (loadError) {
			error.value = loadError instanceof Error ? loadError.message : '课堂列表加载失败'
			sessions.value = []
			selectedSessionId.value = null
			resetSectionData()
		} finally {
			loadingSessions.value = false
		}
	}

	const loadSessionContent = async (sessionId) => {
		if (!sessionId) {
			resetSectionData()
			return
		}

		resetSectionData()
		if (selectedSectionIds.value.length === 0) {
			return
		}

		loading.value = true
		error.value = ''
		try {
			await Promise.all(selectedSectionIds.value.map((sectionId) => ensureSectionLoaded(sectionId)))
		} finally {
			loading.value = false
		}
	}

	const refreshCurrentSelection = () => {
		if (selectedSessionId.value) {
			return loadSessionContent(selectedSessionId.value)
		}

		if (selectedCourseId.value) {
			return loadSessions(selectedCourseId.value)
		}

		return loadCourses()
	}

	const toggleSection = (sectionId) => {
		const existingIndex = selectedSectionIds.value.indexOf(sectionId)
		if (existingIndex >= 0) {
			selectedSectionIds.value = selectedSectionIds.value.filter((item) => item !== sectionId)
			sectionData.value = {
				...sectionData.value,
				[sectionId]: []
			}
			return
		}

		selectedSectionIds.value = [...selectedSectionIds.value, sectionId]
		if (selectedSessionId.value) {
			void ensureSectionLoaded(sectionId)
		}
	}

	const selectAllSections = () => {
		selectedSectionIds.value = SECTION_DEFINITIONS.map((section) => section.id)
		if (selectedSessionId.value) {
			SECTION_DEFINITIONS.forEach((section) => {
				void ensureSectionLoaded(section.id)
			})
		}
	}

	const clearSelectedSections = () => {
		selectedSectionIds.value = []
	}

	watch(selectedCourseId, (courseId) => {
		void loadSessions(courseId)
	})

	watch(selectedSessionId, (sessionId) => {
		void loadSessionContent(sessionId)
	})

	watch(selectedSectionIds, (sectionIds) => {
		if (!selectedSessionId.value || sectionIds.length === 0) {
			return
		}

		sectionIds.forEach((sectionId) => {
			void ensureSectionLoaded(sectionId)
		})
	}, { deep: true })

	onMounted(() => {
		void loadCourses()
	})

	return {
		courses,
		sessions,
		selectedCourseId,
		selectedSessionId,
		selectedCourse,
		selectedSession,
		selectedSectionIds,
		sectionDefinitions: SECTION_DEFINITIONS,
		sectionCounts,
		visibleSections,
		sectionSummaryLabel,
		selectedSectionLabels,
		loading,
		loadingSessions,
		error,
		sectionLoadingState,
		hasSessionSelection,
		refreshCurrentSelection,
		toggleSection,
		selectAllSections,
		clearSelectedSections
	}
}