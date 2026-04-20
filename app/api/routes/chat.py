"""API routes for chat functionality."""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.ai_clients.gmf_taxonomy import SYSTEM_PROMPT
from app.ai_clients.openai import chat_completion
from app.db import get_db
from app.db.tables import Incident

router = APIRouter()


class ChatMessage(BaseModel):
    """Schema for a chat message."""
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    """Schema for a chat request."""
    message: str
    history: list[ChatMessage] = Field(default_factory=list)


class ChatResponse(BaseModel):
    """Schema for a chat response."""
    content: str


class SystemPromptResponse(BaseModel):
    """Schema for system prompt response."""
    system_prompt: str


@router.get("/system-prompt", response_model=SystemPromptResponse)
def get_system_prompt() -> SystemPromptResponse:
    """Get the system prompt for chat.

    Returns:
        System prompt response.
    """
    return SystemPromptResponse(system_prompt=SYSTEM_PROMPT)


@router.post("/chat/{incident_id}", response_model=ChatResponse)
def chat(incident_id: int, body: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    """Chat about an incident.

    Args:
        incident_id: The incident ID.
        body: Chat request with message and history.
        db: Database session.

    Returns:
        Chat response.

    Raises:
        HTTPException: If incident not found.
    """
    incident = db.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incident not found.",
        )
    content = chat_completion(
        title=incident.title,
        report_text=incident.report_text,
        history=[{"role": m.role, "content": m.content} for m in body.history],
        message=body.message,
    )
    return ChatResponse(content=content)
