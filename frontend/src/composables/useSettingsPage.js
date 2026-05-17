import { computed, reactive, ref } from 'vue'
import { fetchSettings, patchSettings } from '../api/api'

const SUCCESS_TOAST_DURATION = 2200
const DEBUG_TOGGLE_STORAGE_KEY = 'openclass.ui.showDebugToggle'
const KEYWORD_SOURCE_FILTER_STORAGE_KEY = 'openclass.keyword.sourceFilter'
const KEYWORD_SOURCE_FILTER_VALUES = ['llm', 'algorithm', 'all']
const QUESTION_TRIGGER_ENABLED_STORAGE_KEY = 'openclass.questionTrigger.enabled'
const QUESTION_TRIGGER_PHRASES_STORAGE_KEY = 'openclass.questionTrigger.phrases'
const QUESTION_TRIGGER_WINDOW_MS_STORAGE_KEY = 'openclass.questionTrigger.windowMs'
const QUESTION_TRIGGER_SILENCE_DURATION_MS_STORAGE_KEY = 'openclass.questionTrigger.silenceDurationMs'
const QUESTION_TRIGGER_SILENCE_LEVEL_STORAGE_KEY = 'openclass.questionTrigger.silenceLevel'
const QUESTION_TRIGGER_COOLDOWN_MS_STORAGE_KEY = 'openclass.questionTrigger.cooldownMs'
const DEFAULT_QUESTION_TRIGGER_PHRASES = [
    '有问题',
    '什么问题',
    '有没有问题',
    '有疑问',
    '什么疑问',
    '有没有疑问',
    '没问题吧',
    '没有问题吧',
    '没有疑问吧',
    '有不清楚',
    '不清楚',
    '不懂',
    '哪里不懂',
    '不明白',
    '哪里不明白',
    '听明白了吗',
    '听懂了吗',
    '都听懂了吗',
    '明白了吗',
    '都明白了吗',
    '清楚了吗',
    '都清楚了吗',
    '理解了吗',
    '都理解了吗',
    '可以提问',
    '请提问',
    '请问',
    '可以问',
    '可以问问题',
    '现在提问',
    '现在可以问',
    '大家可以问',
    '同学可以问',
    '想问',
    '谁想问',
    '谁要问',
    '谁来问',
    '谁有问题',
    '谁有疑问',
    '还有问题',
    '还有疑问',
    '还有不懂',
    '还有哪里',
    '举手提问',
    '可以举手',
    '有没有同学问'
].join('\n')
const DEFAULT_QUESTION_TRIGGER_SETTINGS = {
    enabled: true,
    phrases: DEFAULT_QUESTION_TRIGGER_PHRASES,
    windowMs: 20000,
    silenceDurationMs: 3000,
    silenceLevel: 0.1,
    cooldownMs: 20000
}
const QUESTION_TRIGGER_HELP_TEXT = `自动提问触发逻辑：

1. 前端收到课堂转写后，检查转写文本是否包含“提问触发词”；每一行是一个短触发短语，匹配时会去掉空白，不要求整句完全一致。
2. 命中触发词后进入等待窗口。
3. 在等待窗口内，麦克风音量连续低于“沉默音量阈值”，并持续达到“沉默持续时间”后，前端通过 WebSocket 发送 ask_question。
4. 后端收到 ask_question 后，从候选问题队列中选择一个问题并返回语音播放。
5. “提问冷却时间”从前端成功发送 ask_question 的那一刻开始计时；冷却时间内，即使命中新的触发词并检测到沉默，也不会再次发送 ask_question。
6. 如果 ask_question 已发送但后端还没有返回结果，或当前正在播放提问语音，前端也不会再次触发。`
const QUESTION_TRIGGER_HELP_STEPS = [
    '前端收到课堂转写后，检查转写文本是否包含“提问触发词”；每一行是一个短触发短语，匹配时会去掉空白，不要求整句完全一致。',
    '命中触发词后进入等待窗口。',
    '在等待窗口内，麦克风音量连续低于“沉默音量阈值”，并持续达到“沉默持续时间”后，前端通过 WebSocket 发送 ask_question。',
    '后端收到 ask_question 后，从候选问题队列中选择一个问题并返回语音播放。',
    '“提问冷却时间”从前端成功发送 ask_question 的那一刻开始计时；冷却时间内，即使命中新的触发词并检测到沉默，也不会再次发送 ask_question。',
    '如果 ask_question 已发送但后端还没有返回结果，或当前正在播放提问语音，前端也不会再次触发。'
]

