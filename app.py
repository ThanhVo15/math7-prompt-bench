# app.py

import streamlit as st
import uuid
import random
from datetime import datetime

# Import local modules
from src.core.tokenizer import AdvancedTokenizer
from src.core.metrics import BasicMetrics
from src.services.openai_client import get_solver_response, get_judger_evaluation
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

# --- SESSION STATE MANAGEMENT ---
def init_session_state():
    """Initializes all necessary keys in the session state."""
    if 'session_id' not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.user_id = "user_" + str(uuid.uuid4())[:8]
        st.session_state.classification_complete = False
        st.session_state.view_mode = None
        st.session_state.grade_submitted = False
        st.session_state.chat_history = []
        st.session_state.problem_text = ""
        st.session_state.evaluator_name = ""

# --- CALLBACKS & LOGIC FUNCTIONS ---
def reset_session():
    """Clears the session state but preserves key identifiers for continuity."""
    evaluator = st.session_state.get("evaluator_name", "")
    user_id = st.session_state.get("user_id", "user_" + str(uuid.uuid4())[:8])
    session_id = st.session_state.get("session_id", str(uuid.uuid4()))
    st.session_state.clear()
    init_session_state()
    st.session_state.evaluator_name = evaluator
    st.session_state.user_id = user_id
    st.session_state.session_id = session_id
    
def confirm_classification():
    """Confirms the problem setup, locking the sidebar inputs."""
    if not st.session_state.get("evaluator_name", "").strip():
        st.warning("Please enter your name or ID before confirming.")
        return
    st.session_state.classification_complete = True

def set_view_mode(mode):
    """Sets the user's preferred view (Analysis or Chat)."""
    st.session_state.view_mode = mode
    if mode == 'chat':
        st.session_state.chat_history = []

def handle_submission(user_input):
    """The core logic for handling a prompt submission."""
    problem_text = st.session_state.problem_text
    final_input = user_input

    if not problem_text.strip():
        st.error("A problem description is required.")
        return

    current_run_id = str(uuid.uuid4())
    st.session_state.chat_history.append({"role": "user", "content": user_input, "run_id": current_run_id})

    # Step 1: Get solution and prompt analysis from Solver AI
    with st.spinner("Solver AI is generating solution and analyzing prompt..."):
        solver_response = get_solver_response(problem_text=problem_text, user_prompt=final_input)
    if solver_response.get("error"): return
    prompt_analysis = solver_response.get("prompt_analysis", {})
    solution_text = solver_response.get("solution_text", "Error: No solution text found.")

    # Step 2: Get solution evaluation from Judger AI
    with st.spinner("Judger AI is evaluating the solution..."):
        judger_response = get_judger_evaluation(
            problem_text=problem_text, user_prompt=final_input, solver_solution=solution_text
        )
    if judger_response.get("error"): return
    solution_evaluation = judger_response.get("solution_evaluation", {})
    
    run_id = current_run_id

    # Step 3: Append assistant's response to chat history for display
    st.session_state.chat_history.append({
        "role": "assistant", "content": solution_text,
        "problem_context": problem_text, "prompt_context": final_input,
        "prompt_rationale": prompt_analysis.get("analysis_rationale"),
        "solution_evaluation": solution_evaluation, # Store the entire evaluation object
        "run_id": run_id, "graded": False
    })
    
    # Step 4: Log all collected data to Google Sheets
    metrics_record = metrics_service.compute(final_input, tokenizer, run_id=run_id)
    gsheet_manager.append_data("metrics_deterministic", [metrics_record])

    run_record = Run(
        run_id=run_id, session_id=st.session_state.session_id, user_id=st.session_state.user_id,
        problem_text=problem_text, content_domain=st.session_state.content_domain,
        cognitive_level=st.session_state.cognitive_level, problem_context=st.session_state.problem_context,
        prompt_text=final_input, prompt_level=0,
        model_name="gpt-3.5-turbo-1106", response_text=solution_text,
        estimated_mattr=prompt_analysis.get("estimated_mattr"),
        estimated_reading_ease=prompt_analysis.get("estimated_reading_ease"),
        analysis_rationale=prompt_analysis.get("analysis_rationale"),
        solution_evaluation=solution_evaluation.get("evaluation_text"),
        latency_ms=solver_response.get("latency_ms", 0) + judger_response.get("latency_ms", 0),
        tokens_in=solver_response.get("usage", {}).get("prompt_tokens", 0) + judger_response.get("usage", {}).get("prompt_tokens", 0),
        tokens_out=solver_response.get("usage", {}).get("completion_tokens", 0) + judger_response.get("usage", {}).get("completion_tokens", 0)
    )
    gsheet_manager.append_data("runs", [run_record])

