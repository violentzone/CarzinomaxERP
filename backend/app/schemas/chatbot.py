from typing import Literal
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal['user', 'assistant']
    content: str


class ChatboxRequest(BaseModel):
    # Either `message` (a new turn) or `decision` (answer to a pending approval) must be given
    message: str = ''
    history: list[ChatMessage] = Field(default_factory=list)
    # Client-generated conversation id; the paused run of an approval is stored under it
    thread_id: str | None = None
    decision: Literal['approve', 'reject'] | None = None
