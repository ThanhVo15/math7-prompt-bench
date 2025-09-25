# src/services/openai_client.py

import streamlit as st
import openai
import time
import json
from typing import Dict, Any

# ==============================================================================
# --- 1. ANALYZER: AI chuyên phân tích chất lượng prompt ---
# ==============================================================================

ANALYZER_PROMPT_TEMPLATE = """
You are an expert in prompt engineering. Your task is to analyze the quality of the user's prompt.
Provide a mix of qualitative scores (on a 1-100 scale) and your best estimation for objective metrics.
Your entire output MUST be a single, valid JSON object.

**User's Prompt to Analyze:**
{user_prompt}

---
**REQUIRED JSON OUTPUT STRUCTURE:**
{
  "prompt_analysis": {
    "qualitative_scores": {
      "clarity_score": <int, score from 1-100 for how clear and unambiguous the prompt is>,
      "specificity_score": <int, score from 1-100 for how well the prompt specifies constraints and desired output>,
      "structure_score": <int, score from 1-100 for the logical structure and organization of the prompt>
    },
    "estimated_metrics": {
      "estimated_token_count": <int, your best estimate of the number of tokens>,
      "estimated_mattr_score": <float, your best estimate of the prompt's lexical diversity (MATTR) score from 1-100, window_size = 10>,
      "estimated_reading_ease": <float, your best estimate of reading ease score from 1-100, where:
        90-100 = very easy,
        70-89 = easy,
        50-69 = average,
        30-49 = difficult,
        0-29 = very difficult
      >
    },
    "overall_evaluation": "<Your brief, critical evaluation of the prompt's strengths and weaknesses.>"
  }
}
"""

def _generate_mock_analyzer_response() -> Dict[str, Any]:
    st.warning("OpenAI key not found. Generating MOCK ANALYZER RESPONSE.")
    time.sleep(0.5)
    return {
        "prompt_analysis": {
            "qualitative_scores": {"clarity_score": 75, "specificity_score": 80, "structure_score": 85},
            "estimated_metrics": {"estimated_token_count": 25, "estimated_mattr_score": 80, "estimated_reading_ease": 90},
            "overall_evaluation": "Mock evaluation: This is a well-structured and clear prompt."
        },
        "error": None
    }

def get_analysis_from_analyzer(user_prompt: str, model: str = "gpt-3.5-turbo-1106") -> Dict[str, Any]:
    try:
        api_key = st.secrets.get("openai", {}).get("api_key")
        if not api_key or "YOUR_OPENAI_API_KEY" in api_key:
            return _generate_mock_analyzer_response()

        openai.api_key = api_key
        prompt = ANALYZER_PROMPT_TEMPLATE.format(user_prompt=user_prompt)
        response = openai.ChatCompletion.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.1
        )
        result_json = json.loads(response.choices[0].message['content'])
        result_json["error"] = None
        return result_json
    except Exception as e:
        st.error(f"Analyzer API Error: {e}")
        return {"error": str(e)}

# ==============================================================================
# --- 2. SOLVER: AI chuyên giải toán (không bị mớm prompt) ---
# ==============================================================================

SOLVER_PROMPT_TEMPLATE = """
{user_prompt}

---
Problem:
{problem_text}
"""

def _generate_mock_solver_response() -> Dict[str, Any]:
    st.warning("OpenAI key not found. Generating MOCK SOLVER RESPONSE.")
    time.sleep(1)
    return {
        "solution_text": "--- MOCK SOLUTION ---\nThis is a sample solution text based on the user's prompt.",
        "usage": {"prompt_tokens": 100, "completion_tokens": 150},
        "latency_ms": 1200,
        "error": None
    }

def get_solution_from_solver(user_prompt: str, problem_text: str, model: str = "gpt-3.5-turbo-1106") -> Dict[str, Any]:
    try:
        api_key = st.secrets.get("openai", {}).get("api_key")
        if not api_key or "YOUR_OPENAI_API_KEY" in api_key:
            return _generate_mock_solver_response()

        openai.api_key = api_key
        prompt = SOLVER_PROMPT_TEMPLATE.format(user_prompt=user_prompt, problem_text=problem_text)
        start_time = time.time()
        response = openai.ChatCompletion.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5
        )
        end_time = time.time()
        
        return {
            "solution_text": response.choices[0].message['content'],
            "usage": response.usage,
            "latency_ms": int((end_time - start_time) * 1000),
            "error": None
        }
    except Exception as e:
        st.error(f"Solver API Error: {e}")
        return {"error": str(e), "solution_text": "Error generating solution."}