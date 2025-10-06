import uuid
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import Optional, Dict, Any

def new_uuid():
    return str(uuid.uuid4())

def new_timestamp():
    return datetime.now(timezone.utc)

class Run(BaseModel):
    run_id: str = Field(default_factory=new_uuid)
    session_id: str
    user_id: str
    problem_id: str
    problem_text: str
    content_domain: str
    cognitive_level: int
    problem_context: str
    prompt_text: str
    prompt_level: int
    prompt_name: str | None = None
    solver_model_name: str
    response_text: str  # Lời giải từ Solver

    # --- analyzer (existing) ---
    clarity_score: Optional[int] = None
    specificity_score: Optional[int] = None
    structure_score: Optional[int] = None
    estimated_token_count: Optional[int] = None
    estimated_mattr_score: Optional[float] = None
    estimated_reading_ease: Optional[float] = None
    analysis_rationale: Optional[str] = None

    # --- NEW: aggregates from advanced metrics (scalars only) ---
    cdi_composite: Optional[float] = None      # e.g., 0.5346
    sss_weighted: Optional[float] = None       # e.g., 11
    arq_score: Optional[float] = None          # e.g., 1.5

    latency_ms: int
    tokens_in: int
    tokens_out: int
    created_at: datetime = Field(default_factory=new_timestamp)

class PromptMetrics(BaseModel):
    run_id: str
    tokenizer: str
    window_w: int
    mattr: float
    token_count: int
    reading_ease: float
    # NEW: natural LIX (không scale)
    reading_lix: Optional[float] = None

class AdvancedMetricsRecord(BaseModel):
    run_id: str
    session_id: str
    user_id: str
    prompt_text: str

    # --- flattened CDI ---
    cdi_rate_cognitive_verbs: float
    cdi_lexical_density: float
    cdi_clauses_per_sentence: float
    cdi_rate_abstract_terms: float
    cdi_composite: float

    # --- flattened SSS ---
    sss_n_examples: int
    sss_n_step_markers: int
    sss_n_formula_markers: int
    sss_n_hints: int
    sss_weighted: float

    # --- flattened ARQ ---
    arq_abstract_terms: int
    arq_numbers: int
    arq_ratio: float
    arq_meta_bonus: float
    arq_score: float

    created_at: datetime = Field(default_factory=new_timestamp)

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
