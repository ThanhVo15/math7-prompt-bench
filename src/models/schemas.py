# src/models/schemas.py
# -*- coding: utf-8 -*-
"""
Schema (Pydantic) cho toàn hệ thống, tách rời theo đúng "single-responsibility":

- Run:        Thông tin tối thiểu của một lần chạy (prompt + problem + solver output).
- PromptMetrics:  Các chỉ số nền tảng (MATTR-10, LIX, token_count).
- AdvancedMetricsRecord:  Chỉ số CDI/SSS/ARQ (dạng số) - "no-weight", SSS dùng log(1+x).
- AdvancedMetricsPattern:  "Model con" - liệt kê cụ thể CÁC TỪ/CỤM BẮT ĐƯỢC (pattern hits).
- AnalyzerScores:  Kết quả từ AI analyzer (clarity/specificity/structure, signals, ai_estimated).
- Suggestion / Evaluation:  Giữ nguyên để log gợi ý & chấm thủ công.

Mỗi model tương ứng một sheet:
    runs, metrics_deterministic, metrics_advanced, metrics_patterns, analyzer_scores,
    suggestions, evaluations
"""

import uuid
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import Optional, List


# ---------------- Utilities ----------------
def new_uuid() -> str:
    return str(uuid.uuid4())

def new_timestamp() -> datetime:
    return datetime.now(timezone.utc)


# ---------------- Core: Run ----------------
class Run(BaseModel):
    """
    Một 'run' tối giản: xác định lần đối thoại (prompt) + bối cảnh + lời giải từ solver.
    -> Sheet: 'runs'
    Lý do tách: tránh "phình to" bởi số đo; các metrics/analyzer/pattern được ghi ở sheet riêng.
    """
    run_id: str = Field(default_factory=new_uuid)
    session_id: str
    user_id: str
    
    ai_persona: Optional[str] = None

    problem_id: str
    problem_text: str
    content_domain: str          # e.g., RP / NS / EE / G / SP
    cognitive_level: int         # L1..L5 tuỳ UI bạn định nghĩa
    problem_context: str         # "Theorical Math" | "Applied Math"

    prompt_text: str             # Prompt người dùng
    prompt_level: int            # 0 baseline | taxonomy level
    prompt_name: Optional[str] = None

    solver_model_name: str       # model giải (vd "gpt-3.5-turbo")
    response_text: str           # lời giải trả về (nguyên văn)

    # usage/latency (đặt ở đây vì gắn chặt call solver)
    latency_ms: int = 0
    tokens_in: int = 0
    tokens_out: int = 0

    created_at: datetime = Field(default_factory=new_timestamp)


# ---------------- Deterministic Metrics ----------------
class PromptMetrics(BaseModel):
    """
    Các chỉ số 'deterministic' trên văn bản prompt (không cần model):
    -> Sheet: 'metrics_deterministic'
    """
    run_id: str
    tokenizer: str
    window_w: int                 # cửa sổ MATTR (mặc định 10)
    mattr: float                  # Covington & McFall (2010)
    token_count: int
    reading_ease: float           # ánh xạ 0..100 từ LIX (tiện cho UI)
    reading_lix: Optional[float] = None  # LIX gốc


# ---------------- Advanced Metrics (numbers) ----------------
class AdvancedMetricsRecord(BaseModel):
    """
    CDI/SSS/ARQ (phi trọng số):
    - CDI: geometric mean của (c_rate, a_rate), kèm LD & CPS (ghi riêng ở pattern nếu cần).
    - SSS: log(1+E)+log(1+S)+log(1+F)+log(1+H) để tránh spam; thêm sss_raw để quan sát.
    - ARQ: ratio = abstract_terms / (numbers + formula_marks + 1), có 'meta gate'.

    -> Sheet: 'metrics_advanced'
    """
    run_id: str
    session_id: str
    user_id: str
    prompt_text: str

    # --- flattened CDI ---
    cdi_rate_cognitive_verbs: float
    cdi_lexical_density: float
    cdi_clauses_per_sentence: float
    cdi_rate_abstract_terms: float
    cdi_composite: float          # geometric mean

    # --- flattened SSS ---
    sss_n_examples: int
    sss_n_step_markers: int
    sss_n_formula_markers: int
    sss_n_hints: int
    sss_weighted: float           # log-sum
    sss_raw: Optional[int] = None # E+S+F+H (ghi thêm để debug)

    # --- flattened ARQ ---
    arq_abstract_terms: int
    arq_numbers: int
    arq_ratio: float
    arq_meta_bonus: float
    arq_score: float              # ratio if gate open else 0

    created_at: datetime = Field(default_factory=new_timestamp)


