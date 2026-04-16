import { computed, reactive, ref } from 'vue'
import { fetchSettings, patchSettings } from '../api/api'

const SUCCESS_TOAST_DURATION = 2200
const DEBUG_TOGGLE_STORAGE_KEY = 'openclass.ui.showDebugToggle'

const cardDefs = [
    {
        id: 'debug_ui',
        title: '调试开关状态',
        description: '前端本地设置，控制是否显示调试按钮',
        column: 'left',
        localOnly: true,
        fields: [
            { key: 'ui_show_debug_toggle', label: '显示调试按钮', kind: 'boolean' }
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
            { key: 'tts_language_type', label: 'TTS 语言', kind: 'text' }
        ]
    },
    {
        id: 'prompts',
        title: '提示词',
        description: '课堂提问与总结提示词配置',
        column: 'left',
        fields: [
            { key: 'system_prompt_question', label: '提问提示词', kind: 'longtext-modal' },
            { key: 'system_prompt_segment_summary', label: '总结提示词', kind: 'longtext-modal' }
        ]
    }
]

const fieldKindMap = Object.fromEntries(
    cardDefs.flatMap((card) => card.fields.map((field) => [field.key, field.kind]))
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

    if (value == null) {
        return ''
    }

    return String(value)
}

const loadLocalSettings = () => {
    let showDebugToggle = true
    try {
        const raw = window.localStorage.getItem(DEBUG_TOGGLE_STORAGE_KEY)
        if (raw != null) {
            showDebugToggle = String(raw).toLowerCase() !== 'false'
        }
    } catch {
        showDebugToggle = true
    }

    formValues.ui_show_debug_toggle = showDebugToggle
}

const persistLocalSettings = (card) => {
    const containsDebugToggle = card.fields.some((field) => field.key === 'ui_show_debug_toggle')
    if (!containsDebugToggle) {
        return
    }

    const visible = Boolean(formValues.ui_show_debug_toggle)
    try {
        window.localStorage.setItem(DEBUG_TOGGLE_STORAGE_KEY, String(visible))
    } catch {
        // ignore write failure and keep in-memory value
    }

    window.dispatchEvent(
        new CustomEvent('openclass:debug-toggle-updated', {
            detail: { visible }
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

const getPromptPreview = (key) => {
    const text = String(formValues[key] ?? '').trim()
    if (!text) {
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
    promptDialogVisible.value = true
}

const closePromptEditor = () => {
    promptDialogVisible.value = false
}

const applyPromptEditor = () => {
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
            displayLabel: getFieldLabel(field.key)
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
        getPromptPreview,
        openPromptEditor,
        closePromptEditor,
        applyPromptEditor,
        loadSettings,
        saveCardSettings
    }
}
