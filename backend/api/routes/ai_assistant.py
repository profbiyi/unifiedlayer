"""
AI Assistant API routes.

Provides endpoints for natural language data queries.
"""
import logging
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.database import get_db
from backend.models.pipeline import User
from backend.models.ai import AIConversation, AIMessage, MessageRole, ChartType

from backend.services.ai_schema_context import get_schema_context_service
from backend.services.nl_to_sql import get_nl_to_sql_service
from backend.services.sql_validator import get_sql_validator
from backend.services.query_executor import get_query_executor
from backend.services.auto_visualize import get_auto_visualizer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["AI Assistant"])


# ============================================================
# Schemas
# ============================================================

class AskRequest(BaseModel):
    question: str
    conversation_id: Optional[int] = None


class ChartConfigResponse(BaseModel):
    type: str
    title: Optional[str] = None
    x_axis: Optional[str] = None
    y_axis: Optional[str] = None
    format: Optional[dict] = None


class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    sql: Optional[str] = None
    results: Optional[List[dict]] = None
    row_count: Optional[int] = None
    chart_config: Optional[ChartConfigResponse] = None
    execution_time_ms: Optional[int] = None
    error: Optional[str] = None
    created_at: str


class AskResponse(BaseModel):
    conversation_id: int
    message: MessageResponse


class ConversationSummary(BaseModel):
    id: int
    title: Optional[str]
    message_count: int
    created_at: str
    updated_at: str


class ConversationDetail(BaseModel):
    id: int
    title: Optional[str]
    messages: List[MessageResponse]
    created_at: str
    updated_at: str


class SuggestedQuestion(BaseModel):
    question: str
    category: str


# ============================================================
# Endpoints
# ============================================================

