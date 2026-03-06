"""HTTP Agent API — 供程序调用的同步 Agent 接口

POST /api/agent/chat
程序发送问题，等待 Agent 完整执行后返回最终结果。
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from config import ANTHROPIC_API_KEY
from db.session import AsyncSessionLocal
from models import Conversation
from agent import run_agent
from api.ws.chat import save_message
from utils.logger import logger


router = APIRouter(prefix="/api/agent", tags=["agent"])


class ChatRequest(BaseModel):
    message: str = Field(..., description="用户问题")
    conversation_id: str | None = Field(None, description="会话 ID，传入可继续上下文")
    skill: str | None = Field(
        None, description="指定使用的 Skill 名称，如 mysql-sql-analyzer"
    )


class ToolCallRecord(BaseModel):
    tool_name: str
    tool_input: dict | None = None
    result: str = ""


class ChatResponse(BaseModel):
    conversation_id: str
    content: str = Field("", description="Agent 最终回复文本")
    thinking: str = Field("", description="Agent 思考过程")
    tool_calls: list[ToolCallRecord] = Field(
        default_factory=list, description="工具调用记录"
    )


@router.post("/chat", response_model=ChatResponse)
async def agent_chat(req: ChatRequest):
    """
    同步调用 Agent，等待完整执行后返回最终结果。

    适用于程序集成 — 告警系统、CI/CD、运维脚本等。
    """
    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=503, detail="未配置 ANTHROPIC_API_KEY")

    # 获取或创建会话
    conv_id = req.conversation_id
    if not conv_id:
        async with AsyncSessionLocal() as session:
            conv = Conversation(source="api")
            session.add(conv)
            await session.commit()
            await session.refresh(conv)
            conv_id = conv.id
            logger.info(f"[HTTP API] 新建对话 {conv_id}")

    # 如果指定了 skill，将 @skill 前缀加入消息
    user_message = req.message
    if req.skill:
        user_message = f"@{req.skill} {user_message}"

    # 保存用户消息
    await save_message(conv_id, "user", user_message, "text")

    # 收集 Agent 执行结果
    result_text = ""
    result_thinking = ""
    tool_calls: list[ToolCallRecord] = []
    current_tool: dict | None = None

    async def on_event(event: dict):
        nonlocal result_text, result_thinking, current_tool

        etype = event.get("type")

        if etype == "text_delta":
            result_text += event.get("content", "")

        elif etype == "thinking_delta":
            result_thinking += event.get("content", "")

        elif etype == "tool_call":
            current_tool = {
                "tool_name": event.get("tool_name", ""),
                "tool_input": event.get("tool_input"),
                "result": "",
            }

        elif etype == "tool_result":
            if current_tool:
                current_tool["result"] = event.get("result", "")
                tool_calls.append(ToolCallRecord(**current_tool))
                current_tool = None
            # 持久化工具消息
            await save_message(
                conv_id,
                "system",
                event.get("result", ""),
                "tool_result",
                tool_name=event.get("tool_name"),
            )

        elif etype == "error":
            raise HTTPException(
                status_code=500, detail=event.get("content", "Agent 执行出错")
            )

        elif etype == "done":
            # 持久化最终回复
            if result_text:
                await save_message(
                    conv_id,
                    "assistant",
                    result_text,
                    "text",
                    thinking=result_thinking or None,
                )

    logger.info(f"[HTTP API] 对话 {conv_id} 开始执行 Agent")
    await run_agent(user_message=user_message, conv_id=conv_id, on_event=on_event)

    return ChatResponse(
        conversation_id=conv_id,
        content=result_text,
        thinking=result_thinking,
        tool_calls=tool_calls,
    )
