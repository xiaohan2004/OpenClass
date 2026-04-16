import { computed, onMounted, ref } from 'vue'
import { fetchStatsDailies, fetchStatsTotals } from '../api/api'

const HEATMAP_DAYS = 54 * 7
const CHART_WIDTH = 760
const CHART_HEIGHT = 280
const CHART_LEFT = 48
const CHART_RIGHT = 20
const CHART_TOP = 24
const CHART_BOTTOM = 52
const DAY_MS = 24 * 60 * 60 * 1000
const CHART_DRAWABLE_HEIGHT = CHART_HEIGHT - CHART_TOP - CHART_BOTTOM
const CHART_BASELINE_Y = CHART_HEIGHT - CHART_BOTTOM
const CHART_HALF_Y = CHART_TOP + CHART_DRAWABLE_HEIGHT / 2
const X_AXIS_LABEL_Y = CHART_HEIGHT - 18

const periods = [
  { value: '1', label: '今天' },
  { value: '7', label: '7天' },
  { value: '30', label: '30天' }
]

const trendSources = [
  { value: 'llm', label: 'LLM' },
  { value: 'asr', label: 'ASR' },
  { value: 'tts', label: 'TTS' }
]

const trendMetricDefinitions = [
  { key: 'callCount', label: '调用次数' },
  { key: 'failedCount', label: '失败次数' },
  { key: 'usageValue', label: '用量' },
  { key: 'waitTime', label: '耗时' }
]

const compositeWeights = {
  requestCount: 0.3,
  tokenUsage: 0.3,
  audioLength: 0.2,
  charCount: 0.2
}

const toNumber = (value) => {
  const num = Number(value)
  return Number.isFinite(num) ? num : 0
}

const normalizeServiceType = (value) => String(value || '').trim().toLowerCase()

