from pydantic import BaseModel
from datetime import datetime
from enum import Enum
from typing import Optional, List

class MessageRole(str, Enum):
    USER = "user"
    AI = "AI"

class Problem(BaseModel):
    problem_id: str
    grade: int
    topic: str
    cognitive_level: int
    type: str #Abstract/Real-world
    text: str
    created_at: datetime

class Prompt(BaseModel):
    prompt_id: str
    problem_id: str
    text: str
    prompt_level: str 
    created_at: datetime

class PromptMetrics(BaseModel):
    prompt_id: str
    tokenizer: str
    window_w: int
    mattr: float
    token_count: int
    reading_ease: float
    computed_at: datetime

class Users(BaseModel):
    user_id: str
    user_name: str
    role: str = "user"

class Sessions(BaseModel):
    session_id: str
    user_id: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    source: str = "web"

class Messages(BaseModel):
    msg_id: str
    session_id: str
    user_id: str
    role: MessageRole
    text: str
    tokens_in: int
    tokens_out: int
    latency_ms: int
    created_at: datetime

class Solution:
    final_answer: str
    solution_steps: List[str]