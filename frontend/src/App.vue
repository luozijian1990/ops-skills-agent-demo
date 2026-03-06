<script setup lang="ts">
import { ref, nextTick, watch, computed, onMounted } from 'vue'

// 滚动选中项到可见区域
function scrollActiveIntoView() {
  nextTick(() => {
    const popup = document.querySelector('.mentions-popup')
    const active = popup?.querySelector('.mention-item.active') as HTMLElement | null
    if (active && popup) {
      active.scrollIntoView({ block: 'nearest' })
    }
  })
}
import { useChatStore } from './stores/chat'
import MessageBubble from './components/MessageBubble.vue'
import SkillPanel from './components/SkillPanel.vue'
import ConversationList from './components/ConversationList.vue'

const chatStore = useChatStore()
const inputText = ref('')
const chatContainer = ref<HTMLElement | null>(null)
const showSidebar = ref(true)
const isDark = ref(localStorage.getItem('theme') !== 'light')
const showSkills = ref(true)

// Mentions State
const showMentions = ref(false)
const mentionSearch = ref('')
const mentionIndex = ref(0)

const filteredSkills = computed(() => {
  if (!showMentions.value) return []
  const search = mentionSearch.value.toLowerCase()
  return chatStore.skills.filter(s => s.name.toLowerCase().includes(search))
})

function handleInput() {
  const val = inputText.value
  const match = val.match(/@([\w-]*)$/)
  if (match) {
    showMentions.value = true
    mentionSearch.value = match[1] || ''
    mentionIndex.value = 0
  } else {
    showMentions.value = false
  }
}

function selectMention(skillName: string) {
  inputText.value = inputText.value.replace(/@([\w-]*)$/, `@${skillName} `)
  showMentions.value = false
}

onMounted(() => {
  // 应用保存的主题
  document.documentElement.setAttribute('data-theme', isDark.value ? 'dark' : 'light')
  chatStore.connect()
  chatStore.fetchSkills()
  chatStore.fetchConversations()
})

function toggleTheme() {
  isDark.value = !isDark.value
  const theme = isDark.value ? 'dark' : 'light'
  document.documentElement.setAttribute('data-theme', theme)
  localStorage.setItem('theme', theme)
}

function handleSend() {
  const text = inputText.value.trim()
  if (!text || chatStore.isLoading) return

  let finalContent = text
  let implicitPrompt = ""
  
  const matches = text.match(/@([\w-]+)/g)
  if (matches) {
    const mentionedSkills = matches.map(m => m.slice(1)).filter(name => chatStore.skills.some(s => s.name === name))
    if (mentionedSkills.length > 0) {
       const uniqueSkills = [...new Set(mentionedSkills)]
       implicitPrompt = `\n\n<system_hint>\n[系统内部指令：用户已明确指定使用工具 ${uniqueSkills.map(s => '"' + s + '"').join(', ')}。请你必须优先、立即调用这些工具来处理请求，在工具返回结果之前不要做任何多余回答。]\n</system_hint>`
    }
  }

  chatStore.sendMessage(finalContent, finalContent + implicitPrompt)
  inputText.value = ''
  showMentions.value = false
}

function handleKeyDown(e: KeyboardEvent) {
  if (showMentions.value && filteredSkills.value.length > 0) {
    if (e.key === 'ArrowUp') {
      e.preventDefault()
      e.stopPropagation()
      mentionIndex.value = (mentionIndex.value - 1 + filteredSkills.value.length) % filteredSkills.value.length
      scrollActiveIntoView()
      return
    }
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      e.stopPropagation()
      mentionIndex.value = (mentionIndex.value + 1) % filteredSkills.value.length
      scrollActiveIntoView()
      return
    }
    if (e.key === 'Enter' || e.key === 'Tab') {
      e.preventDefault()
      const selected = filteredSkills.value[mentionIndex.value]
      if (selected) {
        selectMention(selected.name)
      }
      return
    }
    if (e.key === 'Escape') {
      showMentions.value = false
      return
    }
  }

  if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {
    e.preventDefault()
    handleSend()
  }
}

// 监听消息数量和最后一条消息内容的变化，实现流式输出时自动滚动到底部
const scrollTrigger = computed(() => {
  const len = chatStore.messages.length
  const lastContent = len > 0 ? chatStore.messages[len - 1]?.content?.length : 0
  return `${len}-${lastContent}`
})

