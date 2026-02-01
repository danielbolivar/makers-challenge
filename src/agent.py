"""
PydanticAI agent: RAG tool, short-term history, long-term profile injection.
Logfire instrumentation when LOGFIRE_TOKEN is set.
"""

from datetime import datetime
from dataclasses import dataclass
from uuid import UUID

from pydantic_ai import Agent, RunContext
from pydantic_ai.messages import ModelRequest, ModelResponse, TextPart, UserPromptPart
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import ChatMessage, User
from src.rag import search as rag_search
from src.settings import settings


@dataclass
class AgentDeps:
    """Dependencies injected into the agent run (session, user context, profile)."""

    session: AsyncSession
    user_id: str
    channel_id: str
    conversation_id: UUID
    profile_summary: str


# Model: plan said gemini-3-flash-preview; pydantic-ai uses google-gla: model name
MODEL_NAME = "google-gla:gemini-2.0-flash"

SYSTEM_PROMPT = """You are a customer service agent for Camaral. Answer only from the provided knowledge base search results. If the answer is not there, say so and offer to escalate. Be concise and helpful."""


def create_agent():
    """Build the Camaral customer service agent with RAG tool and optional Logfire."""
    agent = Agent(
        MODEL_NAME,
        deps_type=AgentDeps,
        system_prompt=SYSTEM_PROMPT,
        instrument=bool(settings.LOGFIRE_TOKEN),
        retries=1,
    )

    @agent.tool
    async def search_knowledge_base(ctx: RunContext[AgentDeps], query: str) -> str:
        """Search the company knowledge base for information relevant to the user query. Use this before answering questions about Camaral."""
        return await rag_search(ctx.deps.session, query=query)

    return agent


camaral_agent = create_agent()


async def _load_profile_summary(session: AsyncSession, user_id: str, channel_id: str) -> str:
    """Load User.profile_summary for (user_id, channel_id). Returns empty string if not found."""
    stmt = select(User.profile_summary).where(
        User.user_id == user_id,
        User.channel_id == channel_id,
    ).limit(1)
    result = await session.execute(stmt)
    row = result.scalars().first()
    return (row or "") or ""


async def _load_message_history(
    session: AsyncSession,
    user_id: str,
    channel_id: str,
    conversation_id: UUID,
    limit: int,
) -> list:
    """Load last N messages for this conversation and convert to pydantic-ai ModelMessage list."""
    stmt = (
        select(ChatMessage.role, ChatMessage.content, ChatMessage.created_at)
        .where(
            ChatMessage.user_id == user_id,
            ChatMessage.channel_id == channel_id,
            ChatMessage.conversation_id == conversation_id,
        )
        .order_by(ChatMessage.created_at.desc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    rows = list(result.all())[::-1]  # oldest first
    messages = []
    for role, content, created_at in rows:
        ts = created_at or datetime.utcnow()
        if role == "user":
            messages.append(
                ModelRequest(parts=[UserPromptPart(content=content or "", timestamp=ts)], timestamp=ts)
            )
        else:
            messages.append(
                ModelResponse(parts=[TextPart(content=content or "")], timestamp=ts)
            )
    return messages


async def _persist_messages(
    session: AsyncSession,
    user_id: str,
    channel_id: str,
    conversation_id: UUID,
    user_content: str,
    assistant_content: str,
) -> None:
    """Append user and assistant messages to chat_messages."""
    now = datetime.utcnow()
    session.add(
        ChatMessage(
            user_id=user_id,
            channel_id=channel_id,
            conversation_id=conversation_id,
            role="user",
            content=user_content,
            created_at=now,
        )
    )
    session.add(
        ChatMessage(
            user_id=user_id,
            channel_id=channel_id,
            conversation_id=conversation_id,
            role="assistant",
            content=assistant_content,
            created_at=now,
        )
    )
    await session.commit()


async def get_agent_response(
    session: AsyncSession,
    user_id: str,
    channel_id: str,
    conversation_id: UUID,
    user_message: str,
) -> str:
    """
    Load short-term history and profile, run the agent, persist user + assistant messages, return reply.
    """
    profile = await _load_profile_summary(session, user_id, channel_id)
    history = await _load_message_history(
        session, user_id, channel_id, conversation_id, settings.CHAT_HISTORY_LIMIT
    )
    deps = AgentDeps(
        session=session,
        user_id=user_id,
        channel_id=channel_id,
        conversation_id=conversation_id,
        profile_summary=profile,
    )
    instructions = None
    if profile:
        instructions = f"Known user context (use for personalization only): {profile}"

    result = await camaral_agent.run(
        user_message,
        deps=deps,
        message_history=history if history else None,
        instructions=instructions,
    )
    reply = (result.output or "").strip()
    await _persist_messages(
        session, user_id, channel_id, conversation_id, user_message, reply
    )
    return reply
