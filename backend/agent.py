"""Claude Agent 核心模块 (DeepAgents 版)

使用 langchain-ai/deepagents 的 create_deep_agent 实现 Agent 对话。
提供了文件读写、Shell 执行、Skills 读取等能力，并支持真正的流式输出。
"""

import os
from pathlib import Path
from typing import Any, Callable, Awaitable

from langchain_core.messages import HumanMessage
from langchain_anthropic import ChatAnthropic
from deepagents import create_deep_agent
from deepagents.backends import LocalShellBackend, CompositeBackend, StoreBackend
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.store.postgres import AsyncPostgresStore
from psycopg_pool import AsyncConnectionPool

from config import MODEL_NAME, PROJECT_DIR, MAX_TURNS, DATABASE_URL_SYNC
from utils.logger import logger


# 用于推送给前端的事件类型
EVENT_TEXT = "text"
EVENT_TEXT_DELTA = "text_delta"
EVENT_THINKING_DELTA = "thinking_delta"
EVENT_TOOL_CALL = "tool_call"
EVENT_TOOL_RESULT = "tool_result"
EVENT_DONE = "done"
EVENT_ERROR = "error"


# ─── 自定义本地 Tools ──────────────────────────────────────────

# 根据 DeepAgents 的设计，我们不再需要自定义 skill 读取工具，
# create_deep_agent 会通过 skills=["./skills/"] 参数原生自动加载和管理。

# ─── 核心引擎 ──────────────────────────────────────────────────


def _build_shell_env_overrides() -> dict[str, str]:
    """为 LocalShellBackend 注入可复用环境:

    1. 继承当前进程环境变量（含 .env 读取结果）
    2. 优先把项目虚拟环境目录加入 PATH，确保 skills 里的 python 命令可用
    """
    overrides: dict[str, str] = {}
    current_path = os.environ.get("PATH", "")
    project_dir = Path(PROJECT_DIR)

    candidate_bins = [
        project_dir / ".venv" / "bin",  # backend/.venv/bin
        project_dir.parent / ".venv" / "bin",  # repo/.venv/bin
    ]
    existing_bins = [str(p) for p in candidate_bins if p.exists()]

    if existing_bins:
        path_items = existing_bins + ([current_path] if current_path else [])
        overrides["PATH"] = ":".join(path_items)
        overrides["VIRTUAL_ENV"] = str(Path(existing_bins[0]).parent)

    return overrides


# ─── 持久化存储（延迟异步初始化） ──────────────────────────────

# 异步版本需要在 async 上下文中初始化，在 FastAPI startup 中调用 init_pg()
_pg_saver: AsyncPostgresSaver | None = None
_pg_store: AsyncPostgresStore | None = None
_agent = None


async def init_pg():
    """在 FastAPI startup 中调用，异步初始化 PostgresSaver 和 PostgresStore"""
    global _pg_saver, _pg_store, _agent

    # 手动创建连接池，由我们控制生命周期（不使用 from_conn_string 的上下文管理器）
    pool = AsyncConnectionPool(conninfo=DATABASE_URL_SYNC, open=False)
    await pool.open()

    # checkpointer: Agent 对话上下文跨重启保留
    _pg_saver = AsyncPostgresSaver(pool)
    await _pg_saver.setup()

    # store: Agent 长期记忆，跨会话共享
    _pg_store = AsyncPostgresStore(pool)
    await _pg_store.setup()

    logger.info("PostgresSaver + PostgresStore 初始化完成")

    # ─── 初始化 Agent ──────────────────────────────────────────
    _llm = ChatAnthropic(
        model_name=MODEL_NAME,
        temperature=1,  # extended thinking 要求 temperature=1
        thinking={"type": "enabled", "budget_tokens": 10000},
    )

    _agent = create_deep_agent(
        model=_llm,
        memory=["./AGENTS.md"],
        skills=["./skills/"],
        store=_pg_store,
        backend=_make_backend,
        checkpointer=_pg_saver,
    )
    logger.info("Deep Agent 初始化完成")


# ─── Backend 路由 ──────────────────────────────────────────────