# ---------------- Advanced Metrics (pattern hits) ----------------
class AdvancedMetricsPattern(BaseModel):
    """
    Pattern view (model con): lưu các từ/cụm bắt được để soi cấu trúc prompt.
    Lưu ý: các list được join bằng '|' để dễ ghi Google Sheets.
    -> Sheet: 'metrics_patterns'
    """
    run_id: str
    session_id: str
    user_id: str
    prompt_text: str

    # CDI hits
    c_terms_backend: str = ""     # "analyze|explain|compare"
    a_terms_backend: str = ""     # "equation|rate"
    meta_terms_backend: str = ""  # metacognitive verbs bắt được
    logic_connectors_hits: str = ""
    modals_hits: str = ""

    # SSS hits
    examples_hits: str = ""
    step_markers_hits: str = ""
    formula_marks_hits: str = ""
    hints_hits: str = ""

    # ARQ hits
    abstract_terms_backend: str = ""  # duplicate của a_terms (để đọc nhanh)
    numbers_hits: str = ""            # ví dụ "150|3"

    # Numeric snapshot (để tái lập nhanh)
    cdi_c_rate: float
    cdi_a_rate: float
    cdi_ld: float
    cdi_cps: float
    cdi_index: float
    sss_total: int
    sss_log: float
    arq_ratio: float
    arq_meta: bool
    arq_index: float

    # Optional: versioning lexicon để so sánh dọc thời gian
    lexicon_version: str = "v2"

    # Classifier (nếu có) - dự báo level & tên prompt
    level_pred: Optional[str] = None
    name_pred: Optional[str] = None

    created_at: datetime = Field(default_factory=new_timestamp)


# ---------------- Analyzer (LLM-based) ----------------
class AnalyzerScores(BaseModel):
    """
    Kết quả từ 'prompt analyzer' (LLM) – tách riêng để không "bẩn" bảng Run:
    -> Sheet: 'analyzer_scores'

    - signals: đếm/flag do model trả (tokens, steps, flags...)
    - qualitative_scores: clarity/specificity/structure (0..100)
    - ai_estimated: các ước lượng (mattr_like 0..1; reading_ease_like 0..100; cdi/sss/arq_like 0..100)
    - overall_evaluation/evidence: mô tả ngắn + cue

    Lý do tách: dữ liệu phụ thuộc model & prompt đẩy vào context; cần logging riêng để có thể
    thay model/định dạng mà không ảnh hưởng bảng run.
    """
    run_id: str
    session_id: str
    user_id: str
    prompt_text: str
    problem_id: str

    # ---- signals (flatten) ----
    tokens: Optional[int] = None
    sentences: Optional[int] = None
    avg_tokens_per_sentence: Optional[float] = None
    avg_clauses_per_sentence: Optional[float] = None
    cognitive_verbs_count: Optional[int] = None
    abstract_terms_count: Optional[int] = None
    numbers_count: Optional[int] = None
    content_words_count: Optional[int] = None
    sections_count: Optional[int] = None
    explicit_steps_count: Optional[int] = None
    has_worked_example: Optional[bool] = None
    has_formula_given: Optional[bool] = None
    has_hints: Optional[bool] = None
    has_output_format_rule: Optional[bool] = None
    has_verification: Optional[bool] = None
    contradictions: Optional[bool] = None

    # ---- qualitative_scores ----
    clarity_score: Optional[int] = None        # 0..100
    specificity_score: Optional[int] = None    # 0..100
    structure_score: Optional[int] = None      # 0..100

    # ---- ai_estimated ----
    mattr_like_0_1: Optional[float] = None     # giữ đúng 0..1 (không đổi thang)
    reading_ease_like: Optional[float] = None  # 0..100
    cdi_like: Optional[float] = None           # 0..100
    sss_like: Optional[float] = None           # 0..100
    arq_like: Optional[float] = None           # 0..100
    confidence: Optional[str] = None           # "Low"|"Medium"|"High"

    overall_evaluation: Optional[str] = None
    evidence_joined: Optional[str] = None      # "cue1|cue2|cue3"

    created_at: datetime = Field(default_factory=new_timestamp)

class AnalyzerPattern(BaseModel):
    """
    Pattern hits trích xuất bởi AI analyzer (LLM).
    -> Sheet: 'analyzer_patterns'
    Ghi chú:
      - Tất cả list được join bằng '|' để dễ ghi Google Sheets.
      - Đây là 'model con' song song với backend pattern (metrics_patterns).
      - Không chứa điểm số (scores); chỉ là *các cụm/từ bắt được* từ AI.
    """
    run_id: str
    session_id: str
    user_id: str
    prompt_text: str
    problem_id: str

    cognitive_terms_ai: str = ""      # "explain|justify|compare"
    abstract_terms_ai: str = ""       # "equation|ratio"
    meta_terms_ai: str = ""           # "check your work|justify"
    logic_connectors_ai: str = ""     # "if|then|therefore"
    modals_ai: str = ""               # "should|could|might"
    step_markers_ai: str = ""         # "step 1|step 2|1)"
    examples_ai: str = ""             # "for example|e.g."
    formula_markers_ai: str = ""      # "=|*|π"
    hints_ai: str = ""                # "hint|remember|note"
    numbers_ai: str = ""              # "150|3|1/2"
    sections_ai: str = ""             # "Step 1|Final Answer|Output"
    output_rules_ai: str = ""         # "return only|exact format|json"

    created_at: datetime = Field(default_factory=new_timestamp)



# ---------------- Suggestions / Evaluations ----------------
class Suggestion(BaseModel):
    """
    Lưu gợi ý prompt đã show cho user.
    -> Sheet: 'suggestions'
    """
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
    """
    Lưu chấm tay (đúng/sai, ghi chú).
    -> Sheet: 'evaluations'
    """
    evaluation_id: str = Field(default_factory=new_uuid)
    run_id: str
    grader_id: str
    correctness_score: int  # 1 Correct, 0 Incorrect
    evaluation_notes: Optional[str] = None
    evaluated_at: datetime = Field(default_factory=new_timestamp)
