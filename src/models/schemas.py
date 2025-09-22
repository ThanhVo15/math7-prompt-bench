import uuid
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import Optional

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
    content_domain: str
    cognitive_level: int
    problem_context: str
    prompt_text: str
    prompt_level: int
    model_name: str
    response_text: str
    estimated_mattr: Optional[float] = None
    estimated_reading_ease: Optional[float] = None
    analysis_rationale: Optional[str] = None # nhận xét về PROMPT
    solution_evaluation: Optional[str] = None # nhận xét về SOLUTION
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

# Mở file src/models/schemas.py và cập nhật class Evaluation

class Evaluation(BaseModel):
    evaluation_id: str = Field(default_factory=new_uuid)
    run_id: str
    grader_id: str
    evaluator_model_name: str
    
    # --- Điểm thủ công ---
    correctness_score: int
    
    # --- Các điểm do AI tính toán ---
    explanation_score: Optional[float] = None # Đây là tổng điểm
    consistency_score: Optional[float] = None
    
    # --- 4 điểm thành phần chi tiết ---
    logical_soundness_score: Optional[int] = None
    step_completeness_score: Optional[int] = None
    calculation_accuracy_score: Optional[int] = None
    pedagogical_clarity_score: Optional[int] = None
    
    evaluation_notes: Optional[str] = None
    evaluated_at: datetime = Field(default_factory=new_timestamp)