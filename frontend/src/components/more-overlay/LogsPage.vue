<template>
  <section class="logs-root">
    <div class="more-log-toolbar glass-panel">
      <label class="more-log-toolbar__filter" for="log-service-filter">
        <span style="font-weight: 700; font-size: 15px">分类</span>
        <select
          id="log-service-filter"
          :value="selectedServiceType"
          @change="changeServiceType($event.target.value)"
        >
          <option value="all">全部</option>
          <option value="llm">LLM</option>
          <option value="asr">ASR</option>
          <option value="tts">TTS</option>
        </select>
      </label>
      <button
        class="more-log-toolbar__refresh"
        type="button"
        @click="reloadLogs"
      >
        刷新
      </button>
    </div>

    <div v-if="loading" class="more-log-state glass-panel">日志加载中...</div>
    <div
      v-else-if="error"
      class="more-log-state more-log-state--error glass-panel"
    >
      {{ error }}
    </div>
    <div v-else-if="!logItems.length" class="more-log-state glass-panel">
      暂无日志数据
    </div>

    <div v-else class="logs-list-wrapper">
      <div class="logs-list">
        <article
          v-for="entry in logItems"
          :key="entry.id"
          class="more-log-card glass-panel"
          role="button"
          tabindex="0"
          @click="openLogDetail(entry)"
          @keyup.enter="openLogDetail(entry)"
        >
          <div class="more-log-card__header">
            <div
              class="more-log-card__avatar"
              :style="{ backgroundColor: entry.serviceColor }"
            >
              <span>{{ entry.serviceSymbol }}</span>
            </div>
            <div class="more-log-card__title-group">
              <div class="more-log-card__title-line">
                <strong>{{ entry.serviceLabel }}</strong>
                <span class="more-log-card__arrow">→</span>
                <span class="more-log-card__model">{{
                  entry.request_model_name || "未指定模型"
                }}</span>
              </div>
              <div class="more-log-card__meta-line">
                <span class="more-log-card__time">{{ entry.timeLabel }}</span>
                <span class="more-log-chip more-log-card__id"
                  >ID {{ entry.id }}</span
                >

                <span class="more-log-chip"
                  >首响 {{ entry.firstResponseLabel }}</span
                >
                <span class="more-log-chip"
                  >总耗时 {{ entry.latencyLabel }}</span
                >
                <span class="more-log-chip"
                  >输入 {{ entry.inputValueLabel }}</span
                >
                <span class="more-log-chip"
                  >输出 {{ entry.outputValueLabel }}</span
                >
                <span v-if="entry.totalAttemptsLabel" class="more-log-chip">
                  {{ entry.totalAttemptsLabel }}
                </span>
              </div>
            </div>
            <span
              class="more-log-card__status"
              :class="entry.statusClassName"
              >{{ entry.statusLabel }}</span
            >
          </div>

          <p v-if="entry.hasError" class="more-log-card__error">
            {{ entry.errorText }}
          </p>
        </article>

        <button
          v-if="hasMore"
          class="more-log-load-more"
          type="button"
          :disabled="loadingMore"
          @click="loadMoreLogs"
        >
          {{ loadingMore ? "加载中..." : "加载更多" }}
        </button>
      </div>
    </div>

    <Teleport to="body">
      <div
        v-if="isDetailOpen && selectedLog"
        class="more-log-modal"
        @click.self="closeLogDetail"
      >
        <div class="more-log-modal__panel glass-panel">
          <header class="more-log-modal__header">
            <div class="more-log-modal__headline">
              <div
                class="more-log-modal__service"
                :style="{ backgroundColor: selectedLog.serviceColor }"
              >
                <span>{{ selectedLog.serviceSymbol }}</span>
              </div>
              <div>
                <p class="more-log-modal__title">
                  {{ selectedLog.serviceLabel }} →
                  {{ selectedLog.request_model_name || "未指定模型" }}
                </p>
                <span class="more-log-modal__subtitle"
                  >{{ selectedLog.timeLabel }} · ID {{ selectedLog.id }}</span
                >
              </div>
            </div>
            <button
              class="more-log-modal__close"
              type="button"
              @click="closeLogDetail"
            >
              ×
            </button>
          </header>

          <div class="more-log-modal__summary">
            <span class="more-log-chip"
              >状态 {{ selectedLog.statusLabel }}</span
            >
            <span class="more-log-chip"
              >首响 {{ selectedLog.firstResponseLabel }}</span
            >
            <span class="more-log-chip"
              >总耗时 {{ selectedLog.latencyLabel }}</span
            >
            <span class="more-log-chip"
              >输入 {{ selectedLog.inputValueLabel }}</span
            >
            <span class="more-log-chip"
              >输出 {{ selectedLog.outputValueLabel }}</span
            >
            <span v-if="selectedLog.totalAttemptsLabel" class="more-log-chip">{{
              selectedLog.totalAttemptsLabel
            }}</span>
          </div>

          <div class="more-log-modal__body">
            <section class="more-log-detail-pane">
              <div
                class="more-log-detail-pane__header more-log-detail-pane__header--request"
              >
                <span class="more-log-detail-pane__icon">📤</span>
                <h3>请求内容</h3>
              </div>
              <pre class="more-log-detail-pane__content">{{
                selectedLog.requestContentText || "（无请求内容）"
              }}</pre>
            </section>

            <section class="more-log-detail-pane">
              <div
                class="more-log-detail-pane__header more-log-detail-pane__header--response"
              >
                <span
                  class="more-log-detail-pane__icon more-log-detail-pane__icon--response"
                  >📥</span
                >
                <h3>响应内容</h3>
              </div>
              <pre class="more-log-detail-pane__content">{{
                selectedLog.responseContentText || "（无响应内容）"
              }}</pre>
            </section>
          </div>

          <footer v-if="selectedLog.hasError" class="more-log-modal__footer">
            <span class="more-log-modal__footer-label">错误信息</span>
            <p>{{ selectedLog.errorText }}</p>
          </footer>
        </div>
      </div>
    </Teleport>
  </section>
