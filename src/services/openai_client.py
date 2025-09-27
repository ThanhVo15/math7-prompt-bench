# src/services/openai_client.py
import os
import time
import json
from typing import Dict, Any, Optional
from string import Template

import streamlit as st
import httpx
from openai import OpenAI

# ======================================================================
# Helpers
# ======================================================================

def _get_openai_api_key() -> Optional[str]:
    """Return a usable OpenAI API key from Streamlit secrets or environment variables."""
    key = None
    try:
        key = st.secrets.get("openai", {}).get("api_key")
    except Exception:
        pass
    if not key:
        key = os.environ.get("OPENAI_API_KEY")
    if key and "YOUR_OPENAI_API_KEY" not in str(key):
        return str(key).strip()
    return None

def _strip_code_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```json"):
        t = t[7:]
    elif t.startswith("```"):
        t = t[3:]
    if t.endswith("```"):
        t = t[:-3]
    return t.strip()

# ======================================================================
# Analyzer prompt (using Template -> no need to escape curly braces)
# ======================================================================

ANALYZER_PROMPT_TEMPLATE = Template("""
You are an expert in prompt engineering. Evaluate the quality of the user's prompt and produce a single JSON object.

USER PROMPT:
<<<
${user_prompt}
>>>

EVALUATION GOAL
Score how effectively the prompt communicates intent and constraints so that an LLM can produce a high-quality answer.

SCORING RUBRIC (0–100, integers)
1) clarity_score: How clear and unambiguous is the task?
   - 90–100: Crystal-clear objective, audience, and success criteria; no ambiguity.
   - 70–89: Clear task; minor ambiguities that won't derail the model.
   - 50–69: Understandable but missing key context or has mild ambiguity.
   - 30–49: Vague; several missing details; could lead to wrong outputs.
   - 0–29 : Very unclear or contradictory.

2) specificity_score: How well are constraints & output expectations specified?
   Consider: required steps, output format (bullets, JSON, A/B/C), reasoning depth, examples, domain constraints, evaluation criteria.
   - 90–100: Precise constraints and explicit output format; includes necessary boundaries/examples.
   - 70–89 : Good constraints and hints; output expectations mostly explicit.
   - 50–69 : Some constraints but several unspecified expectations.
   - 30–49 : Few constraints; output shape is largely unspecified.
   - 0–29  : Bare instruction (e.g., "Solve this problem."); no constraints.

3) structure_score: Organization and instruction layout.
   Consider: headings, numbered steps, sections, order of operations, disallow/allow rules.
   - 90–100: Strong sectioning/steps; easy to follow; no redundancy.
   - 70–89 : Reasonably organized with minor issues.
   - 50–69 : Mixed structure; some run-on sentences; order unclear in places.
   - 30–49 : Poorly organized; hard to follow.
   - 0–29  : No structure; scattered or single vague sentence.

HEURISTICS (apply BEFORE scoring; adjust bands accordingly)
- If prompt is minimal (e.g., "Solve this problem."), set specificity_score ≤ 30 and structure_score ≤ 30.
- If prompt contains explicit steps, sections, or a required output format (e.g., JSON/bullets), structure_score ≥ 70.
- If the prompt defines success criteria or verification checks, boost specificity_score by +5–10 (cap at 100).
- Penalize any contradictions or open-ended vagueness in clarity_score (−10 to −30 depending on severity).

ESTIMATED METRICS (0–100 floats except token count)
- estimated_token_count (int): Rough estimate of tokens in the user prompt. Use both views and pick the larger:
  A) char_len / 4.0
  B) word_count / 0.75
  Round to nearest integer.
- estimated_mattr_score (float, 0–100): Approximate lexical diversity (window_size=10). 
  Heuristic: more unique content words vs repeats ⇒ higher score.
  Map low diversity ~ 30–50, moderate ~ 50–70, high ~ 70–90, exceptional ~ 90–100.
- estimated_reading_ease (float, 0–100): Overall ease of reading (not grade level). Use:
  90–100 very easy; 70–89 easy; 50–69 average; 30–49 difficult; 0–29 very difficult.
  Short sentences, common words ⇒ higher score; long, nested, jargon-heavy ⇒ lower.

OUTPUT REQUIREMENTS (MUST FOLLOW)
- Output ONLY a single JSON object with EXACTLY this schema (no prose, no code fences).
- Numbers must be JSON numbers (no quotes, no % signs). Use '.' as decimal separator.
- All scores must be within [0,100]. Round qualitative scores to integers; keep estimated_* as reasonable numbers.

REQUIRED JSON OUTPUT STRUCTURE:
{
  "prompt_analysis": {
    "qualitative_scores": {
      "clarity_score": <int>,
      "specificity_score": <int>,
      "structure_score": <int>
    },
    "estimated_metrics": {
      "estimated_token_count": <int>,
      "estimated_mattr_score": <float>,
      "estimated_reading_ease": <float>
    },
    "overall_evaluation": "<one or two crisp sentences summarizing strengths and weaknesses>"
  }
}
""")

