import os, time, json, random
from typing import Dict, Any, Optional
from string import Template
import re 

import uuid
import streamlit as st
import httpx
from openai import OpenAI

# ---------- helpers ----------
def _get_openai_api_key() -> Optional[str]:
    try:
        key = st.secrets.get("openai", {}).get("api_key")
    except Exception:
        key = os.environ.get("OPENAI_API_KEY")
    if key and "YOUR_OPENAI_API_KEY" not in str(key):
        return str(key).strip()
    return None

def _strip_code_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```json"): t = t[7:]
    elif t.startswith("```"): t = t[3:]
    if t.endswith("```"): t = t[:-3]
    return t.strip()

def _client(timeout=45.0):
    api_key = _get_openai_api_key()
    if not api_key: return None, None
    http_client = httpx.Client(timeout=timeout, trust_env=False)
    return OpenAI(api_key=api_key, http_client=http_client), http_client

# ====================================================================================
# === FIX: Hàm helper mới để đảm bảo AI trả về đủ các trường, không tin tưởng AI nữa ===
# ====================================================================================
def _ensure_schema_compliance(analysis_json: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validates the JSON from the AI and fills in any missing keys with default values.
    This makes the system resilient to the AI's "laziness".
    """
    pa = analysis_json.setdefault("prompt_analysis", {})

    # 1. Ensure 'signals' object and all its keys exist
    signals = pa.setdefault("signals", {})
    signal_defaults = {
        "tokens": 0, "sentences": 0, "avg_tokens_per_sentence": 0.0, "avg_clauses_per_sentence": 0.0,
        "cognitive_verbs_count": 0, "abstract_terms_count": 0, "numbers_count": 0, "content_words_count": 0,
        "sections_count": 0, "explicit_steps_count": 0, "has_worked_example": False, "has_formula_given": False,
        "has_hints": False, "has_output_format_rule": False, "has_verification": False, "contradictions": False
    }
    for key, default_value in signal_defaults.items():
        signals.setdefault(key, default_value)

    # 2. Ensure 'qualitative_scores' object and all its keys exist
    scores = pa.setdefault("qualitative_scores", {})
    score_defaults = {"clarity_score": 0, "specificity_score": 0, "structure_score": 0}
    for key, default_value in score_defaults.items():
        scores.setdefault(key, default_value)

    # 3. Ensure 'pattern_hits' object and all its keys exist
    patterns = pa.setdefault("pattern_hits", {})
    pattern_defaults = {
        "cognitive_terms": [], "abstract_terms": [], "meta_terms": [], "logic_connectors": [], "modals": [],
        "step_markers": [], "examples": [], "formula_markers": [], "hints": [], "numbers": [], "sections": [], "output_rules": []
    }
    for key, default_value in pattern_defaults.items():
        patterns.setdefault(key, default_value)
    
    # 4. Ensure 'ai_estimated' object and all its keys exist
    estimated = pa.setdefault("ai_estimated", {})
    estimated_defaults = {
        "mattr_like": 0.0, "reading_ease_like": 0.0, "cdi_like": 0.0, "sss_like": 0.0, "arq_like": 0.0, "confidence": "Low"
    }
    for key, default_value in estimated_defaults.items():
        estimated.setdefault(key, default_value)

    # 5. Ensure other top-level keys exist
    pa.setdefault("overall_evaluation", "N/A")
    pa.setdefault("evidence", [])

    return analysis_json

# ---------- ANALYZER: unified template ----------
ANALYZER_PROMPT_TEMPLATE = Template("""
You are an expert prompt analyst for K-12 mathematics. Your task is to evaluate a USER PROMPT and return a single, valid JSON object without any markdown or extra text.

## Analysis Schema & Instructions

### 1. `signals` (Quantitative metrics)
Extract these raw counts from the USER PROMPT:
- `tokens`: Total word tokens.
- `sentences`: Total number of sentences.
- `avg_tokens_per_sentence`: `tokens` / `sentences`.
- `avg_clauses_per_sentence`: Estimate of clauses per sentence.
- `cognitive_verbs_count`: Count of verbs indicating cognitive processes (e.g., analyze, explain, solve, compare).
- abstract_terms_count: Count of core mathematical concepts, not simple contextual nouns. Prioritize terms like 'ratio', 'perimeter', 'probability', 'variable' over words like 'apples', 'garden', 'pounds'.
- `numbers_count`: Count of numeric values.
- `content_words_count`: Count of non-stop-words.
- `sections_count`: Count of explicit sections (e.g., "Part 1", "Section A").
- `explicit_steps_count`: Count of numbered or bulleted steps (e.g., "1.", "Step 1:").
- `has_worked_example`: `true` if a worked example is provided.
- `has_formula_given`: `true` if a formula is explicitly given.
- `has_hints`: `true` if hints are provided.
- `has_output_format_rule`: `true` for constraints like "return JSON", "only the final answer".
- `has_verification`: `true` for requests like "check your work", "verify your answer".
- `contradictions`: `true` if instructions conflict (e.g., "be concise" and "explain in detail").

### 2. `qualitative_scores` (Scoring based on `signals`)
Calculate these scores from 0-100:
- `clarity_score`: Base=50. +15 if tokens>=12. +10 for clear goals. -25 for contradictions. -10 if tokens<8.
- `specificity_score`: Base=30. +30 for strict output format. +20 for explicit steps. +10 for verification request. +5 for given formulas.
- `structure_score`: Base=30. +40 for explicit steps. +15 for sections. +10 for ordered steps.

### 3. `pattern_hits` (Extracted phrases)
**THIS IS MANDATORY.** List the exact words/phrases found for each category. Return `[]` if none are found.
- `cognitive_terms`: e.g., ["solve", "explain"]
- `abstract_terms`: e.g., ["perimeter", "ratio"]
- `meta_terms`: e.g., ["reflect on", "check your work"]
- `logic_connectors`: e.g., ["if", "then", "because"]
- `modals`: e.g., ["can", "should", "might"]
- `step_markers`: e.g., ["step by step", "1.", "first"]
- `examples`: e.g., ["for example", "e.g."]
- `formula_markers`: e.g., ["=", "+", "pi"]
- `hints`: e.g., ["hint:", "remember that"]
- `numbers`: e.g., ["12", "0.5", "8"]
- `sections`: e.g., ["Part 1"]
- `output_rules`: e.g., ["return a JSON object"]

### 4. `ai_estimated` (Heuristic scores)
Provide your best estimate for these metrics:
- `mattr_like`: Lexical diversity (0.0 to 1.0).
- `reading_ease_like`: Readability score (0-100, higher is easier).
- `cdi_like`, `sss_like`, `arq_like`: Composite scores for cognitive demand, structure, and reasoning (0-100).
- `confidence`: Your confidence in this analysis ("Low", "Medium", "High").

### 5. `overall_evaluation` & `evidence`
- `overall_evaluation`: 1-2 sentence summary of prompt quality.
- `evidence`: 3 short string cues from the prompt that support your evaluation.

## JSON Object to Return
Return your analysis in this exact JSON format. **DO NOT OMIT ANY KEYS.**
{
  "prompt_analysis": {
    "signals": {
      "tokens": <int>, "sentences": <int>, "avg_tokens_per_sentence": <float>, "avg_clauses_per_sentence": <float>,
      "cognitive_verbs_count": <int>, "abstract_terms_count": <int>, "numbers_count": <int>, "content_words_count": <int>,
      "sections_count": <int>, "explicit_steps_count": <int>, "has_worked_example": <bool>, "has_formula_given": <bool>,
      "has_hints": <bool>, "has_output_format_rule": <bool>, "has_verification": <bool>, "contradictions": <bool>
    },
    "qualitative_scores": { "clarity_score": <int>, "specificity_score": <int>, "structure_score": <int> },
    "pattern_hits": {
      "cognitive_terms": ["<verb1>", "..."], "abstract_terms": ["<term1>", "..."], "meta_terms": [], "logic_connectors": [],
      "modals": [], "step_markers": [], "examples": [], "formula_markers": [], "hints": [], "numbers": [], "sections": [], "output_rules": []
    },
    "ai_estimated": {
      "mattr_like": <float>, "reading_ease_like": <float>, "cdi_like": <float>, "sss_like": <float>, "arq_like": <float>, "confidence": "<Low|Medium|High>"
    },
    "overall_evaluation": "<Your 1-2 sentence summary>",
    "evidence": ["<cue 1>", "<cue 2>", "<cue 3>"]
  }
}

## User Data
USER PROMPT:
<<<
${user_prompt}
>>>

ORIGINAL PROBLEM (context only):
<<<
${problem_text}
>>>
""")

# ---------- SOLVER ----------
SOLVER_PROMPT_TEMPLATE = Template("${user_prompt}\n\n${problem_text}\n")

# ---------- mocks ----------
def _mock_analyzer() -> Dict[str, Any]:
    st.warning("OpenAI key not found. Using MOCK ANALYZER.")
    time.sleep(0.2)
    # Return a fully compliant mock object
    mock_json = {
        "prompt_analysis": {
            "signals": {}, "qualitative_scores": {}, "pattern_hits": {}, "ai_estimated": {},
            "overall_evaluation": "Mock evaluation", "evidence": []
        }
    }
    return _ensure_schema_compliance(mock_json)

def _mock_solver() -> Dict[str, Any]:
    st.warning("OpenAI key not found. Using MOCK SOLVER.")
    time.sleep(0.3)
    return {
        "solution_text": "MOCK: step-by-step reasoning with final answer.",
        "usage": {"prompt_tokens": 80, "completion_tokens": 140},
        "latency_ms": 900, "error": None
    }

# ---------- public API ----------
def get_analysis_from_analyzer(user_prompt: str, problem_text: str = "", model="gpt-3.5-turbo") -> Dict[str, Any]:
    client, _ = _client()
    if not client:
        return _mock_analyzer()

    sys_msg = (
        "You are a strict JSON generator. "
        "Always return exactly one JSON object matching the requested schema. "
        "No markdown, no explanations."
    )
    prompt = ANALYZER_PROMPT_TEMPLATE.safe_substitute(
        user_prompt=user_prompt, problem_text=problem_text or ""
    )
    
    # Retry logic remains the same
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.0, max_tokens=1024, # Increased slightly for safety
        )
        content = resp.choices[0].message.content or "{}"
        out = json.loads(content)
    except Exception:
        # Fallback call
        resp2 = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.0, max_tokens=1024,
        )
        content2 = resp2.choices[0].message.content or "{}"
        try:
            out = json.loads(content2)
        except Exception:
            # If all else fails, create a minimal empty structure
            out = {"prompt_analysis": {}}

    # =================================================================
    # === FIX: Luôn chạy hàm dọn dẹp để đảm bảo đủ key trước khi trả về ===
    # =================================================================
    final_out = _ensure_schema_compliance(out)
    final_out["error"] = None
    return final_out

def get_solution_from_solver(user_prompt: str, problem_text: str, model="gpt-3.5-turbo") -> Dict[str, Any]:
    client, _ = _client(60.0)
    if not client: return _mock_solver()
    prompt = SOLVER_PROMPT_TEMPLATE.safe_substitute(user_prompt=user_prompt, problem_text=problem_text)
    t0 = time.time()
    resp = client.chat.completions.create(
        model=model, messages=[{"role": "user", "content": prompt}],
        temperature=0.5, max_tokens=1200,
    )
    t1 = time.time()
    usage = getattr(resp, "usage", None)
    usage_dict = None if not usage else {"prompt_tokens": usage.prompt_tokens, "completion_tokens": usage.completion_tokens}
    return {
        "solution_text": resp.choices[0].message.content,
        "usage": usage_dict, "latency_ms": int((t1 - t0) * 1000), "error": None
    }

# (The paraphrase function synthesize_prompt_from_suggestion remains unchanged)
# src/services/openai_client.py

def synthesize_prompt_from_suggestion(
    problem_text: str,
    suggestion: Dict[str, Any],
    cognitive_level: int,  # <<< THAY ĐỔI 1: Thêm tham số cognitive_level
    *,
    model: str = "gpt-3.5-turbo",
    ai_persona: Optional[str] = None, # Giữ lại để có thể ghi đè nếu cần
    strict_fill: bool = False,
) -> str:
    tpl = suggestion.get("template", "{problem_text}")

    client, _ = _client()
    if not client or strict_fill:
        # Fallback thông minh hơn
        filled_tpl = tpl.replace("{problem_text}", problem_text)
        if "{student_answer}" in filled_tpl:
            plausible_wrong_answer = "The student calculated the area as 96 square meters."
            filled_tpl = filled_tpl.replace("{student_answer}", plausible_wrong_answer)
        if "{hypothesis}" in filled_tpl:
            plausible_hypothesis = "The final number of items is directly proportional to the perimeter."
            filled_tpl = filled_tpl.replace("{hypothesis}", plausible_hypothesis)
        return filled_tpl

    # <<< THAY ĐỔI 2: Tách và mở rộng bộ Persona >>>
    educator_personas = [
        "A patient and encouraging tutor",
        "A sharp, concise university professor",
        "A friendly peer who explains things simply",
        "An examiner focused on precision and keywords",
        "A Socratic coach who asks guiding questions",
        "A motivational coach focused on building confidence"
    ]
    student_personas = [
        "A curious student who wants to know 'why'",
        "An anxious student who needs a lot of reassurance",
        "A practical student who wants real-world examples",
        "A slightly confused student asking for a simpler explanation"
    ]
    
    # 80% là educator, 20% là student để giả lập
    if random.random() < 0.8:
        persona = random.choice(educator_personas)
    else:
        persona = random.choice(student_personas)
    
    # Ghi đè persona nếu được cung cấp
    if ai_persona:
        persona = ai_persona

    # <<< THAY ĐỔI 3: Hướng dẫn từ vựng theo Cognitive Level >>>
    level_guidance = ""
    if cognitive_level == 1:
        level_guidance = "Use direct, simple language. Focus on 'how-to' and concrete steps. Keywords: calculate, find, list, show the steps."
    elif cognitive_level == 2:
        level_guidance = "Use language that promotes understanding. Focus on 'why' and 'what it means'. Keywords: explain, describe, illustrate, compare, what is the relationship."
    elif cognitive_level >= 3:
        level_guidance = "Use advanced language that requires analysis and evaluation. Focus on 'what if' and 'which is best'. Keywords: justify, critique, devise a strategy, optimize, what is the most efficient method."

    # <<< THAY ĐỔI 4: System & User Prompt được viết lại hoàn toàn >>>
    sys = (
        "You are a creative and expert prompt engineer specializing in K-12 math education. "
        "Your task is to rewrite a prompt TEMPLATE by adopting a specific PERSONA and tailoring the language to a given COGNITIVE LEVEL. "
        "You must output ONLY the final, rewritten prompt text."
    )

    user = f"""
You must rewrite the following prompt TEMPLATE.

### CONTEXT
1.  **PERSONA to adopt**: "{persona}"
2.  **COGNITIVE LEVEL of the problem**: L{cognitive_level}
3.  **GUIDANCE for L{cognitive_level}**: "{level_guidance}"

### TEMPLATE (The core task you must preserve)
{tpl}


### PROBLEM (To be inserted and used for context)
{problem_text}


### REWRITE RULES
1.  **ADAPT, DON'T JUST REPLACE**: Do not just robotically fill in the template. Creatively rewrite it to sound natural for the given PERSONA and appropriate for the COGNITIVE LEVEL. A student persona should sound like they are asking a question. An educator persona should sound like they are giving an instruction.
2.  **PRESERVE THE CORE TASK**: The final prompt must still accomplish the main goal of the TEMPLATE (e.g., 'compare 3 strategies', 'review a solution').
3.  **INTELLIGENT PLACEHOLDER FILLING**:
    * If `{{student_answer}}` is present, you MUST invent a plausible (but likely incorrect) student answer based on the PROBLEM. For example, a common conceptual error.
    * If `{{hypothesis}}` is present, you MUST invent a simple, relevant hypothesis for the PROBLEM.
    * NEVER leave placeholders like '[Student answer here]' in the output.
4.  **INSERT PROBLEM TEXT**: Replace `{{problem_text}}` with the exact PROBLEM text.
5.  **OUTPUT**: Return ONLY the final, rewritten prompt. No commentary, no explanations, no markdown.
""".strip()

    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": sys}, {"role": "user", "content": user}],
        temperature=0.7, # <<< THAY ĐỔI 5: Tăng nhiệt độ để khuyến khích sự sáng tạo
        max_tokens=600, # Tăng nhẹ để có không gian cho prompt dài hơn
    )
    out = (resp.choices[0].message.content or "").strip()
    
    # Dọn dẹp output
    if out.startswith("`") and out.endswith("`"):
        out = out.strip("`")
    if out.startswith('"') and out.endswith('"'):
        out = out.strip('"')

    return out