"""
Telegram adapter: rate limit, lazy memory summarization on timeout, then agent response.
Channel-agnostic contract: (user_id, channel_id, message_text) -> response_text.
"""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters

from src.agent import get_agent_response
from src.database import ChatMessage, User, async_session_factory
from src.memory_manager import summarize_conversation
from src.rate_limit import get_rate_limiter
from src.settings import settings

CHANNEL_ID = "telegram"

RATE_LIMIT_MESSAGE = "Too many messages. Please wait a moment before sending more."
ERROR_MESSAGE = "Something went wrong. Please try again later."


async def _get_or_create_user(session: AsyncSession, user_id: str, channel_id: str) -> User:
    """Get existing user or create one for (user_id, channel_id)."""
    stmt = select(User).where(User.user_id == user_id, User.channel_id == channel_id).limit(1)
    result = await session.execute(stmt)
    user = result.scalars().first()
    if user is not None:
        return user
    user = User(user_id=user_id, channel_id=channel_id, profile_summary="")
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def _get_last_conversation(
    session: AsyncSession, user_id: str, channel_id: str
) -> tuple[UUID | None, datetime | None]:
    """Return (conversation_id, last_message_created_at) for the most recent conversation, or (None, None)."""
    stmt = (
        select(ChatMessage.conversation_id, ChatMessage.created_at)
        .where(ChatMessage.user_id == user_id, ChatMessage.channel_id == channel_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    row = result.first()
    if row is None:
        return None, None
    return row.conversation_id, row.created_at


async def _load_conversation_messages(
    session: AsyncSession,
    user_id: str,
    channel_id: str,
    conversation_id: UUID,
) -> list[dict]:
    """Load messages for a conversation as list of {role, content} for summarizer."""
    stmt = (
        select(ChatMessage.role, ChatMessage.content)
        .where(
            ChatMessage.user_id == user_id,
            ChatMessage.channel_id == channel_id,
            ChatMessage.conversation_id == conversation_id,
        )
        .order_by(ChatMessage.created_at)
    )
    result = await session.execute(stmt)
    return [{"role": r.role, "content": r.content or ""} for r in result.all()]


async def _maybe_summarize_and_new_conversation(
    session: AsyncSession, user_id: str, channel_id: str
) -> UUID:
    """
    If previous conversation timed out: load it, summarize into User.profile_summary, return new conversation_id.
    Otherwise return current (last) conversation_id so this message continues it.
    """
    conv_id, last_at = await _get_last_conversation(session, user_id, channel_id)
    now = datetime.now(timezone.utc)
    last_ts = last_at.replace(tzinfo=timezone.utc) if last_at and last_at.tzinfo is None else last_at
    timeout_seconds = settings.CONVERSATION_TIMEOUT_SECONDS

    if conv_id is None or last_ts is None:
        return uuid4()

    elapsed = (now - last_ts).total_seconds()
    if elapsed <= timeout_seconds:
        return conv_id

    # Previous conversation timed out: summarize and start new
    user = await _get_or_create_user(session, user_id, channel_id)
    messages = await _load_conversation_messages(session, user_id, channel_id, conv_id)
    if messages:
        new_summary = summarize_conversation(user.profile_summary, messages)
        user.profile_summary = new_summary
        user.updated_at = datetime.utcnow()
        session.add(user)
        await session.commit()

    return uuid4()


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming text: rate limit, lazy memory, then agent response."""
    if not update.message or not update.message.text:
        return
    user_id = str(update.effective_user.id) if update.effective_user else "unknown"
    text = update.message.text.strip()
    if not text:
        return

    limiter = get_rate_limiter()
    if not limiter.check_and_record(user_id, CHANNEL_ID):
        await update.message.reply_text(RATE_LIMIT_MESSAGE)
        return

    async with async_session_factory() as session:
        try:
            await _get_or_create_user(session, user_id, CHANNEL_ID)
            conversation_id: UUID = await _maybe_summarize_and_new_conversation(
                session, user_id, CHANNEL_ID
            )
            reply = await get_agent_response(
                session,
                user_id=user_id,
                channel_id=CHANNEL_ID,
                conversation_id=conversation_id,
                user_message=text,
            )
            await update.message.reply_text(reply)
        except Exception:
            await update.message.reply_text(ERROR_MESSAGE)
            raise


def build_application(token: str) -> Application:
    """Build Telegram Application with message handler."""
    app = Application.builder().token(token).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    return app


async def run_bot(token: str) -> None:
    """Run the bot (polling). Blocks until stopped (e.g. Ctrl+C)."""
    import asyncio
    app = build_application(token)
    await app.initialize()
    await app.start()
    stop_event = asyncio.Event()
    try:
        await app.updater.start_polling(drop_pending_updates=True)
        await stop_event.wait()
    except asyncio.CancelledError:
        pass
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()
