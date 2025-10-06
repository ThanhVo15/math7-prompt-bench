# src/batch/ai_user_runner.py
import time
import uuid
import random
from typing import List, Tuple, Optional

import streamlit as st

from src.services.google_sheets import get_gsheet_manager
from src.services.openai_client import (
    get_analysis_from_analyzer,
    get_solution_from_solver,
    synthesize_prompt_from_suggestion,
)
from src.core.tokenizer import AdvancedTokenizer
from src.core.metrics import BasicMetrics
from src.core.metrics_advanced import compute_advanced_metrics  # ✅ natural CDI/SSS/ARQ
from src.models.schemas import (
    Run,
    PromptMetrics,
    Suggestion,
    Evaluation,
    AdvancedMetricsRecord,  # ✅ flattened schema for metrics_advanced
)
from src.prompts.taxonomy import PROMPT_TAXONOMY
from src.utils.text import clean_problem_text, generate_problem_id


# ---------------- Utils ----------------
def _canon_ccss(s: str) -> str:
    return str(s or "").split("(")[0].strip().lower()


def _parse_level_num(s: str) -> int:
    s = str(s or "")
    for ch in s:
        if ch.isdigit():
            return int(ch)
    return 0


def _map_context(sheet_val: str) -> str:
    v = (sheet_val or "").strip().lower()
    return "Applied Math" if v in ["real-world", "real world", "applied", "realworld", "real"] else "Theorical Math"


def _band_to_score(band: Optional[str]) -> Optional[int]:
    if not band:
        return None
    m = {"low": 40, "medium": 70, "high": 90}
    return m.get(str(band).strip().lower())