def _make_backend(runtime):
    """CompositeBackend 路由:
    - /memories/ 路径 → StoreBackend (持久化存储，跨会话共享)
    - 其他路径 → LocalShellBackend (本地文件系统)
    """
    return CompositeBackend(
        default=LocalShellBackend(
            root_dir=PROJECT_DIR,
            virtual_mode=False,
            inherit_env=True,
            env=_build_shell_env_overrides(),
        ),
        routes={
            "/memories/": StoreBackend(runtime),
        },
    )


async def run_agent(
    user_message: str,
    conv_id: str,
    on_event: Callable[[dict[str, Any]], Awaitable[None]],
):
    """
    使用 deepagents (LangGraph) 运行 Agent，并处理细粒度的流式事件。
    """
    inputs = {"messages": [HumanMessage(content=user_message)]}

    try:
        # 传入带有 thread_id 的 config，让 MemorySaver 为同一个对话保持上下文
        # recursion_limit 控制 LangGraph 图的最大递归步数（每轮 Agent 循环约消耗 2-4 步）
        config = {
            "configurable": {"thread_id": conv_id},
            "recursion_limit": MAX_TURNS * 4,
        }
        # 使用 astream_events 获取逐 token 的细粒度流
        async for event in _agent.astream_events(inputs, config=config, version="v2"):
            kind = event["event"]
            name = event.get("name", "")

            # --- 文本 Token 流式输出 ---
            if kind == "on_chat_model_stream":
                chunk = event["data"]["chunk"]
                content = chunk.content
                if content:
                    # content 可能是字符串，也可能是包含 text block/thinking block 字典的列表
                    text_delta = ""
                    if isinstance(content, str):
                        text_delta = content
                    if isinstance(content, list):
                        for block in content:
                            logger.debug(
                                f"Stream block type={type(block).__name__}, keys={block.keys() if isinstance(block, dict) else 'N/A'}, block={str(block)[:200]}"
                            )
                            if isinstance(block, dict):
                                if "text" in block:
                                    text_delta += block.get("text", "")
                                elif "thinking" in block:
                                    thinking_text = block.get("thinking", "")
                                    if thinking_text:
                                        await on_event(
                                            {
                                                "type": EVENT_THINKING_DELTA,
                                                "content": thinking_text,
                                            }
                                        )
                            elif isinstance(block, str):
                                text_delta += block

                    if text_delta:
                        await on_event(
                            {"type": EVENT_TEXT_DELTA, "content": text_delta}
                        )

            # --- 工具调用开始 ---
            elif kind == "on_tool_start":
                tool_input = event["data"].get("input", {})
                tool_desc = f"正在调用工具: {name}..."
                if name == "execute":
                    tool_desc = "正在打开终端执行 Shell 命令..."
                elif name in ["read_file", "ls", "glob", "grep"]:
                    tool_desc = "正在检索项目文件..."
                elif name in ["write_file", "edit_file", "write_todos"]:
                    tool_desc = "正在修改本地代码/文件..."

                await on_event(
                    {
                        "type": EVENT_TOOL_CALL,
                        "tool_name": name,
                        "tool_desc": tool_desc,
                        "tool_input": tool_input,
                    }
                )

            # --- 工具调用结束 ---
            elif kind == "on_tool_end":
                output = event["data"].get("output", "")

                # output 可能是一个 Langchain ToolMessage 对象
                if hasattr(output, "content"):
                    result_text = str(output.content)
                elif isinstance(output, dict) and "content" in output:
                    result_text = str(output["content"])
                else:
                    result_text = str(output)

                await on_event(
                    {
                        "type": EVENT_TOOL_RESULT,
                        "tool_name": name,
                        "result": result_text[:2000]
                        + ("\n...[截断]" if len(result_text) > 2000 else ""),
                    }
                )

        # 整个图执行完毕
        await on_event({"type": EVENT_DONE})

    except Exception as e:
        logger.exception(f"Agent 执行异常: {e}")
        await on_event(
            {
                "type": EVENT_ERROR,
                "content": f"Agent 执行出错: {str(e)}",
            }
        )
