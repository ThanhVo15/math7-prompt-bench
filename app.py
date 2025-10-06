# app.py
import streamlit as st
import uuid
import random
from datetime import datetime
import re

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
)
from typing import Optional

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(layout="wide", page_title="PromptOptima")

tokenizer = AdvancedTokenizer()
metrics_service = BasicMetrics()
gsheet_manager = get_gsheet_manager()  # ✅ no _version arg

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
PROBLEM_CONTEXTS = ["Theorical Math", "Applied Math"]
DEFAULT_PROMPT = "Solve this problem."

# =========================
# HELPERS (stable problem_id)
# =========================
def _normalize_problem_text(text: str) -> str:
    t = (text or "").lower().strip()
    t = re.sub(r"\s+", " ", t)
    return t

def generate_problem_id(problem_text: str) -> str:
    norm = _normalize_problem_text(problem_text)
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"promptoptima:problem:{norm}"))

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
            # ✅ pass problem_text to analyzer so it can consider the task context
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

    # Append assistant message to chat
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

    # Compute basic metrics on the PROMPT text
    try:
        metrics_record = metrics_service.compute(
            user_input, tokenizer, run_id=current_run_id
        )
    except Exception as _e:
        metrics_record = None

    # Compute advanced metrics on the PROMPT text (CDI/SSS/ARQ — natural scale)
    # Compute advanced metrics on the PROMPT text
    adv_record = None
    cdi_comp = sss_w = arq_s = None
    try:
        adv_vals = compute_advanced_metrics(user_input)  # dict with keys 'cdi','sss','arq'

        # aggregates for the Run row
        cdi_comp = float(adv_vals["cdi"]["cdi_composite"])
        sss_w    = float(adv_vals["sss"]["sss_weighted"])
        arq_s    = float(adv_vals["arq"]["arq_score"])

        # full flattened row for metrics_advanced
        adv_record = AdvancedMetricsRecord(
            run_id=current_run_id,
            session_id=st.session_state.session_id,
            user_id=st.session_state.user_id,
            prompt_text=user_input,
            cdi_rate_cognitive_verbs=float(adv_vals["cdi"]["rate_cognitive_verbs"]),
            cdi_lexical_density=float(adv_vals["cdi"]["lexical_density"]),
            cdi_clauses_per_sentence=float(adv_vals["cdi"]["clauses_per_sentence"]),
            cdi_rate_abstract_terms=float(adv_vals["cdi"]["rate_abstract_terms"]),
            cdi_composite=cdi_comp,
            sss_n_examples=int(adv_vals["sss"]["n_examples"]),
            sss_n_step_markers=int(adv_vals["sss"]["n_step_markers"]),
            sss_n_formula_markers=int(adv_vals["sss"]["n_formula_markers"]),
            sss_n_hints=int(adv_vals["sss"]["n_hints"]),
            sss_weighted=sss_w,
            arq_abstract_terms=int(adv_vals["arq"]["abstract_terms"]),
            arq_numbers=int(adv_vals["arq"]["numbers"]),
            arq_ratio=float(adv_vals["arq"]["ratio"]),
            arq_meta_bonus=float(adv_vals["arq"]["meta_bonus"]),
            arq_score=arq_s,
        )
    except Exception:
        pass


    # Build Run record (best-effort)
    try:
        # --- MAP ANALYZER v2 → legacy fields for Run ---
        sig = (prompt_analysis.get("signals") or {})
        bands = (prompt_analysis.get("qualitative_scores") or {})
        ai_est = (prompt_analysis.get("ai_estimated") or {})

        def _band_to_score(band: Optional[str]) -> Optional[int]:
            if not band: return None
            m = {"low": 40, "medium": 70, "high": 90}
            return m.get(str(band).strip().lower())

        clarity_v = _band_to_score(bands.get("clarity_band"))
        specificity_v = _band_to_score(bands.get("specificity_band"))
        structure_v = _band_to_score(bands.get("structure_band"))

        # estimated_* theo schema mới
        est_token_count = sig.get("tokens")
        est_mattr = ai_est.get("mattr_like")
        est_reading = ai_est.get("reading_ease_like")

        # Chuẩn hoá về thang 0..100 nếu model trả 0..1
        if isinstance(est_mattr, (int, float)) and est_mattr <= 1:
            est_mattr = est_mattr * 100.0
        if isinstance(est_reading, (int, float)) and est_reading <= 1:
            est_reading = est_reading * 100.0


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

            # 👇 LẤY THEO BẢN MỚI
            clarity_score=clarity_v,
            specificity_score=specificity_v,
            structure_score=structure_v,
            estimated_token_count=est_token_count,
            estimated_mattr_score=est_mattr,
            estimated_reading_ease=est_reading,

            analysis_rationale=prompt_analysis.get("overall_evaluation"),

            # nếu bạn đã thêm 3 cột aggregate từ advanced:
            cdi_composite=cdi_comp,
            sss_weighted=sss_w,
            arq_score=arq_s,

            latency_ms=solver_response.get("latency_ms", 0),
            tokens_in=(solver_response.get("usage") or {}).get("prompt_tokens", 0),
            tokens_out=(solver_response.get("usage") or {}).get("completion_tokens", 0),
        )


        if gsheet_manager:
            if metrics_record:
                gsheet_manager.append_data("metrics_deterministic", [metrics_record])
            if adv_record:
                gsheet_manager.append_data("metrics_advanced", [adv_record])
            gsheet_manager.append_data("runs", [run_record])
        else:
            st.info("Google Sheets chưa cấu hình, bỏ qua bước ghi log.")
    except Exception as e:
        st.warning(f"Không thể ghi log lên Google Sheets: {e}")

