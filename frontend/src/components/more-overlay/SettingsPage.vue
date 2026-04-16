<template>
  <section class="settings-root">
    <section v-for="section in settingSections" :key="section.id" class="more-setting-card glass-panel">
      <div class="more-card-header">
        <p>{{ section.title }}</p>
        <span>示例配置</span>
      </div>
      <div class="more-setting-list">
        <article v-for="field in section.fields" :key="field.key" class="more-setting-row">
          <span>{{ field.label }}</span>
          <strong>{{ field.value }}</strong>
        </article>
      </div>
    </section>
  </section>
</template>

<script setup>
import { useSettingsPage } from '../../composables/useSettingsPage'

const { settingSections } = useSettingsPage()
</script>

<style scoped>
.settings-root {
  display: grid;
  gap: 16px;
}

.more-setting-card {
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

.more-setting-list {
  margin-top: 10px;
  display: grid;
  gap: 8px;
}

.more-setting-row {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 12px;
  background: rgba(108, 163, 132, 0.12);
}

.more-setting-row span {
  color: rgba(180, 212, 194, 0.92);
}

.more-setting-row strong {
  color: #effbf3;
}
</style>
