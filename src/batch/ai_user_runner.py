import time
import uuid
import random
from typing import List, Dict, Optional, Any
import streamlit as st
from src.services.google_sheets import get_gsheet_manager
from src.services.openai_client import (get_analysis_from_analyzer, get_solution_from_solver, synthesize_prompt_from_suggestion)
from src.core.tokenizer import AdvancedTokenizer
from src.core.metrics import BasicMetrics
from src.core.metrics_advanced import compute_advanced_metrics
from src.models.schemas import (Run, PromptMetrics, Suggestion, Evaluation, AdvancedMetricsRecord, AnalyzerScores, AnalyzerPattern, AdvancedMetricsPattern)
from src.prompts.taxonomy import PROMPT_TAXONOMY
from src.utils.text import clean_problem_text, generate_problem_id

# --- Các hàm Utility (không đổi) ---
def _safe_float(value: Any, default: float = 0.0) -> float:
    if value is None: return default
    try: return float(value)
    except (ValueError, TypeError): return default
def _safe_int(value: Any, default: int = 0) -> int:
    if value is None: return default
    try: return int(float(value))
    except (ValueError, TypeError): return default
def _canon_ccss(s: str) -> str:
    return str(s or "").split("(")[0].strip().lower()
def _parse_level_num(s: str) -> int:
    s = str(s or "")
    for ch in s:
        if ch.isdigit(): return int(ch)
    return 0
def _map_context(sheet_val: str) -> str:
    v = (sheet_val or "").strip().lower()
    return "Applied Math" if v in ["real-world", "real world", "applied", "realworld", "real"] else "Theoretical Math"
def _to_dict_any(x: Any) -> Dict:
    from dataclasses import is_dataclass, asdict
    if x is None: return {}
    if hasattr(x, "model_dump"): return x.model_dump()
    if hasattr(x, "dict"):
        try: return x.dict()
        except Exception: pass
    if is_dataclass(x): return asdict(x)
    if isinstance(x, dict): return x
    return {k: v for k, v in getattr(x, "__dict__", {}).items()}
def _append_rows_safe(gsheet, sheet_name: str, items: list):
    if not items: return
    rows = [_to_dict_any(it) for it in items]
    try:
        gsheet.append_data(sheet_name, rows)
    except Exception as e:
        st.error(f"Error writing to sheet '{sheet_name}': {e}")