@router.post("/ask", response_model=AskResponse)
async def ask_question(
    request: AskRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Ask a natural language question about your data.

    Converts the question to SQL, executes it, and returns results
    with automatic visualization suggestions.
    """
    org_id = current_user.organization_id

    # Get or create conversation
    if request.conversation_id:
        conversation = db.query(AIConversation).filter(
            AIConversation.id == request.conversation_id,
            AIConversation.organization_id == org_id,
        ).first()

        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found",
            )
    else:
        # Create new conversation
        nl_service = get_nl_to_sql_service()
        title = nl_service.generate_title(request.question)

        conversation = AIConversation(
            organization_id=org_id,
            user_id=current_user.id,
            title=title,
        )
        db.add(conversation)
        db.flush()

    # Save user message
    user_message = AIMessage(
        conversation_id=conversation.id,
        role=MessageRole.USER,
        content=request.question,
    )
    db.add(user_message)
    db.flush()

    # Get schema context
    schema_service = get_schema_context_service(db)
    schema = schema_service.get_org_schema(org_id)
    schema_context = schema_service.build_llm_context(schema)

    # Get conversation history for context
    history = []
    for msg in conversation.messages[-6:]:  # Last 6 messages
        history.append({
            "role": msg.role.value,
            "content": msg.content if msg.role == MessageRole.USER else msg.content,
        })

    # Generate SQL
    nl_service = get_nl_to_sql_service()
    sql_result = await nl_service.generate_sql(
        question=request.question,
        schema_context=schema_context,
        conversation_history=history,
    )

    # Prepare assistant message
    assistant_message = AIMessage(
        conversation_id=conversation.id,
        role=MessageRole.ASSISTANT,
        content=sql_result.explanation,
        sql=sql_result.sql if sql_result.sql else None,
    )

    if sql_result.error or not sql_result.sql:
        # Query generation failed
        assistant_message.error_message = sql_result.error or "Could not generate SQL"
        db.add(assistant_message)
        db.commit()

        return AskResponse(
            conversation_id=conversation.id,
            message=MessageResponse(
                id=assistant_message.id,
                role="assistant",
                content=sql_result.explanation,
                error=sql_result.error,
                created_at=assistant_message.created_at.isoformat(),
            ),
        )

    # Validate SQL
    validator = get_sql_validator(set(schema.keys()) if schema else None)
    validation = validator.validate(sql_result.sql)

    if not validation.is_valid:
        assistant_message.error_message = "; ".join(validation.errors)
        db.add(assistant_message)
        db.commit()

        return AskResponse(
            conversation_id=conversation.id,
            message=MessageResponse(
                id=assistant_message.id,
                role="assistant",
                content=sql_result.explanation,
                sql=sql_result.sql,
                error=f"Invalid SQL: {'; '.join(validation.errors)}",
                created_at=assistant_message.created_at.isoformat(),
            ),
        )

    # Sanitize SQL (add LIMIT if needed)
    safe_sql = validator.sanitize(sql_result.sql, max_rows=1000)
    assistant_message.sql = safe_sql

    # Execute query
    executor = get_query_executor(db)
    query_result = await executor.execute(safe_sql, timeout_seconds=30, max_rows=1000)

    assistant_message.execution_time_ms = query_result.execution_time_ms

    if not query_result.success:
        assistant_message.error_message = query_result.error
        db.add(assistant_message)
        db.commit()

        return AskResponse(
            conversation_id=conversation.id,
            message=MessageResponse(
                id=assistant_message.id,
                role="assistant",
                content=sql_result.explanation,
                sql=safe_sql,
                execution_time_ms=query_result.execution_time_ms,
                error=query_result.error,
                created_at=assistant_message.created_at.isoformat(),
            ),
        )

    # Store results
    assistant_message.results_json = query_result.data
    assistant_message.row_count = query_result.row_count

    # Auto-detect visualization
    visualizer = get_auto_visualizer()
    chart_config = visualizer.detect_chart_type(
        data=query_result.data,
        columns=query_result.columns,
        llm_suggestion=sql_result.chart_suggestion,
    )

    assistant_message.chart_type = ChartType(chart_config.type)
    assistant_message.chart_config = {
        "type": chart_config.type,
        "title": chart_config.title,
        "x_axis": chart_config.x_axis,
        "y_axis": chart_config.y_axis,
        "format": chart_config.format,
    }

    db.add(assistant_message)

    # Update conversation timestamp
    conversation.updated_at = datetime.now(timezone.utc)

    db.commit()

    return AskResponse(
        conversation_id=conversation.id,
        message=MessageResponse(
            id=assistant_message.id,
            role="assistant",
            content=sql_result.explanation,
            sql=safe_sql,
            results=query_result.data,
            row_count=query_result.row_count,
            chart_config=ChartConfigResponse(
                type=chart_config.type,
                title=chart_config.title,
                x_axis=chart_config.x_axis,
                y_axis=chart_config.y_axis,
                format=chart_config.format,
            ),
            execution_time_ms=query_result.execution_time_ms,
            created_at=assistant_message.created_at.isoformat(),
        ),
    )


@router.get("/conversations", response_model=List[ConversationSummary])
async def list_conversations(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List user's AI conversations.

    Returns conversations sorted by most recently updated.
    """
    conversations = db.query(AIConversation).filter(
        AIConversation.organization_id == current_user.organization_id,
        AIConversation.user_id == current_user.id,
    ).order_by(AIConversation.updated_at.desc()).limit(limit).all()

    return [
        ConversationSummary(
            id=c.id,
            title=c.title,
            message_count=c.message_count,
            created_at=c.created_at.isoformat(),
            updated_at=c.updated_at.isoformat(),
        )
        for c in conversations
    ]


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get a conversation with all messages.
    """
    conversation = db.query(AIConversation).filter(
        AIConversation.id == conversation_id,
        AIConversation.organization_id == current_user.organization_id,
    ).first()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    messages = []
    for msg in conversation.messages:
        chart_config = None
        if msg.chart_config:
            chart_config = ChartConfigResponse(
                type=msg.chart_config.get("type", "table"),
                title=msg.chart_config.get("title"),
                x_axis=msg.chart_config.get("x_axis"),
                y_axis=msg.chart_config.get("y_axis"),
                format=msg.chart_config.get("format"),
            )

        messages.append(MessageResponse(
            id=msg.id,
            role=msg.role.value,
            content=msg.content,
            sql=msg.sql,
            results=msg.results_json,
            row_count=msg.row_count,
            chart_config=chart_config,
            execution_time_ms=msg.execution_time_ms,
            error=msg.error_message,
            created_at=msg.created_at.isoformat(),
        ))

    return ConversationDetail(
        id=conversation.id,
        title=conversation.title,
        messages=messages,
        created_at=conversation.created_at.isoformat(),
        updated_at=conversation.updated_at.isoformat(),
    )


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete a conversation and all its messages.
    """
    conversation = db.query(AIConversation).filter(
        AIConversation.id == conversation_id,
        AIConversation.organization_id == current_user.organization_id,
        AIConversation.user_id == current_user.id,
    ).first()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    db.delete(conversation)
    db.commit()

    return {"message": "Conversation deleted"}


@router.get("/suggestions", response_model=List[SuggestedQuestion])
async def get_suggested_questions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get suggested questions based on connected sources.
    """
    from backend.models.pipeline import DataSource

    # Get connected sources
    sources = db.query(DataSource).filter(
        DataSource.organization_id == current_user.organization_id,
        DataSource.is_active,
    ).all()

    source_types = {s.source_type.lower() for s in sources}

    suggestions = []

    # Finance suggestions (Stripe, Paystack)
    if "stripe" in source_types or "paystack" in source_types:
        suggestions.extend([
            SuggestedQuestion(
                question="What was my total revenue last month?",
                category="revenue",
            ),
            SuggestedQuestion(
                question="Show me my top 10 customers by revenue",
                category="customers",
            ),
            SuggestedQuestion(
                question="What's my payment success rate?",
                category="payments",
            ),
            SuggestedQuestion(
                question="How has my revenue changed over the last 6 months?",
                category="trends",
            ),
        ])

    # Accounting suggestions (Xero, QuickBooks)
    if "xero" in source_types or "quickbooks" in source_types:
        suggestions.extend([
            SuggestedQuestion(
                question="Show me overdue invoices",
                category="invoices",
            ),
            SuggestedQuestion(
                question="What's my total outstanding receivables?",
                category="receivables",
            ),
            SuggestedQuestion(
                question="Show invoice aging by bucket",
                category="invoices",
            ),
        ])

    # Banking suggestions (Mono, TrueLayer)
    if "mono" in source_types or "truelayer" in source_types:
        suggestions.extend([
            SuggestedQuestion(
                question="What's my current bank balance?",
                category="banking",
            ),
            SuggestedQuestion(
                question="Show my spending by category this month",
                category="expenses",
            ),
            SuggestedQuestion(
                question="What were my largest transactions this week?",
                category="transactions",
            ),
        ])

    # Default suggestions if no sources
    if not suggestions:
        suggestions = [
            SuggestedQuestion(
                question="Connect a data source to start asking questions",
                category="setup",
            ),
        ]

    return suggestions[:8]  # Return max 8 suggestions
