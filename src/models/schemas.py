# src/models/schemas.py

import uuid
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import Optional

def new_uuid():
    return str(uuid.uuid4())

def new_timestamp():
    return datetime.now(timezone.utc)

class Run(BaseModel):
    run_id: str = Field(default_factory=new_uuid)
    session_id: str
    user_id: str
    # ➕ NEW:
    problem_id: str  # ID xác định duy nhất 1 đề bài (ổn định theo nội dung)
    problem_text: str
    content_domain: str
    cognitive_level: int
    problem_context: str
    prompt_text: str
    prompt_level: int
    solver_model_name: str
    response_text: str  # Lời giải từ Solver

    # --- CÁC TRƯỜNG MỚI TỪ ANALYZER ---
    clarity_score: Optional[int] = None
    specificity_score: Optional[int] = None
    structure_score: Optional[int] = None

    estimated_token_count: Optional[int] = None
    estimated_mattr_score: Optional[float] = None
    estimated_reading_ease: Optional[float] = None

    analysis_rationale: Optional[str] = None  # Nhận xét tổng thể từ Analyzer
    # -----------------------------------

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
    suggestion_key: int
    suggestion_name: str
    suggested_level: int
    shown_at: datetime = Field(default_factory=new_timestamp)
    accepted: bool = False

class Evaluation(BaseModel):
    evaluation_id: str = Field(default_factory=new_uuid)
    run_id: str
    grader_id: str
    correctness_score: int  # 1 for Correct, 0 for Incorrect
    evaluation_notes: Optional[str] = None
    evaluated_at: datetime = Field(default_factory=new_timestamp)
