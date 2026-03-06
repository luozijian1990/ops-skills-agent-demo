<script setup lang="ts">
import { ref, watch } from 'vue'
import type { ConversationItem } from '../stores/chat'

defineProps<{
  conversations: ConversationItem[]
  currentId: string | null
}>()

const emit = defineEmits<{
  (e: 'select', id: string): void
  (e: 'create'): void
  (e: 'delete', id: string): void
  (e: 'search', query: string): void
}>()

const searchQuery = ref('')
let debounceTimer: ReturnType<typeof setTimeout> | null = null

watch(searchQuery, (val) => {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    emit('search', val)
  }, 300)
})

function formatTime(iso: string | null): string {
  if (!iso) return ''
  const d = new Date(iso)
  const now = new Date()
  const diff = now.getTime() - d.getTime()

  if (diff < 60_000) return '刚刚'
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)}分钟前`
  if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)}小时前`
  if (diff < 604_800_000) return `${Math.floor(diff / 86_400_000)}天前`

  return `${d.getMonth() + 1}/${d.getDate()}`
}
</script>

<template>
  <div class="conv-list">
    <button class="new-conv" @click="emit('create')">
      <span class="plus">+</span>
      <span>新对话</span>
    </button>

    <div class="search-box">
      <input
        v-model="searchQuery"
        type="text"
        class="search-input"
        placeholder="搜索历史对话..."
      />
      <span class="search-icon">🔍</span>
    </div>

    <div class="list">
      <div
        v-for="conv in conversations"
        :key="conv.id"
        class="conv-item"
        :class="{ active: conv.id === currentId }"
        @click="emit('select', conv.id)"
      >
        <div class="conv-info">
          <div class="title-wrapper">
            <span v-if="conv.source === 'api'" class="api-badge">API</span>
            <span class="conv-title">{{ conv.title || '新对话' }}</span>
          </div>
          <span class="conv-time">{{ formatTime(conv.updated_at) }}</span>
        </div>
        <button
          class="del-btn"
          @click.stop="emit('delete', conv.id)"
          title="删除"
        >✕</button>
      </div>
    </div>

    <div v-if="conversations.length === 0" class="empty">
      <span class="dim">{{ searchQuery ? '未找到匹配的对话' : '暂无会话' }}</span>
    </div>
  </div>
</template>

<style scoped>
.conv-list {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
}

.search-box {
  padding: 0 10px 6px;
  position: relative;
}

.search-input {
  width: 100%;
  padding: 6px 30px 6px 10px;
  font-size: 12px;
  font-family: inherit;
  background: var(--bg-input);
  color: var(--text-bright);
  border: 1px solid var(--border);
  border-radius: 4px;
  outline: none;
  transition: border-color 0.15s;
}

.search-icon {
  position: absolute;
  right: 18px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 12px;
  pointer-events: none;
  opacity: 0.5;
}

.search-input:focus {
  border-color: var(--blue);
}

.search-input::placeholder {
  color: var(--text-dim);
}

.new-conv {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 10px 10px 6px;
  padding: 7px 12px;
  font-size: 12px;
  font-family: inherit;
  background: transparent;
  color: var(--green);
  border: 1px dashed var(--border);
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.15s;
}

.new-conv:hover {
  border-color: var(--green);
  background: var(--bg-hover);
}

.plus {
  font-size: 14px;
  font-weight: 700;
}

.list {
  flex: 1;
  overflow-y: auto;
  padding: 0 6px;
}

.list::-webkit-scrollbar { width: 4px; }
.list::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px; }

.conv-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 10px;
  margin: 1px 0;
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.1s;
}

.conv-item:hover {
  background: var(--bg-hover);
}

.conv-item.active {
  background: var(--selection);
  border-left: 2px solid var(--cyan);
  padding-left: 8px;
}

.conv-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.conv-title {
  font-size: 12px;
  color: var(--text-bright);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
}

.title-wrapper {
  display: flex;
  align-items: center;
  gap: 4px;
  overflow: hidden;
}

.api-badge {
  font-size: 9px;
  background: var(--blue);
  color: #fff;
  padding: 2px 4px;
  border-radius: 3px;
  line-height: 1;
  font-weight: 600;
  flex-shrink: 0;
}

.conv-time {
  font-size: 10px;
  color: var(--text-dim);
}

.del-btn {
  background: none;
  border: none;
  color: var(--text-dim);
  cursor: pointer;
  font-size: 10px;
  padding: 2px 4px;
  border-radius: 2px;
  opacity: 0;
  transition: all 0.1s;
}

.conv-item:hover .del-btn {
  opacity: 1;
}

.del-btn:hover {
  color: var(--red);
  background: var(--bg-hover);
}

.empty {
  padding: 20px;
  text-align: center;
}

.dim {
  color: var(--text-dim);
  font-size: 12px;
}
</style>
