<template>
  <section class="stats-root">
    <!-- 总统计卡片 - 左右分割布局 -->
    <section class="more-stats-grid">
      <article v-for="card in moreStatCards" :key="card.id" class="more-stat-card glass-panel">
        <div class="more-stat-card__header">
          <span class="more-stat-card__title">{{ card.title }}</span>
          <div class="more-stat-card__divider"></div>
        </div>
        <div class="more-stat-card__rows">
          <div v-for="row in card.rows" :key="row.label" class="more-stat-row">
            <div class="more-stat-row__icon" :style="{ backgroundColor: row.bgColor }">
              <span class="more-stat-row__icon-inner">{{ getIconEmoji(row.icon) }}</span>
            </div>
            <div class="more-stat-row__content">
              <span class="more-stat-row__label">{{ row.label }}</span>
              <div class="more-stat-row__value">
                <strong>{{ row.value }}</strong>
                <span v-if="row.unit" class="more-stat-row__unit">{{ row.unit }}</span>
              </div>
            </div>
          </div>
        </div>
      </article>
    </section>

    <!-- 热力图 - 可滚动的 -->
    <section class="more-heatmap glass-panel">
      <div class="more-heatmap__scroll-container" ref="heatmapScroll" @scroll="handleHeatmapScroll">
        <div class="more-heatmap__dots">
          <span
            v-for="dot in heatmapDots"
            :key="dot.id"
            class="more-heatmap__dot"
            :class="dot.level"
            @mouseenter="(e) => showHeatmapTooltip(dot, e)"
            @mouseleave="hideHeatmapTooltip"
          ></span>
        </div>
      </div>
      <Teleport to="body">
        <div v-if="heatmapTooltip" class="more-heatmap__tooltip" :style="{ left: heatmapTooltip.x + 'px', top: heatmapTooltip.y + 'px' }">
          <div class="tooltip-date">{{ heatmapTooltip.data.date }}</div>
          <template v-if="heatmapTooltip.data.hasData">
            <div class="tooltip-row">
              <span class="tooltip-label">请求次数</span>
              <span class="tooltip-value">{{ heatmapTooltip.data.requests }}</span>
            </div>
            <div class="tooltip-row">
              <span class="tooltip-label">等待时间</span>
              <span class="tooltip-value">{{ heatmapTooltip.data.waitTime }}</span>
            </div>
            <div class="tooltip-row">
              <span class="tooltip-label">消耗Token</span>
              <span class="tooltip-value">{{ heatmapTooltip.data.tokenCost }}</span>
            </div>
            <div class="tooltip-row">
              <span class="tooltip-label">音频长度</span>
              <span class="tooltip-value">{{ heatmapTooltip.data.audioLength }}</span>
            </div>
            <div class="tooltip-row">
              <span class="tooltip-label">字符数量</span>
              <span class="tooltip-value">{{ heatmapTooltip.data.charCount }}</span>
            </div>
            <div class="tooltip-row">
              <span class="tooltip-label">综合指数</span>
              <span class="tooltip-value">{{ heatmapTooltip.data.compositeScoreText }}</span>
            </div>
          </template>
          <div v-else class="tooltip-empty">无数据</div>
        </div>
      </Teleport>
    </section>

    <!-- 趋势图 - 支持时间段选择 -->
    <section class="more-trend glass-panel">
      <div class="more-card-header">
        <p>趋势</p>
        <div class="more-trend__controls">
          <div class="more-trend__source-group" role="radiogroup" aria-label="趋势来源">
            <button
              v-for="source in trendSources"
              :key="source.value"
              class="more-trend__source-option"
              :class="{ 'is-active': selectedTrendSource === source.value }"
              type="button"
              role="radio"
              :aria-checked="selectedTrendSource === source.value"
              @click="selectedTrendSource = source.value"
            >
              <span>{{ source.label }}</span>
            </button>
          </div>
          <button class="more-trend__period-btn" @click="handlePeriodClick">
            {{ getCurrentPeriodLabel() }}
          </button>
        </div>
      </div>
      <div class="more-trend__metrics" role="radiogroup" aria-label="趋势指标">
        <button
          v-for="metric in trendMetrics"
          :key="metric.key"
          class="more-metric-pill"
          :class="{ 'is-active': selectedTrendMetric === metric.key }"
          type="button"
          role="radio"
          :aria-checked="selectedTrendMetric === metric.key"
          @click="selectedTrendMetric = metric.key"
        >
          <span>{{ metric.label }}</span>
          <strong>{{ metric.value }}</strong>
        </button>
      </div>
      <svg class="more-trend__chart" :viewBox="`0 0 ${chartWidth} ${chartHeight}`" preserveAspectRatio="none" aria-hidden="true">
        <defs>
          <linearGradient id="trendFill" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stop-color="rgba(132, 230, 148, 0.44)" />
            <stop offset="100%" stop-color="rgba(132, 230, 148, 0.04)" />
          </linearGradient>
        </defs>
        <g class="more-trend__axis-group">
          <line class="more-trend__axis-line" :x1="chartLeft" :y1="chartTop" :x2="chartLeft" :y2="chartBaselineY" />
          <line class="more-trend__axis-line" :x1="chartLeft" :y1="chartBaselineY" :x2="chartWidth - chartRight" :y2="chartBaselineY" />
          <g v-for="tick in trendYAxisTicks" :key="tick.label + tick.y" class="more-trend__y-tick">
            <line class="more-trend__tick-line" :x1="chartLeft - 6" :y1="tick.y" :x2="chartLeft" :y2="tick.y" />
            <text class="more-trend__axis-text more-trend__axis-text--y" :x="chartLeft - 10" :y="tick.y" dy="0.35em">{{ tick.label }}</text>
          </g>
          <g v-for="label in trendXAxisLabels" :key="label.key" class="more-trend__x-label">
            <text class="more-trend__axis-text more-trend__axis-text--x" :x="label.x" :y="xAxisLabelY">{{ label.label }}</text>
          </g>
        </g>
        <path
          class="more-trend__area"
          :d="trendAreaPath"
        />
        <path
          class="more-trend__line"
          :d="trendChartPath"
        />
      </svg>
    </section>


  </section>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useStatsPage } from '../../composables/useStatsPage'

