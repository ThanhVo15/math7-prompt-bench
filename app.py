# app.py

import streamlit as st
import uuid
import random
from datetime import datetime

# Import local modules
from src.core.tokenizer import AdvancedTokenizer
from src.core.metrics import BasicMetrics
from src.services.openai_client import get_analysis_from_analyzer, get_solution_from_solver # <-- IMPORT HÀM MỚI
from src.services.google_sheets import get_gsheet_manager
from src.prompts.taxonomy import PROMPT_TAXONOMY
from src.models.schemas import Run, PromptMetrics, Suggestion, Evaluation

# --- INITIALIZATION ---
st.set_page_config(layout="wide", page_title="PromptOptima")
tokenizer = AdvancedTokenizer()
metrics_service = BasicMetrics()
gsheet_manager = get_gsheet_manager()

# --- STATIC DATA ---
CONTENT_DOMAINS = ["Ratios & Proportional Relationships", "The Number System", "Expressions & Equations", "Geometry", "Statistics & Probability"]
COGNITIVE_LEVELS = {1: "Level 1: Procedural Fluency", 2: "Level 2: Conceptual Understanding", 3: "Level 3: Strategic Reasoning"}
PROBLEM_CONTEXTS = ["Theorical Math", "Applied Math"]
DEFAULT_PROMPT = "Solve this problem."

# --- SESSION STATE MANAGEMENT (Không đổi) ---
def init_session_state():
    if 'session_id' not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.user_id = "user_" + str(uuid.uuid4())[:8]
        st.session_state.classification_complete = False
        st.session_state.view_mode = None
        st.session_state.chat_history = []
        st.session_state.problem_text = ""
        st.session_state.evaluator_name = ""

# --- CALLBACKS & LOGIC FUNCTIONS ---
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

def set_view_mode(mode):
    st.session_state.view_mode = mode
    if mode == 'chat':
        st.session_state.chat_history = []

def handle_submission(user_input):
    """Core logic with new two-model architecture."""
    problem_text = st.session_state.problem_text
    if not problem_text.strip():
        st.error("A problem description is required.")
        return

    current_run_id = str(uuid.uuid4())
    st.session_state.chat_history.append({"role": "user", "content": user_input, "run_id": current_run_id})

    # --- NEW LOGIC: TWO SEPARATE API CALLS ---
    # Step 1: Get prompt analysis from the ANALYZER
    with st.spinner("AI is analyzing your prompt..."):
        analysis_response = get_analysis_from_analyzer(user_prompt=user_input)
    if analysis_response.get("error"):
        st.error(f"Prompt Analysis Error: {analysis_response['error']}")
        return
    prompt_analysis = analysis_response.get("prompt_analysis", {})

    # Step 2: Get the solution from the SOLVER
    with st.spinner("AI is solving the problem..."):
        solver_response = get_solution_from_solver(user_prompt=user_input, problem_text=problem_text)
    if solver_response.get("error"):
        st.error(f"Problem Solving Error: {solver_response['error']}")
        return
    solution_text = solver_response.get("solution_text")
    # ---------------------------------------------

    # Step 3: Append assistant's response to chat history
    st.session_state.chat_history.append({
        "role": "assistant",
        "content": solution_text,
        "prompt_context": user_input,
        "problem_context": problem_text,
        "prompt_analysis": prompt_analysis,
        "run_id": current_run_id,
        "graded": False
    })
    
    # Step 4: Log all data
    metrics_record = metrics_service.compute(user_input, tokenizer, run_id=current_run_id)
    gsheet_manager.append_data("metrics_deterministic", [metrics_record])

    qual_scores = prompt_analysis.get('qualitative_scores', {})
    est_metrics = prompt_analysis.get('estimated_metrics', {})

    run_record = Run(
        run_id=current_run_id,
        session_id=st.session_state.session_id, user_id=st.session_state.user_id,
        problem_text=problem_text, content_domain=st.session_state.content_domain,
        cognitive_level=st.session_state.cognitive_level, problem_context=st.session_state.problem_context,
        prompt_text=user_input, prompt_level=0, model_name="gpt-3.5-turbo-1106",
        response_text=solution_text,
        clarity_score=qual_scores.get('clarity_score'),
        specificity_score=qual_scores.get('specificity_score'),
        structure_score=qual_scores.get('structure_score'),
        estimated_token_count=est_metrics.get('estimated_token_count'),
        estimated_mattr_score=est_metrics.get('estimated_mattr_score'),
        estimated_reading_ease=est_metrics.get('estimated_reading_ease'),
        analysis_rationale=prompt_analysis.get('overall_evaluation'),
        latency_ms=solver_response.get("latency_ms", 0),
        tokens_in=solver_response.get("usage", {}).get("prompt_tokens", 0),
        tokens_out=solver_response.get("usage", {}).get("completion_tokens", 0)
    )
    gsheet_manager.append_data("runs", [run_record])