const dateKey = (date) => {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

const formatMonthDay = (key) => {
  const parts = key.split('-')
  if (parts.length !== 3) {
    return key
  }
  return `${parts[1]}-${parts[2]}`
}

const compactNumber = (value) => {
  const abs = Math.abs(value)
  if (abs >= 1000000) {
    return `${(value / 1000000).toFixed(2)}M`
  }
  if (abs >= 1000) {
    return `${(value / 1000).toFixed(2)}K`
  }
  return String(Math.round(value))
}

const formatAdaptiveTimeFromMs = (milliseconds) => {
  const ms = toNumber(milliseconds)
  if (ms >= 3600000) {
    return `${(ms / 3600000).toFixed(2)} h`
  }
  if (ms >= 60000) {
    return `${(ms / 60000).toFixed(2)} min`
  }
  if (ms >= 1000) {
    return `${(ms / 1000).toFixed(2)} s`
  }
  return `${Math.round(ms)} ms`
}

const formatAdaptiveTimeFromSeconds = (seconds) => {
  const sec = toNumber(seconds)
  if (sec >= 3600) {
    return `${(sec / 3600).toFixed(2)} h`
  }
  if (sec >= 60) {
    return `${(sec / 60).toFixed(2)} min`
  }
  if (sec >= 1) {
    return `${sec.toFixed(1)} s`
  }
  return `${Math.round(sec * 1000)} ms`
}

const formatAdaptiveToken = (tokens) => {
  const value = toNumber(tokens)
  const abs = Math.abs(value)
  if (abs >= 1000000000) {
    return `${(value / 1000000000).toFixed(2)}B`
  }
  if (abs >= 1000000) {
    return `${(value / 1000000).toFixed(2)}M`
  }
  if (abs >= 1000) {
    return `${(value / 1000).toFixed(2)}K`
  }
  if (abs >= 1) {
    return `${Math.round(value)}`
  }
  return `${value.toFixed(3)}`
}

const formatChineseChars = (chars) => {
  const value = toNumber(chars)
  const abs = Math.abs(value)
  if (abs >= 10000) {
    return `${(value / 10000).toFixed(2)} 万字符`
  }
  if (abs >= 1000) {
    return `${(value / 1000).toFixed(1)} 千字符`
  }
  if (abs >= 100) {
    return `${(value / 100).toFixed(1)} 百字符`
  }
  return `${Math.round(value)}字符`
}

const formatUsageByService = (service, usageValue) => {
  if (service === 'asr') {
    return formatAdaptiveTimeFromSeconds(usageValue)
  }
  if (service === 'tts') {
    return formatChineseChars(usageValue)
  }
  return formatAdaptiveToken(usageValue)
}

const formatCompositeScore = (score) => `${toNumber(score).toFixed(1)}`

const aggregateByDate = (items) => {
  const map = new Map()

  items.forEach((item) => {
    const key = item.date
    if (!key) {
      return
    }

    if (!map.has(key)) {
      map.set(key, {
        requestCount: 0,
        waitTime: 0,
        callsByService: {},
        failedByService: {},
        waitByService: {},
        inputByService: {},
        outputByService: {}
      })
    }

    const bucket = map.get(key)
    const service = normalizeServiceType(item.service_type)
    const inputValue = toNumber(item.input_value)
    const outputValue = toNumber(item.output_value)
    const waitTime = toNumber(item.wait_time)
    const success = toNumber(item.request_success)
    const failed = toNumber(item.request_failed)

    bucket.requestCount += success + failed
    bucket.waitTime += waitTime
    bucket.callsByService[service] = (bucket.callsByService[service] || 0) + success + failed
    bucket.failedByService[service] = (bucket.failedByService[service] || 0) + failed
    bucket.waitByService[service] = (bucket.waitByService[service] || 0) + waitTime
    bucket.inputByService[service] = (bucket.inputByService[service] || 0) + inputValue
    bucket.outputByService[service] = (bucket.outputByService[service] || 0) + outputValue
  })

  return map
}

const buildLinePath = (values) => {
  if (!values.length) {
    return `M${CHART_LEFT},${CHART_BASELINE_Y} L${CHART_WIDTH - CHART_RIGHT},${CHART_BASELINE_Y}`
  }

  const maxValue = Math.max(...values, 1)
  const drawableWidth = CHART_WIDTH - CHART_LEFT - CHART_RIGHT

  const points = values.map((value, index) => {
    const x = values.length === 1
      ? CHART_LEFT + drawableWidth / 2
      : CHART_LEFT + (index / (values.length - 1)) * drawableWidth
    const y = CHART_TOP + ((maxValue - value) / maxValue) * CHART_DRAWABLE_HEIGHT
    return `${x.toFixed(2)},${y.toFixed(2)}`
  })

  return `M${points.join(' L')}`
}

export function useStatsPage() {
  const statsTotals = ref([])
  const statsDailies = ref([])
  const loading = ref(false)
  const error = ref('')

  const currentPeriod = ref('30')
  const selectedTrendSource = ref('llm')
  const selectedTrendMetric = ref('callCount')

  const loadStats = async () => {
    loading.value = true
    error.value = ''
    try {
      const [totals, dailies] = await Promise.all([
        fetchStatsTotals(),
        fetchStatsDailies()
      ])
      statsTotals.value = Array.isArray(totals) ? totals : []
      statsDailies.value = Array.isArray(dailies) ? dailies : []
    } catch (err) {
      error.value = err instanceof Error ? err.message : '统计数据加载失败'
      statsTotals.value = []
      statsDailies.value = []
    } finally {
      loading.value = false
    }
  }

  const totalsByService = computed(() => {
    const map = new Map()
    statsTotals.value.forEach((item) => {
      map.set(normalizeServiceType(item.service_type), {
        inputValue: toNumber(item.input_value),
        outputValue: toNumber(item.output_value),
        waitTime: toNumber(item.wait_time),
        requestSuccess: toNumber(item.request_success),
        requestFailed: toNumber(item.request_failed)
      })
    })
    return map
  })

  const overallTotal = computed(() => {
    return Array.from(totalsByService.value.values()).reduce(
      (acc, item) => {
        acc.requestCount += item.requestSuccess + item.requestFailed
        acc.waitTime += item.waitTime
        return acc
      },
      { requestCount: 0, waitTime: 0 }
    )
  })

  const moreStatValues = computed(() => {
    const llm = totalsByService.value.get('llm') || {
      inputValue: 0,
      outputValue: 0,
      requestSuccess: 0,
      requestFailed: 0
    }
    const asr = totalsByService.value.get('asr') || {
      inputValue: 0,
      requestSuccess: 0,
      requestFailed: 0
    }
    const tts = totalsByService.value.get('tts') || {
      inputValue: 0,
      requestSuccess: 0,
      requestFailed: 0
    }

    return {
      req: {
        requestCount: compactNumber(overallTotal.value.requestCount),
        durationHours: formatAdaptiveTimeFromMs(overallTotal.value.waitTime)
      },
      llm: {
        inOutTokens: `${formatAdaptiveToken(llm.inputValue)} / ${formatAdaptiveToken(llm.outputValue)}`,
        successFail: `${llm.requestSuccess} / ${llm.requestFailed}`
      },
      asr: {
        totalAudioSeconds: formatAdaptiveTimeFromSeconds(asr.inputValue),
        successFail: `${asr.requestSuccess} / ${asr.requestFailed}`
      },
      tts: {
        totalChars: formatChineseChars(tts.inputValue),
        successFail: `${tts.requestSuccess} / ${tts.requestFailed}`
      }
    }
  })

  const heatmapDateKeys = computed(() => {
    const today = new Date()
    today.setHours(0, 0, 0, 0)
    const keys = []

    for (let offset = HEATMAP_DAYS - 1; offset >= 0; offset -= 1) {
      const date = new Date(today.getTime() - offset * DAY_MS)
      keys.push(dateKey(date))
    }

    return keys
  })

  const dailiesByDate = computed(() => aggregateByDate(statsDailies.value))

  const heatmapCompositeMaxValues = computed(() => {
    return statsDailies.value.reduce((acc, item) => {
      const serviceType = normalizeServiceType(item.service_type)
      const requestCount = toNumber(item.request_success) + toNumber(item.request_failed)
      const tokenUsage = serviceType === 'llm'
        ? toNumber(item.input_value) + toNumber(item.output_value)
        : 0
      const audioLength = serviceType === 'asr' ? toNumber(item.input_value) : 0
      const charCount = serviceType === 'tts' ? toNumber(item.input_value) : 0

      acc.requestCount = Math.max(acc.requestCount, requestCount)
      acc.tokenUsage = Math.max(acc.tokenUsage, tokenUsage)
      acc.audioLength = Math.max(acc.audioLength, audioLength)
      acc.charCount = Math.max(acc.charCount, charCount)
      return acc
    }, {
      requestCount: 0,
      tokenUsage: 0,
      audioLength: 0,
      charCount: 0
    })
  })

  const getHeatmapCompositeScore = (bucket) => {
    if (!bucket) {
      return 0
    }

    const maxValues = heatmapCompositeMaxValues.value

    const tokenUsage = (bucket.inputByService.llm || 0) + (bucket.outputByService.llm || 0)
    const audioLength = bucket.inputByService.asr || 0
    const charCount = bucket.inputByService.tts || 0
    const requestRatio = maxValues.requestCount > 0 ? bucket.requestCount / maxValues.requestCount : 0
    const tokenRatio = maxValues.tokenUsage > 0 ? tokenUsage / maxValues.tokenUsage : 0
    const audioRatio = maxValues.audioLength > 0 ? audioLength / maxValues.audioLength : 0
    const charRatio = maxValues.charCount > 0 ? charCount / maxValues.charCount : 0

    return (
      requestRatio * compositeWeights.requestCount +
      tokenRatio * compositeWeights.tokenUsage +
      audioRatio * compositeWeights.audioLength +
      charRatio * compositeWeights.charCount
    ) * 100
  }

  const heatmapDots = computed(() => {
    const maxScore = heatmapDateKeys.value.reduce((max, key) => {
      const score = getHeatmapCompositeScore(dailiesByDate.value.get(key))
      return Math.max(max, score)
    }, 0)

    return heatmapDateKeys.value.map((key, index) => {
      const bucket = dailiesByDate.value.get(key)
      const requestCount = bucket?.requestCount || 0
      const hasData = requestCount > 0
      const compositeScore = getHeatmapCompositeScore(bucket)

      let level = 'is-idle'
      if (hasData && maxScore > 0) {
        const ratio = compositeScore / maxScore
        if (ratio < 0.34) {
          level = 'is-cold'
        } else if (ratio < 0.67) {
          level = 'is-warm'
        } else {
          level = 'is-hot'
        }
      }

      const tokenCost = (bucket?.inputByService.llm || 0) + (bucket?.outputByService.llm || 0)
      const audioLength = bucket?.inputByService.asr || 0
      const charCount = bucket?.inputByService.tts || 0

      return {
        id: `dot-${index}`,
        level,
        data: {
          date: key,
          hasData,
          requests: hasData ? `${requestCount}次` : '',
          waitTime: hasData
            ? formatAdaptiveTimeFromMs(bucket.waitTime / Math.max(requestCount, 1))
            : '',
          tokenCost: hasData ? formatAdaptiveToken(tokenCost) : '',
          audioLength: hasData ? formatAdaptiveTimeFromSeconds(audioLength) : '',
          charCount: hasData ? formatChineseChars(charCount) : '',
          compositeScore: hasData ? compositeScore : 0,
          compositeScoreText: hasData ? formatCompositeScore(compositeScore) : ''
        }
      }
    })
  })

  const trendDateKeys = computed(() => {
    const days = Math.max(1, toNumber(currentPeriod.value))
    const today = new Date()
    today.setHours(0, 0, 0, 0)
    const keys = []

    for (let offset = days - 1; offset >= 0; offset -= 1) {
      const date = new Date(today.getTime() - offset * DAY_MS)
      keys.push(dateKey(date))
    }

    return keys
  })

  const trendSeriesBase = computed(() => {
    const service = selectedTrendSource.value

    return trendDateKeys.value.map((key) => {
      const bucket = dailiesByDate.value.get(key)
      const requestCount = bucket?.requestCount || 0
      const tokenUsage = (bucket?.inputByService.llm || 0) + (bucket?.outputByService.llm || 0)
      const audioLength = bucket?.inputByService.asr || 0
      const charCount = bucket?.inputByService.tts || 0
      const inputValue = bucket?.inputByService[service] || 0
      const outputValue = bucket?.outputByService[service] || 0
      const callCount = bucket?.callsByService[service] || 0
      const failedCount = bucket?.failedByService[service] || 0
      const waitTime = bucket?.waitByService[service] || 0
      const usageValue = service === 'llm' ? inputValue + outputValue : inputValue
      return {
        key,
        requestCount,
        tokenUsage,
        audioLength,
        charCount,
        inputValue,
        outputValue,
        callCount,
        failedCount,
        usageValue,
        waitTime
      }
    })
  })

  const trendSeries = computed(() => trendSeriesBase.value)

  const trendSelectedMetricValues = computed(() => {
    const metricKey = selectedTrendMetric.value
    return trendSeries.value.map((item) => item[metricKey] || 0)
  })

  const trendChartMaxValue = computed(() => {
    return Math.max(...trendSelectedMetricValues.value, 0)
  })

  const trendYAxisTicks = computed(() => {
    const maxValue = trendChartMaxValue.value
    const halfValue = Math.ceil(maxValue / 2)
    return [
      { label: compactNumber(maxValue), y: CHART_TOP },
      { label: compactNumber(halfValue), y: CHART_HALF_Y },
      { label: '0', y: CHART_BASELINE_Y }
    ]
  })

  const trendXAxisLabels = computed(() => {
    if (!trendDateKeys.value.length) {
      return []
    }

    const points = [
      trendDateKeys.value[0],
      trendDateKeys.value[Math.floor((trendDateKeys.value.length - 1) / 2)],
      trendDateKeys.value[trendDateKeys.value.length - 1]
    ]

    return points.map((key, index) => ({
      key: `${key}-${index}`,
      label: formatMonthDay(key),
      x: valuesToXPosition(index, points.length)
    }))
  })

  function valuesToXPosition(index, total) {
    const drawableWidth = CHART_WIDTH - CHART_LEFT - CHART_RIGHT
    if (total <= 1) {
      return CHART_LEFT + drawableWidth / 2
    }
    return CHART_LEFT + (index / (total - 1)) * drawableWidth
  }

  const trendMetrics = computed(() => {
    const totalCalls = trendSeries.value.reduce((sum, item) => sum + item.callCount, 0)
    const totalFailed = trendSeries.value.reduce((sum, item) => sum + item.failedCount, 0)
    const totalUsage = trendSeries.value.reduce((sum, item) => sum + item.usageValue, 0)
    const totalWait = trendSeries.value.reduce((sum, item) => sum + item.waitTime, 0)
    const service = selectedTrendSource.value

    return [
      { key: 'callCount', label: '调用次数', value: `${compactNumber(totalCalls)}次` },
      { key: 'failedCount', label: '失败次数', value: `${compactNumber(totalFailed)}次` },
      { key: 'usageValue', label: '用量', value: formatUsageByService(service, totalUsage) },
      { key: 'waitTime', label: '耗时', value: formatAdaptiveTimeFromMs(totalWait) }
    ]
  })

  const trendChartPath = computed(() => {
    const values = trendSelectedMetricValues.value
    return buildLinePath(values)
  })

  const trendAreaPath = computed(() => {
    const linePath = trendChartPath.value
    return `${linePath} L${CHART_WIDTH - CHART_RIGHT},${CHART_BASELINE_Y} L${CHART_LEFT},${CHART_BASELINE_Y} Z`
  })

  onMounted(() => {
    loadStats()
  })

  return {
    chartWidth: CHART_WIDTH,
    chartHeight: CHART_HEIGHT,
    chartLeft: CHART_LEFT,
    chartRight: CHART_RIGHT,
    chartTop: CHART_TOP,
    chartBaselineY: CHART_BASELINE_Y,
    xAxisLabelY: X_AXIS_LABEL_Y,
    currentPeriod,
    selectedTrendSource,
    selectedTrendMetric,
    periods,
    trendSources,
    trendMetricDefinitions,
    loading,
    error,
    moreStatValues,
    heatmapDots,
    trendMetrics,
    trendChartPath,
    trendAreaPath,
    trendYAxisTicks,
    trendXAxisLabels,
    reloadStats: loadStats
  }
}
