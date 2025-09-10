import uuid
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import Optional, List

# Hàm factory để tự động tạo UUID và thời gian
def new_uuid():
    return str(uuid.uuid4())

def new_timestamp():
    return datetime.now(timezone.utc)

class Run(BaseModel):
    run_id: str = Field(default_factory=new_uuid)
    session_id: str
    user_id: str
    problem_text: str
    prompt_text: str
    prompt_level: int
    model_name: str
    response_text: str
    latency_ms: int
    tokens_in: int
    tokens_out: int
    created_at: datetime = Field(default_factory=new_timestamp)

class PromptMetrics(BaseModel):
    metric_id: str = Field(default_factory=new_uuid)
    run_id: str
    tokenizer: str
    window_w: int
    mattr: float
    token_count: int
    reading_ease: float
    computed_at: datetime = Field(default_factory=new_timestamp)

class Suggestion(BaseModel):
    suggestion_id: str = Field(default_factory=new_uuid)
    session_id: str
    user_id: str
    run_id: str
    suggested_level: int
    shown_at: datetime = Field(default_factory=new_timestamp)
    accepted: bool = False
    accepted_at: Optional[datetime] = None