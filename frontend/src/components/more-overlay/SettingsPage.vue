<template>
  <section class="settings-root">
    <div v-if="error" class="settings-state settings-state--error glass-panel">{{ error }}</div>

    <Transition name="settings-toast">
      <div
        v-if="successTip"
        :key="successTipKey"
        class="settings-toast glass-panel"
        :style="{ '--toast-duration': `${toastDurationMs}ms` }"
      >
        {{ successTip }}
      </div>
    </Transition>

    <div class="settings-columns">
      <div class="settings-column">
        <section v-for="card in leftCards" :key="card.id" class="settings-card glass-panel">
          <header class="settings-card__head">
            <div>
              <h4>{{ card.title }}</h4>
              <p>{{ card.description }}</p>
            </div>
            <button
              type="button"
              class="settings-btn"
              :disabled="savingCardId === card.id || loading"
              @click="saveCardSettings(card.id)"
            >
              {{ savingCardId === card.id ? '保存中...' : '保存' }}
            </button>
          </header>

          <div class="settings-fields">
            <label v-for="field in card.fields" :key="field.key" class="settings-field">
              <span v-if="field.kind !== 'longtext-modal'">{{ field.displayLabel }}</span>

              <template v-if="field.kind === 'boolean'">
                <select v-model="formValues[field.key]" class="settings-input">
                  <option :value="true">开启</option>
                  <option :value="false">关闭</option>
                </select>
              </template>

              <template v-else-if="field.kind === 'longtext-modal'">
                <div class="settings-prompt-editor">
                  <div class="settings-prompt-editor__head">
                    <span>{{ field.displayLabel }}</span>
                    <button type="button" class="settings-btn settings-btn--mini" @click="openPromptEditor(field)">编辑提示词</button>
                  </div>
                  <p class="settings-prompt-preview">{{ getPromptPreview(field.key) }}</p>
                </div>
              </template>

              <template v-else>
                <input
                  v-model="formValues[field.key]"
                  class="settings-input"
                  :type="field.kind === 'password' ? 'password' : field.kind === 'number' ? 'number' : 'text'"
                  :min="field.min"
                  :step="field.step"
                  :placeholder="field.placeholder"
                />
              </template>
            </label>
          </div>
        </section>
      </div>

      <div class="settings-column">
        <section v-for="card in rightCards" :key="card.id" class="settings-card glass-panel">
          <header class="settings-card__head">
            <div>
              <h4>{{ card.title }}</h4>
              <p>{{ card.description }}</p>
            </div>
            <button
              type="button"
              class="settings-btn"
              :disabled="savingCardId === card.id || loading"
              @click="saveCardSettings(card.id)"
            >
              {{ savingCardId === card.id ? '保存中...' : '保存' }}
            </button>
          </header>

          <div class="settings-fields">
            <label v-for="field in card.fields" :key="field.key" class="settings-field">
              <div class="settings-field__label-row">
                <span>{{ field.displayLabel }}</span>
                <small v-if="field.sensitive && field.hasValue" class="settings-sensitive">已配置</small>
              </div>

              <template v-if="field.kind === 'boolean'">
                <select v-model="formValues[field.key]" class="settings-input">
                  <option :value="true">开启</option>
                  <option :value="false">关闭</option>
                </select>
              </template>

              <template v-else-if="field.kind === 'longtext-modal'">
                <div class="settings-prompt-editor">
                  <div class="settings-prompt-editor__head">
                    <span>{{ field.displayLabel }}</span>
                    <button type="button" class="settings-btn settings-btn--mini" @click="openPromptEditor(field)">编辑提示词</button>
                  </div>
                  <p class="settings-prompt-preview">{{ getPromptPreview(field.key) }}</p>
                </div>
              </template>

              <template v-else>
                <input
                  v-model="formValues[field.key]"
                  class="settings-input"
                  :type="field.kind === 'password' ? 'password' : field.kind === 'number' ? 'number' : 'text'"
                  :min="field.min"
                  :step="field.step"
                  :placeholder="field.placeholder"
                />
              </template>
            </label>
          </div>
        </section>
      </div>
    </div>

    <Teleport to="body">
      <div v-if="promptDialogVisible" class="settings-prompt-modal" @click.self="closePromptEditor">
        <div class="settings-prompt-modal__panel glass-panel">
          <header class="settings-prompt-modal__header">
            <h4>{{ promptDialogTitle }}</h4>
            <button type="button" class="settings-prompt-modal__close" @click="closePromptEditor">×</button>
          </header>

          <textarea
            v-model="promptDialogDraft"
            class="settings-prompt-modal__textarea"
            placeholder="请输入提示词内容"
          />

          <footer class="settings-prompt-modal__footer">
            <button type="button" class="settings-btn settings-btn--subtle" @click="closePromptEditor">取消</button>
            <button type="button" class="settings-btn" @click="applyPromptEditor">应用</button>
          </footer>
        </div>
      </div>
    </Teleport>
  </section>
