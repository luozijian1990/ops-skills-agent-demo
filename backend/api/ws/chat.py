import json
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select, update, func

from config import ANTHROPIC_API_KEY
from db.session import AsyncSessionLocal
from models import Conversation, Message
from agent import run_agent
from utils.logger import logger


router = APIRouter(prefix="/ws", tags=["websocket"])


async def save_message(
    conv_id: str,
    role: str,
    content: str,
    msg_type: str = "text",
    tool_name: str | None = None,
    tool_input: dict | None = None,
    thinking: str | None = None,
):
    """保存消息到数据库"""
    async with AsyncSessionLocal() as session:
        msg = Message(
            conversation_id=conv_id,
            role=role,
            content=content,
            type=msg_type,
            tool_name=tool_name,
            tool_input=tool_input,
            thinking=thinking,
        )
        session.add(msg)
        # 同时更新会话的 updated_at
        await session.execute(
            update(Conversation)
            .where(Conversation.id == conv_id)
            .values(updated_at=func.now())
        )
        await session.commit()
        logger.debug(f"已保存消息到对话 {conv_id} (role={role}, type={msg_type})")
        return msg


async def auto_title(conv_id: str, first_message: str):
    """用第一条消息的前 30 个字符作为会话标题"""
    title = first_message[:30].replace("\n", " ")
    if len(first_message) > 30:
        title += "..."
    async with AsyncSessionLocal() as session:
        await session.execute(
            update(Conversation).where(Conversation.id == conv_id).values(title=title)
        )
        await session.commit()
    logger.info(f"已为对话 {conv_id} 自动生成标题: {title}")


