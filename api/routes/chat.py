"""Chat route handling conversational spending queries."""
import uuid
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.db.session import get_db
from api.schemas import ChatRequest, ChatResponse
from api.services.chat.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("", response_model=ChatResponse, summary="Send a question to ask your statements")
def post_chat_message(
    request: ChatRequest,
    db: Session = Depends(get_db),
) -> ChatResponse:
    return ChatService.ask(
        db=db,
        message=request.message,
        session_id=request.session_id,
    )


@router.get("/{session_id}", summary="Get message history for a chat session")
def get_chat_history(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    return ChatService.get_history(db=db, session_id=session_id)
