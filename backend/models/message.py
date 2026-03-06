import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, Text, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base_class import Base

if TYPE_CHECKING:
    from models.conversation import Conversation


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    conversation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("conversations.id", ondelete="CASCADE")
    )
    role: Mapped[str] = mapped_column(String(20))  # user / assistant / system
    content: Mapped[str] = mapped_column(Text, default="")
    type: Mapped[str] = mapped_column(
        String(20), default="text"
    )  # text / tool_call / tool_result / error
    tool_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tool_input: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    thinking: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # 字符串引用 Conversation，因为两边相互引用
    conversation: Mapped["Conversation"] = relationship(back_populates="messages")

    def to_dict(self):
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "role": self.role,
            "content": self.content,
            "type": self.type,
            "tool_name": self.tool_name,
            "tool_input": self.tool_input,
            "thinking": self.thinking,
            "created_at": (
                self.created_at.isoformat(timespec="milliseconds")
                if self.created_at
                else None
            ),
        }