def save_grade_callback(grade, run_id_to_grade, notes, ai_evaluation):
    """Saves manual grade and AI-generated scores to the 'evaluations' sheet."""
    evaluator_name = st.session_state.get("evaluator_name", "Manual").strip()
    if not evaluator_name: evaluator_name = "Manual"

    correctness_score = 1 if grade == "Correct" else 0
    detailed_scores = ai_evaluation.get('explanation_scores_detailed', {})
    
    evaluation_record = Evaluation(
        run_id=run_id_to_grade,
        grader_id=st.session_state.user_id,
        evaluator_model_name=evaluator_name, 
        correctness_score=correctness_score,
        evaluation_notes=notes,
        explanation_score=ai_evaluation.get('explanation_score_total'),
        consistency_score=ai_evaluation.get('predicted_consistency_score'),
        logical_soundness_score=detailed_scores.get('logical_soundness'),
        step_completeness_score=detailed_scores.get('step_completeness'),
        calculation_accuracy_score=detailed_scores.get('calculation_accuracy'),
        pedagogical_clarity_score=detailed_scores.get('pedagogical_clarity')
    )
    gsheet_manager.append_data("evaluations", [evaluation_record])
    st.toast(f"Grade '{grade}' saved!")
    
    for msg in st.session_state.chat_history:
        if msg.get("run_id") == run_id_to_grade and msg.get("role") == "assistant":
            msg["graded"] = True
            break
    
def show_suggestion(for_run_id):
    """Shows a new prompt suggestion and logs it to the 'suggestions' sheet."""
    # Lấy danh sách các suggestion đã dùng trong session
    used_names = {msg.get("suggestion", {}).get("name") for msg in st.session_state.chat_history if msg.get("suggestion")}
    # Lọc các key chưa dùng
    unused_keys = [k for k, v in PROMPT_TAXONOMY.items() if v['name'] not in used_names]
    if not unused_keys:
        st.warning("All suggestions have been shown!")
        return
    random_key = random.choice(unused_keys)
    suggestion_data = PROMPT_TAXONOMY[random_key]

    suggestion_record = Suggestion(
        run_id=for_run_id, session_id=st.session_state.session_id, user_id=st.session_state.user_id,
        suggestion_name=suggestion_data['name'],
        suggestion_template=suggestion_data['template'],
        suggestion_example=suggestion_data['example'],
        suggested_level=suggestion_data.get('level', 0),
        accepted=True
    )
    gsheet_manager.append_data("suggestions", [suggestion_record])
    st.toast("Suggestion saved!")

    st.session_state.chat_history.append({
        "role": "assistant", "content": "Here is a suggestion for a different prompt structure:",
        "suggestion": suggestion_data, "run_id": str(uuid.uuid4())
    })