const cardDefs = [
    {
        id: 'debug_ui',
        title: '本地设置',
        description: '前端本地设置，只保存在当前浏览器',
        column: 'left',
        localOnly: true,
        fields: [
            { key: 'ui_show_debug_toggle', label: '显示调试按钮', kind: 'boolean' },
            {
                key: 'keyword_source_filter',
                label: '关键词来源',
                kind: 'select',
                options: [
                    { value: 'llm', label: 'llm' },
                    { value: 'algorithm', label: 'algorithm' },
                    { value: 'all', label: 'all' }
                ]
            },
            {
                key: 'question_trigger_enabled',
                label: '自动提问触发',
                kind: 'boolean',
                infoText: QUESTION_TRIGGER_HELP_TEXT,
                infoSteps: QUESTION_TRIGGER_HELP_STEPS
            },
            { key: 'question_trigger_phrases', label: '提问触发词', kind: 'longtext-modal' },
            { key: 'question_trigger_window_ms', label: '触发词等待窗口(ms)', kind: 'number', min: 1000, step: 500 },
            { key: 'question_trigger_silence_duration_ms', label: '沉默持续时间(ms)', kind: 'number', min: 300, step: 100 },
            { key: 'question_trigger_silence_level', label: '沉默音量阈值(0-1)', kind: 'number', min: 0, step: 0.01 },
            { key: 'question_trigger_cooldown_ms', label: '提问冷却时间(ms)', kind: 'number', min: 0, step: 500 }
        ]
    },
    {
        id: 'model',
        title: 'LLM服务',
        description: 'LLM 大模型服务配置',
        column: 'left',
        fields: [
            { key: 'model_name', label: '模型名称', kind: 'text', placeholder: 'deepseek-chat' },
            { key: 'deepseek_base_url', label: '模型服务地址', kind: 'text', placeholder: 'https://api.deepseek.com' },
            { key: 'max_tokens', label: '最大输出 Token', kind: 'number', min: 1 },
            { key: 'temperature', label: '温度', kind: 'number', min: 0, step: 0.1 }
        ]
    },
    {
        id: 'runtime',
        title: '运行策略',
        description: '核心流程运行参数、热更新参数',
        column: 'left',
        fields: [
            { key: 'question_concurrent_workers', label: '并发提问线程', kind: 'number', min: 1 },
            { key: 'max_questions', label: '问题队列上限', kind: 'number', min: 1 },
            { key: 'recent_lecture_window', label: '近期讲解窗口', kind: 'number', min: 1 },
            { key: 'history_summary_window', label: '历史总结窗口', kind: 'number', min: 1 },
            { key: 'keyword_knowledge_quiz_trigger_interval', label: '关键词/知识点/小测触发间隔', kind: 'number', min: 1 },
            { key: 'settings_refresh_interval_seconds', label: '设置热更新间隔(秒)', kind: 'number', min: 0.5, step: 0.5 }
        ]
    },
    {
        id: 'secrets',
        title: 'API 密钥',
        description: '敏感配置，默认不回显',
        column: 'right',
        fields: [
            { key: 'deepseek_api_key', label: 'DeepSeek API Key', kind: 'password', placeholder: '输入后保存', sensitive: true },
            { key: 'qwen_api_key', label: 'Qwen API Key', kind: 'password', placeholder: '输入后保存', sensitive: true }
        ]
    },
    {
        id: 'asr',
        title: 'ASR服务',
        description: 'ASR 语音识别服务配置',
        column: 'right',
        fields: [
            { key: 'asr_model', label: 'ASR 模型', kind: 'text' },
            { key: 'asr_base_url', label: 'ASR 服务地址', kind: 'text' },
            { key: 'asr_language', label: 'ASR 语言', kind: 'text' },
            { key: 'asr_enable_itn', label: 'ASR 逆文本归一化', kind: 'boolean' }
        ]
    },
    {
        id: 'tts',
        title: 'TTS服务',
        description: 'TTS 语音合成服务配置',
        column: 'right',
        fields: [
            { key: 'tts_model', label: 'TTS 模型', kind: 'text' },
            { key: 'tts_base_url', label: 'TTS 服务地址', kind: 'text' },
            { key: 'tts_voice', label: 'TTS 音色', kind: 'text' },
            { key: 'tts_language_type', label: 'TTS 语言', kind: 'text' },
            { key: 'tts_instructions', label: 'TTS 指令', kind: 'longtext-modal' },
            { key: 'tts_optimize_instructions', label: 'TTS 自动优化指令', kind: 'boolean' }
        ]
    },
    {
        id: 'prompts',
        title: '提示词',
        description: '课堂提问与总结提示词配置',
        column: 'left',
        fields: [
            { key: 'system_prompt_question', label: '提问提示词', kind: 'longtext-modal' },
            { key: 'system_prompt_question_quality', label: '问题评分提示词', kind: 'longtext-modal' },
            { key: 'system_prompt_segment_summary', label: '总结提示词', kind: 'longtext-modal' },
            { key: 'system_prompt_keywords', label: '关键词提示词', kind: 'longtext-modal' },
            { key: 'system_prompt_knowledge', label: '知识点提示词', kind: 'longtext-modal' },
            { key: 'system_prompt_quiz', label: '小测提示词', kind: 'longtext-modal' },
            { key: 'system_prompt_report', label: '报告提示词', kind: 'longtext-modal' }
        ]
    }
]

