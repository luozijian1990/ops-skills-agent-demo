<script setup lang="ts">
import type { Skill } from '../stores/chat'

const props = defineProps<{
  skills: Skill[]
}>()
</script>

<template>
  <div class="panel">
    <div v-if="skills.length === 0" class="panel-empty">
      <span class="dim">no skills loaded</span>
    </div>
    <div v-else class="skill-list">
      <div v-for="skill in skills" :key="skill.name" class="skill-item">
        <div class="skill-head">
          <span class="skill-dot">●</span>
          <span class="skill-name">{{ skill.name }}</span>
        </div>
        <div class="skill-desc">{{ skill.description }}</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.panel {
  padding: 10px;
  flex: 1;
  overflow-y: auto;
}

.panel-empty {
  padding: 20px 10px;
  text-align: center;
}

.dim {
  color: var(--text-dim);
  font-size: 12px;
}

.skill-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.skill-item {
  padding: 8px 10px;
  border-radius: 4px;
  transition: background 0.1s;
}

.skill-item:hover {
  background: var(--bg-hover);
}

.skill-head {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 2px;
}

.skill-dot {
  font-size: 8px;
  color: var(--green);
}

.skill-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-bright);
}

.skill-desc {
  font-size: 11px;
  color: var(--text-dim);
  padding-left: 14px;
  line-height: 1.5;
}
</style>