def save_grade_callback(grade, run_id_to_grade, notes):
    evaluator_name = st.session_state.get("evaluator_name", "Manual").strip() or "Manual"
    evaluation_record = Evaluation(
        run_id=run_id_to_grade,
        grader_id=evaluator_name,
        correctness_score=(1 if grade == "Correct" else 0),
        evaluation_notes=notes,
    )
    if gsheet_manager:
        gsheet_manager.append_data("evaluations", [evaluation_record])
        st.toast(f"Grade '{grade}' saved!")
    else:
        st.info("Google Sheets chưa cấu hình, bỏ qua lưu đánh giá.")
    for msg in st.session_state.chat_history:
        if msg.get("run_id") == run_id_to_grade and msg.get("role") == "assistant":
            msg["graded"] = True
            break

def show_suggestion(for_run_id):
    used_names = {
        msg.get("suggestion", {}).get("name")
        for msg in st.session_state.chat_history
        if msg.get("suggestion")
    }
    unused_keys = [k for k, v in PROMPT_TAXONOMY.items() if v["name"] not in used_names]
    if not unused_keys:
        st.warning("All suggestions have been shown!")
        return
    random_key = random.choice(unused_keys)
    suggestion_data = PROMPT_TAXONOMY[random_key]
    suggestion_record = Suggestion(
        run_id=for_run_id,
        session_id=st.session_state.session_id,
        user_id=st.session_state.user_id,
        suggestion_key=random_key,
        suggestion_name=suggestion_data["name"],
        suggested_level=suggestion_data.get("level", 0),
        accepted=True,
    )
    if gsheet_manager:
        gsheet_manager.append_data("suggestions", [suggestion_record])
        st.toast("Suggestion saved!")
    st.session_state.chat_history.append(
        {
            "role": "assistant",
            "content": "Here is a suggestion for a different prompt structure:",
            "suggestion": suggestion_data,
            "run_id": str(uuid.uuid4()),
        }
    )

# =========================
# UI
# =========================
init_session_state()