const {
  currentPeriod,
  selectedTrendSource,
  periods,
  trendSources,
  moreStatValues,
  heatmapDots,
  chartWidth,
  chartHeight,
  chartLeft,
  chartRight,
  chartTop,
  chartBaselineY,
  xAxisLabelY,
  selectedTrendMetric,
  trendMetrics,
  trendChartPath,
  trendAreaPath,
  trendYAxisTicks,
  trendXAxisLabels
} = useStatsPage()

const statCardMeta = [
  {
    id: 'req',
    title: '请求统计',
    rows: [
      {
        label: '请求次数',
        valueKey: 'requestCount',
        icon: 'IconMessage',
        bgColor: 'rgba(132, 230, 148, 0.2)',
        unit: ''
      },
      {
        label: '消耗时间',
        valueKey: 'durationHours',
        icon: 'IconClock',
        bgColor: 'rgba(245, 199, 94, 0.2)',
        unit: ''
      }
    ]
  },
  {
    id: 'llm',
    title: 'LLM统计',
    rows: [
      {
        label: '输入 / 输出Tokens',
        valueKey: 'inOutTokens',
        icon: 'IconBot',
        bgColor: 'rgba(100, 181, 246, 0.2)',
        unit: ''
      },
      {
        label: '成功 / 失败',
        valueKey: 'successFail',
        icon: 'IconChart',
        bgColor: 'rgba(147, 112, 219, 0.2)',
        unit: ''
      }
    ]
  },
  {
    id: 'asr',
    title: 'ASR统计',
    rows: [
      {
        label: '音频总长',
        valueKey: 'totalAudioSeconds',
        icon: 'IconClock',
        bgColor: 'rgba(100, 181, 246, 0.2)',
        unit: ''
      },
      {
        label: '成功 / 失败',
        valueKey: 'successFail',
        icon: 'IconChart',
        bgColor: 'rgba(147, 112, 219, 0.2)',
        unit: ''
      }
    ]
  },
  {
    id: 'tts',
    title: 'TTS统计',
    rows: [
      {
        label: '字符总数',
        valueKey: 'totalChars',
        icon: 'IconMessage',
        bgColor: 'rgba(245, 199, 94, 0.2)',
        unit: ''
      },
      {
        label: '成功 / 失败',
        valueKey: 'successFail',
        icon: 'IconChart',
        bgColor: 'rgba(147, 112, 219, 0.2)',
        unit: ''
      }
    ]
  }
]

const formatSlashSpacing = (value) => {
  if (typeof value !== 'string') {
    return value
  }
  return value.replace(/\s*\/\s*/g, ' / ')
}

