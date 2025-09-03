# Math7 Prompt Bench – MVP (Streamlit + Python)

A Streamlit web app where each user logs in, resumes **their own chat session**, and iterates on prompts. Every turn computes metrics from **two sources**:

* **LLM Self-Eval** (GPT-3.5-turbo estimates)
* **Math7M** (our backend, deterministic)

We **do not judge solution correctness** in Phase-1. We “gamify” moving from **Baseline → Level 1 → Level 2 → Level 3…** by suggesting stronger prompt structures that the user **manually adapts** (no auto-send), then **Replace & Resend**.

All data (users, sessions, messages, problems, prompts, metrics, suggestions, gamification progress) is saved to **Google Sheets** (CSV fallback for dev).

---

## 1) Core user flow

1. **Login & resume**

   * User logs in (username/password).
   * If a previous session exists, restore it (same chat history). Otherwise, create a new session.

2. **Chat turn (3 inputs + 2 selectors)**

   * Text inputs:

     * **Prompt** (free text; baseline or edited template)
     * **Problem** (free text)
     * **Request / Yêu cầu** (free text; optional constraints/instructions)
   * Selectors:

     * **Domain Type** (e.g., `algebra | geometry | other`) — configurable list
     * **Cognitive Level** (`1 | 2 | 3`)
   * The app renders a **full\_prompt** (use the Prompt directly or render a selected template with variables).

3. **Model call + metrics**

   * Call **GPT-3.5-turbo** → get a **Solution** (Phase-1: don’t judge correctness).
   * In parallel, compute **two sets of prompt metrics**:

     * **LLM Self-Eval**: ask the model to estimate the metrics below (advisory).
     * **Math7M**: compute the same metrics deterministically on our backend.

4. **Metrics panel**

   * Show a **side-by-side table**: **LLM Self-Eval** vs **Math7M** (same metric names, units).
   * Keep both visible to highlight gaps/bias.

5. **Suggestion → manual refinement (no auto-send)**

   * App proposes a **higher-level prompt structure** (from the taxonomy).
   * **User manually adapts** that structure into their Prompt field (diversifies wording), then clicks **Replace & Resend**.
   * Log suggestion shown/accepted and the new level.

6. **Gamification loop**

   * Baseline → Level 1 → Level 2 → Level 3…
   * Track **delta improvements** in Math7M metrics vs the user’s baseline for the same problem.
   * Show progress badges (e.g., “+10% MATTR, +15 Reading Ease, −20% tokens”).

---

## 2) Unified metrics (used by **both** sources)

Use **the same named fields** from LLM Self-Eval and Math7M so they line up in one table:

* **`lexical_mattr_0_1`** — *Lexical Diversity (MATTR)*
  Moving-Average Type-Token Ratio with window `w=25`.
  If `len(tokens) < w`, use `unique(tokens)/len(tokens)`.

* **`token_count`** — *Token Count*
  Prefer your model’s tokenizer; fallback to a whitespace/punctuation tokenizer.
  (LLM Self-Eval may only **estimate** this; label as “estimated”.)

* **`reading_ease_0_100`** — *Readability (LIX → 0..100)*
  ✔ **Cross-language friendly** (no syllables).

  ```
  LIX = (words / sentences) + 100 * (long_words / words)   # long_words = len(word) ≥ 7
  reading_ease_0_100 = clamp(100 - (LIX - 20) * (100/40), 0, 100)
  ```

  > **Why LIX, not Flesch?** Flesch Reading Ease relies on **syllables**, works well for English but is unreliable cross-language (e.g., Vietnamese).
  > LIX, **Coleman–Liau (CLI)**, and **ARI** avoid syllables. If you want extras:
  >
  > * **CLI**: `0.0588*L - 0.296*S - 15.8`, where `L = letters per 100 words`, `S = sentences per 100 words`
  > * **ARI**: `4.71*(characters/words) + 0.5*(words/sentences) - 21.43`
  >   Keep **LIX** as the primary shared metric; optionally show CLI/ARI as secondary rows.

**Takeaway:** To answer your question — yes, use **MATTR**, **Token Count**, and **LIX** as the **shared metrics set** both the **LLM Self-Eval** and **Math7M** can produce (LLM’s token count may be an estimate unless you ask for characters/words instead). If you need a single readability metric across languages, **LIX** is the safest default.

---

## 3) LLM Self-Eval response schema (example)

Ask GPT-3.5-turbo to **return JSON** for the prompt **text only** (not the solution):

```json
{
  "lexical_mattr_0_1_est": 0.72,
  "token_count_est": 84,
  "reading_ease_0_100_est": 68.5,
  "rationale": "Short sentences, moderate variety; a few long words reduce readability."
}
```

Show these next to Math7M’s ground-truth fields:

```json
{
  "lexical_mattr_0_1": 0.69,
  "token_count": 91,
  "reading_ease_0_100": 63.2,
  "tokenizer": "simple|cl100k_base",
  "window_w": 25
}
```