const fieldKindMap = Object.fromEntries(
    cardDefs.flatMap((card) => card.fields.map((field) => [field.key, field.kind]))
)
const fieldOptionMap = Object.fromEntries(
    cardDefs.flatMap((card) => card.fields.map((field) => [field.key, field.options || []]))
)

const formValues = reactive({})
const sensitiveStatus = reactive({})
const loading = ref(false)
const savingCardId = ref('')
const error = ref('')
const successTip = ref('')
const successTipKey = ref(0)
const promptDialogVisible = ref(false)
const promptDialogKey = ref('')
const promptDialogTitle = ref('')
const promptDialogDraft = ref('')
const promptDialogReadOnly = ref(false)
const promptDialogInfoSteps = ref([])

let successTipTimer = null

const showSuccessTip = (message) => {
    successTipKey.value += 1
    successTip.value = message

    if (successTipTimer) {
        clearTimeout(successTipTimer)
    }

    successTipTimer = setTimeout(() => {
        successTip.value = ''
    }, SUCCESS_TOAST_DURATION)
}

const normalizeValue = (key, value) => {
    const kind = fieldKindMap[key]

    if (kind === 'number') {
        const numberValue = Number(value)
        return Number.isFinite(numberValue) ? numberValue : 0
    }

    if (kind === 'boolean') {
        if (typeof value === 'boolean') {
            return value
        }
        return String(value).toLowerCase() === 'true'
    }

    if (kind === 'select') {
        const options = fieldOptionMap[key] || []
        const normalized = String(value ?? '').trim()
        return options.some((option) => option.value === normalized)
            ? normalized
            : String(options[0]?.value ?? '')
    }

    if (value == null) {
        return ''
    }

    return String(value)
}

const readLocalBoolean = (key, fallback) => {
    const raw = window.localStorage.getItem(key)
    return raw == null ? fallback : String(raw).toLowerCase() !== 'false'
}