const moreStatCards = computed(() =>
  statCardMeta.map((card) => ({
    ...card,
    rows: card.rows.map((row) => ({
      ...row,
      value: formatSlashSpacing(moreStatValues.value?.[card.id]?.[row.valueKey] ?? '--')
    }))
  }))
)

const heatmapScroll = ref(null)
const heatmapTooltip = ref(null)

// 图标映射
const iconMap = {
  IconActivity: '📊',
  IconMessage: '💬',
  IconClock: '⏱️',
  IconChart: '📈',
  IconBot: '🤖',
  IconDollar: '💵',
  IconArrowDown: '⬇️',
  IconRewind: '⏮️',
  IconArrowUp: '⬆️',
  IconFastForward: '⏭️'
}

const getIconEmoji = (iconName) => {
  return iconMap[iconName] || '•'
}

// 获取当前时间段标签
const getCurrentPeriodLabel = () => {
  const current = periods.find(p => p.value === currentPeriod.value)
  return current ? current.label : '30天'
}

// 循环切换时间段
const handlePeriodClick = () => {
  const currentIndex = periods.findIndex(p => p.value === currentPeriod.value)
  const nextIndex = (currentIndex + 1) % periods.length
  currentPeriod.value = periods[nextIndex].value
}

// 显示热力图 tooltip
const showHeatmapTooltip = (dot, event) => {
  const tooltipWidth = 140 // 与 CSS 中的 min-width 一致
  const offsetY = 10 // 距离光标的垂直距离
  
  heatmapTooltip.value = {
    x: event.clientX - tooltipWidth / 2,
    y: event.clientY + offsetY,
    data: dot.data
  }
}

// 隐藏热力图 tooltip
const hideHeatmapTooltip = () => {
  heatmapTooltip.value = null
}

// 监听滚动时自动调整 mask 效果
const handleHeatmapScroll = (e) => {
  if (!heatmapScroll.value) return
  const { scrollLeft, scrollWidth, clientWidth } = heatmapScroll.value
  const isStart = scrollLeft <= 1
  const isEnd = Math.abs(scrollWidth - clientWidth - scrollLeft) <= 1
  
  let maskImage = 'none'
  if (!isStart && !isEnd) {
    maskImage = 'linear-gradient(to right, transparent, rgba(0,0,0,0) 10px, black 40px, black calc(100% - 40px), rgba(0,0,0,0) calc(100% - 10px), transparent)'
  } else if (isStart && !isEnd) {
    maskImage = 'linear-gradient(to left, transparent, rgba(0,0,0,0) 10px, black 40px)'
  } else if (!isStart && isEnd) {
    maskImage = 'linear-gradient(to right, transparent, rgba(0,0,0,0) 10px, black 40px)'
  }
  
  heatmapScroll.value.style.maskImage = maskImage
  heatmapScroll.value.style.webkitMaskImage = maskImage
}
</script>

<style scoped>
.stats-root {
  display: grid;
  gap: 16px;
}

/* 总统计卡片 - 左右分割布局 */
.more-stats-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.more-stat-card {
  border-radius: 18px;
  padding: 16px;
  background: linear-gradient(180deg, rgba(46, 72, 58, 0.8), rgba(32, 53, 43, 0.75));
  border: 1px solid rgba(132, 178, 150, 0.18);
  box-shadow: 0 20px 32px rgba(4, 22, 17, 0.28);
  display: flex;
  flex-direction: column;
  gap: 12px;
  align-items: stretch;
}

.more-stat-card__header {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: flex-start;
  gap: 8px;
  border-bottom: 1px solid rgba(130, 178, 145, 0.2);
  padding-bottom: 12px;
  flex-shrink: 0;
}

.more-stat-card__title {
  margin: 0;
  color: #e8f8ee;
  font-size: 1.1rem;
  text-align: left;
  flex: 1;
  line-height: 1.3;
  font-weight: 700;
  letter-spacing: -0.01em;
}

.more-stat-card__divider {
  display: none;
}

.more-stat-card__rows {
  display: flex;
  flex-direction: column;
  gap: 10px;
  flex: 1;
}

.more-stat-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.more-stat-row__icon {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  opacity: 0.95;
  font-size: 16px;
  line-height: 1;
}

.more-stat-row__icon-inner {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
}

