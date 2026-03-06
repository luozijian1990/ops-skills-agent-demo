from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import select

from db.session import AsyncSessionLocal
from models import Conversation, Message
from utils.logger import logger

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.get("")
async def list_conversations(q: str | None = None):
    """获取所有会话列表，按更新时间倒序。支持 ?q=关键词 按标题模糊搜索"""
    logger.info(f"正在获取对话列表, 搜索关键词: {q}")
    async with AsyncSessionLocal() as session:
        stmt = select(Conversation)
        if q and q.strip():
            stmt = stmt.where(Conversation.title.ilike(f"%{q.strip()}%"))
        stmt = stmt.order_by(Conversation.updated_at.desc())
        result = await session.execute(stmt)
        conversations = result.scalars().all()
        return JSONResponse([c.to_dict() for c in conversations])


@router.post("")
async def create_conversation():
    """新建会话"""
    logger.info("正在创建新对话")
    async with AsyncSessionLocal() as session:
        conv = Conversation()
        session.add(conv)
        await session.commit()
        await session.refresh(conv)
        return JSONResponse(conv.to_dict())


@router.get("/{conv_id}/messages")
async def get_messages(conv_id: str):
    """获取某个会话的所有消息"""
    logger.info(f"正在获取对话 {conv_id} 的消息记录")
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Message)
            .where(Message.conversation_id == conv_id)
            .order_by(Message.created_at)
        )
        msgs = result.scalars().all()
        return JSONResponse([m.to_dict() for m in msgs])


@router.delete("/{conv_id}")
async def delete_conversation(conv_id: str):
    """删除会话及其所有消息"""
    logger.info(f"正在删除对话 {conv_id}")
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Conversation).where(Conversation.id == conv_id)
        )
        conv = result.scalar_one_or_none()
        if not conv:
            logger.warning(f"要删除的对话 {conv_id} 未找到")
            return JSONResponse({"error": "会话不存在"}, status_code=404)
        await session.delete(conv)
        await session.commit()
        return JSONResponse({"ok": True})


@router.patch("/{conv_id}")
async def update_conversation(conv_id: str, body: dict = None):
    """更新会话标题"""
    logger.info(f"正在更新对话 {conv_id}，数据: {body}")
    pass