const readLocalNumber = (key, fallback) => {
    const raw = window.localStorage.getItem(key)
    if (raw == null || raw === '') {
        return fallback
    }
    const numeric = Number(raw)
    return Number.isFinite(numeric) ? numeric : fallback
}

const toLocalNumber = (value, fallback) => {
    const numeric = Number(value)
    return Number.isFinite(numeric) ? numeric : fallback
}

const loadLocalSettings = () => {
    let showDebugToggle = true
    let keywordSourceFilter = 'llm'
    let questionTriggerSettings = { ...DEFAULT_QUESTION_TRIGGER_SETTINGS }
    try {
        const raw = window.localStorage.getItem(DEBUG_TOGGLE_STORAGE_KEY)
        if (raw != null) {
            showDebugToggle = String(raw).toLowerCase() !== 'false'
        }
        const rawKeywordSourceFilter = window.localStorage.getItem(KEYWORD_SOURCE_FILTER_STORAGE_KEY)
        if (KEYWORD_SOURCE_FILTER_VALUES.includes(rawKeywordSourceFilter)) {
            keywordSourceFilter = rawKeywordSourceFilter
        }
        questionTriggerSettings = {
            enabled: readLocalBoolean(
                QUESTION_TRIGGER_ENABLED_STORAGE_KEY,
                DEFAULT_QUESTION_TRIGGER_SETTINGS.enabled
            ),
            phrases:
                window.localStorage.getItem(QUESTION_TRIGGER_PHRASES_STORAGE_KEY) ||
                DEFAULT_QUESTION_TRIGGER_SETTINGS.phrases,
            windowMs: readLocalNumber(
                QUESTION_TRIGGER_WINDOW_MS_STORAGE_KEY,
                DEFAULT_QUESTION_TRIGGER_SETTINGS.windowMs
            ),
            silenceDurationMs: readLocalNumber(
                QUESTION_TRIGGER_SILENCE_DURATION_MS_STORAGE_KEY,
                DEFAULT_QUESTION_TRIGGER_SETTINGS.silenceDurationMs
            ),
            silenceLevel: readLocalNumber(
                QUESTION_TRIGGER_SILENCE_LEVEL_STORAGE_KEY,
                DEFAULT_QUESTION_TRIGGER_SETTINGS.silenceLevel
            ),
            cooldownMs: readLocalNumber(
                QUESTION_TRIGGER_COOLDOWN_MS_STORAGE_KEY,
                DEFAULT_QUESTION_TRIGGER_SETTINGS.cooldownMs
            )
        }
    } catch {
        showDebugToggle = true
        keywordSourceFilter = 'llm'
        questionTriggerSettings = { ...DEFAULT_QUESTION_TRIGGER_SETTINGS }
    }

    formValues.ui_show_debug_toggle = showDebugToggle
    formValues.keyword_source_filter = keywordSourceFilter
    formValues.question_trigger_enabled = questionTriggerSettings.enabled
    formValues.question_trigger_phrases = questionTriggerSettings.phrases
    formValues.question_trigger_window_ms = questionTriggerSettings.windowMs
    formValues.question_trigger_silence_duration_ms = questionTriggerSettings.silenceDurationMs
    formValues.question_trigger_silence_level = questionTriggerSettings.silenceLevel
    formValues.question_trigger_cooldown_ms = questionTriggerSettings.cooldownMs
}

