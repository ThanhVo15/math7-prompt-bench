# src/services/openai_client.py
import os, time, json, random
from typing import Dict, Any, Optional
from string import Template

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

# ---------- ANALYZER: unified template ----------
ANALYZER_PROMPT_TEMPLATE = Template("""
You are an expert in prompt engineering for K–12 mathematics. Evaluate the USER PROMPT.
Return ONLY one JSON object (no markdown), and DO NOT solve the problem.

SCORING: produce numeric 0..100 scores using the rules below. Cap to [0,100]. Be consistent and deterministic.

Signals to detect (extract first):
- tokens, sentences, avg_tokens_per_sentence, avg_clauses_per_sentence
- cognitive_verbs_count, abstract_terms_count, numbers_count, content_words_count
- sections_count (headings/parts), explicit_steps_count (1., 2., or "Step N")
- has_worked_example, has_formula_given, has_hints
- has_output_format_rule (e.g., "ONLY", "exact format", "JSON", "return exactly")
- has_verification (e.g., "Final Answer", "verify", "check", "show your work")
- contradictions (boolean) if the instruction conflicts (e.g., "ONLY one line" then ask multiple items).

SCORING RULES (numeric only):

clarity_score (0..100):
- Base = 50
- +15 if tokens >= 12
- +10 if the prompt clearly states the task/goal (e.g., "determine", "solve", "compute", "evaluate")
- -25 if contradictions == true
- -10 if tokens < 8 (too short)
- Clamp to 0..100

specificity_score (0..100):
- Base = 30
- +30 if has_output_format_rule == true (strict output / JSON / exact format)
- +20 if explicit_steps_count >= 2
- +10 if has_verification == true (final answer / verify / check / show work)
- +5  if has_formula_given == true
- Clamp to 0..100

structure_score (0..100):
- Base = 30
- +40 if explicit_steps_count >= 2
- +15 if sections_count >= 1 (headings/parts/sections)
- +10 if the steps are clearly ordered/numbered (1., 2., 3. or "Step N")
- Clamp to 0..100

ai_estimated (heuristics; numeric only):
- mattr_like: 0..1 estimate of lexical diversity (window=10)
- reading_ease_like: 0..100 (higher=easier)
- cdi_like, sss_like, arq_like: scalar 0..100 rough indicators
- confidence: "Low" | "Medium" | "High"

Return JSON with this exact schema:

{
  "prompt_analysis": {
    "signals": {
      "tokens": <int>,
      "sentences": <int>,
      "avg_tokens_per_sentence": <float>,
      "avg_clauses_per_sentence": <float>,
      "cognitive_verbs_count": <int>,
      "abstract_terms_count": <int>,
      "numbers_count": <int>,
      "content_words_count": <int>,
      "sections_count": <int>,
      "explicit_steps_count": <int>,
      "has_worked_example": <bool>,
      "has_formula_given": <bool>,
      "has_hints": <bool>,
      "has_output_format_rule": <bool>,
      "has_verification": <bool>,
      "contradictions": <bool>
    },
    "qualitative_scores": {
      "clarity_score": <int>,        // 0..100 (no bands)
      "specificity_score": <int>,    // 0..100
      "structure_score": <int>       // 0..100
    },
    "ai_estimated": {
      "mattr_like": <float>,         // 0..1
      "reading_ease_like": <float>,  // 0..100
      "cdi_like": <float>,           // 0..100
      "sss_like": <float>,           // 0..100
      "arq_like": <float>,           // 0..100
      "confidence": "<Low|Medium|High>"
    },
    "overall_evaluation": "<1–2 sentences: strengths & weaknesses>",
    "evidence": ["<short cue 1>", "<cue 2>", "<cue 3>"]
  }
}

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
    return {
        "prompt_analysis": {
            "qualitative_scores": {"clarity_score": 72, "specificity_score": 68, "structure_score": 70},
            "estimated_metrics": {
                "estimated_token_count": 40,
                "estimated_mattr_score": 62.0,
                "estimated_reading_ease": 74.0,
                "estimated_cdi": 55.0, "estimated_sss": 35.0, "estimated_arq": 48.0
            },
            "overall_evaluation": "Mostly clear; could strengthen output constraints and verification."
        },
        "error": None
    }

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

    def _call():
        return client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": sys_msg},
                      {"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.0, max_tokens=800,
        )

    # try once
    resp = _call()
    content = resp.choices[0].message.content or "{}"
    try:
        out = json.loads(content)
        out["error"] = None
        return out
    except Exception:
        # retry with even stricter reminder
        strict_user = (
            "Return ONLY valid JSON per the schema. No prose. "
            "If unsure, estimate based on heuristics in the prompt."
        )
        resp2 = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": sys_msg},
                      {"role": "user", "content": prompt},
                      {"role": "user", "content": strict_user}],
            response_format={"type": "json_object"},
            temperature=0.0, max_tokens=800,
        )
        content2 = resp2.choices[0].message.content or "{}"
        try:
            out = json.loads(content2)
            out["error"] = None
            return out
        except Exception:
            # final local heuristic fallback (never leave blanks)
            from src.core.metrics import BasicMetrics
            from src.core.tokenizer import AdvancedTokenizer
            bm = BasicMetrics().compute(user_prompt, AdvancedTokenizer(), run_id=str(uuid.uuid4()))
            # Heuristic bands
            txt = user_prompt.strip().lower()
            has_steps = any(k in txt for k in ["step", "1)", "2)", "•", "-", "json", "output:"])
            has_verify = any(k in txt for k in ["check", "verify", "show your work", "explain why"])
            bare = len(user_prompt.split()) < 6

            clarity = 80
            spec = 60
            struct = 60
            if bare:
                spec = min(spec, 30); struct = min(struct, 30); clarity = 50
            if has_steps: struct = max(struct, 75)
            if has_verify: spec = min(100, spec + 8)

            result_json = {
                "prompt_analysis": {
                    "qualitative_scores": {
                        "clarity_score": int(clarity),
                        "specificity_score": int(spec),
                        "structure_score": int(struct)
                    },
                    "estimated_metrics": {
                        "estimated_token_count": int(max(len(user_prompt)/4.0, len(user_prompt.split())/0.75)),
                        "estimated_mattr_score": float(bm.mattr),
                        "estimated_reading_ease": float(bm.reading_ease),
                    },
                    "overall_evaluation": "Fallback heuristic: JSON parse failed; scores estimated locally."
                },
                "error": "model_json_failed"
            }
            return result_json

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

def synthesize_prompt_from_suggestion(problem_text: str, suggestion: Dict[str, Any],
                                      *, target_style: Optional[str] = None, model="gpt-3.5-turbo") -> str:
    client, _ = _client()
    tpl = suggestion.get("template", "{problem_text}")
    if not client:
        return tpl.replace("{problem_text}", problem_text)

    style_pool = [
        "concise teacher", "friendly tutor", "examiner style", "step-by-step coach",
        "Socratic Q&A", "structured outline", "JSON output requirement", "bullets then final answer"
    ]
    style = target_style or random.choice(style_pool)

    sys = "You rewrite user prompts. Output ONLY the rewritten prompt, no quotes, no code fences, no solution."
    user = f"""
Rewrite the instruction prompt for this math problem using the structure idea below.
Vary tone/verbosity/format slightly to avoid duplicates, but stay faithful to the structure.

STRUCTURE NAME: {suggestion.get('name', 'Suggestion')}
GUIDELINE: {suggestion.get('description','')}
TEMPLATE (reference only): {tpl}
EXAMPLE (reference only): {suggestion.get('example','')}
STYLE TARGET (loose): {style}

MUST:
- Include this problem verbatim where appropriate:
{problem_text}
- Do NOT solve the problem. Produce ONLY the instruction prompt the user would type.
- Bullets/steps/sections allowed. Keep length natural.
""".strip()

    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": sys}, {"role": "user", "content": user}],
        temperature=0.7, max_tokens=500,
    )
    out = (resp.choices[0].message.content or "").strip()
    if out.startswith("```"): out = _strip_code_fences(out)
    return out