# -------------- Main --------------
def run_ai_user_batch(
    *,
    sheet_name: str = "problems",
    ccss_filters: List[str],      # allow empty => all
    level_filters: List[str],     # e.g. ["Level 1","Level 3"] or ["1","3"]
    context_filters: List[str],   # allow empty => all
    evaluator_name: str,          # dùng cho user_id & grader_id
    include_baseline: bool = True,
    analyzer_model: str = "gpt-3.5-turbo",
    solver_model: str = "gpt-3.5-turbo",
    paraphraser_model: str = "gpt-3.5-turbo",
    throttle_sec: float = 0.15,
    flush_every: int = 20,
):
    gsheet = get_gsheet_manager(_version=2)  # giữ theo bản của bạn
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

    # ---- Chuẩn hoá filter ----
    ccss_norm = {_canon_ccss(x) for x in ccss_filters} if ccss_filters else set()
    lvl_set_nums = {_parse_level_num(x) for x in level_filters} if level_filters else set()
    # Chuẩn hoá context filter sang canonical để khớp với _map_context
    ctx_norm = {str(x).strip().lower() for x in context_filters} if context_filters else set()

    def pass_ccss(x):
        if not ccss_norm:
            return True
        return _canon_ccss(x) in ccss_norm

    def pass_level(x):
        if not lvl_set_nums:
            return True
        return _parse_level_num(x) in lvl_set_nums

    def pass_ctx(x):
        if not ctx_norm:
            return True
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

    runs_buf: List[Run] = []
    metrics_buf: List[PromptMetrics] = []
    adv_buf: List[AdvancedMetricsRecord] = []
    suggestions_buf: List[Suggestion] = []
    evals_buf: List[Evaluation] = []

    taxonomy_keys = sorted(PROMPT_TAXONOMY.keys())
    total_tasks = len(df_sel) * (len(taxonomy_keys) + (1 if include_baseline else 0))
    done = 0

    progress = st.progress(0.0)
    status = st.empty()

    ai_user_id = f"{evaluator_name} - AI"
    ai_grader = ai_user_id

    for _, row in df_sel.iterrows():
        raw_problem = row[cols["problem"]]
        problem_text = clean_problem_text(raw_problem)
        problem_id = generate_problem_id(problem_text)
        content_domain = str(row[cols["ccss"]]).split("(")[0].strip()
        cognitive_level = _parse_level_num(row[cols["level"]])
        problem_context = _map_context(row[cols["abstract / real-world"]])

        # ---- Tạo các biến thể prompt ----
        variants: List[Tuple[str, int, str, int | None]] = []
        if include_baseline:
            variants.append(("Solve this problem.", 0, "Baseline", None))

        for k in taxonomy_keys:
            sug = PROMPT_TAXONOMY[k]
            prompt_text = synthesize_prompt_from_suggestion(
                problem_text=problem_text, suggestion=sug, model=paraphraser_model
            )
            variants.append((prompt_text, int(sug.get("level", 0)), str(sug["name"]), k))

        for prompt_text, level_hint, prompt_name, sug_key in variants:
            # Chuẩn bị run_id để đồng bộ mọi bảng
            run_id = str(uuid.uuid4())

            # ---------- Analyzer ----------
            try:
                analysis = get_analysis_from_analyzer(
                    user_prompt=prompt_text, problem_text=problem_text, model=analyzer_model
                )
                prompt_analysis = analysis.get("prompt_analysis", {}) or {}
            except Exception as e:
                prompt_analysis = {}
                st.warning(f"Analyzer lỗi: {e}")

            # ---------- Solver ----------
            try:
                sol = get_solution_from_solver(
                    user_prompt=prompt_text, problem_text=problem_text, model=solver_model
                )
                solution_text = sol.get("solution_text") or ""
            except Exception as e:
                sol = {}
                solution_text = f"--- ERROR --- {e}"
                st.warning(f"Solver lỗi: {e}")

            # ---------- Basic metrics (deterministic) ----------
            pm = metrics.compute(prompt_text, tokenizer, run_id=run_id, w=10)
            metrics_buf.append(pm)

            # ---------- Advanced metrics (CDI/SSS/ARQ) ----------
            cdi_comp = sss_w = arq_s = None
            try:
                adv_vals = compute_advanced_metrics(prompt_text)  # {"cdi": {...}, "sss": {...}, "arq": {...}}
                cdi = adv_vals.get("cdi", {}) or {}
                sss = adv_vals.get("sss", {}) or {}
                arq = adv_vals.get("arq", {}) or {}

                # aggregates cho bảng runs
                cdi_comp = float(cdi.get("cdi_composite", 0.0))
                sss_w = float(sss.get("sss_weighted", 0.0))
                arq_s = float(arq.get("arq_score", 0.0))

                # flattened record cho metrics_advanced
                adv_rec = AdvancedMetricsRecord(
                    run_id=run_id,
                    session_id=str(uuid.uuid4())[:8],
                    user_id=ai_user_id,
                    prompt_text=prompt_text,
                    cdi_rate_cognitive_verbs=float(cdi.get("rate_cognitive_verbs", 0.0)),
                    cdi_lexical_density=float(cdi.get("lexical_density", 0.0)),
                    cdi_clauses_per_sentence=float(cdi.get("clauses_per_sentence", 0.0)),
                    cdi_rate_abstract_terms=float(cdi.get("rate_abstract_terms", 0.0)),
                    cdi_composite=float(cdi.get("cdi_composite", 0.0)),
                    sss_n_examples=int(sss.get("n_examples", 0)),
                    sss_n_step_markers=int(sss.get("n_step_markers", 0)),
                    sss_n_formula_markers=int(sss.get("n_formula_markers", 0)),
                    sss_n_hints=int(sss.get("n_hints", 0)),
                    sss_weighted=float(sss.get("sss_weighted", 0.0)),
                    arq_abstract_terms=int(arq.get("abstract_terms", 0)),
                    arq_numbers=int(arq.get("numbers", 0)),
                    arq_ratio=float(arq.get("ratio", 0.0)),
                    arq_meta_bonus=float(arq.get("meta_bonus", 0.0)),
                    arq_score=float(arq.get("arq_score", 0.0)),
                )
                adv_buf.append(adv_rec)
            except Exception as _e:
                # Không chặn batch
                pass

            # ---------- Map Analyzer (schema mới + fallback cũ) ----------
            sig = (prompt_analysis.get("signals") or {})
            bands = (prompt_analysis.get("qualitative_scores") or {})
            # mới: ai_estimated ; cũ: estimated_metrics
            ai_est = (prompt_analysis.get("ai_estimated")
                      or prompt_analysis.get("estimated_metrics")
                      or {})

            clarity_v = _band_to_score(bands.get("clarity_band")) or bands.get("clarity_score")
            specificity_v = _band_to_score(bands.get("specificity_band")) or bands.get("specificity_score")
            structure_v = _band_to_score(bands.get("structure_band")) or bands.get("structure_score")

            est_token_count = sig.get("tokens") or ai_est.get("estimated_token_count")
            est_mattr = ai_est.get("mattr_like", ai_est.get("estimated_mattr_score"))
            est_reading = ai_est.get("reading_ease_like", ai_est.get("estimated_reading_ease"))

            # Chuẩn hoá 0..1 → 0..100 nếu cần
            if isinstance(est_mattr, (int, float)) and est_mattr is not None and est_mattr <= 1:
                est_mattr = est_mattr * 100.0
            if isinstance(est_reading, (int, float)) and est_reading is not None and est_reading <= 1:
                est_reading = est_reading * 100.0

            # ---------- Build Run ----------
            run = Run(
                run_id=run_id,
                session_id=str(uuid.uuid4())[:8],
                user_id=ai_user_id,
                problem_id=problem_id,
                problem_text=problem_text,
                content_domain=content_domain,
                cognitive_level=cognitive_level,
                problem_context=problem_context,
                prompt_text=prompt_text,
                prompt_level=level_hint,
                prompt_name=prompt_name,
                solver_model_name=solver_model,
                response_text=solution_text,
                clarity_score=clarity_v,
                specificity_score=specificity_v,
                structure_score=structure_v,
                estimated_token_count=est_token_count,
                estimated_mattr_score=est_mattr,
                estimated_reading_ease=est_reading,
                analysis_rationale=prompt_analysis.get("overall_evaluation") if prompt_analysis else None,
                # aggregates từ advanced metrics
                cdi_composite=cdi_comp,
                sss_weighted=sss_w,
                arq_score=arq_s,
                latency_ms=sol.get("latency_ms", 0),
                tokens_in=(sol.get("usage") or {}).get("prompt_tokens", 0),
                tokens_out=(sol.get("usage") or {}).get("completion_tokens", 0),
            )
            runs_buf.append(run)

            # ---------- Suggestion ----------
            if sug_key is not None:
                suggestions_buf.append(
                    Suggestion(
                        run_id=run_id,
                        session_id=run.session_id,
                        user_id=run.user_id,
                        suggestion_key=int(sug_key),
                        suggestion_name=prompt_name,
                        suggested_level=level_hint,
                        accepted=True,
                    )
                )

            # ---------- Auto evaluation ----------
            evals_buf.append(
                Evaluation(
                    run_id=run_id,
                    grader_id=ai_grader,
                    correctness_score=1,
                    evaluation_notes="Auto (AI batch). Please review.",
                )
            )

            # ---------- Progress & Flush ----------
            done += 1
            if len(runs_buf) >= flush_every:
                try:
                    if runs_buf:
                        gsheet.append_data("runs", runs_buf)
                    if metrics_buf:
                        gsheet.append_data("metrics_deterministic", metrics_buf)
                    if adv_buf:
                        gsheet.append_data("metrics_advanced", adv_buf)
                    if suggestions_buf:
                        gsheet.append_data("suggestions", suggestions_buf)
                    if evals_buf:
                        gsheet.append_data("evaluations", evals_buf)
                except Exception as e:
                    st.error(f"Lỗi ghi batch: {e}")

                runs_buf.clear()
                metrics_buf.clear()
                adv_buf.clear()
                suggestions_buf.clear()
                evals_buf.clear()

            status.write(f"AI User: {done}/{total_tasks} | {content_domain} | L{cognitive_level} | {prompt_name}")
            progress.progress(min(1.0, done / total_tasks))
            time.sleep(throttle_sec)

    # ---------- Flush phần còn lại ----------
    if runs_buf or metrics_buf or adv_buf or suggestions_buf or evals_buf:
        try:
            if runs_buf:
                gsheet.append_data("runs", runs_buf)
            if metrics_buf:
                gsheet.append_data("metrics_deterministic", metrics_buf)
            if adv_buf:
                gsheet.append_data("metrics_advanced", adv_buf)
            if suggestions_buf:
                gsheet.append_data("suggestions", suggestions_buf)
            if evals_buf:
                gsheet.append_data("evaluations", evals_buf)
        except Exception as e:
            st.error(f"Lỗi ghi batch cuối: {e}")

    progress.progress(1.0)
    status.write("✅ AI User hoàn tất.")
    return {"selected": int(len(df_sel)), "created_runs": int(total_tasks)}