const persistLocalSettings = (card) => {
    const containsDebugToggle = card.fields.some((field) => field.key === 'ui_show_debug_toggle')
    const containsKeywordSourceFilter = card.fields.some((field) => field.key === 'keyword_source_filter')
    const containsQuestionTriggerSettings = card.fields.some((field) =>
        String(field.key).startsWith('question_trigger_')
    )
    if (!containsDebugToggle && !containsKeywordSourceFilter && !containsQuestionTriggerSettings) {
        return
    }

    const visible = Boolean(formValues.ui_show_debug_toggle)
    const keywordSourceFilter = KEYWORD_SOURCE_FILTER_VALUES.includes(formValues.keyword_source_filter)
        ? formValues.keyword_source_filter
        : 'llm'
    const questionTriggerSettings = {
        enabled: Boolean(formValues.question_trigger_enabled),
        phrases: String(formValues.question_trigger_phrases || DEFAULT_QUESTION_TRIGGER_SETTINGS.phrases),
        windowMs: toLocalNumber(formValues.question_trigger_window_ms, DEFAULT_QUESTION_TRIGGER_SETTINGS.windowMs),
        silenceDurationMs: toLocalNumber(
            formValues.question_trigger_silence_duration_ms,
            DEFAULT_QUESTION_TRIGGER_SETTINGS.silenceDurationMs
        ),
        silenceLevel: toLocalNumber(
            formValues.question_trigger_silence_level,
            DEFAULT_QUESTION_TRIGGER_SETTINGS.silenceLevel
        ),
        cooldownMs: toLocalNumber(formValues.question_trigger_cooldown_ms, DEFAULT_QUESTION_TRIGGER_SETTINGS.cooldownMs)
    }
    try {
        window.localStorage.setItem(DEBUG_TOGGLE_STORAGE_KEY, String(visible))
        window.localStorage.setItem(KEYWORD_SOURCE_FILTER_STORAGE_KEY, keywordSourceFilter)
        window.localStorage.setItem(QUESTION_TRIGGER_ENABLED_STORAGE_KEY, String(questionTriggerSettings.enabled))
        window.localStorage.setItem(QUESTION_TRIGGER_PHRASES_STORAGE_KEY, questionTriggerSettings.phrases)
        window.localStorage.setItem(QUESTION_TRIGGER_WINDOW_MS_STORAGE_KEY, String(questionTriggerSettings.windowMs))
        window.localStorage.setItem(
            QUESTION_TRIGGER_SILENCE_DURATION_MS_STORAGE_KEY,
            String(questionTriggerSettings.silenceDurationMs)
        )
        window.localStorage.setItem(
            QUESTION_TRIGGER_SILENCE_LEVEL_STORAGE_KEY,
            String(questionTriggerSettings.silenceLevel)
        )
        window.localStorage.setItem(QUESTION_TRIGGER_COOLDOWN_MS_STORAGE_KEY, String(questionTriggerSettings.cooldownMs))
    } catch {
        // ignore write failure and keep in-memory value
    }

    window.dispatchEvent(
        new CustomEvent('openclass:debug-toggle-updated', {
            detail: { visible }
        })
    )
    window.dispatchEvent(
        new CustomEvent('openclass:local-settings-updated', {
            detail: { visible, keywordSourceFilter, questionTriggerSettings }
        })
    )
}

const getFieldLabel = (key) => {
    for (const card of cardDefs) {
        const field = card.fields.find((item) => item.key === key)
        if (field) {
            return field.label
        }
    }
    return key
}

const getLongTextEditLabel = (key) => {
    if (key === 'question_trigger_phrases') {
        return '编辑触发词'
    }
    return '编辑提示词'
}

const getPromptPreview = (key) => {
    const text = String(formValues[key] ?? '').trim()
    if (!text) {
        if (key === 'question_trigger_phrases') {
            return '未设置触发词'
        }
        return '未设置提示词'
    }

    if (text.length > 44) {
        return `${text.slice(0, 44)}...`
    }

    return text
}

const loadSettings = async () => {
    loading.value = true
    error.value = ''
    successTip.value = ''
    loadLocalSettings()

    try {
        const data = await fetchSettings()
        const items = Array.isArray(data?.items) ? data.items : []

        for (const item of items) {
            const key = item.key
            formValues[key] = normalizeValue(key, item.value)
            sensitiveStatus[key] = Boolean(item.has_value)
        }
    } catch (loadError) {
        error.value = loadError instanceof Error ? loadError.message : '配置加载失败'
    } finally {
        loading.value = false
    }
}

