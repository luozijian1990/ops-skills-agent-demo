import { defineStore } from "pinia";
import { ref, reactive } from "vue";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  type: "text" | "tool_call" | "tool_result" | "error";
  toolName?: string;
  toolDesc?: string;
  toolInput?: Record<string, unknown>;
  timestamp: number;
  streaming?: boolean;
  thinking?: string;
}

export interface Skill {
  name: string;
  description: string;
}

export interface ConversationItem {
  id: string;
  title: string;
  source?: string;
  created_at: string | null;
  updated_at: string | null;
}

export const useChatStore = defineStore("chat", () => {
  // 默认使用相对路径，依赖 Nginx 的 proxy_pass 反向代理到 backend
  // 如果本地开发 npm run dev 配置了 VITE_WS_URL 则使用本地的直连代理
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  
  // WebSocket 地址：优先取环境变量，没有则组合当前域名 + /ws/chat
  const defaultWsUrl = `${protocol}//${window.location.host}/ws/chat`;
  const WS_URL = import.meta.env.VITE_WS_URL || defaultWsUrl;
  
  // REST API 地址：优先取环境变量，没有则使用空字符串（即相对路径，由浏览器自动加上当前域名发送给 Nginx）
  const backendUrl = import.meta.env.VITE_API_BASE_URL || "";

  const messages = reactive<ChatMessage[]>([]);
  const isConnected = ref(false);
  const isLoading = ref(false);
  const sessionId = ref<string | null>(null);
  const skills = ref<Skill[]>([]);
  const conversations = ref<ConversationItem[]>([]);
  const currentConversationId = ref<string | null>(null);

  let ws: WebSocket | null = null;
  let messageIdCounter = 0;

  function genId(): string {
    return `msg-${Date.now()}-${messageIdCounter++}`;
  }

  // ─── WebSocket ──────────────────────────────

  function connect() {
    if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
        return;
    }
    
    ws = new WebSocket(WS_URL);

    ws.onopen = () => {
      isConnected.value = true;
      // 如果有当前会话，绑定到该会话
      ws?.send(
        JSON.stringify({
          type: "init",
          conversation_id: currentConversationId.value,
        })
      );
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);

      switch (data.type) {
        case "session":
          sessionId.value = data.session_id;
          if (data.conversation_id) {
            currentConversationId.value = data.conversation_id;
          }
          break;

        case "text":
          messages.push({
            id: genId(),
            role: "assistant",
            content: data.content,
            type: "text",
            timestamp: Date.now(),
          });
          break;

        case "text_delta":
          if (messages.length > 0) {
            const lastMsg = messages[messages.length - 1];
            // 如果最后一条消息是 assistant 的文本消息，直接追加文本
            if (lastMsg && lastMsg.role === "assistant" && lastMsg.type === "text") {
              lastMsg.content += data.content;
              break;
            }
          }
          // 如果没有，或者最后一条不是文本消息（可能是工具调用等），则新建一条
          messages.push({
            id: genId(),
            role: "assistant",
            content: data.content,
            type: "text",
            timestamp: Date.now(),
            streaming: true,
          });
          break;

        case "thinking_delta":
          // 思考内容追加到最后一条助手消息，或新建一条
          if (messages.length > 0) {
            const lastMsg = messages[messages.length - 1];
            if (lastMsg && lastMsg.role === "assistant") {
              lastMsg.thinking = (lastMsg.thinking || "") + data.content;
              break;
            }
          }
          messages.push({
            id: genId(),
            role: "assistant",
            content: "",
            type: "text",
            timestamp: Date.now(),
            streaming: true,
            thinking: data.content,
          });
          break;

        case "tool_call":
          messages.push({
            id: genId(),
            role: "system",
            content: data.tool_desc || `正在执行 Tool: **${data.tool_name}**`,
            type: "tool_call",
            toolName: data.tool_name,
            toolDesc: data.tool_desc,
            toolInput: data.tool_input,
            timestamp: Date.now(),
          });
          break;

        case "tool_result":
          messages.push({
            id: genId(),
            role: "system",
            content: data.result,
            type: "tool_result",
            toolName: data.tool_name,
            timestamp: Date.now(),
          });
          break;

        case "done":
          isLoading.value = false;
          // 标记最后一条助手消息为非流式，触发完整 Markdown 渲染
          if (messages.length > 0) {
            const lastMsg = messages[messages.length - 1];
            if (lastMsg && lastMsg.role === "assistant" && lastMsg.streaming) {
              lastMsg.streaming = false;
            }
          }
          // 刷新会话列表（标题可能更新了）
          fetchConversations();
          break;

        case "error":
          messages.push({
            id: genId(),
            role: "system",
            content: data.content,
            type: "error",
            timestamp: Date.now(),
          });
          isLoading.value = false;
          break;

        case "cleared":
          messages.length = 0;
          break;

        case "title_update":
          // 更新会话列表中的标题
          const conv = conversations.value.find(
            (c) => c.id === data.conversation_id
          );
          if (conv) {
            conv.title = data.title;
          }
          break;
      }
    };

    ws.onclose = () => {
      isConnected.value = false;
      setTimeout(connect, 3000);
    };

    ws.onerror = () => {
      isConnected.value = false;
    };
  }

  function sendMessage(displayContent: string, sendContent?: string) {
    if (!ws || !displayContent.trim()) return;

    messages.push({
      id: genId(),
      role: "user",
      content: displayContent,
      type: "text",
      timestamp: Date.now(),
    });

    isLoading.value = true;
    ws.send(JSON.stringify({ type: "message", content: sendContent || displayContent }));
  }

  function clearChat() {
    if (!ws) return;
    ws.send(JSON.stringify({ type: "clear" }));
  }

  function abortAgent() {
    if (!ws || !isLoading.value) return;
    ws.send(JSON.stringify({ type: "abort" }));
  }

  // ─── REST API: 会话管理 ─────────────────────

  async function fetchConversations(query?: string) {
    try {
      const url = query?.trim()
        ? `${backendUrl}/api/conversations?q=${encodeURIComponent(query.trim())}`
        : `${backendUrl}/api/conversations`;
      const res = await fetch(url);
      conversations.value = await res.json();
    } catch (e) {
      console.warn("获取会话列表失败:", e);
    }
  }

  async function createConversation() {
    try {
      const res = await fetch(`${backendUrl}/api/conversations`, {
        method: "POST",
      });
      const conv: ConversationItem = await res.json();
      conversations.value.unshift(conv);
      await switchConversation(conv.id);
    } catch (e) {
      console.warn("创建会话失败:", e);
    }
  }

  async function switchConversation(convId: string) {
    currentConversationId.value = convId;
    messages.length = 0;

    // 加载历史消息
    try {
      const res = await fetch(
        `${backendUrl}/api/conversations/${convId}/messages`
      );
      const historyMsgs: Array<{
        id: string;
        role: string;
        content: string;
        type: string;
        tool_name: string | null;
        tool_input: Record<string, unknown> | null;
        thinking: string | null;
        created_at: string | null;
      }> = await res.json();

      for (const m of historyMsgs) {
        messages.push({
          id: m.id,
          role: m.role as "user" | "assistant" | "system",
          content: m.role === 'user' 
            ? m.content.replace(/<system_hint>[\s\S]*?<\/system_hint>/g, '').trim() 
            : m.content,
          type: m.type as "text" | "tool_call" | "tool_result" | "error",
          toolName: m.tool_name || undefined,
          toolInput: m.tool_input || undefined,
          thinking: m.thinking || undefined,
          timestamp: m.created_at ? new Date(m.created_at).getTime() : Date.now(),
        });
      }
    } catch (e) {
      console.warn("加载历史消息失败:", e);
    }

    // 重新绑定 WebSocket 到新会话
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(
        JSON.stringify({
          type: "init",
          conversation_id: convId,
        })
      );
    }
  }

  async function deleteConversation(convId: string) {
    try {
      await fetch(`${backendUrl}/api/conversations/${convId}`, {
        method: "DELETE",
      });
      conversations.value = conversations.value.filter((c) => c.id !== convId);

      // 如果删的是当前会话，切换到第一个或清空
      if (currentConversationId.value === convId) {
        if (conversations.value.length > 0 && conversations.value[0]) {
          await switchConversation(conversations.value[0].id);
        } else {
          currentConversationId.value = null;
          messages.length = 0;
        }
      }
    } catch (e) {
      console.warn("删除会话失败:", e);
    }
  }

  // ─── Skills ─────────────────────────────────

  async function fetchSkills() {
    try {
      const res = await fetch(`${backendUrl}/api/skills`);
      skills.value = await res.json();
    } catch (e) {
      console.warn("获取 Skills 列表失败:", e);
    }
  }

  function disconnect() {
    ws?.close();
    ws = null;
  }

  // 组件卸载时不要清理全局连接，所以通常不再这里定义 onUnmounted
  // 但如果你有特殊需求，可以使用 application 级别的钩子

  return {
    messages,
    isConnected,
    isLoading,
    sessionId,
    skills,
    conversations,
    currentConversationId,
    connect,
    sendMessage,
    clearChat,
    abortAgent,
    fetchConversations,
    createConversation,
    switchConversation,
    deleteConversation,
    fetchSkills,
    disconnect
  };
});