> Keep field names aligned so your table renders **LLM vs Math7M** row-by-row.

---

## 4) Prompt taxonomy (for suggestions & gamification)

We keep your ladder but **don’t auto-replace or auto-send**. The suggestion **prefills structure**; the user **edits manually**, clicks **Replace & Resend**.

| Level | Category                           | Short intent                                                  |
| ----: | ---------------------------------- | ------------------------------------------------------------- |
|     0 | Zero-Shot                          | Baseline direct ask                                           |
|     1 | Few-Shot / Instruction             | Student profile + 3-part output (breakdown/solution/summary)  |
|     1 | Thought Generation (Zero-Shot CoT) | “Let’s think step by step.”                                   |
|     2 | CoT – Thread of Thought            | Solve then summarize knowledge used (e.g., geometry concepts) |
|     2 | CoT – Chain of Verification        | Solve → generate 3 checks → answer them → conclude            |
|     2 | GoT – Graph of Thoughts            | Brainstorm multiple outlines → pick best → solve              |
|     3 | Ensembling / Meta-Reasoning        | Compare multiple outlines; choose best for grade-7            |
|     3 | HTML Blocks                        | Task Instruction / Task Detail / Output Format / Examples     |

**UI behavior**

* Button **“Suggest next level”** → show structure in a read-only box + **“Apply to Prompt”** (copies into the Prompt textarea but **does not send**).
* User edits → **Replace & Resend** triggers a new turn.
* Log: `suggested_level`, `suggested_category`, `suggested_template_id`, `shown_at`, `accepted(bool)`, `accepted_at`.

**Gamification**

* Track **improvement vs Baseline** for the same `Problem`:
  `ΔMATTR`, `ΔReadingEase`, `ΔTokenCount` (prefer lower).
* Show badges like: “+10% MATTR since baseline”, “+15 readability”, “−20% tokens”.
* Optional points: `points = 100 * (ΔMATTR + ΔRE_norm) - 50 * ΔTokens_norm`.

---

## 5) Data model (Google Sheets tabs)

* **Users**: `user_id, username, password_hash, role, created_at`
* **Sessions**: `session_id, user_id, started_at, ended_at, last_activity_at, source`
* **Messages**: `msg_id, session_id, user_id, role(user|assistant), text, prompt_template_id, domain_type, cognitive_level, created_at`
* **Problems**: `problem_id, user_id, text, domain_type, difficulty, created_at`
* **Prompts**: `prompt_id, name, text, variables(csv), level, category, created_at, author`
* **Runs**: `run_id, session_id, problem_id, prompt_id, model_name, temperature, response_json, latency_ms, created_at`
* **Metrics\_LLM**: `metric_id, run_id, lexical_mattr_0_1_est, token_count_est, reading_ease_0_100_est, rationale, computed_at, source("llm")`
* **Metrics\_Math7M**: `metric_id, run_id, tokenizer, window_w, lexical_mattr_0_1, token_count, reading_ease_0_100, computed_at, source("math7m")`
* **Suggestions**: `event_id, session_id, run_id, suggested_level, suggested_category, suggested_template_id, shown_at, accepted(bool), accepted_at`
* **Gamification**: `progress_id, user_id, problem_id, baseline_run_id, current_best_run_id, delta_mattr, delta_reading_ease, delta_token_count, points, updated_at`

> IDs = ULID/UUID. Never rely on row numbers.

---

## 6) Acceptance criteria (MVP)

* Login → session restored (or created) and chat history visible.
* Chat turn accepts **Prompt, Problem, Request** + **Domain Type, Cognitive Level**.
* Model returns **Solution**.
* **Two metric sets** appear (LLM vs Math7M) with aligned rows: `lexical_mattr_0_1`, `token_count`, `reading_ease_0_100`.
* Suggestion shows structure → **Apply to Prompt** (no auto-send) → user edits → **Replace & Resend**.
* Sheets updated for **Users, Sessions, Messages, Problems, Prompts, Runs, Metrics (both), Suggestions, Gamification**.
* CSV fallback works locally when Google creds are missing.

---

## 7) Dev notes

* **Tokenizer:** If you can’t use your model’s tokenizer, compute both **characters/words/sentences** and derive LIX (robust across languages).
* **LLM Self-Eval:** note `*_est` fields are estimates; keep Math7M as ground truth.
* **State restore:** on login, fetch last unclosed session or latest by `last_activity_at`.
* **Privacy:** keep passwords hashed in secrets; never store raw secrets in Sheets.
* **Stability:** pin window `w=25` for MATTR; don’t change normalization mid-study.

---

### TL;DR

* Replace **auto-apply+send** with **Apply to Prompt → user edits → Replace & Resend** to ensure **diversity**.
* Use **MATTR**, **Token Count**, and **LIX** as the **shared metrics** both sources can produce; keep field names aligned.
* Ladder the user **Baseline → L1 → L2 → L3** and show **metric gains** as gamification.
* Persist everything to Sheets with CSV fallback.