# --- Hàm Helper xử lý một prompt (không đổi) ---
def _process_single_prompt_variant(*, run_id: str, prompt_text: str, persona: str, problem_id: str, problem_text: str, content_domain: str, cognitive_level: int, problem_context: str, level_hint: int, prompt_name: str, sug_key: Optional[int], ai_user_id: str, ai_grader: str, analyzer_model: str, solver_model: str, tokenizer: AdvancedTokenizer, metrics: BasicMetrics) -> Optional[Dict[str, Any]]:
    try:
        analysis = get_analysis_from_analyzer(user_prompt=prompt_text, problem_text=problem_text, model=analyzer_model)
        prompt_analysis = analysis.get("prompt_analysis", {}) or {}
        sol = get_solution_from_solver(user_prompt=prompt_text, problem_text=problem_text, model=solver_model)
        solution_text = sol.get("solution_text") or "--- NO SOLUTION TEXT ---"
        ph = prompt_analysis.get("pattern_hits", {})
        adv_vals = compute_advanced_metrics(prompt_text, ai_pattern_hits=ph)
        pm = metrics.compute(prompt_text, tokenizer, run_id=run_id, w=10)
        cdi, sss, arq, hits = adv_vals.get("cdi", {}), adv_vals.get("sss", {}), adv_vals.get("arq", {}), adv_vals.get("hits", {})
        sig, bands, ai_est = prompt_analysis.get("signals", {}), prompt_analysis.get("qualitative_scores", {}), prompt_analysis.get("ai_estimated", {})
        session_id_for_run = str(uuid.uuid4())[:8]
        adv_record = AdvancedMetricsRecord( run_id=run_id, session_id=session_id_for_run, user_id=ai_user_id, prompt_text=prompt_text, cdi_rate_cognitive_verbs=_safe_float(cdi.get("rate_cognitive_verbs")), cdi_lexical_density=_safe_float(cdi.get("lexical_density")), cdi_clauses_per_sentence=_safe_float(cdi.get("clauses_per_sentence")), cdi_rate_abstract_terms=_safe_float(cdi.get("rate_abstract_terms")), cdi_composite=_safe_float(cdi.get("cdi_composite")), sss_n_examples=_safe_int(sss.get("n_examples")), sss_n_step_markers=_safe_int(sss.get("n_step_markers")), sss_n_formula_markers=_safe_int(sss.get("n_formula_markers")), sss_n_hints=_safe_int(sss.get("n_hints")), sss_weighted=_safe_float(sss.get("sss_weighted")), sss_raw=_safe_int(sss.get("sss_raw")), arq_abstract_terms=_safe_int(arq.get("abstract_terms")), arq_numbers=_safe_int(arq.get("numbers")), arq_ratio=_safe_float(arq.get("ratio")), arq_meta_bonus=_safe_float(arq.get("meta_bonus")), arq_score=_safe_float(arq.get("arq_score")),)
        metrics_pattern_record = AdvancedMetricsPattern( run_id=run_id, session_id=session_id_for_run, user_id=ai_user_id, prompt_text=prompt_text, cdi_c_rate=_safe_float(cdi.get("rate_cognitive_verbs")), cdi_a_rate=_safe_float(cdi.get("rate_abstract_terms")), cdi_ld=_safe_float(cdi.get("lexical_density")), cdi_cps=_safe_float(cdi.get("clauses_per_sentence")), sss_log=_safe_float(sss.get("sss_weighted")), arq_meta=bool(arq.get("meta_gate", False)), c_terms_backend="|".join(hits.get("c_terms", [])), a_terms_backend="|".join(hits.get("a_terms", [])), meta_terms_backend="|".join(hits.get("meta_terms", [])), examples_hits="|".join(hits.get("examples", [])), step_markers_hits="|".join(hits.get("step_markers", [])), formula_marks_hits="|".join(hits.get("formula_marks", [])), hints_hits="|".join(hits.get("hints", [])), numbers_hits="|".join(hits.get("numbers", [])), cdi_index=_safe_float(cdi.get("cdi_composite")), sss_total=_safe_int(sss.get("sss_raw")), arq_ratio=_safe_float(arq.get("ratio")), arq_index=_safe_float(arq.get("arq_score")),)
        analyzer_score_record = AnalyzerScores( run_id=run_id, session_id=session_id_for_run, user_id=ai_user_id, prompt_text=prompt_text, problem_id=problem_id, tokens=_safe_int(sig.get("tokens")), sentences=_safe_int(sig.get("sentences")), avg_tokens_per_sentence=_safe_float(sig.get("avg_tokens_per_sentence")), avg_clauses_per_sentence=_safe_float(sig.get("avg_clauses_per_sentence")), cognitive_verbs_count=_safe_int(sig.get("cognitive_verbs_count")), abstract_terms_count=_safe_int(sig.get("abstract_terms_count")), clarity_score=_safe_int(bands.get("clarity_score")), specificity_score=_safe_int(bands.get("specificity_score")), structure_score=_safe_int(bands.get("structure_score")), mattr_like_0_1=_safe_float(ai_est.get("mattr_like")), reading_ease_like=_safe_float(ai_est.get("reading_ease_like")), cdi_like=_safe_float(ai_est.get("cdi_like")), sss_like=_safe_float(ai_est.get("sss_like")), arq_like=_safe_float(ai_est.get("arq_like")), confidence=str(ai_est.get("confidence", "")),)
        analyzer_pattern_record = AnalyzerPattern( run_id=run_id, session_id=session_id_for_run, user_id=ai_user_id, prompt_text=prompt_text, problem_id=problem_id, cognitive_terms_ai="|".join(ph.get("cognitive_terms", [])), abstract_terms_ai="|".join(ph.get("abstract_terms", [])), meta_terms_ai="|".join(ph.get("meta_terms", [])), logic_connectors_ai="|".join(ph.get("logic_connectors", [])), modals_ai="|".join(ph.get("modals", [])), step_markers_ai="|".join(ph.get("step_markers", [])), examples_ai="|".join(ph.get("examples", [])), formula_markers_ai="|".join(ph.get("formula_markers", [])), hints_ai="|".join(ph.get("hints", [])), numbers_ai="|".join(ph.get("numbers", [])), sections_ai="|".join(ph.get("sections", [])), output_rules_ai="|".join(ph.get("output_rules", [])),)
        run_obj = Run( run_id=run_id, session_id=session_id_for_run, user_id=ai_user_id, ai_persona=persona, problem_id=problem_id, problem_text=problem_text, content_domain=content_domain, cognitive_level=cognitive_level, problem_context=problem_context, prompt_text=prompt_text, prompt_level=level_hint, prompt_name=prompt_name, solver_model_name=solver_model, response_text=solution_text, latency_ms=_safe_int(sol.get("latency_ms")), tokens_in=_safe_int((sol.get("usage") or {}).get("prompt_tokens")), tokens_out=_safe_int((sol.get("usage") or {}).get("completion_tokens")),)
        suggestion_record = None
        if sug_key is not None:
            suggestion_record = Suggestion( run_id=run_id, session_id=run_obj.session_id, user_id=ai_user_id, suggestion_key=_safe_int(sug_key), suggestion_name=prompt_name, suggested_level=level_hint, accepted=True,)
        evaluation_record = Evaluation( run_id=run_id, grader_id=ai_grader, correctness_score=1, evaluation_notes="Auto (AI batch). Please review.",)
        return { "run": run_obj, "metrics": pm, "adv_metrics": adv_record, "metrics_pattern": metrics_pattern_record, "analyzer_score": analyzer_score_record, "analyzer_pattern": analyzer_pattern_record, "suggestion": suggestion_record, "evaluation": evaluation_record }
    except Exception as e:
        st.warning(f"Skipping run for prompt '{prompt_name}' (ID: {run_id[:8]}) due to error: {e}")
        return None

