<template>
  <section class="logs-root">
    <section v-for="group in logGroups" :key="group.id" class="more-log-card glass-panel">
      <div class="more-card-header">
        <p>{{ group.title }}</p>
        <span>{{ group.rows.length }} 条</span>
      </div>
      <article v-for="entry in group.rows" :key="`${group.id}-${entry.time}-${entry.text}`" class="more-log-item">
        <span class="more-log-item__time">{{ entry.time }}</span>
        <span class="more-log-item__level" :class="`is-${entry.level.toLowerCase()}`">{{ entry.level }}</span>
        <p>{{ entry.text }}</p>
      </article>
    </section>
  </section>
</template>

<script setup>
import { useLogsPage } from '../../composables/useLogsPage'

const { logGroups } = useLogsPage()
</script>

<style scoped>
.logs-root {
  display: grid;
  gap: 16px;
}

.more-log-card {
  border-radius: 20px;
  padding: 14px;
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

.more-log-item {
  margin-top: 10px;
  padding: 10px 12px;
  border-radius: 12px;
  background: rgba(108, 163, 132, 0.12);
  display: grid;
  grid-template-columns: auto auto 1fr;
  gap: 10px;
  align-items: center;
}

.more-log-item p {
  margin: 0;
  color: rgba(228, 245, 235, 0.96);
  line-height: 1.45;
}

.more-log-item__time {
  color: rgba(170, 203, 184, 0.88);
  font-size: 0.78rem;
}

.more-log-item__level {
  padding: 3px 8px;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 600;
}

.more-log-item__level.is-info {
  background: rgba(132, 230, 148, 0.2);
  color: #9cf0ae;
}

.more-log-item__level.is-warn {
  background: rgba(245, 199, 94, 0.2);
  color: #ffd67a;
}

.more-log-item__level.is-error {
  background: rgba(240, 113, 113, 0.2);
  color: #ff9a9a;
}

@media (max-width: 560px) {
  .more-log-item {
    grid-template-columns: 1fr;
    align-items: start;
    gap: 6px;
  }
}
</style>
