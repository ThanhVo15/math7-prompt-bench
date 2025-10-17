import streamlit as st
import uuid
import random
from datetime import datetime
import re
from typing import Optional
import json
# --- LOCAL IMPORTS ---
from src.core.tokenizer import AdvancedTokenizer
from src.core.metrics import BasicMetrics
from src.core.metrics_advanced import compute_advanced_metrics
from src.services.openai_client import (
    get_analysis_from_analyzer,
    get_solution_from_solver,
)
from src.services.google_sheets import get_gsheet_manager
from src.prompts.taxonomy import PROMPT_TAXONOMY
from src.models.schemas import (
    Run,
    PromptMetrics,
    Suggestion,
    Evaluation,
    AdvancedMetricsRecord,
    AnalyzerScores,
    AnalyzerPattern,
    AdvancedMetricsPattern,
)

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(layout="wide", page_title="PromptOptima")

tokenizer = AdvancedTokenizer()
metrics_service = BasicMetrics()
gsheet_manager = get_gsheet_manager()  # ✅ giữ nguyên logic cũ

# =========================
# STATIC DATA
# =========================
CONTENT_DOMAINS = [
    "Ratios & Proportional Relationships",
    "The Number System",
    "Expressions & Equations",
    "Geometry",
    "Statistics & Probability",
]
COGNITIVE_LEVELS = {
    1: "Level 1: Procedural Fluency",
    2: "Level 2: Conceptual Understanding",
    3: "Level 3: Strategic Reasoning",
}
PROBLEM_CONTEXTS = ["Theoretical Math", "Applied Math", "Test"]
DEFAULT_PROMPT = "Solve this problem."

# =========================
# HELPERS
# =========================
def _normalize_problem_text(text: str) -> str:
    t = (text or "").lower().strip()
    t = re.sub(r"\s+", " ", t)
    return t

def generate_problem_id(problem_text: str) -> str:
    norm = _normalize_problem_text(problem_text)
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"promptoptima:problem:{norm}"))

def _band_to_score(band: Optional[str]) -> Optional[int]:
    if not band:
        return None
    m = {"low": 40, "medium": 70, "high": 90}
    return m.get(str(band).strip().lower())

# =========================
# SESSION STATE
# =========================
def init_session_state():
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.user_id = "user_" + str(uuid.uuid4())[:8]
        st.session_state.classification_complete = False
        st.session_state.chat_history = []
        st.session_state.problem_text = ""
        st.session_state.evaluator_name = ""

def reset_session():
    evaluator = st.session_state.get("evaluator_name", "")
    user_id = st.session_state.get("user_id", "user_" + str(uuid.uuid4())[:8])
    session_id = st.session_state.get("session_id", str(uuid.uuid4()))
    st.session_state.clear()
    init_session_state()
    st.session_state.evaluator_name = evaluator
    st.session_state.user_id = user_id
    st.session_state.session_id = session_id

def confirm_classification():
    if not st.session_state.get("evaluator_name", "").strip():
        st.warning("Please enter your name or ID before confirming.")
        return
    st.session_state.classification_complete = True