# -------------- Main Function (Corrected) --------------
def run_ai_user_batch(
    *, sheet_name: str = "problems", ccss_filters: List[str], level_filters: List[str],
    context_filters: List[str], evaluator_name: str, include_baseline: bool = True,
    analyzer_model: str = "gpt-3.5-turbo", solver_model: str = "gpt-3.5-turbo",
    paraphraser_model: str = "gpt-3.5-turbo", throttle_sec: float = 0.15, flush_every: int = 20,
):
    gsheet = get_gsheet_manager()
    df = gsheet.get_df(sheet_name)
    if df.empty:
        st.error(f"Sheet '{sheet_name}' is empty or could not be read.")
        return {"selected": 0, "created_runs": 0}

    cols = {c.lower().strip(): c for c in df.columns}
    need = ["ccss", "level", "abstract / real-world", "problem"]
    for n in need:
        if n not in cols:
            st.error(f"Missing column '{n}' in sheet '{sheet_name}'.")
            return {"selected": 0, "created_runs": 0}
    
    # --- Filtering Logic (No changes) ---
    ccss_norm = {_canon_ccss(x) for x in ccss_filters} if ccss_filters else set()
    lvl_set_nums = {_parse_level_num(x) for x in level_filters} if level_filters else set()
    ctx_norm = {str(x).strip().lower() for x in context_filters} if context_filters else set()
    def pass_ccss(x): return not ccss_norm or _canon_ccss(x) in ccss_norm
    def pass_level(x): return not lvl_set_nums or _parse_level_num(x) in lvl_set_nums
    def pass_ctx(x): return not ctx_norm or (str(x or "").strip().lower()) in ctx_norm
    df_sel = df[df[cols["ccss"]].apply(pass_ccss) & df[cols["level"]].apply(pass_level) & df[cols["abstract / real-world"]].apply(pass_ctx)].copy()

    if df_sel.empty:
        st.warning("No problems match the selected filters.")
        return {"selected": 0, "created_runs": 0}

    # --- Initialization ---
    tokenizer, metrics = AdvancedTokenizer(), BasicMetrics()
    buffers = { "runs": [], "metrics_deterministic": [], "metrics_advanced": [], "suggestions": [], "evaluations": [], "analyzer_scores": [], "analyzer_patterns": [], "metrics_patterns": [] }
    taxonomy_keys = sorted(PROMPT_TAXONOMY.keys())
    total_tasks = len(df_sel) * (len(taxonomy_keys) + (1 if include_baseline else 0))
    done, created_runs_count = 0, 0
    progress, status = st.progress(0.0), st.empty()
    ai_user_id = f"{evaluator_name} - AI"

    educator_personas = ["A patient and encouraging tutor", "A sharp, concise university professor", "A friendly peer who explains things simply", "An examiner focused on precision and keywords", "A Socratic coach", "A motivational coach"]
    student_personas = ["A curious student who wants to know 'why'", "An anxious student who needs a lot of reassurance", "A practical student who wants real-world examples", "A slightly confused student asking for a simpler explanation"]
    persona_pool = educator_personas + student_personas

    # --- Main Loop ---
    for _, row in df_sel.iterrows():
        problem_text = clean_problem_text(row[cols["problem"]])
        problem_id = generate_problem_id(problem_text)
        content_domain = str(row[cols["ccss"]]).split("(")[0].strip()
        cognitive_level = _parse_level_num(row[cols["level"]])
        problem_context = _map_context(row[cols["abstract / real-world"]])
        
        # <<< SỬA LỖI QUAN TRỌNG: CHỌN PERSONA MỘT LẦN DUY NHẤT CHO MỖI BÀI TOÁN >>>
        persona_for_this_problem = random.choice(persona_pool)

        variants = []
        if include_baseline:
            variants.append((f"Solve this problem:\n{problem_text}", persona_for_this_problem, 0, "Zero-Shot Baseline", None))

        for k in taxonomy_keys:
                    sug = PROMPT_TAXONOMY[k]
                    # SỬA Ở ĐÂY: Giải nén tuple, chỉ lấy giá trị đầu tiên (prompt_text)
                    # Dấu gạch dưới (_) dùng để chứa giá trị persona trả về mà chúng ta không cần dùng đến.
                    prompt_text, _ = synthesize_prompt_from_suggestion(
                        problem_text=problem_text,
                        suggestion=sug,
                        cognitive_level=cognitive_level,
                        ai_persona=persona_for_this_problem,
                        model=paraphraser_model,
                        strict_fill=False,
                    )
                    variants.append((prompt_text, persona_for_this_problem, int(sug.get("level", 0)), str(sug["name"]), k))
                    
        for prompt_text, persona, level_hint, prompt_name, sug_key in variants:
            processed_data = _process_single_prompt_variant(
                run_id=str(uuid.uuid4()), prompt_text=prompt_text, persona=persona,
                problem_id=problem_id, problem_text=problem_text, content_domain=content_domain,
                cognitive_level=cognitive_level, problem_context=problem_context,
                level_hint=level_hint, prompt_name=prompt_name, sug_key=sug_key,
                ai_user_id=ai_user_id, ai_grader=ai_user_id,
                analyzer_model=analyzer_model, solver_model=solver_model,
                tokenizer=tokenizer, metrics=metrics
            )

            done += 1
            if processed_data:
                created_runs_count += 1
                buffers["runs"].append(processed_data["run"])
                buffers["metrics_deterministic"].append(processed_data["metrics"])
                buffers["metrics_advanced"].append(processed_data["adv_metrics"])
                buffers["metrics_patterns"].append(processed_data["metrics_pattern"])
                buffers["analyzer_scores"].append(processed_data["analyzer_score"])
                buffers["analyzer_patterns"].append(processed_data["analyzer_pattern"])
                if processed_data["suggestion"]:
                    buffers["suggestions"].append(processed_data["suggestion"])
                buffers["evaluations"].append(processed_data["evaluation"])

            status.write(f"AI User: {done}/{total_tasks} | {prompt_name} | Persona: {persona}")
            progress.progress(min(1.0, done / total_tasks))

            if created_runs_count > 0 and created_runs_count % flush_every == 0:
                for sheet_name, items in buffers.items():
                    if items: _append_rows_safe(gsheet, sheet_name, items)
                    items.clear()
            
            time.sleep(throttle_sec)

    # Final flush
    for sheet_name, items in buffers.items():
        if items: _append_rows_safe(gsheet, sheet_name, items)

    progress.progress(1.0)
    status.write("✅ AI User process complete.")
    return {"selected": int(len(df_sel)), "created_runs": created_runs_count}