</template>

<script setup>
import { useLogsPage } from "../../composables/useLogsPage";

const {
  logItems,
  loading,
  loadingMore,
  error,
  hasMore,
  selectedServiceType,
  selectedLog,
  isDetailOpen,
  openLogDetail,
  closeLogDetail,
  reloadLogs,
  loadMoreLogs,
  changeServiceType,
} = useLogsPage();
</script>

<style scoped>
.logs-root {
  display: grid;
  gap: 14px;
}

.logs-list {
  display: grid;
  gap: 12px;
}

.logs-list-wrapper {
  position: relative;
}

.more-log-toolbar {
  border-radius: 20px;
  padding: 14px 16px;
  background: linear-gradient(
    180deg,
    rgba(40, 68, 55, 0.78),
    rgba(30, 51, 42, 0.84)
  );
  border: 1px solid rgba(132, 178, 150, 0.18);
  display: flex;
  align-items: center;
  gap: 12px;
}

.more-log-toolbar__filter {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: rgba(220, 241, 229, 0.92);
  font-size: 0.8rem;
  flex-shrink: 0;
}

.more-log-toolbar__filter select {
  min-width: 96px;
  padding: 7px 28px 7px 10px;
  border-radius: 999px;
  border: 1px solid rgba(132, 230, 148, 0.3);
  background: rgba(10, 33, 24, 0.62);
  color: #e8f8ee;
  font-size: 0.78rem;
}

.more-log-toolbar__filter select:focus {
  outline: none;
  border-color: rgba(132, 230, 148, 0.58);
}

.more-log-toolbar__refresh {
  min-width: 76px;
  padding: 8px 14px;
  border-radius: 999px;
  background: linear-gradient(
    180deg,
    rgba(113, 213, 134, 0.92),
    rgba(95, 198, 118, 0.92)
  );
  color: #063821;
  font-weight: 700;
  margin-left: auto;
  flex-shrink: 0;
}

.more-log-state {
  border-radius: 18px;
  padding: 18px;
  color: rgba(228, 245, 235, 0.92);
  text-align: center;
  background: linear-gradient(
    180deg,
    rgba(40, 68, 55, 0.78),
    rgba(30, 51, 42, 0.84)
  );
  border: 1px solid rgba(132, 178, 150, 0.18);
}

