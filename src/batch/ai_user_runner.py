import time
import uuid
import random
from typing import List, Dict, Optional, Any

import streamlit as st

from src.services.google_sheets import get_gsheet_manager
from src.services.openai_client import (
    get_analysis_from_analyzer,
    get_solution_from_solver,
    synthesize_prompt_from_suggestion,
)
from src.core.tokenizer import AdvancedTokenizer
from src.core.metrics import BasicMetrics
from src.core.metrics_advanced import compute_advanced_metrics
from src.models.schemas import (
    Run, PromptMetrics, Suggestion, Evaluation,
    AdvancedMetricsRecord, AnalyzerScores, AnalyzerPattern, AdvancedMetricsPattern
)
from src.prompts.taxonomy import PROMPT_TAXONOMY
from src.utils.text import clean_problem_text, generate_problem_id

# --- Các hàm Utils giữ nguyên ---
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
        st.error(f"Lỗi ghi vào sheet '{sheet_name}': {e}")


# =================================================================================
# === NÂNG CẤP 1: Tách logic xử lý ra hàm helper riêng                       ===
# === NÂNG CẤP 2: Bọc toàn bộ logic trong try-except để đảm bảo tính toàn vẹn   ===
# =================================================================================
def _process_single_prompt_variant(
    *,
    run_id: str,
    prompt_text: str,
    problem_id: str,
    problem_text: str,
    content_domain: str,
    cognitive_level: int,
    problem_context: str,
    level_hint: int,
    prompt_name: str,
    sug_key: Optional[int],
    ai_user_id: str,
    ai_grader: str,
    persona: str,
    analyzer_model: str,
    solver_model: str,
    tokenizer: AdvancedTokenizer,
    metrics: BasicMetrics
) -> Optional[Dict[str, Any]]:
    """
    Xử lý toàn bộ chu trình cho một prompt: Analyzer -> Solver -> Metrics -> Gói dữ liệu.
    Trả về một dictionary chứa tất cả các đối tượng dữ liệu, hoặc None nếu có lỗi.
    """
    try:
        # --- 1. AI Calls ---
        analysis = get_analysis_from_analyzer(
            user_prompt=prompt_text, problem_text=problem_text, model=analyzer_model
        )
        prompt_analysis = analysis.get("prompt_analysis", {}) or {}

        sol = get_solution_from_solver(
            user_prompt=prompt_text, problem_text=problem_text, model=solver_model
        )
        solution_text = sol.get("solution_text") or "--- NO SOLUTION TEXT ---"

        # --- 2. Metrics Calculation ---
        ph = prompt_analysis.get("pattern_hits", {})
        adv_vals = compute_advanced_metrics(prompt_text, ai_pattern_hits=ph)
        pm = metrics.compute(prompt_text, tokenizer, run_id=run_id, w=10)

        # --- 3. Data Assembly ---
        cdi = adv_vals.get("cdi", {})
        sss = adv_vals.get("sss", {})
        arq = adv_vals.get("arq", {})
        hits = adv_vals.get("hits", {})
        sig = prompt_analysis.get("signals", {})
        bands = prompt_analysis.get("qualitative_scores", {})
        ai_est = prompt_analysis.get("ai_estimated", {})

        # Gói dữ liệu vào các Pydantic models
        adv_record = AdvancedMetricsRecord(
            run_id=run_id, session_id=str(uuid.uuid4())[:8], user_id=ai_user_id, prompt_text=prompt_text,
            cdi_rate_cognitive_verbs=_safe_float(cdi.get("rate_cognitive_verbs")),
            cdi_lexical_density=_safe_float(cdi.get("lexical_density")),
            cdi_clauses_per_sentence=_safe_float(cdi.get("clauses_per_sentence")),
            cdi_rate_abstract_terms=_safe_float(cdi.get("rate_abstract_terms")),
            cdi_composite=_safe_float(cdi.get("cdi_composite")),
            sss_n_examples=_safe_int(sss.get("n_examples")), sss_n_step_markers=_safe_int(sss.get("n_step_markers")),
            sss_n_formula_markers=_safe_int(sss.get("n_formula_markers")), sss_n_hints=_safe_int(sss.get("n_hints")),
            sss_weighted=_safe_float(sss.get("sss_weighted")),
            arq_abstract_terms=_safe_int(arq.get("abstract_terms")), arq_numbers=_safe_int(arq.get("numbers")),
            arq_ratio=_safe_float(arq.get("ratio")), arq_meta_bonus=_safe_float(arq.get("meta_bonus")),
            arq_score=_safe_float(arq.get("arq_score")),
        )
        
        metrics_pattern_record = AdvancedMetricsPattern(
            run_id=run_id, session_id=adv_record.session_id, user_id=ai_user_id, prompt_text=prompt_text,
            cdi_c_rate=_safe_float(cdi.get("rate_cognitive_verbs")), cdi_a_rate=_safe_float(cdi.get("rate_abstract_terms")),
            cdi_ld=_safe_float(cdi.get("lexical_density")), cdi_cps=_safe_float(cdi.get("clauses_per_sentence")),
            sss_log=_safe_float(sss.get("sss_weighted")), arq_meta=bool(arq.get("meta_gate")),
            c_terms_backend="|".join(hits.get("c_terms", [])), a_terms_backend="|".join(hits.get("a_terms", [])),
            meta_terms_backend="|".join(hits.get("meta_terms", [])),
            examples_hits="|".join(hits.get("examples", [])), step_markers_hits="|".join(hits.get("step_markers", [])),
            formula_marks_hits="|".join(hits.get("formula_marks", [])), hints_hits="|".join(hits.get("hints", [])),
            numbers_hits="|".join(hits.get("numbers", [])),
            cdi_index=_safe_float(cdi.get("cdi_composite")),
            sss_total=_safe_int(sss.get("sss_raw")),
            arq_ratio=_safe_float(arq.get("ratio")), arq_index=_safe_float(arq.get("arq_score")),
        )

        analyzer_score_record = AnalyzerScores(
            run_id=run_id, session_id=adv_record.session_id, user_id=ai_user_id, prompt_text=prompt_text, problem_id=problem_id,
            tokens=_safe_int(sig.get("tokens")), sentences=_safe_int(sig.get("sentences")),
            avg_tokens_per_sentence=_safe_float(sig.get("avg_tokens_per_sentence")),
            avg_clauses_per_sentence=_safe_float(sig.get("avg_clauses_per_sentence")),
            cognitive_verbs_count=_safe_int(sig.get("cognitive_verbs_count")), abstract_terms_count=_safe_int(sig.get("abstract_terms_count")),
            clarity_score=_safe_int(bands.get("clarity_score")), specificity_score=_safe_int(bands.get("specificity_score")),
            structure_score=_safe_int(bands.get("structure_score")), mattr_like_0_1=_safe_float(ai_est.get("mattr_like")),
            reading_ease_like=_safe_float(ai_est.get("reading_ease_like")), cdi_like=_safe_float(ai_est.get("cdi_like")),
            sss_like=_safe_float(ai_est.get("sss_like")), arq_like=_safe_float(ai_est.get("arq_like")),
            confidence=str(ai_est.get("confidence", "")),
        )

        analyzer_pattern_record = AnalyzerPattern(
            run_id=run_id, session_id=adv_record.session_id, user_id=ai_user_id, prompt_text=prompt_text, problem_id=problem_id,
            cognitive_terms_ai="|".join(ph.get("cognitive_terms", [])), abstract_terms_ai="|".join(ph.get("abstract_terms", [])),
            meta_terms_ai="|".join(ph.get("meta_terms", [])), logic_connectors_ai="|".join(ph.get("logic_connectors", [])),
            modals_ai="|".join(ph.get("modals", [])), step_markers_ai="|".join(ph.get("step_markers", [])),
            examples_ai="|".join(ph.get("examples", [])), formula_markers_ai="|".join(ph.get("formula_markers", [])),
            hints_ai="|".join(ph.get("hints", [])), numbers_ai="|".join(ph.get("numbers", [])),
            sections_ai="|".join(ph.get("sections", [])), output_rules_ai="|".join(ph.get("output_rules", [])),
        )

        run_obj = Run(
            run_id=run_id, session_id=adv_record.session_id, user_id=ai_user_id, ai_persona=persona,
            problem_id=problem_id, problem_text=problem_text, content_domain=content_domain,
            cognitive_level=cognitive_level, problem_context=problem_context,
            prompt_text=prompt_text, prompt_level=level_hint, prompt_name=prompt_name,
            solver_model_name=solver_model, response_text=solution_text,
            latency_ms=_safe_int(sol.get("latency_ms")),
            tokens_in=_safe_int((sol.get("usage") or {}).get("prompt_tokens")),
            tokens_out=_safe_int((sol.get("usage") or {}).get("completion_tokens")),
        )

        suggestion_record = None
        if sug_key is not None:
            suggestion_record = Suggestion(
                run_id=run_id, session_id=run_obj.session_id, user_id=ai_user_id,
                suggestion_key=_safe_int(sug_key), suggestion_name=prompt_name,
                suggested_level=level_hint, accepted=True,
            )
        
        evaluation_record = Evaluation(
            run_id=run_id, grader_id=ai_grader, correctness_score=1,
            evaluation_notes="Auto (AI batch). Please review.",
        )

        # Trả về một dictionary chứa tất cả các đối tượng
        return {
            "run": run_obj, "metrics": pm, "adv_metrics": adv_record,
            "metrics_pattern": metrics_pattern_record, "analyzer_score": analyzer_score_record,
            "analyzer_pattern": analyzer_pattern_record, "suggestion": suggestion_record,
            "evaluation": evaluation_record
        }

    except Exception as e:
        st.warning(f"Lỗi khi xử lý prompt '{prompt_name}' cho problem ID {problem_id[:8]}: {e}")
        return None