const buildUpdateItemsByCard = (cardId) => {
    const card = cardDefs.find((item) => item.id === cardId)
    if (!card) {
        return []
    }

    return card.fields.map((field) => {
        const rawValue = formValues[field.key]

        if (field.kind === 'number') {
            return { key: field.key, value: Number(rawValue) }
        }

        if (field.kind === 'boolean') {
            return { key: field.key, value: Boolean(rawValue) }
        }

        return { key: field.key, value: rawValue == null ? '' : String(rawValue) }
    })
}

const saveCardSettings = async (cardId) => {
    const card = cardDefs.find((item) => item.id === cardId)
    if (!card) {
        return
    }

    savingCardId.value = cardId
    error.value = ''
    successTip.value = ''

    try {
        if (card.localOnly) {
            persistLocalSettings(card)
            showSuccessTip(`${card.title}已保存`)
            return
        }

        const payload = {
            items: buildUpdateItemsByCard(cardId)
        }

        await patchSettings(payload)
        await loadSettings()

        showSuccessTip(`${card.title}已保存`)
    } catch (saveError) {
        error.value = saveError instanceof Error ? saveError.message : '保存失败'
    } finally {
        savingCardId.value = ''
    }
}

const openPromptEditor = (field) => {
    const fieldKey = field?.key
    if (!fieldKey) {
        return
    }

    promptDialogKey.value = fieldKey
    promptDialogTitle.value = field?.displayLabel || field?.label || fieldKey
    promptDialogDraft.value = String(formValues[fieldKey] ?? '')
    promptDialogReadOnly.value = false
    promptDialogInfoSteps.value = []
    promptDialogVisible.value = true
}

const openInfoDialog = (field) => {
    promptDialogKey.value = ''
    promptDialogTitle.value = field?.displayLabel || field?.label || '说明'
    promptDialogDraft.value = String(field?.infoText || '')
    promptDialogInfoSteps.value = Array.isArray(field?.infoSteps) ? field.infoSteps : []
    promptDialogReadOnly.value = true
    promptDialogVisible.value = true
}

const closePromptEditor = () => {
    promptDialogVisible.value = false
    promptDialogReadOnly.value = false
    promptDialogInfoSteps.value = []
}

const applyPromptEditor = () => {
    if (promptDialogReadOnly.value) {
        closePromptEditor()
        return
    }
    if (!promptDialogKey.value) {
        closePromptEditor()
        return
    }

    formValues[promptDialogKey.value] = String(promptDialogDraft.value ?? '')
    closePromptEditor()
}

const sectionCards = computed(() =>
    cardDefs.map((card) => ({
        ...card,
        fields: card.fields.map((field) => ({
            ...field,
            value: formValues[field.key],
            hasValue: Boolean(sensitiveStatus[field.key]),
            displayLabel: getFieldLabel(field.key),
            editLabel: getLongTextEditLabel(field.key),
            infoText: field.infoText || '',
            infoSteps: field.infoSteps || []
        }))
    }))
)

const leftCards = computed(() => sectionCards.value.filter((card) => card.column === 'left'))
const rightCards = computed(() => sectionCards.value.filter((card) => card.column === 'right'))

export function useSettingsPage() {
    return {
        loading,
        error,
        successTip,
        successTipKey,
        toastDurationMs: SUCCESS_TOAST_DURATION,
        leftCards,
        rightCards,
        formValues,
        savingCardId,
        promptDialogVisible,
        promptDialogTitle,
        promptDialogDraft,
        promptDialogReadOnly,
        promptDialogInfoSteps,
        getPromptPreview,
        getLongTextEditLabel,
        openPromptEditor,
        openInfoDialog,
        closePromptEditor,
        applyPromptEditor,
        loadSettings,
        saveCardSettings
    }
}
