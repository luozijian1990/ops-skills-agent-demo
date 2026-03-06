<script setup lang="ts">
import { computed, ref } from 'vue'
import { marked } from 'marked'
import type { ChatMessage } from '../stores/chat'
import { useChatStore } from '../stores/chat'

const chatStore = useChatStore()

const props = defineProps<{
  message: ChatMessage
}>()

marked.setOptions({ breaks: true, gfm: true })

const renderedContent = computed(() => {
  if (props.message.type === 'tool_result') {
    let content = props.message.content || ''
    return marked.parse(`\`\`\`text\n${content}\n\`\`\``) as string
  }

  const raw = props.message.content || ''

  // 流式输出时使用轻量渲染，避免每次 token 都重新解析完整 Markdown
  if (props.message.streaming) {
    return raw
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/\n/g, '<br/>')
  }

  return marked.parse(raw) as string
})

const toolInputJson = computed(() => {
  if (props.message.type === 'tool_call' && props.message.toolInput) {
    return JSON.stringify(props.message.toolInput, null, 2)
  }
  return ''
})

const linePrefix = computed(() => {
  switch (props.message.role) {
    case 'user': return { icon: '❯', label: 'you', cls: 'prefix-user' }
    case 'assistant': return { icon: '◆', label: 'agent', cls: 'prefix-agent' }
    case 'system': return { icon: '⚙', label: 'sys', cls: 'prefix-sys' }
    default: return { icon: '?', label: '', cls: '' }
  }
})

const toolLabel = computed(() => {
  if (props.message.type === 'tool_call') return `→ ${props.message.toolName}`
  if (props.message.type === 'tool_result') return `← ${props.message.toolName}`
  return ''
})

const showThinking = ref(false)
const showSysContent = ref(false)

const formattedTime = computed(() => {
  if (!props.message.timestamp) return ''
  const d = new Date(props.message.timestamp)
  return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false })
})
</script>

<template>
  <div class="msg" :class="[`msg-${message.role}`, `msg-${message.type}`]">
    <!-- 标签行 -->
    <div class="msg-head">
      <span class="msg-prefix" :class="linePrefix.cls">
        <span v-if="message.type === 'tool_call' && chatStore.isLoading" class="spinner"></span>
        <span v-else>{{ linePrefix.icon }}</span> 
        {{ linePrefix.label }}
      </span>
      <span v-if="toolLabel" class="msg-tool">{{ toolLabel }}</span>
      <span v-if="message.type === 'error'" class="msg-err-badge">ERROR</span>
      <span v-if="formattedTime" class="msg-time">{{ formattedTime }}</span>
    </div>
    <!-- 内容 -->
    <div class="msg-body">
      <!-- Thinking 折叠区 -->
      <div v-if="message.thinking" class="thinking-panel">
        <div class="thinking-header" @click="showThinking = !showThinking">
          <span class="thinking-icon">{{ message.streaming ? '✨' : '💡' }}</span>
          <span class="thinking-label">{{ message.streaming ? '思考中...' : '思考过程' }}</span>
          <span class="thinking-toggle">{{ showThinking ? '▴' : '▾' }}</span>
        </div>
        <div v-if="showThinking" class="thinking-body">
          {{ message.thinking }}
        </div>
      </div>

      <!-- 工具调用：可折叠显示 -->
      <div v-if="message.type === 'tool_call'" class="sys-panel">
        <div class="sys-header" @click="showSysContent = !showSysContent">
          <span class="sys-icon">⚙</span>
          <span class="sys-label">{{ message.content }}</span>
          <span class="sys-toggle">{{ showSysContent ? '▴' : '▾' }}</span>
        </div>
        <div v-if="showSysContent" class="sys-body">
          <pre v-if="toolInputJson"><code>{{ toolInputJson }}</code></pre>
          <span v-else class="sys-empty">无参数</span>
        </div>
      </div>
      <!-- 工具结果：可折叠显示 -->
      <div v-else-if="message.type === 'tool_result'" class="sys-panel sys-panel-result">
        <div class="sys-header" @click="showSysContent = !showSysContent">
          <span class="sys-icon">←</span>
          <span class="sys-label">返回结果：{{ message.toolName }}</span>
          <span class="sys-toggle">{{ showSysContent ? '▴' : '▾' }}</span>
        </div>
        <div v-if="showSysContent" class="sys-body">
          <div v-html="renderedContent"></div>
        </div>
      </div>
      <div v-else v-html="renderedContent"></div>
    </div>
  </div>
</template>

<style scoped>
.msg {
  padding: 6px 0;
  line-height: 1.6;
  animation: fadeIn 0.15s ease;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.msg-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
  font-size: 12px;
}