# --- USER INTERFACE ---
init_session_state()

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("## Problem Setup")
    is_disabled = st.session_state.classification_complete
    st.text_input("Your Name / ID", key="evaluator_name", disabled=is_disabled)
    st.radio("Content Domain", CONTENT_DOMAINS, key="content_domain", disabled=is_disabled)
    st.radio("Cognitive Level", options=list(COGNITIVE_LEVELS.keys()), format_func=lambda x: COGNITIVE_LEVELS[x], key="cognitive_level", disabled=is_disabled)
    st.radio("Problem Context", PROBLEM_CONTEXTS, key="problem_context", disabled=is_disabled)
    st.button("Confirm Setup", on_click=confirm_classification, type="primary", use_container_width=True, disabled=is_disabled)
    st.markdown("---")
    if st.session_state.classification_complete:
        st.markdown("### View Mode")
        if st.button("Analysis View", use_container_width=True): set_view_mode('analysis')
        if st.button("Chat View", use_container_width=True): set_view_mode('chat')
    st.markdown("---")
    if st.button("New Problem / Reset", use_container_width=True, on_click=reset_session): st.rerun()

# --- MAIN PAGE LAYOUT ---
st.markdown("<div style='text-align: center;'><h1>Welcome to PromptOptima</h1></div>", unsafe_allow_html=True)

if not st.session_state.classification_complete:
    st.info("Please complete the problem setup in the sidebar to begin.")
    st.stop()

if not st.session_state.view_mode:
    st.markdown("---")
    st.subheader("Choose Your Interface")
    col1, col2 = st.columns(2)
    col1.button("Analysis View", on_click=set_view_mode, args=('analysis',), use_container_width=True)
    col2.button("Chat View", on_click=set_view_mode, args=('chat',), use_container_width=True)

elif st.session_state.view_mode == 'analysis':
    st.error("Analysis View is not implemented in this version.")

# --- CHAT VIEW ---
elif st.session_state.view_mode == 'chat':
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
                # Display context and main content
                if msg['role'] == 'assistant' and msg.get("problem_context"):
                    with st.expander("Show Context for this Response"):
                        st.markdown("**Your Prompt:**"); st.container(border=True).markdown(f"_{msg['prompt_context']}_")
                        st.markdown("**Problem:**"); st.container(border=True).markdown(f"{msg['problem_context']}")
                        
                st.markdown(msg["content"])
                
                # Display suggestion if it's a suggestion message
                if msg.get("suggestion"):
                    s = msg["suggestion"]
                    st.info(f"**Suggestion: {s['name']}**\n\n{s['description']}")
                    with st.expander("Show Structure & Example"):
                        st.code(s['template'].replace("{problem_text}", "[Your Problem]"), 'text')
                        st.code(s['example'], 'text')

                # Logic to display feedback and action buttons for the last assistant message
                is_last_message = (index == len(history) - 1)
                is_actionable_assistant = (msg['role'] == 'assistant' and 'prompt_rationale' in msg)
                if is_last_message and is_actionable_assistant:
                    st.divider()
                    with st.container(border=True):
                        evaluation_obj = msg.get('solution_evaluation', {})
                        st.markdown("##### AI's Feedback")
                        col_prompt, col_solution = st.columns(2)
                        with col_prompt: st.info(f"**On Your Prompt:**\n\n_{msg.get('prompt_rationale', 'N/A')}_")
                        with col_solution: st.success(f"**On the Solution:**\n\n_{evaluation_obj.get('evaluation_text', 'N/A')}_")
                        st.markdown("---")
                        
                        if not msg.get('graded'):
                            st.markdown("##### Your Action: Please Grade This Response")
                            grade = st.radio("Grade:", ("Correct", "Incorrect"), horizontal=True, key=f"grade_{msg['run_id']}")
                            notes = st.text_area("Evaluation Notes (Optional)", key=f"notes_{msg['run_id']}")
                            if st.button("Save Grade", key=f"save_{msg['run_id']}", use_container_width=True):
                                save_grade_callback(grade, msg['run_id'], notes, evaluation_obj)
                                st.rerun()
                        else:
                            st.markdown("##### Next Step")
                            if st.button("Suggestion", key=f"suggestion_{msg['run_id']}", use_container_width=True, on_click=show_suggestion, args=(msg['run_id'],)):
                                st.rerun()

    # --- INPUT AREA ---
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