.more-log-state--error {
  color: #ffb5b5;
}

.more-log-card {
  border-radius: 20px;
  padding: 16px;
  background: linear-gradient(
    180deg,
    rgba(40, 68, 55, 0.78),
    rgba(30, 51, 42, 0.84)
  );
  border: 1px solid rgba(132, 178, 150, 0.18);
  cursor: pointer;
  transition: transform 150ms ease, border-color 150ms ease,
    box-shadow 150ms ease;
}

.more-log-card:hover {
  transform: translateY(-1px);
  border-color: rgba(132, 230, 148, 0.34);
  box-shadow: 0 14px 28px rgba(8, 25, 19, 0.24);
}

.more-log-card__header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.more-log-card__avatar,
.more-log-modal__service {
  width: 42px;
  height: 42px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 1.05rem;
  font-weight: 700;
  flex-shrink: 0;
}

.more-log-card__title-group {
  min-width: 0;
  flex: 1;
}

.more-log-card__title-line {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.more-log-card__title-line strong {
  color: #f0fbf4;
  font-size: 1rem;
  white-space: nowrap;
}

.more-log-card__arrow {
  color: rgba(173, 209, 188, 0.72);
}

.more-log-card__model {
  color: rgba(205, 231, 216, 0.88);
  font-size: 0.92rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.more-log-card__subline {
  margin-top: 4px;
  display: flex;
  flex-wrap: nowrap;
  align-items: center;
  gap: 4px;
  color: rgba(170, 203, 184, 0.86);
  font-size: 0.76rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.more-log-card__dot {
  color: rgba(132, 230, 148, 0.7);
}

.more-log-card__status {
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 700;
  flex-shrink: 0;
}

.more-log-card__status.is-success {
  color: #9cf0ae;
  background: rgba(132, 230, 148, 0.16);
}

.more-log-card__status.is-warn {
  color: #ffd67a;
  background: rgba(245, 199, 94, 0.16);
}

.more-log-card__status.is-error {
  color: #ff9a9a;
  background: rgba(240, 113, 113, 0.16);
}

.more-log-card__status.is-info {
  color: #7dc8ff;
  background: rgba(96, 182, 255, 0.16);
}

.more-log-modal__summary {
  margin-top: 12px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.more-log-card__meta-line {
  margin-top: 10px;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.more-log-card__time {
  color: rgba(220, 241, 229, 0.92);
  font-size: 0.82rem;
  font-weight: 700;
  letter-spacing: 0.01em;
  white-space: nowrap;
  margin-right: 2px;
}

.more-log-card__id {
  font-weight: 500;
  white-space: nowrap;
}

.more-log-card__meta-line .more-log-chip {
  flex: 0 0 118px;
  justify-content: center;
  box-sizing: border-box;
}

@media (max-width: 860px) {
  .more-log-card__meta-line .more-log-chip {
    flex-basis: 108px;
  }
}

.more-log-chip {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 4px 10px;
  border-radius: 999px;
  background: rgba(132, 230, 148, 0.12);
  border: 1px solid rgba(132, 230, 148, 0.2);
  color: rgba(228, 245, 235, 0.92);
  font-size: 0.74rem;
  line-height: 1.2;
}

.more-log-card__error {
  margin: 10px 0 0;
  padding: 10px 12px;
  border-radius: 12px;
  background: rgba(240, 113, 113, 0.12);
  color: #ffb0b0;
  font-size: 0.82rem;
}

.more-log-load-more {
  justify-self: center;
  min-width: 140px;
  padding: 9px 14px;
  border-radius: 999px;
  border: 1px solid rgba(132, 230, 148, 0.28);
  background: rgba(108, 163, 132, 0.2);
  color: #def5e7;
  font-weight: 600;
  transition: opacity 120ms ease;
}

.more-log-load-more:disabled {
  opacity: 0.72;
  cursor: not-allowed;
}

.more-log-scroll-top-wrap {
  position: fixed;
  left: 50%;
  transform: translateX(-45%);
  bottom: 20px;

  width: min(100%, 1100px);
  display: flex;
  justify-content: flex-end;

  pointer-events: none;
  z-index: 50;
}

.more-log-scroll-top {
  pointer-events: auto;

  width: 56px;
  height: 56px;
  border-radius: 999px;

  border: 1px solid rgba(132, 230, 148, 0.4);
  background: rgba(108, 163, 132, 0.3);
  color: #def5e7;
  font-size: 1.2rem;
  line-height: 1;
  cursor: pointer;
  transition: all 200ms ease;
}

.more-log-scroll-top:hover {
  background: rgba(132, 230, 148, 0.25);
  border-color: rgba(132, 230, 148, 0.6);
  transform: translateY(-2px);
}

.more-log-modal {
  position: fixed;
  inset: 0;
  z-index: 60;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  background: rgba(5, 18, 14, 0.68);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
}

.more-log-modal__panel {
  width: min(1180px, 100%);
  max-height: min(88vh, 920px);
  overflow: hidden;
  border-radius: 24px;
  padding: 16px;
  background: linear-gradient(
    180deg,
    rgba(40, 68, 55, 0.96),
    rgba(20, 40, 32, 0.96)
  );
  border: 1px solid rgba(132, 178, 150, 0.22);
  display: grid;
  gap: 14px;
}

.more-log-modal__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
}

.more-log-modal__headline {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 12px;
}

.more-log-modal__title {
  margin: 0;
  color: #f2fdf5;
  font-size: 1.08rem;
  font-weight: 700;
}

.more-log-modal__subtitle {
  display: inline-block;
  margin-top: 4px;
  color: rgba(173, 209, 188, 0.82);
  font-size: 0.8rem;
}

.more-log-modal__close {
  width: 34px;
  height: 34px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  color: #eaf7ee;
  font-size: 1.4rem;
  line-height: 1;
}

.more-log-modal__body {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
  min-height: 0;
}

.more-log-detail-pane {
  min-width: 0;
  border-radius: 18px;
  padding: 14px;
  background: rgba(108, 163, 132, 0.1);
  border: 1px solid rgba(132, 178, 150, 0.14);
  display: grid;
  grid-template-rows: auto 1fr;
  gap: 10px;
  min-height: 0;
}

.more-log-detail-pane__header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(132, 178, 150, 0.18);
}

.more-log-detail-pane__header h3 {
  margin: 0;
  color: #effcf2;
  font-size: 0.96rem;
}

.more-log-detail-pane__icon {
  font-size: 1rem;
}

.more-log-detail-pane__icon--response {
  color: #c38dff;
}

.more-log-detail-pane__content {
  margin: 0;
  padding: 12px;
  border-radius: 14px;
  background: rgba(11, 24, 19, 0.45);
  color: rgba(235, 248, 239, 0.95);
  font-size: 0.8rem;
  line-height: 1.65;
  white-space: pre-wrap;
  word-break: break-word;
  overflow: auto;
  min-height: 320px;
  max-height: calc(88vh - 220px);
  border: 1px solid rgba(132, 230, 148, 0.12);
}

.more-log-modal__footer {
  display: grid;
  gap: 8px;
  padding-top: 4px;
  border-top: 1px solid rgba(132, 178, 150, 0.16);
}

.more-log-modal__footer-label {
  color: rgba(173, 209, 188, 0.82);
  font-size: 0.76rem;
}

.more-log-modal__footer p {
  margin: 0;
  color: #ffb0b0;
  line-height: 1.55;
}

@media (max-width: 560px) {
  .more-log-toolbar {
    align-items: center;
    flex-wrap: wrap;
  }

  .more-log-toolbar__filter {
    flex: 0 0 auto;
  }

  .more-log-toolbar__refresh {
    margin-left: auto;
  }

  .more-log-card__header {
    align-items: flex-start;
    flex-direction: column;
  }

  .more-log-card__status {
    align-self: flex-start;
  }

  .more-log-modal__body {
    grid-template-columns: 1fr;
  }

  .more-log-modal {
    padding: 12px;
  }

  .more-log-modal__panel {
    max-height: 92vh;
  }
}
</style>