</template>

<script setup>
import { onActivated, onMounted } from 'vue'
import { useSettingsPage } from '../../composables/useSettingsPage'

const {
  loading,
  error,
  successTip,
  successTipKey,
  toastDurationMs,
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
} = useSettingsPage()

onMounted(() => {
  loadSettings()
})

onActivated(() => {
  loadSettings()
})
</script>

<style scoped>
.settings-root {
  display: grid;
  gap: 14px;
}

.settings-toast {
  position: fixed;
  right: 30px;
  top: 86px;
  z-index: 60;
  width: 300px;
  min-height: 52px;
  display: flex;
  align-items: center;
  border-radius: 12px;
  padding: 12px 14px 10px;
  overflow: hidden;
  border: 1px solid rgba(126, 210, 146, 0.3);
  color: #ddfbe4;
  font-size: 0.9rem;
  line-height: 1.35;
  background: linear-gradient(180deg, rgba(32, 88, 53, 0.86), rgba(25, 70, 42, 0.9));
  box-shadow: 0 10px 24px rgba(9, 34, 22, 0.45);
}

.settings-toast::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  width: 100%;
  height: 3px;
  background: linear-gradient(90deg, rgba(189, 255, 207, 0.95), rgba(115, 220, 146, 0.9));
  transform-origin: left center;
  animation: settings-toast-progress var(--toast-duration) linear forwards;
}

.settings-toast-enter-active,
.settings-toast-leave-active {
  transition: opacity 220ms ease, transform 220ms ease;
}

.settings-toast-enter-from,
.settings-toast-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

@keyframes settings-toast-progress {
  from {
    transform: scaleX(1);
  }
  to {
    transform: scaleX(0);
  }
}

.settings-state {
  border-radius: 16px;
  padding: 10px 14px;
  font-size: 0.9rem;
}

.settings-state--error {
  border: 1px solid rgba(255, 124, 124, 0.36);
  color: #ffd0d0;
  background: linear-gradient(180deg, rgba(92, 32, 32, 0.8), rgba(73, 26, 26, 0.86));
}

.settings-state--ok {
  border: 1px solid rgba(126, 210, 146, 0.3);
  color: #ddfbe4;
  background: linear-gradient(180deg, rgba(32, 88, 53, 0.75), rgba(25, 70, 42, 0.82));
}

.settings-columns {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.settings-column {
  display: grid;
  gap: 14px;
  align-content: start;
}

.settings-card {
  border-radius: 20px;
  padding: 14px;
  background: linear-gradient(180deg, rgba(37, 63, 51, 0.82), rgba(28, 47, 39, 0.9));
  border: 1px solid rgba(126, 188, 154, 0.2);
}

.settings-card__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}

.settings-card__head h4 {
  margin: 0;
  color: #ebf8f0;
  font-size: 0.98rem;
}

.settings-card__head p {
  margin: 3px 0 0;
  color: rgba(187, 222, 201, 0.84);
  font-size: 0.78rem;
}

.settings-fields {
  margin-top: 12px;
  display: grid;
  gap: 10px;
}