# -------------- Main --------------
def run_ai_user_batch(
    *,
    sheet_name: str = "problems",
    ccss_filters: List[str],
    level_filters: List[str],
    context_filters: List[str],
    evaluator_name: str,
    include_baseline: bool = True,
    analyzer_model: str = "gpt-3.5-turbo",
    solver_model: str = "gpt-3.5-turbo",
    paraphraser_model: str = "gpt-3.5-turbo",
    throttle_sec: float = 0.15,
    flush_every: int = 20,
):
    gsheet = get_gsheet_manager(_version=2)
    df = gsheet.get_df(sheet_name)
    if df.empty:
        st.error(f"Sheet '{sheet_name}' rỗng hoặc đọc lỗi.")
        return {"selected": 0, "created_runs": 0}

    cols = {c.lower().strip(): c for c in df.columns}
    need = ["ccss", "level", "abstract / real-world", "problem"]
    for n in need:
        if n not in cols:
            st.error(f"Thiếu cột '{n}' trong sheet '{sheet_name}'.")
            return {"selected": 0, "created_runs": 0}

    ccss_norm = {_canon_ccss(x) for x in ccss_filters} if ccss_filters else set()
    lvl_set_nums = {_parse_level_num(x) for x in level_filters} if level_filters else set()
    ctx_norm = {str(x).strip().lower() for x in context_filters} if context_filters else set()

    def pass_ccss(x): return True if not ccss_norm else _canon_ccss(x) in ccss_norm
    def pass_level(x): return True if not lvl_set_nums else _parse_level_num(x) in lvl_set_nums
    def pass_ctx(x):
        if not ctx_norm: return True
        v = str(x or "").strip().lower()
        return v in ctx_norm

    df_sel = df[
        df[cols["ccss"]].apply(pass_ccss)
        & df[cols["level"]].apply(pass_level)
        & df[cols["abstract / real-world"]].apply(pass_ctx)
    ].copy()

    if df_sel.empty:
        st.warning("Không có problem nào khớp bộ lọc.")
        return {"selected": 0, "created_runs": 0}

    tokenizer = AdvancedTokenizer()
    metrics = BasicMetrics()

    runs_buf, metrics_buf, adv_buf = [], [], []
    suggestions_buf, evals_buf = [], []
    analyzer_scores_buf, analyzer_patterns_buf, metrics_patterns_buf = [], [], []

    taxonomy_keys = sorted(PROMPT_TAXONOMY.keys())
    total_tasks = len(df_sel) * (len(taxonomy_keys) + (1 if include_baseline else 0))
    done = 0

    progress = st.progress(0.0)
    status = st.empty()

    ai_user_id = f"{evaluator_name} - AI"
    ai_grader = ai_user_id

    persona_pool = [
        "concise teacher", "friendly tutor", "examiner style", "Socratic coach",
        "motivational tutor", "precision-focused analyst", "step-by-step coach", "structured outline mentor",
    ]

    for _, row in df_sel.iterrows():
        raw_problem = row[cols["problem"]]
        problem_text = clean_problem_text(raw_problem)
        problem_id = generate_problem_id(problem_text)
        content_domain = str(row[cols["ccss"]]).split("(")[0].strip()
        cognitive_level = _parse_level_num(row[cols["level"]])
        problem_context = _map_context(row[cols["abstract / real-world"]])

        persona = random.choice(persona_pool)

        variants = []
        if include_baseline:
            baseline_text = f"Solve this problem:\n{problem_text}"
            variants.append((baseline_text, 1, "Zero-Shot Baseline", None))

        for k in taxonomy_keys:
            sug = PROMPT_TAXONOMY[k]
            prompt_text = synthesize_prompt_from_suggestion(
                problem_text=problem_text, suggestion=sug,cognitive_level=cognitive_level, model=paraphraser_model,
                ai_persona=persona, strict_fill=False,
            )
            variants.append((prompt_text, int(sug.get("level", 0)), str(sug["name"]), k))

        for prompt_text, level_hint, prompt_name, sug_key in variants:
            run_id = str(uuid.uuid4())

            # Analyzer
            try:
                analysis = get_analysis_from_analyzer(user_prompt=prompt_text, problem_text=problem_text, model=analyzer_model)
                prompt_analysis = analysis.get("prompt_analysis", {}) or {}
            except Exception as e:
                prompt_analysis = {}
                st.warning(f"Analyzer lỗi: {e}")

            # Solver
            try:
                sol = get_solution_from_solver(user_prompt=prompt_text, problem_text=problem_text, model=solver_model)
                solution_text = sol.get("solution_text") or ""
            except Exception as e:
                sol, solution_text = {}, f"--- ERROR --- {e}"
                st.warning(f"Solver lỗi: {e}")

            # Metrics
            try:
                pm = metrics.compute(prompt_text, tokenizer, run_id=run_id, w=10)
                metrics_buf.append(pm)
            except Exception:
                pass

            # Advanced metrics
            adv_vals = {}
            try:
                adv_vals = compute_advanced_metrics(prompt_text, ai_pattern_hits=ph)
                cdi = adv_vals.get("cdi", {})
                sss = adv_vals.get("sss", {})
                arq = adv_vals.get("arq", {})
                hits = adv_vals.get("hits", {})

                adv_buf.append(AdvancedMetricsRecord(
                    run_id=run_id, session_id=str(uuid.uuid4())[:8], user_id=ai_user_id,
                    prompt_text=prompt_text,
                    cdi_rate_cognitive_verbs=_safe_float(cdi.get("rate_cognitive_verbs")),
                    cdi_lexical_density=_safe_float(cdi.get("lexical_density")),
                    cdi_clauses_per_sentence=_safe_float(cdi.get("clauses_per_sentence")),
                    cdi_rate_abstract_terms=_safe_float(cdi.get("rate_abstract_terms")),
                    cdi_composite=_safe_float(cdi.get("cdi_composite")),
                    sss_n_examples=_safe_int(sss.get("n_examples")),
                    sss_n_step_markers=_safe_int(sss.get("n_step_markers")),
                    sss_n_formula_markers=_safe_int(sss.get("n_formula_markers")),
                    sss_n_hints=_safe_int(sss.get("n_hints")),
                    sss_weighted=_safe_float(sss.get("sss_weighted")),
                    arq_abstract_terms=_safe_int(arq.get("abstract_terms")),
                    arq_numbers=_safe_int(arq.get("numbers")),
                    arq_ratio=_safe_float(arq.get("ratio")),
                    arq_meta_bonus=_safe_float(arq.get("meta_bonus")),
                    arq_score=_safe_float(arq.get("arq_score")),
                ))
                
                metrics_patterns_buf.append(AdvancedMetricsPattern(
                    run_id=run_id, session_id=str(uuid.uuid4())[:8], user_id=ai_user_id,
                    prompt_text=prompt_text,
                    cdi_c_rate=_safe_float(cdi.get("rate_cognitive_verbs")),
                    cdi_a_rate=_safe_float(cdi.get("rate_abstract_terms")),
                    cdi_ld=_safe_float(cdi.get("lexical_density")),
                    cdi_cps=_safe_float(cdi.get("clauses_per_sentence")),
                    sss_log=_safe_float(sss.get("sss_weighted")),
                    arq_meta=_safe_float(arq.get("meta_bonus")),
                    c_terms_backend="|".join(hits.get("c_terms", [])),
                    a_terms_backend="|".join(hits.get("a_terms", [])),
                    meta_terms_backend="|".join(hits.get("meta_terms", [])),
                    examples_hits="|".join(hits.get("examples", [])),
                    step_markers_hits="|".join(hits.get("step_markers", [])),
                    formula_marks_hits="|".join(hits.get("formula_marks", [])),
                    hints_hits="|".join(hits.get("hints", [])),
                    numbers_hits="|".join(hits.get("numbers", [])),
                    cdi_index=_safe_float(cdi.get("cdi_composite")),
                    sss_total=(_safe_int(sss.get("n_examples")) + _safe_int(sss.get("n_step_markers")) +
                               _safe_int(sss.get("n_formula_markers")) + _safe_int(sss.get("n_hints"))),
                    arq_ratio=_safe_float(arq.get("ratio")),
                    arq_index=_safe_float(arq.get("arq_score")),
                ))

            except Exception as e:
                st.warning(f"Lỗi tính toán/ghi nhận advanced metrics cho run_id {run_id}: {e}")

            # Analyzer Scores + Pattern
            sig = (prompt_analysis.get("signals") or {})
            bands = (prompt_analysis.get("qualitative_scores") or {})
            ai_est = (prompt_analysis.get("ai_estimated") or {})
            ph = (prompt_analysis.get("pattern_hits") or {})
            
            # =========================================================================
            # === FIX: Sử dụng hàm ép kiểu an toàn khi đọc dữ liệu từ AI Analyzer    ===
            # =========================================================================
            analyzer_scores_buf.append(AnalyzerScores(
                run_id=run_id, session_id=str(uuid.uuid4())[:8], user_id=ai_user_id,
                prompt_text=prompt_text, problem_id=problem_id,
                tokens=_safe_int(sig.get("tokens")),
                sentences=_safe_int(sig.get("sentences")),
                avg_tokens_per_sentence=_safe_float(sig.get("avg_tokens_per_sentence")),
                avg_clauses_per_sentence=_safe_float(sig.get("avg_clauses_per_sentence")),
                cognitive_verbs_count=_safe_int(sig.get("cognitive_verbs_count")),
                abstract_terms_count=_safe_int(sig.get("abstract_terms_count")),
                clarity_score=_safe_int(bands.get("clarity_score")),
                specificity_score=_safe_int(bands.get("specificity_score")),
                structure_score=_safe_int(bands.get("structure_score")),
                mattr_like=_safe_float(ai_est.get("mattr_like")),
                reading_ease_like=_safe_float(ai_est.get("reading_ease_like")),
                cdi_like=_safe_float(ai_est.get("cdi_like")),
                sss_like=_safe_float(ai_est.get("sss_like")),
                arq_like=_safe_float(ai_est.get("arq_like")),
                confidence=str(ai_est.get("confidence", "")),
            ))

            analyzer_patterns_buf.append(AnalyzerPattern(
                run_id=run_id, session_id=str(uuid.uuid4())[:8], user_id=ai_user_id,
                prompt_text=prompt_text, problem_id=problem_id,
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
            ))
            
            # Suggestion + Evaluation + Run
            run_obj = Run(
                run_id=run_id, session_id=str(uuid.uuid4())[:8], user_id=ai_user_id,
                problem_id=problem_id, problem_text=problem_text, content_domain=content_domain,
                cognitive_level=cognitive_level, problem_context=problem_context,
                prompt_text=prompt_text, prompt_level=level_hint, prompt_name=prompt_name,
                solver_model_name=solver_model, response_text=solution_text,
                clarity_score=_safe_int(bands.get("clarity_score")),
                specificity_score=_safe_int(bands.get("specificity_score")),
                structure_score=_safe_int(bands.get("structure_score")),
                estimated_token_count=_safe_int(sig.get("tokens")),
                estimated_mattr_score=_safe_float(ai_est.get("mattr_like")),
                estimated_reading_ease=_safe_float(ai_est.get("reading_ease_like")),
                cdi_composite=_safe_float(adv_vals.get("cdi", {}).get("cdi_composite")),
                sss_weighted=_safe_float(adv_vals.get("sss", {}).get("sss_weighted")),
                arq_score=_safe_float(adv_vals.get("arq", {}).get("arq_score")),
                analysis_rationale=prompt_analysis.get("overall_evaluation"),
                latency_ms=_safe_int(sol.get("latency_ms")),
                tokens_in=_safe_int((sol.get("usage") or {}).get("prompt_tokens")),
                tokens_out=_safe_int((sol.get("usage") or {}).get("completion_tokens")),
            )
            run_row = _to_dict_any(run_obj)
            run_row["ai_persona"] = persona
            runs_buf.append(run_row)

            if sug_key is not None:
                suggestions_buf.append(Suggestion(
                    run_id=run_id, session_id=run_row["session_id"],
                    user_id=run_row["user_id"], suggestion_key=_safe_int(sug_key),
                    suggestion_name=prompt_name, suggested_level=level_hint, accepted=True,
                ))

            evals_buf.append(Evaluation(
                run_id=run_id, grader_id=ai_grader, correctness_score=1,
                evaluation_notes="Auto (AI batch). Please review.",
            ))

            done += 1
            if len(runs_buf) >= flush_every:
                _append_rows_safe(gsheet, "runs", runs_buf); runs_buf.clear()
                _append_rows_safe(gsheet, "metrics_deterministic", metrics_buf); metrics_buf.clear()
                _append_rows_safe(gsheet, "metrics_advanced", adv_buf); adv_buf.clear()
                _append_rows_safe(gsheet, "suggestions", suggestions_buf); suggestions_buf.clear()
                _append_rows_safe(gsheet, "evaluations", evals_buf); evals_buf.clear()
                _append_rows_safe(gsheet, "analyzer_scores", analyzer_scores_buf); analyzer_scores_buf.clear()
                _append_rows_safe(gsheet, "analyzer_patterns", analyzer_patterns_buf); analyzer_patterns_buf.clear()
                _append_rows_safe(gsheet, "metrics_patterns", metrics_patterns_buf); metrics_patterns_buf.clear()

            status.write(f"AI User: {done}/{total_tasks} | {content_domain} | L{cognitive_level} | {prompt_name} | persona={persona}")
            progress.progress(min(1.0, done / total_tasks))
            time.sleep(throttle_sec)

    _append_rows_safe(gsheet, "runs", runs_buf)
    _append_rows_safe(gsheet, "metrics_deterministic", metrics_buf)
    _append_rows_safe(gsheet, "metrics_advanced", adv_buf)
    _append_rows_safe(gsheet, "suggestions", suggestions_buf)
    _append_rows_safe(gsheet, "evaluations", evals_buf)
    _append_rows_safe(gsheet, "analyzer_scores", analyzer_scores_buf)
    _append_rows_safe(gsheet, "analyzer_patterns", analyzer_patterns_buf)
    _append_rows_safe(gsheet, "metrics_patterns", metrics_patterns_buf)

    progress.progress(1.0)
    status.write("✅ AI User hoàn tất.")
    return {"selected": int(len(df_sel)), "created_runs": int(total_tasks)}