# =========================
# CORE HANDLERS
# =========================
def handle_submission(user_input: str):
    problem_text = (st.session_state.get("problem_text") or "").strip()
    if not problem_text:
        st.error("A problem description is required.")
        return

    problem_id = generate_problem_id(problem_text)
    current_run_id = str(uuid.uuid4())

    # Show user message in chat
    st.session_state.chat_history.append(
        {"role": "user", "content": user_input, "run_id": current_run_id}
    )

    # Call Analyzer & Solver
    prompt_analysis, solution_text, solver_response = {}, "", {}
    try:
        with st.spinner("🔎 Running analyzer & solver..."):
            analysis_response = get_analysis_from_analyzer(
                user_prompt=user_input,
                problem_text=problem_text
            )
            prompt_analysis = analysis_response.get("prompt_analysis", {}) or {}

            solver_response = get_solution_from_solver(
                user_prompt=user_input, problem_text=problem_text
            )
            solution_text = solver_response.get(
                "solution_text", "No solution text returned from API."
            )
    except Exception as e:
        st.exception(e)
        st.warning("Không gọi được AI, hiển thị thông tin lỗi thay thế.")
        solution_text = f"--- ERROR ---\n{e}"

    # Append assistant message
    st.session_state.chat_history.append(
        {
            "role": "assistant",
            "content": solution_text,
            "prompt_context": user_input,
            "problem_context": problem_text,
            "prompt_analysis": prompt_analysis,
            "run_id": current_run_id,
            "graded": False,
        }
    )

    # Compute deterministic metrics
    try:
        metrics_record = metrics_service.compute(user_input, tokenizer, run_id=current_run_id)
    except Exception:
        metrics_record = None

    adv_record = None
    adv_vals = {}
    try:
        adv_vals = compute_advanced_metrics(user_input, ai_pattern_hits=ph)
        adv_record = AdvancedMetricsRecord(
            run_id=current_run_id,
            session_id=st.session_state.session_id,
            user_id=st.session_state.user_id,
            prompt_text=user_input,
            cdi_rate_cognitive_verbs=float(adv_vals["cdi"]["rate_cognitive_verbs"]),
            cdi_lexical_density=float(adv_vals["cdi"]["lexical_density"]),
            cdi_clauses_per_sentence=float(adv_vals["cdi"]["clauses_per_sentence"]),
            cdi_rate_abstract_terms=float(adv_vals["cdi"]["rate_abstract_terms"]),
            cdi_composite=float(adv_vals["cdi"]["cdi_composite"]),
            sss_n_examples=int(adv_vals["sss"]["n_examples"]),
            sss_n_step_markers=int(adv_vals["sss"]["n_step_markers"]),
            sss_n_formula_markers=int(adv_vals["sss"]["n_formula_markers"]),
            sss_n_hints=int(adv_vals["sss"]["n_hints"]),
            sss_weighted=float(adv_vals["sss"]["sss_weighted"]),
            arq_abstract_terms=int(adv_vals["arq"]["abstract_terms"]),
            arq_numbers=int(adv_vals["arq"]["numbers"]),
            arq_ratio=float(adv_vals["arq"]["ratio"]),
            arq_meta_bonus=float(adv_vals["arq"]["meta_bonus"]),
            arq_score=float(adv_vals["arq"]["arq_score"]),
        )
    except Exception:
        pass

    try:
        sig = (prompt_analysis.get("signals") or {})
        bands = (prompt_analysis.get("qualitative_scores") or {})
        ai_est = (prompt_analysis.get("ai_estimated") or {})

        clarity_v = _band_to_score(bands.get("clarity_band"))
        specificity_v = _band_to_score(bands.get("specificity_band"))
        structure_v = _band_to_score(bands.get("structure_band"))

        est_token_count = sig.get("tokens")
        est_mattr = ai_est.get("mattr_like")
        est_reading = ai_est.get("reading_ease_like")

        if isinstance(est_mattr, (int, float)) and est_mattr <= 1:
            est_mattr *= 100.0
        if isinstance(est_reading, (int, float)) and est_reading <= 1:
            est_reading *= 100.0

        run_record = Run(
            run_id=current_run_id,
            session_id=st.session_state.session_id,
            user_id=st.session_state.user_id,
            problem_id=problem_id,
            problem_text=problem_text,
            content_domain=st.session_state.content_domain,
            cognitive_level=st.session_state.cognitive_level,
            problem_context=st.session_state.problem_context,
            prompt_text=user_input,
            prompt_level=0,
            prompt_name="Baseline/Custom",
            solver_model_name="gpt-3.5-turbo",
            response_text=solution_text,
            clarity_score=clarity_v,
            specificity_score=specificity_v,
            structure_score=structure_v,
            estimated_token_count=est_token_count,
            estimated_mattr_score=est_mattr,
            estimated_reading_ease=est_reading,
            analysis_rationale=prompt_analysis.get("overall_evaluation"),
            cdi_composite=float(adv_vals.get("cdi", {}).get("cdi_composite", 0)),
            sss_weighted=float(adv_vals.get("sss", {}).get("sss_weighted", 0)),
            arq_score=float(adv_vals.get("arq", {}).get("arq_score", 0)),
            latency_ms=solver_response.get("latency_ms", 0),
            tokens_in=(solver_response.get("usage") or {}).get("prompt_tokens", 0),
            tokens_out=(solver_response.get("usage") or {}).get("completion_tokens", 0),
        )

        # AnalyzerScores
        analyzer_scores = AnalyzerScores(
            run_id=current_run_id,
            session_id=st.session_state.session_id,
            user_id=st.session_state.user_id,
            prompt_text=user_input,
            problem_id=problem_id,
            tokens=int(sig.get("tokens", 0)),
            sentences=int(sig.get("sentences", 0)),
            avg_tokens_per_sentence=float(sig.get("avg_tokens_per_sentence", 0)),
            avg_clauses_per_sentence=float(sig.get("avg_clauses_per_sentence", 0)),
            cognitive_verbs_count=int(sig.get("cognitive_verbs_count", 0)),
            abstract_terms_count=int(sig.get("abstract_terms_count", 0)),
            clarity_score=int(bands.get("clarity_score", 0)),
            specificity_score=int(bands.get("specificity_score", 0)),
            structure_score=int(bands.get("structure_score", 0)),
            mattr_like=float(ai_est.get("mattr_like", 0)),
            reading_ease_like=float(ai_est.get("reading_ease_like", 0)),
            cdi_like=float(ai_est.get("cdi_like", 0)),
            sss_like=float(ai_est.get("sss_like", 0)),
            arq_like=float(ai_est.get("arq_like", 0)),
            confidence=str(ai_est.get("confidence", "")),
        )

        # AnalyzerPattern
        ph = (prompt_analysis.get("pattern_hits") or {})
        analyzer_pattern = AnalyzerPattern(
            run_id=current_run_id,
            session_id=st.session_state.session_id,
            user_id=st.session_state.user_id,
            prompt_text=user_input,
            problem_id=problem_id,
            cognitive_terms_ai="|".join(ph.get("cognitive_terms", [])),
            abstract_terms_ai="|".join(ph.get("abstract_terms", [])),
            meta_terms_ai="|".join(ph.get("meta_terms", [])),
            logic_connectors_ai="|".join(ph.get("logic_connectors", [])),
            modals_ai="|".join(ph.get("modals", [])),
            step_markers_ai="|".join(ph.get("step_markers", [])),
            examples_ai="|".join(ph.get("examples", [])),
            formula_markers_ai="|".join(ph.get("formula_markers", [])),
            hints_ai="|".join(ph.get("hints", [])),
            numbers_ai="|".join(ph.get("numbers", [])),
            sections_ai="|".join(ph.get("sections", [])),
            output_rules_ai="|".join(ph.get("output_rules", [])),
        )

        # Metrics Patterns (backend)
        hits = adv_vals.get("hits", {})
        backend_pattern = AdvancedMetricsPattern(
            run_id=current_run_id,
            session_id=st.session_state.session_id,
            user_id=st.session_state.user_id,
            prompt_text=user_input,
            c_terms_backend="|".join(hits.get("c_terms", [])),
            a_terms_backend="|".join(hits.get("a_terms", [])),
            meta_terms_backend="|".join(hits.get("meta_terms", [])),
            examples_hits="|".join(hits.get("examples", [])),
            step_markers_hits="|".join(hits.get("step_markers", [])),
            formula_marks_hits="|".join(hits.get("formula_marks", [])),
            hints_hits="|".join(hits.get("hints", [])),
            numbers_hits="|".join(hits.get("numbers", [])),
            cdi_index=float(adv_vals.get("cdi", {}).get("cdi_composite", 0)),
            sss_total=int(adv_vals.get("sss", {}).get("n_examples", 0))
                      + int(adv_vals.get("sss", {}).get("n_step_markers", 0))
                      + int(adv_vals.get("sss", {}).get("n_formula_markers", 0))
                      + int(adv_vals.get("sss", {}).get("n_hints", 0)),
            arq_ratio=float(adv_vals.get("arq", {}).get("ratio", 0)),
            arq_index=float(adv_vals.get("arq", {}).get("arq_score", 0)),
        )

        # --- SAVE TO GOOGLE SHEETS ---
        if gsheet_manager:
            if metrics_record:
                gsheet_manager.append_data("metrics_deterministic", [metrics_record])
            if adv_record:
                gsheet_manager.append_data("metrics_advanced", [adv_record])
            gsheet_manager.append_data("runs", [run_record])
            gsheet_manager.append_data("analyzer_scores", [analyzer_scores])
            gsheet_manager.append_data("analyzer_patterns", [analyzer_pattern])
            gsheet_manager.append_data("metrics_patterns", [backend_pattern])
        else:
            st.info("Google Sheets chưa cấu hình, bỏ qua ghi log.")

    except Exception as e:
        st.warning(f"Không thể ghi log lên Google Sheets: {e}")