def _generate_mock_analyzer_response() -> Dict[str, Any]:
    st.warning("OpenAI key not found. Generating MOCK ANALYZER RESPONSE.")
    time.sleep(0.3)
    return {
        "prompt_analysis": {
            "qualitative_scores": {
                "clarity_score": 75,
                "specificity_score": 80,
                "structure_score": 85,
            },
            "estimated_metrics": {
                "estimated_token_count": 25,
                "estimated_mattr_score": 0.8,
                "estimated_reading_ease": 0.9,
            },
            "overall_evaluation": "Mock evaluation: This is a well-structured and clear prompt.",
        },
        "error": None,
    }

def _generate_mock_solver_response() -> Dict[str, Any]:
    st.warning("OpenAI key not found. Generating MOCK SOLVER RESPONSE.")
    time.sleep(0.5)
    return {
        "solution_text": "--- MOCK SOLUTION ---\nThis is a sample solution text based on the user's prompt.",
        "usage": {"prompt_tokens": 100, "completion_tokens": 150},
        "latency_ms": 1200,
        "error": None,
    }

# ======================================================================
# Public API
# ======================================================================

def get_analysis_from_analyzer(user_prompt: str, model: str = "gpt-3.5-turbo") -> Dict[str, Any]:
    api_key = _get_openai_api_key()
    if not api_key:
        return _generate_mock_analyzer_response()

    # Avoid proxy/env interference that led to "proxies" TypeError in some stacks
    http_client = httpx.Client(timeout=30.0, trust_env=False)
    client = OpenAI(api_key=api_key, http_client=http_client)

    prompt = ANALYZER_PROMPT_TEMPLATE.safe_substitute(user_prompt=user_prompt)
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.1,
        max_tokens=600,
    )

    content = response.choices[0].message.content or "{}"
    try:
        result_json = json.loads(content)
    except json.JSONDecodeError:
        # Try stripping code fences
        try:
            result_json = json.loads(_strip_code_fences(content))
        except Exception:
            # Last resort: return minimal structure
            result_json = {
                "prompt_analysis": {
                    "qualitative_scores": {},
                    "estimated_metrics": {},
                    "overall_evaluation": content[:500],
                }
            }

    result_json["error"] = None
    return result_json


SOLVER_PROMPT_TEMPLATE = Template("""
${user_prompt}
${problem_text}
""")

def get_solution_from_solver(user_prompt: str, problem_text: str, model: str = "gpt-3.5-turbo") -> Dict[str, Any]:
    api_key = _get_openai_api_key()
    if not api_key:
        return _generate_mock_solver_response()

    http_client = httpx.Client(timeout=60.0, trust_env=False)
    client = OpenAI(api_key=api_key, http_client=http_client)

    prompt = SOLVER_PROMPT_TEMPLATE.safe_substitute(
        user_prompt=user_prompt, problem_text=problem_text
    )
    start_time = time.time()
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
        max_tokens=1200,
    )
    end_time = time.time()

    usage = None
    if getattr(response, "usage", None):
        usage = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
        }

    return {
        "solution_text": response.choices[0].message.content,
        "usage": usage,
        "latency_ms": int((end_time - start_time) * 1000),
        "error": None,
    }