.spinner {
  display: inline-block;
  width: 10px;
  height: 10px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-radius: 50%;
  border-top-color: var(--cyan);
  animation: spin 1s ease-in-out infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.msg-prefix {
  font-weight: 600;
  font-size: 12px;
}

.prefix-user { color: var(--green); }
.prefix-agent { color: var(--cyan); }
.prefix-sys { color: var(--yellow); }

.msg-tool {
  color: var(--magenta);
  font-size: 11px;
}

.msg-err-badge {
  background: var(--red);
  color: var(--bg);
  font-size: 10px;
  font-weight: 700;
  padding: 1px 6px;
  border-radius: 2px;
  letter-spacing: 0.05em;
}

.msg-time {
  margin-left: auto;
  color: var(--text);
  font-size: 10px;
  opacity: 0.8;
}

/* ─── 内容区 ───── */
.msg-body {
  padding-left: 20px;
  color: var(--text);
}

.msg-user .msg-body {
  color: var(--text-bright);
}

.msg-error .msg-body {
  color: var(--red);
}

/* tool_call / tool_result 紧凑显示 */
.msg-tool_call,
.msg-tool_result {
  padding: 2px 12px;
  margin: 4px 0;
  border-radius: 4px;
}

/* ─── Sys 可折叠面板 ───── */
.sys-panel {
  border: 1px solid var(--border);
  border-radius: 4px;
  overflow: hidden;
  background: var(--bg-light);
  border-left: 2px solid var(--magenta);
}

.sys-panel-result {
  border-left-color: var(--green);
}

.sys-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  cursor: pointer;
  user-select: none;
  font-size: 12px;
  transition: background 0.1s;
}

.sys-header:hover {
  background: var(--bg-hover);
}

.sys-icon {
  font-size: 12px;
  color: var(--yellow);
  flex-shrink: 0;
}

.sys-label {
  flex: 1;
  color: var(--text-dim);
  font-size: 12px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sys-toggle {
  margin-left: auto;
  color: var(--text-dim);
  font-size: 10px;
  flex-shrink: 0;
}

.sys-body {
  padding: 8px 12px;
  border-top: 1px solid var(--border);
  font-size: 12px;
  line-height: 1.5;
  max-height: 400px;
  overflow-y: auto;
}

.sys-body pre {
  margin: 0 !important;
  background: var(--bg) !important;
}

.sys-empty {
  color: var(--text-dim);
  font-style: italic;
}

/* Markdown 样式 — 终端风格 */
.msg-body :deep(p) {
  margin: 0 0 6px 0;
}

.msg-body :deep(p:last-child) {
  margin-bottom: 0;
}

.msg-body :deep(pre) {
  background: var(--bg);
  border: 1px solid var(--border);
  padding: 10px 14px;
  border-radius: 4px;
  overflow-x: auto;
  margin: 6px 0;
  font-size: 12px;
  line-height: 1.5;
}

.msg-body :deep(code) {
  font-family: inherit;
  font-size: 12px;
}

.msg-body :deep(p > code) {
  background: var(--bg-panel);
  color: var(--orange);
  padding: 1px 5px;
  border-radius: 3px;
  border: 1px solid var(--border);
}

.msg-body :deep(ul),
.msg-body :deep(ol) {
  padding-left: 18px;
  margin: 6px 0;
}

.msg-body :deep(li) {
  margin-bottom: 3px;
}

.msg-body :deep(strong) {
  color: var(--text-bright);
  font-weight: 600;
}

.msg-body :deep(a) {
  color: var(--blue);
  text-decoration: none;
}

.msg-body :deep(a:hover) {
  text-decoration: underline;
}

.msg-body :deep(blockquote) {
  border-left: 2px solid var(--text-dim);
  padding-left: 12px;
  margin: 6px 0;
  color: var(--text-dim);
}

.msg-body :deep(h1),
.msg-body :deep(h2),
.msg-body :deep(h3) {
  color: var(--text-bright);
  margin: 8px 0 4px;
}

.msg-body :deep(table) {
  border-collapse: collapse;
  margin: 6px 0;
  font-size: 12px;
}

.msg-body :deep(th),
.msg-body :deep(td) {
  border: 1px solid var(--border);
  padding: 4px 10px;
}

.msg-body :deep(th) {
  background: var(--bg-panel);
  color: var(--text-bright);
}

/* ─── Thinking Panel ───── */
.thinking-panel {
  margin-bottom: 8px;
  border: 1px solid var(--border);
  border-radius: 4px;
  overflow: hidden;
  background: var(--bg-light);
}

.thinking-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  cursor: pointer;
  user-select: none;
  font-size: 12px;
  transition: background 0.1s;
}

.thinking-header:hover {
  background: var(--bg-hover);
}

.thinking-icon {
  font-size: 13px;
}

.thinking-label {
  color: var(--magenta);
  font-weight: 600;
  font-size: 11px;
  letter-spacing: 0.03em;
}

.thinking-toggle {
  margin-left: auto;
  color: var(--text-dim);
  font-size: 10px;
}

.thinking-body {
  padding: 8px 12px;
  border-top: 1px solid var(--border);
  color: var(--text-dim);
  font-size: 12px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 300px;
  overflow-y: auto;
}
</style>