# =========================
# UI
# =========================
init_session_state()

with st.sidebar:
    st.markdown("## Problem Setup")
    st.text("Version: v5.0.0")
    is_disabled = st.session_state.classification_complete
    st.text_input("Your Name / ID", key="evaluator_name", disabled=is_disabled)
    st.radio("Content Domain", CONTENT_DOMAINS, key="content_domain", disabled=is_disabled)
    st.radio(
        "Cognitive Level",
        options=list(COGNITIVE_LEVELS.keys()),
        format_func=lambda x: COGNITIVE_LEVELS[x],
        key="cognitive_level",
        disabled=is_disabled,
    )
    st.radio("Problem Context", PROBLEM_CONTEXTS, key="problem_context", disabled=is_disabled)

    st.button(
        "Confirm Setup",
        on_click=confirm_classification,
        type="primary",
        use_container_width=True,
        disabled=is_disabled,
    )

    st.markdown("---")
    with st.expander("🤖 Advanced: Run AI User (batch)", expanded=False):
        try:
            _g = get_gsheet_manager()
            _dfopt = _g.get_df("problems") if _g else None
        except Exception:
            _dfopt = None

        DEFAULT_CTX = ["Applied Math", "Theoretical Math", "Test"]

        if _dfopt is None or _dfopt.empty:
            st.warning("Không đọc được tab 'problems'.")
            ccss_opts = CONTENT_DOMAINS
            level_opts = [str(x) for x in COGNITIVE_LEVELS.keys()]
            ctx_opts = DEFAULT_CTX
        else:
            # Tự dò tên cột gần đúng
            colnames = [c.lower().strip() for c in _dfopt.columns]
            ctx_col = next((c for c in _dfopt.columns if "abstract" in c.lower() and "real" in c.lower()), None)
            ctx_vals = set()
            if ctx_col:
                ctx_vals = {str(x).strip() for x in _dfopt[ctx_col] if str(x).strip()}
            ccss_opts = sorted({str(x).split("(")[0].strip() for x in _dfopt.get("CCSS", []) if str(x).strip()})
            level_opts = sorted({str(x).strip() for x in _dfopt.get("Level", []) if str(x).strip()})
            ctx_opts = sorted(ctx_vals) if ctx_vals else DEFAULT_CTX

        ms_ccss = st.multiselect("Content Domains (để trống = tất cả)", options=ccss_opts)
        ms_level = st.multiselect("Cognitive Levels (để trống = tất cả)", options=level_opts)
        ms_ctx = st.multiselect("Problem Contexts (để trống = tất cả)", options=ctx_opts)

        inc_baseline = st.checkbox("Include baseline", value=True)
        flush_every = st.slider("Flush mỗi N runs", 5, 100, 20, 5)
        throttle = st.slider("Delay mỗi request (s)", 0.0, 1.0, 0.15, 0.05)

        valid_filters = any([ms_ccss, ms_level, ms_ctx])

        if st.button("🚀 Run AI User", type="primary", use_container_width=True):
            if not valid_filters:
                st.error("Hãy chọn ít nhất 1 nhóm (Domain/Level/Context).")
            else:
                from src.batch.ai_user_runner import run_ai_user_batch
                evaluator_name = (st.session_state.get("evaluator_name") or "").strip() or "Anonymous"
                res = run_ai_user_batch(
                    sheet_name="problems",
                    ccss_filters=ms_ccss,
                    level_filters=ms_level,
                    context_filters=ms_ctx,
                    evaluator_name=evaluator_name,
                    include_baseline=inc_baseline,
                    analyzer_model="gpt-3.5-turbo",
                    solver_model="gpt-3.5-turbo",
                    paraphraser_model="gpt-3.5-turbo",
                    throttle_sec=float(throttle),
                    flush_every=int(flush_every),
                )
                st.session_state["ai_user_result"] = res

        if st.session_state.get("ai_user_result"):
            r = st.session_state["ai_user_result"]
            st.success(f"AI User đã xử lý {r['selected']} problems, tạo {r['created_runs']} runs.")

    st.markdown("---")
    # st.write("DEBUG analyzer:", json.dumps(prompt_analysis, indent=2))
    if st.button("New Problem / Reset", use_container_width=True, on_click=reset_session):
        st.rerun()