@router.websocket("/chat")
async def websocket_chat(ws: WebSocket):
    await ws.accept()
    logger.info("WebSocket 客户端已连接")
    current_conv_id: str | None = None
    agent_task: asyncio.Task | None = None

    # 用于中断 Agent 的共享状态
    abort_event = asyncio.Event()
    streaming_text = ""
    streaming_thinking = ""
    step_thinking = ""
    delta_buffer = ""
    flush_task: asyncio.Task | None = None

    async def flush_delta():
        """将缓冲的 delta 合并发送"""
        nonlocal delta_buffer
        if delta_buffer:
            chunk = delta_buffer
            delta_buffer = ""
            await ws.send_text(
                json.dumps(
                    {"type": "text_delta", "content": chunk},
                    ensure_ascii=False,
                )
            )

    async def self_flush_after(delay: float):
        """延迟后自动刷新缓冲区"""
        await asyncio.sleep(delay)
        await flush_delta()

    async def on_event(event: dict):
        nonlocal streaming_text, streaming_thinking, delta_buffer, flush_task
        nonlocal step_thinking

        # 检查是否已被中断
        if abort_event.is_set():
            raise asyncio.CancelledError("用户中断")

        etype = event.get("type")

        if etype == "text_delta":
            streaming_text += event.get("content", "")
            delta_buffer += event.get("content", "")
            if flush_task is None or flush_task.done():
                flush_task = asyncio.create_task(self_flush_after(0.08))
            return

        if etype == "thinking_delta":
            streaming_thinking += event.get("content", "")
            step_thinking += event.get("content", "")
            await ws.send_text(json.dumps(event, ensure_ascii=False))
            return

        # 非 text_delta 事件：先把缓冲区刷掉
        if delta_buffer:
            await flush_delta()
            if flush_task and not flush_task.done():
                flush_task.cancel()

        await ws.send_text(json.dumps(event, ensure_ascii=False))

        if etype == "tool_call":
            desc = event.get("tool_desc", f"执行 Tool: {event.get('tool_name', '')}")
            await save_message(
                current_conv_id,
                "system",
                desc,
                "tool_call",
                tool_name=event.get("tool_name"),
                tool_input=event.get("tool_input"),
                thinking=step_thinking or None,
            )
            # 当前 step 的思考已保存，重置
            step_thinking = ""
        elif etype == "tool_result":
            await save_message(
                current_conv_id,
                "system",
                event.get("result", ""),
                "tool_result",
                tool_name=event.get("tool_name"),
            )
        elif etype == "error":
            logger.error(f"Agent 报错事件: {event.get('content')}")
            await save_message(
                current_conv_id, "system", event.get("content", ""), "error"
            )
        elif etype == "done":
            if streaming_text:
                await save_message(
                    current_conv_id,
                    "assistant",
                    streaming_text,
                    "text",
                    thinking=step_thinking or None,
                )

    async def do_abort():
        """执行中断：取消 Agent Task，保存已有结果"""
        nonlocal agent_task, delta_buffer
        if agent_task and not agent_task.done():
            agent_task.cancel()
            try:
                await agent_task
            except (asyncio.CancelledError, Exception):
                pass

        # 刷掉剩余缓冲
        if delta_buffer:
            try:
                await flush_delta()
            except Exception:
                pass

        # 保存已有的文本到数据库
        if streaming_text and current_conv_id:
            partial = streaming_text + "\n\n> ⚠️ *（回答被用户中断）*"
            await save_message(
                current_conv_id,
                "assistant",
                partial,
                "text",
                thinking=streaming_thinking or None,
            )

        # 通知前端结束
        try:
            await ws.send_text(json.dumps({"type": "done"}, ensure_ascii=False))
        except Exception:
            pass

        agent_task = None
        logger.info(f"对话 {current_conv_id} 已被用户中断")

    try:
        while True:
            # 如果 Agent 正在运行，同时监听 Agent 完成和新的 WS 消息
            if agent_task and not agent_task.done():
                recv_task = asyncio.create_task(ws.receive_text())
                done_set, _ = await asyncio.wait(
                    {agent_task, recv_task},
                    return_when=asyncio.FIRST_COMPLETED,
                )

                if recv_task in done_set:
                    raw = recv_task.result()
                else:
                    # agent_task 完成了,取消 recv_task，回去等下一条消息
                    recv_task.cancel()
                    try:
                        await recv_task
                    except (asyncio.CancelledError, Exception):
                        pass
                    # 处理 agent_task 的异常
                    if agent_task.done() and not agent_task.cancelled():
                        exc = agent_task.exception()
                        if exc:
                            logger.exception(f"Agent Task 异常: {exc}")
                    agent_task = None
                    continue
            else:
                raw = await ws.receive_text()

            data = json.loads(raw)
            msg_type = data.get("type", "message")
            logger.debug(f"收到 WS 消息类型: {msg_type}")

            # ── abort: 中断 Agent ──
            if msg_type == "abort":
                abort_event.set()
                await do_abort()
                continue

            # ── init: 绑定或创建会话 ──
            if msg_type == "init":
                conv_id = data.get("conversation_id")

                async with AsyncSessionLocal() as session:
                    if conv_id:
                        result = await session.execute(
                            select(Conversation).where(Conversation.id == conv_id)
                        )
                        conv = result.scalar_one_or_none()
                        if conv:
                            current_conv_id = conv_id
                            logger.info(f"已绑定到现有对话 {conv_id}")
                        else:
                            conv = Conversation()
                            session.add(conv)
                            await session.commit()
                            await session.refresh(conv)
                            current_conv_id = conv.id
                            logger.info(f"未找到对话 {conv_id}，已新建 {conv.id}")
                    else:
                        current_conv_id = None
                        logger.info(
                            "客户端 init 未传 conversation_id，等待首条消息创建对话"
                        )

                await ws.send_text(
                    json.dumps(
                        {
                            "type": "session",
                            "session_id": current_conv_id,
                            "conversation_id": current_conv_id,
                        }
                    )
                )
                continue

            # ── clear: 清空当前会话消息 ──
            if msg_type == "clear":
                if current_conv_id:
                    async with AsyncSessionLocal() as session:
                        result = await session.execute(
                            select(Message).where(
                                Message.conversation_id == current_conv_id
                            )
                        )
                        deleted_count = 0
                        for msg in result.scalars().all():
                            await session.delete(msg)
                            deleted_count += 1
                        await session.commit()
                        logger.info(
                            f"已清空对话 {current_conv_id} 的 {deleted_count} 条消息记录"
                        )
                await ws.send_text(json.dumps({"type": "cleared"}))
                continue

            # ── message: 用户发送消息 ──
            if msg_type == "message":
                content = data.get("content", "")

                if not ANTHROPIC_API_KEY:
                    logger.warning("收到消息，但未配置 ANTHROPIC_API_KEY")
                    await ws.send_text(
                        json.dumps(
                            {
                                "type": "error",
                                "content": "未配置 ANTHROPIC_API_KEY，请在 backend/.env 文件中设置",
                            }
                        )
                    )
                    continue

                if not current_conv_id:
                    async with AsyncSessionLocal() as session:
                        conv = Conversation()
                        session.add(conv)
                        await session.commit()
                        await session.refresh(conv)
                        current_conv_id = conv.id
                        logger.info(f"收到新消息，已自动新建对话 {conv.id}")
                    await ws.send_text(
                        json.dumps(
                            {
                                "type": "session",
                                "session_id": current_conv_id,
                                "conversation_id": current_conv_id,
                            }
                        )
                    )

                # 保存用户消息
                await save_message(current_conv_id, "user", content, "text")

                # 自动设标题
                async with AsyncSessionLocal() as session:
                    result = await session.execute(
                        select(Conversation).where(Conversation.id == current_conv_id)
                    )
                    conv = result.scalar_one_or_none()
                    if conv and conv.title == "新对话":
                        await auto_title(current_conv_id, content)
                        await ws.send_text(
                            json.dumps(
                                {
                                    "type": "title_update",
                                    "conversation_id": current_conv_id,
                                    "title": content[:30]
                                    + ("..." if len(content) > 30 else ""),
                                },
                                ensure_ascii=False,
                            )
                        )

                # 重置流式状态
                streaming_text = ""
                streaming_thinking = ""
                step_thinking = ""
                delta_buffer = ""
                abort_event.clear()

                logger.info(f"正在为对话 {current_conv_id} 启动 Agent")

                # 用 create_task 异步执行，让主循环可以继续接收 abort 消息
                agent_task = asyncio.create_task(
                    run_agent(
                        user_message=content,
                        conv_id=current_conv_id,
                        on_event=on_event,
                    )
                )
                # 不再 await agent_task，让循环顶部的 asyncio.wait 来处理

    except WebSocketDisconnect:
        logger.info("WebSocket 客户端已正常断开连接")
        if agent_task and not agent_task.done():
            agent_task.cancel()
    except Exception as e:
        logger.exception(f"WebSocket 异常错误: {e}")
        if agent_task and not agent_task.done():
            agent_task.cancel()
        try:
            await ws.send_text(
                json.dumps(
                    {
                        "type": "error",
                        "content": f"服务器错误: {str(e)}",
                    }
                )
            )
        except Exception:
            pass