.more-stat-row__content {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.more-stat-row__label {
  color: rgba(176, 209, 192, 0.8);
  font-size: 0.75rem;
}

.more-stat-row__value {
  display: flex;
  align-items: baseline;
  gap: 3px;
}

.more-stat-row__value strong {
  color: #ebf8ef;
  font-size: 1rem;
  letter-spacing: -0.02em;
}

.more-stat-row__unit {
  color: rgba(176, 209, 192, 0.7);
  font-size: 1rem;
}

/* 热力图 - 可滚动的 */
.more-heatmap {
  border-radius: 20px;
  padding: 16px;
  background: linear-gradient(180deg, rgba(40, 68, 55, 0.75), rgba(30, 51, 42, 0.8));
  border: 1px solid rgba(132, 178, 150, 0.18);
  position: relative;
}

.more-heatmap__scroll-container {
  overflow-x: auto;
  overflow-y: hidden;
  scrollbar-width: thin;
  scrollbar-color: rgba(132, 230, 148, 0.3) rgba(132, 230, 148, 0.1);
  display: flex;
  justify-content: center;
  align-items: center;
}

.more-heatmap__scroll-container::-webkit-scrollbar {
  height: 6px;
}

.more-heatmap__scroll-container::-webkit-scrollbar-track {
  background: rgba(132, 230, 148, 0.1);
}

.more-heatmap__scroll-container::-webkit-scrollbar-thumb {
  background: rgba(132, 230, 148, 0.3);
  border-radius: 3px;
}

.more-heatmap__scroll-container::-webkit-scrollbar-thumb:hover {
  background: rgba(132, 230, 148, 0.5);
}

.more-heatmap__dots {
  display: grid;
  grid-auto-flow: column;
  grid-auto-columns: 14px;
  grid-template-rows: repeat(7, 14px);
  gap: 3px;
  width: fit-content;
  padding: 4px;
  place-items: center;
}

.more-heatmap__dot {
  display: block;
  width: 14px;
  height: 14px;
  border-radius: 3px;
  background: rgba(114, 160, 132, 0.16);
  cursor: pointer;
  transition: all 150ms ease;
}

.more-heatmap__dot:hover {
  transform: scale(1.3);
  box-shadow: 0 2px 8px rgba(132, 230, 148, 0.2);
}

.more-heatmap__dot.is-idle {
  background: rgba(114, 160, 132, 0.16);
}

.more-heatmap__dot.is-cold {
  background: rgba(122, 186, 143, 0.28);
}

.more-heatmap__dot.is-warm {
  background: rgba(137, 214, 161, 0.44);
}

.more-heatmap__dot.is-hot {
  background: rgba(150, 242, 171, 0.68);
}

.more-heatmap__tooltip {
  position: fixed;
  background: linear-gradient(180deg, rgba(20, 40, 32, 0.95), rgba(15, 30, 25, 0.95));
  border: 1px solid rgba(132, 230, 148, 0.3);
  border-radius: 8px;
  padding: 10px 12px;
  z-index: 9999999;
  font-size: 0.8rem;
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
  pointer-events: none;
  min-width: 140px;
}

.tooltip-date {
  margin-bottom: 10px;
  border-bottom: 1px solid rgba(132, 230, 148, 0.2);
  padding-bottom: 8px;
  text-align: left;
  font-size: 1rem;
  color: #e8f8ee;
  font-weight: 700;
  letter-spacing: -0.01em;
}

.tooltip-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  margin-bottom: 7px;
}

.tooltip-label {
  color: rgba(180, 217, 197, 0.8);
  font-size: 0.73rem;
}

.tooltip-value {
  color: #84e694;
  font-weight: 600;
  font-size: 0.8rem;
  white-space: nowrap;
  text-align: right;
}

.tooltip-empty {
  color: rgba(193, 221, 206, 0.78);
  font-size: 0.78rem;
  text-align: left;
}

/* 趋势图 */
.more-trend {
  border-radius: 22px;
  padding: 16px;
  background: linear-gradient(180deg, rgba(40, 68, 55, 0.78), rgba(30, 51, 42, 0.84));
  border: 1px solid rgba(132, 178, 150, 0.18);
}

.more-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.more-card-header p {
  margin: 0;
  color: #e8f8ee;
  font-size: 1.03rem;
  font-weight: 600;
}

.more-trend__controls {
  display: flex;
  align-items: center;
  gap: 10px;
}

.more-trend__source-group {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 7px 12px;
  border-radius: 999px;
  background: rgba(131, 182, 154, 0.16);
  border: 1px solid rgba(132, 178, 150, 0.2);
}

