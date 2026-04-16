<template>
  <section class="stats-root">
    <section class="more-stats-grid">
      <article v-for="card in moreStatCards" :key="card.id" class="more-stat-card glass-panel">
        <p class="more-stat-card__title">{{ card.title }}</p>
        <div class="more-stat-card__rows">
          <div v-for="row in card.rows" :key="row.label" class="more-stat-row">
            <span>{{ row.label }}</span>
            <strong>{{ row.value }}</strong>
          </div>
        </div>
      </article>
    </section>

    <section class="more-heatmap glass-panel">
      <div class="more-heatmap__dots">
        <span
          v-for="dot in heatmapDots"
          :key="dot.id"
          class="more-heatmap__dot"
          :class="dot.level"
        ></span>
      </div>
    </section>

    <section class="more-trend glass-panel">
      <div class="more-card-header">
        <p>趋势</p>
        <span>Tokens · 30天</span>
      </div>
      <div class="more-trend__metrics">
        <div v-for="metric in trendMetrics" :key="metric.label" class="more-metric-pill">
          <span>{{ metric.label }}</span>
          <strong>{{ metric.value }}</strong>
        </div>
      </div>
      <svg class="more-trend__chart" viewBox="0 0 760 180" preserveAspectRatio="none" aria-hidden="true">
        <defs>
          <linearGradient id="trendFill" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stop-color="rgba(132, 230, 148, 0.44)" />
            <stop offset="100%" stop-color="rgba(132, 230, 148, 0.04)" />
          </linearGradient>
        </defs>
        <path
          class="more-trend__area"
          d="M0,164 C80,160 110,148 160,108 C200,76 238,58 280,94 C314,122 338,160 388,154 C434,148 470,146 508,152 C548,158 576,46 620,70 C656,90 672,160 704,166 C730,170 748,166 760,164 L760,180 L0,180 Z"
        />
        <path
          class="more-trend__line"
          d="M0,164 C80,160 110,148 160,108 C200,76 238,58 280,94 C314,122 338,160 388,154 C434,148 470,146 508,152 C548,158 576,46 620,70 C656,90 672,160 704,166 C730,170 748,166 760,164"
        />
      </svg>
    </section>

    <section class="more-rank glass-panel">
      <div class="more-card-header">
        <p>排行榜</p>
        <span>Tokens</span>
      </div>
      <article v-for="user in rankItems" :key="user.name" class="more-rank__item">
        <span class="more-rank__medal">{{ user.medal }}</span>
        <p>{{ user.name }}</p>
        <strong>{{ user.value }}</strong>
      </article>
    </section>
  </section>
</template>

<script setup>
import { useStatsPage } from '../../composables/useStatsPage'

const {
  moreStatCards,
  trendMetrics,
  rankItems,
  heatmapDots
} = useStatsPage()
</script>

<style scoped>
.stats-root {
  display: grid;
  gap: 16px;
}

.more-stats-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.more-stat-card {
  border-radius: 18px;
  padding: 14px;
  background: linear-gradient(180deg, rgba(46, 72, 58, 0.8), rgba(32, 53, 43, 0.75));
  border: 1px solid rgba(132, 178, 150, 0.18);
  box-shadow: 0 20px 32px rgba(4, 22, 17, 0.28);
}

.more-stat-card__title {
  margin: 0;
  color: rgba(180, 212, 194, 0.76);
  font-size: 0.84rem;
}

.more-stat-card__rows {
  margin-top: 10px;
  display: grid;
  gap: 8px;
}

.more-stat-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 10px;
}

.more-stat-row span {
  color: rgba(176, 209, 192, 0.8);
  font-size: 0.8rem;
}

.more-stat-row strong {
  color: #ebf8ef;
  font-size: 1.07rem;
  letter-spacing: -0.02em;
}

.more-heatmap {
  border-radius: 20px;
  padding: 14px;
  background: linear-gradient(180deg, rgba(40, 68, 55, 0.75), rgba(30, 51, 42, 0.8));
  border: 1px solid rgba(132, 178, 150, 0.18);
}

.more-heatmap__dots {
  display: grid;
  grid-template-columns: repeat(22, minmax(0, 1fr));
  gap: 5px;
}

.more-heatmap__dot {
  display: block;
  width: 100%;
  aspect-ratio: 1 / 1;
  border-radius: 4px;
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

.more-trend,
.more-rank {
  border-radius: 22px;
  padding: 14px 14px 16px;
  background: linear-gradient(180deg, rgba(40, 68, 55, 0.78), rgba(30, 51, 42, 0.84));
  border: 1px solid rgba(132, 178, 150, 0.18);
}

.more-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
}

.more-card-header p {
  margin: 0;
  color: #e8f8ee;
  font-size: 1.03rem;
  font-weight: 600;
}

.more-card-header span {
  color: rgba(173, 209, 188, 0.86);
  font-size: 0.84rem;
}

.more-trend__metrics {
  margin-top: 10px;
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.more-metric-pill {
  padding: 8px 10px;
  border-radius: 12px;
  background: rgba(131, 182, 154, 0.18);
  display: grid;
  gap: 4px;
}

.more-metric-pill span {
  color: rgba(180, 217, 197, 0.82);
  font-size: 0.78rem;
}

.more-metric-pill strong {
  color: #f0fbf4;
}

.more-trend__chart {
  margin-top: 10px;
  width: 100%;
  height: 178px;
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

.more-rank {
  padding-top: 12px;
}

.more-rank__item {
  margin-top: 12px;
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 10px;
  color: #d7efdf;
}

.more-rank__medal {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: rgba(244, 197, 104, 0.24);
  color: #ffd990;
  font-size: 0.76rem;
  font-weight: 700;
}

.more-rank__item p {
  margin: 0;
}

.more-rank__item strong {
  color: #f0fbf4;
}

@media (max-width: 860px) {
  .more-stats-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 560px) {
  .more-stats-grid {
    grid-template-columns: 1fr;
  }

  .more-heatmap__dots {
    grid-template-columns: repeat(14, minmax(0, 1fr));
  }
}
</style>
