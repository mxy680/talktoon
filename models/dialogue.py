from __future__ import annotations

from typing import List
from pydantic import BaseModel


class DialogueMessage(BaseModel):
    character: str
    text: str


class DialogueScript(BaseModel):
    messages: List[DialogueMessage]