.settings-field {
  display: grid;
  gap: 6px;
}

.settings-field span {
  color: rgba(202, 232, 213, 0.95);
  font-size: 0.83rem;
  font-weight: 600;
}

.settings-field__label-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.settings-sensitive {
  color: rgba(129, 215, 156, 0.95);
  font-size: 0.75rem;
}

.settings-input {
  width: 100%;
  min-height: 36px;
  border-radius: 10px;
  border: 1px solid rgba(125, 180, 151, 0.24);
  padding: 8px 10px;
  color: #e9f5ee;
  background: rgba(18, 35, 28, 0.45);
  outline: none;
  transition: border-color 160ms ease, box-shadow 160ms ease, background 160ms ease;
}

.settings-input:focus {
  border-color: rgba(137, 224, 169, 0.56);
  box-shadow: 0 0 0 2px rgba(123, 212, 153, 0.22);
  background: rgba(21, 40, 32, 0.62);
}

.settings-prompt-editor {
  display: grid;
  gap: 8px;
}

.settings-prompt-editor__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.settings-prompt-editor__head span {
  color: rgba(202, 232, 213, 0.95);
  font-size: 0.83rem;
  font-weight: 600;
}

.settings-prompt-preview {
  margin: 0;
  font-size: 0.77rem;
  line-height: 1.45;
  color: rgba(179, 219, 197, 0.9);
}

.settings-btn {
  border-radius: 10px;
  min-height: 34px;
  padding: 0 14px;
  background: linear-gradient(180deg, rgba(96, 189, 123, 0.95), rgba(74, 162, 103, 0.94));
  color: #093a23;
  font-size: 0.84rem;
  font-weight: 700;
  transition: transform 160ms ease, box-shadow 160ms ease, opacity 160ms ease;
}

.settings-btn:hover:enabled {
  transform: translateY(-1px);
  box-shadow: 0 8px 16px rgba(38, 91, 59, 0.35);
}

.settings-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.settings-btn--mini {
  min-height: 30px;
  width: fit-content;
  padding: 0 10px;
  font-size: 0.78rem;
}

.settings-btn--subtle {
  background: rgba(108, 159, 130, 0.25);
  color: #d8f2e2;
  border: 1px solid rgba(131, 207, 160, 0.32);
}

.settings-prompt-modal {
  position: fixed;
  inset: 0;
  z-index: 80;
  background: rgba(6, 20, 14, 0.56);
  display: grid;
  place-items: center;
  padding: 16px;
}

.settings-prompt-modal__panel {
  width: min(860px, calc(100vw - 32px));
  border-radius: 20px;
  padding: 14px;
  background: linear-gradient(180deg, rgba(30, 57, 45, 0.96), rgba(20, 42, 33, 0.98));
  border: 1px solid rgba(130, 200, 163, 0.24);
  display: grid;
  gap: 12px;
}

.settings-prompt-modal__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.settings-prompt-modal__header h4 {
  margin: 0;
  color: #e9f7ef;
}

.settings-prompt-modal__close {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: rgba(108, 159, 130, 0.25);
  color: #d9f5e6;
  border: 1px solid rgba(130, 200, 163, 0.3);
}

.settings-prompt-modal__textarea {
  min-height: 280px;
  width: 100%;
  resize: vertical;
  border-radius: 12px;
  border: 1px solid rgba(125, 180, 151, 0.24);
  padding: 10px 12px;
  color: #e9f5ee;
  background: rgba(13, 30, 24, 0.68);
  outline: none;
  line-height: 1.5;
}

.settings-prompt-modal__textarea:focus {
  border-color: rgba(137, 224, 169, 0.56);
  box-shadow: 0 0 0 2px rgba(123, 212, 153, 0.22);
}

.settings-prompt-modal__footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

@media (max-width: 960px) {
  .settings-columns {
    grid-template-columns: 1fr;
  }

  .settings-toast {
    right: 14px;
    top: 72px;
    left: 14px;
    width: auto;
  }
}
</style>