def save_grade_callback(grade, run_id_to_grade, notes):
    """Saves manual grade to the 'evaluations' sheet."""
    evaluator_name = st.session_state.get("evaluator_name", "Manual").strip()
    if not evaluator_name: evaluator_name = "Manual"
    
    evaluation_record = Evaluation(
        run_id=run_id_to_grade,
        grader_id=evaluator_name,
        correctness_score=(1 if grade == "Correct" else 0),
        evaluation_notes=notes
    )
    gsheet_manager.append_data("evaluations", [evaluation_record])
    st.toast(f"Grade '{grade}' saved!")
    
    for msg in st.session_state.chat_history:
        if msg.get("run_id") == run_id_to_grade and msg.get("role") == "assistant":
            msg["graded"] = True
            break
    
def show_suggestion(for_run_id):
    used_names = {msg.get("suggestion", {}).get("name") for msg in st.session_state.chat_history if msg.get("suggestion")}
    unused_keys = [k for k, v in PROMPT_TAXONOMY.items() if v['name'] not in used_names]
    if not unused_keys:
        st.warning("All suggestions have been shown!")
        return
    random_key = random.choice(unused_keys)
    suggestion_data = PROMPT_TAXONOMY[random_key]
    
    suggestion_record = Suggestion(
        run_id=for_run_id, session_id=st.session_state.session_id, user_id=st.session_state.user_id,
        suggestion_key=random_key, suggestion_name=suggestion_data['name'],
        suggested_level=suggestion_data.get('level', 0), accepted=True
    )
    gsheet_manager.append_data("suggestions", [suggestion_record])
    st.toast("Suggestion saved!")

    st.session_state.chat_history.append({
        "role": "assistant", "content": "Here is a suggestion for a different prompt structure:",
        "suggestion": suggestion_data, "run_id": str(uuid.uuid4())
    })

# --- USER INTERFACE (Phần Sidebar và Layout chính không đổi) ---
init_session_state()

with st.sidebar:
    st.markdown("## Problem Setup")
    st.text("Version: v2.3.0")
    is_disabled = st.session_state.classification_complete
    st.text_input("Your Name / ID", key="evaluator_name", disabled=is_disabled)
    st.radio("Content Domain", CONTENT_DOMAINS, key="content_domain", disabled=is_disabled)
    st.radio("Cognitive Level", options=list(COGNITIVE_LEVELS.keys()), format_func=lambda x: COGNITIVE_LEVELS[x], key="cognitive_level", disabled=is_disabled)
    st.radio("Problem Context", PROBLEM_CONTEXTS, key="problem_context", disabled=is_disabled)
    st.button("Confirm Setup", on_click=confirm_classification, type="primary", use_container_width=True, disabled=is_disabled)
    st.markdown("---")
    if st.button("New Problem / Reset", use_container_width=True, on_click=reset_session): st.rerun()

st.markdown("<div style='text-align: center;'><h1>Welcome to PromptOptima</h1></div>", unsafe_allow_html=True)

if not st.session_state.classification_complete:
    st.info("Please complete the problem setup in the sidebar to begin.")
    st.stop()

# --- CHAT VIEW ---
st.markdown("---")
is_expanded = not bool(st.session_state.get("problem_text", ""))
with st.expander("**Problem Description** (Collapsible)", expanded=is_expanded):
    st.text_area("Enter the base math problem here.", key="problem_text", height=30)
    if not st.session_state.problem_text:
        st.info("Please enter a problem description to start the chat.")
        st.stop()
    
st.markdown("### Chat History")
chat_container = st.container(height=700, border=True)
with chat_container:
    history = st.session_state.chat_history
    for index, msg in enumerate(history):
        with st.chat_message(msg["role"]):
            if msg['role'] == 'assistant' and msg.get("prompt_context"):
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
                    st.code(s['template'].replace("{problem_text}", "[Your Problem]"), language='text')

                    st.markdown("**💡 Example**")
                    st.code(s['example'], language='text')

            is_last_message = (index == len(history) - 1)
            is_actionable_assistant = (msg['role'] == 'assistant' and 'prompt_analysis' in msg)
            
            # --- NEW UI FOR FEEDBACK ---
            if is_last_message and is_actionable_assistant:
                st.divider()
                with st.container(border=True):
                    analysis = msg.get('prompt_analysis', {})
                    qual_scores = analysis.get('qualitative_scores', {})
                    est_metrics = analysis.get('estimated_metrics', {})

                    st.markdown("##### 🤖 AI's Prompt Analysis")
                    st.info(f"**Overall Evaluation:**\n\n_{analysis.get('overall_evaluation', 'N/A')}_")
                    
                    if not msg.get('graded'):
                        st.markdown("##### ✍️ Your Action: Please Grade The Solution Manually")
                        grade = st.radio("Is the final answer in the solution text correct?", ("Correct", "Incorrect"), horizontal=True, key=f"grade_{msg['run_id']}")
                        notes = st.text_area("Evaluation Notes (Optional)", key=f"notes_{msg['run_id']}")
                        if st.button("Save Grade", key=f"save_{msg['run_id']}", use_container_width=True):
                            save_grade_callback(grade, msg['run_id'], notes)
                            st.rerun()
                    else:
                        st.markdown("##### Next Step")
                        if st.button("Suggestion", key=f"suggestion_{msg['run_id']}", use_container_width=True, on_click=show_suggestion, args=(msg['run_id'],)):
                            st.rerun()

# --- INPUT AREA (Không đổi) ---
st.markdown("---")
prompt = st.chat_input("Enter your custom prompt here...")
if prompt:
    handle_submission(prompt)
    st.rerun()