import streamlit as st
import openai
import time
import json
from typing import Dict, Any

# ==============================================================================
# --- 1. SOLVER: Vừa giải toán, vừa tự phân tích prompt (e.g., GPT-3.5) ---
# ==============================================================================

SOLVER_PROMPT_TEMPLATE = """
You are a large language model. Your task is twofold:
1.  Based on the **User's Instructions** provided below, provide a clear, step-by-step solution to the **Problem Description**.
2.  Analyze the linguistic qualities of the User's Instructions.

Your entire output MUST be a single, valid JSON object with the exact structure below.

**Problem Description:**
{problem_text}

**User's Instructions (Prompt to be analyzed):**
{user_prompt}

---
**REQUIRED JSON OUTPUT STRUCTURE:**
{
  "prompt_analysis": {
    "estimated_mattr": <float between 0.0 and 1.0, your estimation of the prompt's lexical diversity>,
    "estimated_reading_ease": <float between 0.0 and 1.0, where 1.0 is very easy to read. Format to 2 decimal places>,
    "analysis_rationale": "<Your brief analysis of the user's prompt, focusing on identifying the core request and any specific constraints given.>"
  },
  "solution_text": "<Your full, step-by-step solution to the math problem>"
}
"""

def _generate_mock_solver_response() -> Dict[str, Any]:
    """Generates a mock response for the Solver."""
    st.warning("OpenAI key not found. Generating a MOCK SOLVER RESPONSE.")
    time.sleep(1)
    return {
        "prompt_analysis": {"estimated_mattr": 0.5, "estimated_reading_ease": 0.50, "analysis_rationale": "Mock rationale: The user wants a direct solution."},
        "solution_text": "--- MOCK SOLUTION ---\nThis is a sample solution text generated because no API key was found.",
        "usage": {"prompt_tokens": 100, "completion_tokens": 150},
        "latency_ms": 1200, "error": None
    }

def get_solver_response(problem_text: str, user_prompt: str, model: str = "gpt-3.5-turbo-1106") -> Dict[str, Any]:
    try:
        api_key = st.secrets.get("openai", {}).get("api_key")
        if not api_key or "YOUR_OPENAI_API_KEY" in api_key:
            return _generate_mock_solver_response()

        openai.api_key = api_key
        prompt = SOLVER_PROMPT_TEMPLATE.format(problem_text=problem_text, user_prompt=user_prompt)
        start_time = time.time()
        response = openai.ChatCompletion.create(model=model, messages=[{"role": "user", "content": prompt}], response_format={"type": "json_object"}, temperature=0.5)
        end_time = time.time()
        result_json = json.loads(response.choices[0].message['content'])
        result_json["usage"] = response.usage
        result_json["latency_ms"] = int((end_time - start_time) * 1000)
        result_json["error"] = None
        return result_json
    except Exception as e:
        st.error(f"Solver API Error: {e}")
        return {"prompt_analysis": {}, "solution_text": "Error generating solution.", "usage": {}, "latency_ms": 0, "error": str(e)}

# ==============================================================================
# --- 2. JUDGER: Đánh giá solution và tính toán các chỉ số chất lượng ---
# ==============================================================================

JUDGER_PROMPT_TEMPLATE = """
You are an expert AI analyst and master teacher. Your task is to critically evaluate an AI-generated solution to a 7th-grade math problem and provide quantitative scores.
Your entire output MUST be a single, valid JSON object.

**1. Original Problem:**
{problem_text}

**2. User's Prompt that generated the solution:**
{user_prompt}

**3. The Solver AI's Solution to evaluate:**
{solver_solution}

---
**YOUR TASKS:**

1.  **Provide a qualitative evaluation:** Write a brief, critical evaluation of the Solver AI's solution.
2.  **Score the explanation quality:** Based on the rubric below, provide a score for each of the 4 criteria (integer from 1 to 4 points each).
    * **Logical Soundness (1-4):** Is the reasoning clear and correct?
    * **Step Completeness (1-4):** Are all necessary steps shown?
    * **Calculation Accuracy (1-4):** Are the calculations correct?
    * **Pedagogical Clarity (1-4):** Is the explanation easy for a 7th grader to understand?
3.  **Predict Consistency:** Predict the solution's consistency on a scale from 0.0 to 1.0. A deterministic, unambiguous solution should score high (e.g., 1.0).

**REQUIRED JSON OUTPUT STRUCTURE:**
{
  "solution_evaluation": {
    "evaluation_text": "<Your brief but critical evaluation of the solver's solution>",
    "explanation_score_total": <float, SUM of the 4 scores below, max 16.0>,
    "explanation_scores_detailed": {
        "logical_soundness": <int, 1-4>,
        "step_completeness": <int, 1-4>,
        "calculation_accuracy": <int, 1-4>,
        "pedagogical_clarity": <int, 1-4>
    },
    "predicted_consistency_score": <float, 0.0 to 1.0>
  }
}
"""

# ----- FIX: BỔ SUNG LẠI HÀM BỊ THIẾU -----
def _generate_mock_judger_response() -> Dict[str, Any]:
    """Generates a mock response for the Judger."""
    st.warning("OpenAI key not found. Generating MOCK JUDGER EVALUATION.")
    time.sleep(0.5)
    return {
        "solution_evaluation": {
            "evaluation_text": "Mock evaluation: The solution appears to be structured correctly.",
            "explanation_score_total": 14.0,
            "explanation_scores_detailed": {
                "logical_soundness": 4,
                "step_completeness": 3,
                "calculation_accuracy": 4,
                "pedagogical_clarity": 3
            },
            "predicted_consistency_score": 0.9,
        },
        "usage": {"prompt_tokens": 200, "completion_tokens": 80},
        "latency_ms": 1800, "error": None
    }

def get_judger_evaluation(problem_text: str, user_prompt: str, solver_solution: str, model: str = "gpt-4o") -> Dict[str, Any]:
    try:
        api_key = st.secrets.get("openai", {}).get("api_key")
        if not api_key or "YOUR_OPENAI_API_KEY" in api_key:
            # Sửa lại để gọi hàm mock đã được bổ sung
            return _generate_mock_judger_response()
            
        openai.api_key = api_key
        prompt = JUDGER_PROMPT_TEMPLATE.format(problem_text=problem_text, user_prompt=user_prompt, solver_solution=solver_solution)
        start_time = time.time()
        response = openai.ChatCompletion.create(model=model, messages=[{"role": "user", "content": prompt}], response_format={"type": "json_object"}, temperature=0.1)
        end_time = time.time()
        result_json = json.loads(response.choices[0].message['content'])
        result_json["usage"] = response.usage
        result_json["latency_ms"] = int((end_time - start_time) * 1000)
        result_json["error"] = None
        return result_json
    except Exception as e:
        st.error(f"Judger API Error: {e}")
        return {"solution_evaluation": {}, "usage": {}, "latency_ms": 0, "error": str(e)}