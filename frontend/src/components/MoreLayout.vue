<template>
  <section ref="overlayRef" class="more-overlay">
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
          <span class="more-nav__icon">{{ item.symbol }}</span>
          <small class="more-nav__label">{{ item.label }}</small>
        </button>
      </aside>

      <div class="more-panel-body">
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

          <CoursePage
            v-else-if="activeView === 'course'"
          />

          <SettingsPage
            v-else
          />
        </div>

        <button
          class="more-scroll-top"
          type="button"
          title="回顶"
          aria-label="回到顶部"
          @click="scrollToTop"
        >
          ↑
        </button>
      </div>
    </div>
  </section>
</template>

<script setup>
import { ref } from 'vue'
import CoursePage from './more-overlay/CoursePage.vue'
import LogsPage from './more-overlay/LogsPage.vue'
import SettingsPage from './more-overlay/SettingsPage.vue'
import StatsPage from './more-overlay/StatsPage.vue'
import { useMoreLayout } from '../composables/useMoreLayout'

const {
  moreNavItems,
  moreViewTitleMap
} = useMoreLayout()

const activeView = ref('stats')
const overlayRef = ref(null)

const scrollToTop = () => {
  overlayRef.value?.scrollTo({ top: 0, behavior: 'smooth' })
}
</script>

<style scoped>
.more-overlay {
  position: fixed;
  inset: 0;
  z-index: 26;
  display: block;
  padding: 20px;
  overflow-y: auto;
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
  grid-template-columns: 78px minmax(0, 1fr);
  gap: 20px;
}

.more-panel-body {
  min-width: 0;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 16px;
  align-items: start;
}

.more-overlay__eyebrow {
  margin: 0;
  font-size: 1.05rem;
  color: rgba(190, 227, 202, 0.78);
  letter-spacing: 0.06em;
}

.more-scroll-top {
  position: fixed;
  right: max(18px, calc((100vw - min(1080px, calc(100vw - 40px))) / 2 - 60px));
  bottom: 26px;
  z-index: 2;
  width: 52px;
  height: 52px;
  border-radius: 999px;
  border: 1px solid rgba(164, 226, 184, 0.24);
  display: grid;
  place-items: center;
  font-size: 1.4rem;
  font-weight: 800;
  color: #063821;
  background: linear-gradient(180deg, rgba(144, 230, 168, 0.96), rgba(96, 199, 119, 0.92));
  box-shadow:
    0 12px 24px rgba(19, 63, 42, 0.38),
    inset 0 1px 0 rgba(242, 255, 246, 0.42);
  transition: transform 180ms ease, box-shadow 180ms ease,
    filter 180ms ease;
}

.more-scroll-top:hover {
  transform: translateY(-2px) scale(1.04);
  filter: brightness(1.03);
  box-shadow:
    0 16px 28px rgba(19, 63, 42, 0.44),
    0 0 0 3px rgba(138, 225, 165, 0.2),
    inset 0 1px 0 rgba(242, 255, 246, 0.42);
}

.more-scroll-top:focus-visible {
  outline: none;
  box-shadow:
    0 0 0 3px rgba(138, 225, 165, 0.34),
    0 16px 28px rgba(19, 63, 42, 0.44),
    inset 0 1px 0 rgba(242, 255, 246, 0.42);
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
  border-radius: 22px;
  padding: 12px 10px;
  display: grid;
  gap: 8px;
  background:
    linear-gradient(180deg, rgba(27, 67, 55, 0.9), rgba(11, 41, 34, 0.9));
  border: 1px solid rgba(132, 190, 156, 0.26);
  box-shadow:
    inset 0 1px 0 rgba(236, 253, 245, 0.12),
    0 12px 28px rgba(4, 20, 14, 0.34);
}

.more-nav__item {
  position: relative;
  width: 56px;
  min-height: 68px;
  border-radius: 16px;
  border: 1px solid rgba(157, 214, 182, 0.12);
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 7px;
  color: rgba(196, 228, 209, 0.82);
  background:
    linear-gradient(180deg, rgba(209, 241, 222, 0.08), rgba(164, 212, 185, 0.03));
  overflow: hidden;
  transition: transform 180ms ease, box-shadow 180ms ease,
    border-color 180ms ease, background 180ms ease, color 180ms ease;
}

.more-nav__item::after {
  content: '';
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 50% 0%, rgba(187, 246, 205, 0.26), transparent 55%);
  opacity: 0;
  transition: opacity 180ms ease;
}

.more-nav__item::before {
  content: '';
  position: absolute;
  left: -8px;
  top: 50%;
  width: 3px;
  height: 0;
  border-radius: 999px;
  background: linear-gradient(180deg, #8df0a5, #72d491);
  opacity: 0;
  transform: translateY(-50%);
  transition: height 180ms ease, opacity 180ms ease;
}

.more-nav__icon {
  font-size: 1.02rem;
  font-weight: 700;
  line-height: 1;
  filter: drop-shadow(0 1px 2px rgba(7, 27, 20, 0.2));
}

.more-nav__label {
  font-size: 0.72rem;
  line-height: 1;
  letter-spacing: 0.02em;
  font-weight: 800;
  color: rgba(224, 245, 233, 0.95);
}

.more-nav__item:hover {
  transform: translateY(-2px) scale(1.05);
  border-color: rgba(156, 231, 183, 0.68);
  background:
    linear-gradient(180deg, rgba(215, 248, 228, 0.2), rgba(170, 220, 191, 0.08));
  box-shadow:
    0 0 0 1px rgba(169, 238, 193, 0.28),
    0 14px 26px rgba(13, 46, 33, 0.44),
    0 0 24px rgba(127, 224, 158, 0.22);
}

.more-nav__item:hover::after {
  opacity: 1;
}

.more-nav__item.is-active {
  background: linear-gradient(180deg, rgba(113, 213, 134, 0.9), rgba(95, 198, 118, 0.9));
  color: #063821;
  border-color: rgba(145, 226, 174, 0.75);
  box-shadow:
    inset 0 1px 0 rgba(241, 255, 247, 0.42),
    0 12px 22px rgba(79, 186, 108, 0.32);
}

.more-nav__item.is-active::before {
  opacity: 1;
  height: 24px;
}

.more-nav__item:focus-visible {
  outline: none;
  border-color: rgba(169, 238, 193, 0.9);
  box-shadow:
    0 0 0 3px rgba(131, 226, 161, 0.28),
    0 8px 18px rgba(16, 56, 38, 0.34);
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

  .more-scroll-top {
    right: 18px;
    bottom: 18px;
    width: 48px;
    height: 48px;
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

  .more-nav__item::before {
    left: 50%;
    top: auto;
    bottom: -7px;
    width: 20px;
    height: 3px;
    transform: translateX(-50%);
  }

  .more-nav__item.is-active::before {
    width: 24px;
    height: 3px;
  }

  .more-nav__item {
    min-height: 62px;
  }
}

@media (max-width: 560px) {
  .more-header h2 {
    font-size: 1.55rem;
  }
}
</style>
