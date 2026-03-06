import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base_class import Base

if TYPE_CHECKING:
    from models.message import Message


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    title: Mapped[str] = mapped_column(String(200), default="新对话")
    source: Mapped[str] = mapped_column(String(20), default="web", server_default="web")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "source": self.source,
            "created_at": (
                self.created_at.isoformat(timespec="milliseconds")
                if self.created_at
                else None
            ),
            "updated_at": (
                self.updated_at.isoformat(timespec="milliseconds")
                if self.updated_at
                else None
            ),
        }