.more-trend__source-option {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 6px 14px;
  border: none;
  background: transparent;
  border-radius: 999px;
  color: rgba(216, 239, 225, 0.9);
  font-size: 0.82rem;
  cursor: pointer;
  user-select: none;
  transition: background-color 150ms ease, color 150ms ease;
}

.more-trend__source-option + .more-trend__source-option::before {
  content: '';
  position: absolute;
  left: -3px;
  top: 50%;
  transform: translateY(-50%);
  width: 1px;
  height: 18px;
  background: rgba(183, 219, 198, 0.45);
}

.more-trend__source-option.is-active {
  background: linear-gradient(180deg, rgba(132, 230, 148, 0.5), rgba(108, 214, 130, 0.36));
  color: #f4fff6;
  box-shadow: inset 0 0 0 1px rgba(187, 247, 201, 0.72), 0 2px 8px rgba(110, 214, 130, 0.28);
  font-weight: 600;
}

.more-trend__source-option:hover {
  color: #f1fbf3;
  background: rgba(132, 230, 148, 0.2);
}

.more-trend__period-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 88px;
  padding: 8px 20px;
  border-radius: 8px;
  background: linear-gradient(180deg, rgba(113, 213, 134, 0.9), rgba(95, 198, 118, 0.9));
  color: #063821;
  border: none;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 150ms ease;
  letter-spacing: -0.01em;
}

.more-trend__period-btn:hover {
  background: linear-gradient(180deg, rgba(113, 213, 134, 1), rgba(95, 198, 118, 1));
  box-shadow: 0 4px 12px rgba(132, 230, 148, 0.3);
}

.more-trend__period-btn:active {
  transform: scale(0.98);
}

.more-trend__metrics {
  margin-bottom: 12px;
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.more-metric-pill {
  width: 100%;
  min-width: 0;
  padding: 8px 10px;
  border-radius: 12px;
  background: rgba(131, 182, 154, 0.18);
  border: 1px solid rgba(132, 178, 150, 0.16);
  display: grid;
  gap: 4px;
  text-align: left;
  cursor: pointer;
  transition: background-color 150ms ease, border-color 150ms ease, box-shadow 150ms ease, transform 150ms ease;
}

.more-metric-pill.is-active {
  background: linear-gradient(180deg, rgba(132, 230, 148, 0.42), rgba(108, 214, 130, 0.24));
  border-color: rgba(187, 247, 201, 0.7);
  box-shadow: inset 0 0 0 1px rgba(187, 247, 201, 0.35), 0 4px 12px rgba(110, 214, 130, 0.2);
  transform: translateY(-1px);
}

.more-metric-pill:hover {
  background: rgba(131, 182, 154, 0.26);
}

.more-metric-pill span {
  color: rgba(180, 217, 197, 0.82);
  font-size: 0.78rem;
  white-space: nowrap;
}

.more-metric-pill strong {
  color: #f0fbf4;
  font-size: 0.95rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.more-trend__chart {
  width: 100%;
  height: 320px;
}

.more-trend__axis-line {
  stroke: rgba(190, 226, 203, 0.36);
  stroke-width: 1;
}

.more-trend__tick-line {
  stroke: rgba(190, 226, 203, 0.28);
  stroke-width: 1;
}

.more-trend__axis-text {
  fill: rgba(217, 240, 223, 0.82);
  font-size: 10px;
}

.more-trend__axis-text--y {
  text-anchor: end;
}

.more-trend__axis-text--x {
  text-anchor: middle;
}

.more-trend__area {
  fill: url(#trendFill);
}

.more-trend__line {
  fill: none;
  stroke: #84e694;
  stroke-width: 2.4;
  stroke-linecap: round;
  stroke-linejoin: round;
}

/* 响应式设计 */
@media (max-width: 860px) {
  .more-stats-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .more-heatmap__dots {
    grid-auto-columns: 12px;
    grid-template-rows: repeat(7, 12px);
  }
}

@media (max-width: 560px) {
  .more-stats-grid {
    grid-template-columns: 1fr;
  }

  .more-trend__metrics {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .more-trend__controls {
    width: 100%;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 8px;
  }

  .more-trend__source-group {
    flex-wrap: wrap;
  }

  .more-heatmap__dots {
    grid-auto-columns: 10px;
    grid-template-rows: repeat(7, 10px);
    gap: 2px;
  }

  .more-card-header {
    flex-direction: column;
    align-items: flex-start;
  }

}
</style>
