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
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = Field(default_factory=list)


class ChatResponse(BaseModel):
    content: str


class SystemPromptResponse(BaseModel):
    system_prompt: str


@router.get("/system-prompt", response_model=SystemPromptResponse)
def get_system_prompt() -> SystemPromptResponse:
    return SystemPromptResponse(system_prompt=SYSTEM_PROMPT)


@router.post("/chat/{incident_id}", response_model=ChatResponse)
def chat(incident_id: int, body: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
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