watch(
  scrollTrigger,
  async () => {
    await nextTick()
    if (chatContainer.value) {
      chatContainer.value.scrollTop = chatContainer.value.scrollHeight
    }
  }
)

const statusText = computed(() => {
  if (!chatStore.isConnected) return '● DISCONNECTED'
  if (chatStore.isLoading) return '● RUNNING...'
  return '● CONNECTED'
})

const statusClass = computed(() => {
  if (!chatStore.isConnected) return 'status-off'
  if (chatStore.isLoading) return 'status-busy'
  return 'status-on'
})
</script>

<template>
  <div class="app">
    <!-- 侧边栏 -->
    <aside class="sidebar" v-if="showSidebar">
      <div class="sidebar-head">
        <span class="sidebar-title">CONVERSATIONS</span>
        <button class="sidebar-close" @click="showSidebar = false">✕</button>
      </div>
      <ConversationList
        :conversations="chatStore.conversations"
        :currentId="chatStore.currentConversationId"
        @select="chatStore.switchConversation"
        @create="chatStore.createConversation"
        @delete="chatStore.deleteConversation"
        @search="chatStore.fetchConversations"
      />
    </aside>

    <!-- 主区域 -->
    <main class="main">
      <!-- 顶栏 -->
      <header class="topbar">
        <div class="topbar-left">
          <button v-if="!showSidebar" class="icon-btn" @click="showSidebar = true" title="显示侧栏">☰</button>
          <span class="app-name">claude-agent</span>
          <span class="app-ver">v0.1.0</span>
        </div>
        <div class="topbar-right">
          <span class="status" :class="statusClass">{{ statusText }}</span>
          <button class="theme-btn" @click="toggleTheme" :title="isDark ? '切换浅色' : '切换深色'">
            {{ isDark ? '☀' : '☾' }}
          </button>
          <button class="text-btn" @click="chatStore.clearChat">clear</button>
          <button v-if="!showSkills" class="icon-btn" style="margin-left: 8px;" @click="showSkills = true" title="显示 Skills">⚡</button>
        </div>
      </header>

      <!-- 终端输出区 -->
      <div class="terminal" ref="chatContainer">
        <div v-if="chatStore.messages.length === 0" class="welcome">
          <pre class="ascii-logo">
   _____ _                 _
  / ____| |               | |
 | |    | | __ _ _   _  __| | ___
 | |    | |/ _` | | | |/ _` |/ _ \
 | |____| | (_| | |_| | (_| |  __/
  \_____|_|\__,_|\__,_|\__,_|\___|
          </pre>
          <p class="welcome-text">Claude Agent Terminal — 输入指令开始</p>
          <div class="quick-cmds">
            <button @click="chatStore.sendMessage('帮我查看当前目录下的文件列表')">$ ls -la</button>
            <button @click="chatStore.sendMessage('读取 /etc/hosts 文件的内容')">$ cat /etc/hosts</button>
            <button @click="chatStore.sendMessage('查看当前系统信息')">$ uname -a</button>
          </div>
        </div>

        <MessageBubble
          v-for="msg in chatStore.messages"
          :key="msg.id"
          :message="msg"
        />

        <div v-if="chatStore.isLoading" class="cursor-line">
          <span class="prompt">agent $</span>
          <span class="cursor-blink">█</span>
        </div>
      </div>

      <!-- 输入区 -->
      <div class="input-bar" style="position: relative;">
        <!-- Mentions 弹出框 -->
        <div v-if="showMentions && filteredSkills.length > 0" class="mentions-popup">
          <div 
            v-for="(skill, idx) in filteredSkills" 
            :key="skill.name" 
            class="mention-item" 
            :class="{ 'active': idx === mentionIndex }"
            @click="selectMention(skill.name)"
            @mouseenter="mentionIndex = idx"
          >
            <span class="mention-name">@{{ skill.name }}</span>
            <span class="mention-desc">{{ skill.description }}</span>
          </div>
        </div>

        <span class="input-prompt">❯</span>
        <textarea
          v-model="inputText"
          @keydown="handleKeyDown"
          @input="handleInput"
          placeholder="输入 @ 指定工具..."
          rows="3"
          :disabled="!chatStore.isConnected"
        ></textarea>
        <button
          v-if="chatStore.isLoading"
          class="send-btn stop-btn"
          @click="chatStore.abortAgent()"
        >
          ■ STOP
        </button>
        <button
          v-else
          class="send-btn"
          @click="handleSend"
          :disabled="!inputText.trim() || !chatStore.isConnected"
        >
          RUN
        </button>
      </div>
    </main>

    <!-- 右侧边栏 (Skills) -->
    <aside class="sidebar sidebar-right" v-if="showSkills">
      <div class="sidebar-head">
        <span class="sidebar-title">SKILLS ({{ chatStore.skills.length }})</span>
        <button class="sidebar-close" @click="showSkills = false">✕</button>
      </div>
      <div class="section-body full-height">
        <SkillPanel :skills="chatStore.skills" />
      </div>
    </aside>
  </div>
</template>

<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;600;700&display=swap');

/* ─── 深色主题 (Tokyo Night) ───── */
:root,
[data-theme="dark"] {
  --bg: #1a1b26;
  --bg-light: #1f2133;
  --bg-panel: #24283b;
  --bg-hover: #292e42;
  --bg-input: #1a1b26;
  --text: #a9b1d6;
  --text-bright: #c0caf5;
  --text-dim: #565f89;
  --green: #9ece6a;
  --blue: #7aa2f7;
  --cyan: #7dcfff;
  --yellow: #e0af68;
  --red: #f7768e;
  --magenta: #bb9af7;
  --orange: #ff9e64;
  --border: #292e42;
  --selection: rgba(122, 162, 247, 0.15);
}

/* ─── 浅色主题 ───── */
[data-theme="light"] {
  --bg: #fafafa;
  --bg-light: #f0f0f0;
  --bg-panel: #ffffff;
  --bg-hover: #e8e8e8;
  --bg-input: #ffffff;
  --text: #4a4a4a;
  --text-bright: #1a1a1a;
  --text-dim: #999999;
  --green: #50a14f;
  --blue: #4078f2;
  --cyan: #0184bc;
  --yellow: #c18401;
  --red: #e45649;
  --magenta: #a626a4;
  --orange: #d75f00;
  --border: #d4d4d4;
  --selection: rgba(64, 120, 242, 0.1);
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'JetBrains Mono', 'SF Mono', 'Fira Code', 'Cascadia Code', monospace;
  background: var(--bg);
  color: var(--text);
  font-size: 13px;
  -webkit-font-smoothing: antialiased;
}

#app {
  width: 100vw;
  height: 100vh;
}

.app {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

/* ─── Sidebar ───── */
.sidebar {
  width: 260px;
  background: var(--bg-panel);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.sidebar-right {
  border-right: none;
  border-left: 1px solid var(--border);
}

.sidebar-section {
  border-top: 1px solid var(--border);
}

.section-toggle {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 8px 14px;
  font-size: 11px;
  font-weight: 600;
  font-family: inherit;
  letter-spacing: 0.08em;
  color: var(--text-dim);
  background: none;
  border: none;
  cursor: pointer;
  transition: color 0.1s;
}

.section-toggle:hover {
  color: var(--text);
}

.skill-count {
  font-size: 10px;
  background: var(--bg-hover);
  color: var(--text-dim);
  padding: 1px 6px;
  border-radius: 8px;
}

.section-body {
  max-height: 200px;
  overflow-y: auto;
}

.full-height {
  flex: 1;
  max-height: none;
  overflow-y: auto;
}

.sidebar-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  border-bottom: 1px solid var(--border);
}

.sidebar-title {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.12em;
  color: var(--text-dim);
}

.sidebar-close {
  background: none;
  border: none;
  color: var(--text-dim);
  cursor: pointer;
  font-size: 12px;
  padding: 2px 4px;
}

.sidebar-close:hover {
  color: var(--text);
}

/* ─── Main ───── */
.main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

/* ─── Topbar ───── */
.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  border-bottom: 1px solid var(--border);
  background: var(--bg-panel);
  height: 40px;
}

.topbar-left, .topbar-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.icon-btn {
  background: none;
  border: none;
  color: var(--text-dim);
  cursor: pointer;
  font-size: 16px;
  padding: 2px;
}

.icon-btn:hover {
  color: var(--text);
}

.app-name {
  color: var(--cyan);
  font-weight: 600;
  font-size: 13px;
}

.app-ver {
  color: var(--text-dim);
  font-size: 11px;
}

.status {
  font-size: 11px;
  font-weight: 500;
}

.status-on { color: var(--green); }
.status-busy { color: var(--yellow); animation: blink 1s step-end infinite; }
.status-off { color: var(--red); }

@keyframes blink {
  50% { opacity: 0.4; }
}

.text-btn {
  background: none;
  border: 1px solid var(--border);
  color: var(--text-dim);
  padding: 3px 10px;
  font-size: 11px;
  font-family: inherit;
  cursor: pointer;
  border-radius: 3px;
}

.text-btn:hover {
  color: var(--text);
  border-color: var(--text-dim);
}

.theme-btn {
  background: none;
  border: 1px solid var(--border);
  color: var(--yellow);
  padding: 3px 8px;
  font-size: 14px;
  cursor: pointer;
  border-radius: 3px;
  transition: all 0.15s;
  line-height: 1;
}

.theme-btn:hover {
  border-color: var(--yellow);
  background: var(--bg-hover);
}

/* ─── Terminal ───── */
.terminal {
  flex: 1;
  overflow-y: auto;
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  scroll-behavior: smooth;
}

.terminal::-webkit-scrollbar {
  width: 6px;
}

.terminal::-webkit-scrollbar-track {
  background: transparent;
}

.terminal::-webkit-scrollbar-thumb {
  background: var(--border);
  border-radius: 3px;
}

/* ─── Welcome ───── */
.welcome {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 16px;
}

.ascii-logo {
  color: var(--cyan);
  font-size: 11px;
  line-height: 1.3;
  opacity: 0.6;
}

.welcome-text {
  color: var(--text-dim);
  font-size: 13px;
}

.quick-cmds {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}

.quick-cmds button {
  padding: 6px 14px;
  font-size: 12px;
  font-family: inherit;
  background: var(--bg-panel);
  color: var(--green);
  border: 1px solid var(--border);
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.15s;
}

.quick-cmds button:hover {
  background: var(--bg-hover);
  border-color: var(--green);
}

/* ─── Cursor ───── */
.cursor-line {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
  font-size: 13px;
}

.prompt {
  color: var(--magenta);
}

.cursor-blink {
  color: var(--text-bright);
  animation: cursor 1s step-end infinite;
}

@keyframes cursor {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

/* ─── Input Bar ───── */
/* ─── Mentions Popup ───── */
.mentions-popup {
  position: absolute;
  bottom: 100%;
  left: 30px;
  background: var(--bg-panel);
  border: 1px solid var(--border);
  border-radius: 6px;
  box-shadow: 0 -4px 12px rgba(0, 0, 0, 0.1);
  margin-bottom: 8px;
  max-height: 200px;
  max-width: 400px;
  min-width: 250px;
  overflow-y: auto;
  z-index: 1000;
  padding: 4px;
}

.mention-item {
  padding: 6px 12px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  cursor: pointer;
  border-radius: 4px;
}

.mention-item.active {
  background: var(--bg-hover);
}

.mention-name {
  color: var(--cyan);
  font-weight: 600;
  font-size: 13px;
}

.mention-desc {
  color: var(--text-dim);
  font-size: 11px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.input-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  border-top: 1px solid var(--border);
  background: var(--bg-panel);
}

.input-prompt {
  color: var(--green);
  font-size: 16px;
  font-weight: 700;
  flex-shrink: 0;
}

.input-bar textarea {
  flex: 1;
  background: var(--bg-input);
  border: 1px solid var(--border);
  color: var(--text-bright);
  font-size: 13px;
  font-family: inherit;
  padding: 12px 14px;
  border-radius: 4px;
  resize: vertical;
  outline: none;
  min-height: 60px;
  max-height: 250px;
  line-height: 1.5;
}

.input-bar textarea:focus {
  border-color: var(--blue);
}

.input-bar textarea::placeholder {
  color: var(--text-dim);
}

.send-btn {
  padding: 8px 16px;
  font-size: 11px;
  font-weight: 700;
  font-family: inherit;
  letter-spacing: 0.08em;
  background: var(--green);
  color: var(--bg);
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.15s;
  flex-shrink: 0;
}

.send-btn:hover:not(:disabled) {
  filter: brightness(1.1);
}

.send-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.stop-btn {
  background: var(--red) !important;
  color: #fff !important;
  animation: pulse-stop 1.5s ease-in-out infinite;
}

.stop-btn:hover {
  filter: brightness(1.2) !important;
}

@keyframes pulse-stop {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}
</style>
