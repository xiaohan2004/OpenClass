<template>
  <section class="more-overlay">
    <div class="more-overlay__bg"></div>
    <div class="more-overlay__panel">
      <aside class="more-nav glass-panel">
        <button
          v-for="item in moreNavItems"
          :key="item.id"
          class="more-nav__item"
          :class="{ 'is-active': activeView === item.id }"
          type="button"
          :title="item.label"
          :aria-label="item.label"
          @click="activeView = item.id"
        >
          <span>{{ item.symbol }}</span>
          <small>{{ item.label }}</small>
        </button>
      </aside>

      <div class="more-content">
        <header class="more-header">
          <p class="more-overlay__eyebrow">课堂模拟学生提问助手</p>
          <h2>{{ moreViewTitleMap[activeView] }}</h2>
        </header>

        <StatsPage
          v-if="activeView === 'stats'"
        />

        <LogsPage
          v-else-if="activeView === 'logs'"
        />

        <SettingsPage
          v-else
        />
      </div>
    </div>
  </section>
</template>

<script setup>
import { ref } from 'vue'
import LogsPage from './more-overlay/LogsPage.vue'
import SettingsPage from './more-overlay/SettingsPage.vue'
import StatsPage from './more-overlay/StatsPage.vue'
import { useMoreLayout } from '../composables/useMoreLayout'

const {
  moreNavItems,
  moreViewTitleMap
} = useMoreLayout()

const activeView = ref('stats')
</script>

<style scoped>
.more-overlay {
  position: fixed;
  inset: 0;
  z-index: 26;
  display: block;
  padding: 20px;
  overflow-y: scroll;
  overflow-x: hidden;
  scrollbar-gutter: stable;
}

.more-overlay__bg {
  position: fixed;
  inset: 0;
  background:
    radial-gradient(circle at 78% 26%, rgba(95, 179, 115, 0.14), transparent 28%),
    radial-gradient(circle at 14% 84%, rgba(120, 204, 151, 0.18), transparent 26%),
    linear-gradient(145deg, rgba(7, 33, 26, 0.92), rgba(9, 36, 30, 0.88));
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
}

.more-overlay__panel {
  position: relative;
  z-index: 1;
  width: min(1080px, calc(100vw - 40px));
  min-height: calc(100vh - 40px);
  margin: 0 auto;
  display: grid;
  grid-template-columns: 60px minmax(0, 1fr);
  gap: 20px;
}

.more-overlay__eyebrow {
  margin: 0;
  font-size: 0.9rem;
  color: rgba(190, 227, 202, 0.78);
  letter-spacing: 0.06em;
}

.more-header h2 {
  margin: 0;
  font-size: 2rem;
  color: #eaf7ee;
  letter-spacing: -0.02em;
}

.more-nav {
  position: sticky;
  top: 18vh;
  align-self: start;
  height: fit-content;
  border-radius: 24px;
  padding: 12px 8px;
  display: grid;
  gap: 10px;
  background: linear-gradient(180deg, rgba(20, 53, 44, 0.8), rgba(10, 39, 33, 0.8));
  border: 1px solid rgba(130, 178, 145, 0.2);
}

.more-nav__item {
  width: 42px;
  min-height: 54px;
  border-radius: 14px;
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 3px;
  color: rgba(185, 218, 198, 0.7);
  background: rgba(196, 230, 209, 0.04);
  transition: all 180ms ease;
}

.more-nav__item span {
  font-size: 0.9rem;
  font-weight: 700;
}

.more-nav__item small {
  font-size: 0.65rem;
  line-height: 1;
}

.more-nav__item.is-active,
.more-nav__item:hover {
  background: linear-gradient(180deg, rgba(113, 213, 134, 0.9), rgba(95, 198, 118, 0.9));
  color: #063821;
  box-shadow: 0 10px 20px rgba(79, 186, 108, 0.28);
}

.more-content {
  min-width: 0;
  display: grid;
  gap: 16px;
  align-content: start;
}

.more-header {
  display: grid;
  gap: 6px;
  padding: 4px 4px 0;
}

@media (max-width: 860px) {
  .more-overlay {
    padding: 14px;
  }

  .more-overlay__panel {
    width: calc(100vw - 28px);
    min-height: calc(100vh - 28px);
    grid-template-columns: 1fr;
    gap: 14px;
  }

  .more-nav {
    position: static;
    grid-auto-flow: column;
    grid-template-columns: repeat(3, 60px);
    width: fit-content;
  }
}

@media (max-width: 560px) {
  .more-header h2 {
    font-size: 1.55rem;
  }
}
</style>
