"""
AI Assistant Models.

Models for storing AI conversation history, queries, and results.
"""
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    JSON,
    Enum as SQLEnum,
    Index,
)
from sqlalchemy.orm import relationship
import enum

from backend.database import Base


class MessageRole(str, enum.Enum):
    """Role of a message in a conversation."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChartType(str, enum.Enum):
    """Supported chart types for visualization."""
    LINE = "line"
    BAR = "bar"
    PIE = "pie"
    NUMBER = "number"
    TABLE = "table"


class AIConversation(Base):
    """
    AI conversation thread.

    Stores conversation metadata and links to messages.
    """
    __tablename__ = "ai_conversations"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Conversation metadata
    title = Column(String(255), nullable=True)  # Auto-generated from first question

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    messages = relationship("AIMessage", back_populates="conversation", cascade="all, delete-orphan", order_by="AIMessage.created_at")
    user = relationship("User", backref="ai_conversations")
    organization = relationship("Organization", backref="ai_conversations")

    __table_args__ = (
        Index("ix_ai_conversations_org_user", "organization_id", "user_id"),
        Index("ix_ai_conversations_updated", "updated_at"),
    )

    @property
    def message_count(self) -> int:
        """Get the number of messages in this conversation."""
        return len(self.messages) if self.messages else 0


class AIMessage(Base):
    """
    Individual message in an AI conversation.

    Stores the message content, generated SQL, query results, and visualization config.
    """
    __tablename__ = "ai_messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("ai_conversations.id", ondelete="CASCADE"), nullable=False)

    # Message content
    role = Column(SQLEnum(MessageRole), nullable=False)
    content = Column(Text, nullable=False)  # The question or explanation

    # For assistant messages: SQL and results
    sql = Column(Text, nullable=True)  # Generated SQL query
    results_json = Column(JSON, nullable=True)  # Query results (list of dicts)
    row_count = Column(Integer, nullable=True)  # Number of rows returned

    # Visualization configuration
    chart_type = Column(SQLEnum(ChartType), nullable=True)
    chart_config = Column(JSON, nullable=True)  # {x_axis, y_axis, title, colors, etc.}

    # Execution metadata
    execution_time_ms = Column(Integer, nullable=True)  # Query execution time
    error_message = Column(Text, nullable=True)  # If query failed

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    conversation = relationship("AIConversation", back_populates="messages")

    __table_args__ = (
        Index("ix_ai_messages_conversation", "conversation_id"),
    )


class AISuggestedQuestion(Base):
    """
    Pre-defined suggested questions based on connected sources.

    Used to help users get started with AI assistant.
    """
    __tablename__ = "ai_suggested_questions"

    id = Column(Integer, primary_key=True, index=True)

    # Question content
    question = Column(String(500), nullable=False)
    category = Column(String(50), nullable=False)  # finance, sales, operations, etc.

    # Which source types this question applies to
    source_types = Column(JSON, nullable=False)  # ["stripe", "paystack"]

    # Display order
    priority = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_ai_suggested_category", "category"),
    )