with st.sidebar:
    st.markdown("## Problem Setup")
    st.text("Version: v4.1.0")
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

    DEFAULT_CTX = ["Applied Math", "Theorical Math", "Test"]

    st.markdown("---")
    # Collapsible "Run AI User" as requested
    with st.expander("🤖 Advanced: Run AI User (batch)", expanded=False):
        # Pull filters from the 'problems' tab (no blocking if not available)
        try:
            _g = get_gsheet_manager()
            _dfopt = _g.get_df("problems") if _g else None
        except Exception:
            _dfopt = None

        if _dfopt is None or _dfopt.empty:
            st.warning("Không đọc được tab 'problems'.")
            ccss_opts, level_opts, ctx_opts = [], [], []
        else:
            ccss_opts = sorted({str(x).split("(")[0].strip() for x in _dfopt.get("CCSS", []) if str(x).strip()})
            level_opts = sorted({str(x).strip() for x in _dfopt.get("Level", []) if str(x).strip()})
            ctx_opts   = sorted({str(x).strip() for x in _dfopt.get("Abstract / Real-World", DEFAULT_CTX) if str(x).strip()})

        ms_ccss  = st.multiselect("Content Domains (để trống = tất cả)", options=ccss_opts)
        ms_level = st.multiselect("Cognitive Levels (để trống = tất cả)", options=level_opts)
        ms_ctx   = st.multiselect("Problem Contexts (để trống = tất cả)", options=ctx_opts)

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
                    evaluator_name=evaluator_name,      # sẽ lưu 'user_id' = "<name> - AI"
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
    if st.button("New Problem / Reset", use_container_width=True, on_click=reset_session):
        st.rerun()

    with st.expander("🛠 Debug"):
        try:
            import openai as _openai_pkg
            import httpx as _httpx_pkg
            st.write("OpenAI SDK:", getattr(_openai_pkg, "__version__", "unknown"))
            st.write("HTTPX:", getattr(_httpx_pkg, "__version__", "unknown"))
        except Exception:
            st.write("Cannot inspect versions.")
        st.write("Setup confirmed:", st.session_state.get("classification_complete"))
        st.write("Problem text length:", len(st.session_state.get("problem_text", "")))
        st.write("Google Sheets ready:", gsheet_manager is not None)

# =========================
# MAIN PANE
# =========================
st.markdown("<div style='text-align: center;'><h1>Welcome to PromptOptima</h1></div>", unsafe_allow_html=True)

if not st.session_state.classification_complete:
    st.info("Please complete the problem setup in the sidebar to begin.")
    st.stop()

st.markdown("---")
with st.expander("**Problem Description** (Collapsible)", expanded=not bool(st.session_state.get("problem_text", ""))):
    st.text_area("Enter the base math problem here.", key="problem_text", height=100)

st.markdown("### Chat History")
chat_container = st.container(height=500, border=True)
with chat_container:
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            if msg["role"] == "assistant" and msg.get("prompt_context"):
                with st.expander("Show Context for this Response"):
                    st.markdown("**Your Prompt:**")
                    st.container(border=True).markdown(f"_{msg['prompt_context']}_")
                    st.markdown("**Your Problem:**")
                    st.container(border=True).markdown(f"{msg.get('problem_context', 'N/A')}")

            st.markdown(msg["content"])

            if msg.get("suggestion"):
                s = msg["suggestion"]
                st.info(f"**Suggestion: {s['name']}**\n\n{s['description']}")
                with st.expander("Show Structure & Example"):
                    st.markdown("**📝 Structure / Template**")
                    st.code(s["template"].replace("{problem_text}", "[Your Problem]"), language="text")
                    st.markdown("**💡 Example**")
                    st.code(s["example"], language="text")

            if msg["role"] == "assistant" and msg.get("prompt_analysis"):
                st.divider()
                with st.container(border=True):
                    analysis = msg.get("prompt_analysis", {})
                    st.markdown("##### 🤖 AI's Prompt Analysis")
                    st.info(f"**Overall Evaluation:**\n\n_{analysis.get('overall_evaluation', 'N/A')}_")
                    st.markdown("---")

                    if not msg.get("graded"):
                        st.markdown("##### ✍️ Your Action: Please Grade The Solution Manually")
                        grade = st.radio(
                            "Is the final answer in the solution text correct?",
                            ("Correct", "Incorrect"),
                            horizontal=True,
                            key=f"grade_{msg['run_id']}",
                        )
                        notes = st.text_area("Evaluation Notes (Optional)", key=f"notes_{msg['run_id']}")
                        if st.button("Save Grade", key=f"save_{msg['run_id']}", use_container_width=True):
                            save_grade_callback(grade, msg["run_id"], notes)
                            st.rerun()
                    else:
                        st.markdown("##### Next Step")
                        if st.button(
                            "Suggestion",
                            key=f"suggestion_{msg['run_id']}",
                            use_container_width=True,
                            on_click=show_suggestion,
                            args=(msg["run_id"],),
                        ):
                            st.rerun()

# =========================
# INPUT AREA
# =========================
st.markdown("---")
col1, col2 = st.columns([1, 5])
with col1:
    if st.button("Solve with Default Prompt"):
        handle_submission(DEFAULT_PROMPT)
        st.rerun()
with col2:
    prompt = st.chat_input("Or enter your custom prompt here...")
    if prompt:
        handle_submission(prompt)
        st.rerun()
