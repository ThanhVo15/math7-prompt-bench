# Ship-ready folder structure (clean, scalable, still MVP)

Below is a **full repo layout** tailored to your README. I’ll explain *why each folder exists* and the *main responsibility* of key files, so you can keep it clean now and scale later without refactor pain.

```
math7-prompt-bench/
├─ app/                           # Streamlit UI (thin layer, no business logic)
│  ├─ main.py                     # Streamlit entrypoint: routing, top-level layout, state boot
│  ├─ state.py                    # SessionState helpers: logged-in user, session_id, cached deps
│  ├─ pages/                      # Multi-page Streamlit files
│  │  ├─ 1_🔐_Login.py           # Login + “resume session” UI (calls auth_service, session_service)
│  │  ├─ 2_💬_Chat.py            # Prompt/Problem/Request inputs; runs model; shows metrics table
│  │  └─ 3_📈_Progress.py        # Gamification view: deltas vs baseline, badges
│  ├─ components/                 # Reusable UI widgets (pure rendering + events)
│  │  ├─ auth_widgets.py          # Username/password form, errors
│  │  ├─ chat_widgets.py          # Prompt/Problem/Request inputs, selectors, full_prompt preview
│  │  ├─ metrics_table.py         # Side-by-side LLM vs Math7M table renderer
│  │  └─ suggestion_panel.py      # “Suggest next level” box + “Apply to Prompt” behavior
│  └─ __init__.py
│
├─ core/                          # All real logic: domain, services, metrics, storage
│  ├─ config/
│  │  └─ settings.py              # Typed config (envs): model name, Sheets or CSV, paths, secrets
│  ├─ domain/
│  │  ├─ models.py                # Dataclasses: User, Session, Problem, Prompt, Run, Metrics, etc.
│  │  ├─ taxonomy.py              # Prompt levels, categories, templates (ids, strings, variables)
│  │  ├─ constants.py             # Domain enums/lists (DomainType, CognitiveLevel, sheet names)
│  │  └─ __init__.py
│  ├─ llm/
│  │  ├─ openai_client.py         # LLM client wrapper (self-eval only), retries, timeouts
│  │  └─ prompts/
│  │     └─ self_eval.md          # System prompt template for JSON metrics estimation
│  ├─ metrics/                    # Deterministic Math7M metrics (ground truth)
│  │  ├─ mattr.py                 # MATTR (w=25) calculation with short-text fallback
│  │  ├─ lix.py                   # LIX → 0..100 normalization helpers
│  │  ├─ token_count.py           # Token/word/sentence/char counting, tokenizer adapters
│  │  └─ pipeline.py              # Orchestrates Math7M for a text → returns unified dict
│  ├─ services/                   # “Use-case” layer: orchestrates domain + storage + metrics + llm
│  │  ├─ auth_service.py          # Login, password hash/verify, user fetch/create
│  │  ├─ session_service.py       # Find/restore last session; create/end; heartbeat last_activity_at
│  │  ├─ run_service.py           # One chat turn: persist message, call LLM, compute metrics, persist
│  │  ├─ suggestion_service.py    # Select next-level template; log shown/accepted
│  │  └─ gamification_service.py  # Compute deltas vs baseline, points, best run selection
│  ├─ persistence/                # Storage abstraction (Google Sheets or CSV fallback)
│  │  ├─ storage.py               # Interfaces: IUserRepo, ISessionRepo, IRunsRepo, etc.
│  │  ├─ sheets_storage.py        # GSheets impl (gspread/pygsheets). One tab per entity.
│  │  ├─ csv_storage.py           # Local CSV impl: same interface, drop-in replacement
│  │  ├─ schemas.py               # Column maps + (de)serialization (models ↔ row dicts)
│  │  └─ ids.py                   # UUID/ULID generation utilities
│  ├─ utils/
│  │  ├─ text.py                  # Tokenization (fallback), sentence split, normalization
│  │  ├─ time.py                  # Now(), iso formatting, VN timezone utilities
│  │  └─ logging.py               # App logger (structured logs, user/session correlation)
│  └─ __init__.py
│
├─ data/
│  └─ csv/                        # Dev-only fallback data (gitignored *except* sample files)
│     ├─ users.csv
│     ├─ sessions.csv
│     ├─ messages.csv
│     ├─ problems.csv
│     ├─ prompts.csv
│     ├─ runs.csv
│     ├─ metrics_llm.csv
│     ├─ metrics_math7m.csv
│     ├─ suggestions.csv
│     └─ gamification.csv
│
├─ docs/
│  ├─ README.md                   # Your provided README (kept in repo)
│  └─ ARCHITECTURE.md             # 1-pager: layers, data flow, future scale notes
│
├─ scripts/
│  ├─ bootstrap_dev.py            # Create sample users, seed taxonomy templates to storage
│  ├─ export_sheets_to_csv.py     # One-off sync helpers
│  └─ import_csv_to_sheets.py
│
├─ tests/
│  ├─ test_metrics_mattr.py       # Edge cases (short text), invariants
│  ├─ test_metrics_lix.py
│  ├─ test_storage_csv.py
│  └─ test_storage_contract.py    # Contract tests ensuring CSV & Sheets behave identically
│
├─ .streamlit/
│  └─ config.toml                 # Theme, server.headless, browser.gatherUsageStats=false
├─ .env.template                  # ENV names (no secrets)
├─ pyproject.toml                 # Or requirements.txt; pin minimal, stable deps
├─ .gitignore                     # Ignore /data/csv/*.csv (keep example-*.csv if useful)
└─ LICENSE
```

---

## Why this shape works (MVP today, scale tomorrow)

### 1) `app/`: UI stays thin

* **Goal:** Keep Streamlit pages as *glue only*. They call services; they do not compute metrics, hash passwords, or write rows.
* **Benefit:** Swap Streamlit later for FastAPI, Gradio, or a React front-end without touching domain logic.

### 2) `core/domain/`: one source of truth

* **`models.py`** holds dataclasses matching your **Google Sheets tabs** (User, Session, Message, Problem, Prompt, Run, MetricsLLM, MetricsMath7M, Suggestion, Gamification).
  *Single responsibility:* shape your data, not how it’s stored or displayed.
* **`taxonomy.py`** centralizes your **Level/Category templates** with stable IDs.
  *Prevents drift* between suggestions and analytics.

### 3) `core/metrics/`: Math7M (deterministic)

* **`mattr.py`** (w=25, fallback when text is short), **`lix.py`** (to 0..100), **`token_count.py`** (tokenizer adapters + safe fallback).
* **`pipeline.py`** returns a *unified dict*:

  ```python
  {
    "lexical_mattr_0_1": float,
    "token_count": int,
    "reading_ease_0_100": float,
    "tokenizer": "simple|cl100k_base",
    "window_w": 25
  }
  ```

  *You keep the same keys as LLM Self-Eval (with/without `_est`).*

### 4) `core/llm/`: self-eval only

* **`openai_client.py`**: a tiny wrapper with timeouts, retries, and **one** function: `estimate_metrics(text) -> {..._est}`.
* **`prompts/self_eval.md`** keeps the JSON-return spec in one place.
  *If you add Claude/Gemini later, you change only this folder.*

### 5) `core/services/`: your “use cases”

* **`auth_service.py`**: verify password (hashing), fetch/create user.
* **`session_service.py`**: restore last session or create a new one; heartbeat updates `last_activity_at`.
* **`run_service.py`**: one chat turn orchestration:

  1. persist inputs,
  2. call LLM for **Solution**,
  3. call LLM **Self-Eval** (**est** fields),
  4. run **Math7M**,
  5. persist runs + metrics (both),
  6. return everything to UI.
* **`suggestion_service.py`**: choose next level template, log shown/accepted, **no auto-send**.
* **`gamification_service.py`**: compute deltas vs baseline; pick best run; return badge flags/points.

> This layer enforces **Clean Architecture** boundaries: UI → Services → Storage/Metrics/LLM.
> No service calls Streamlit directly; no storage logic leaks upward.

### 6) `core/persistence/`: plug storage (Sheets ↔ CSV)

* **`storage.py`** defines repository interfaces; e.g. `IUsers`, `ISessions`, `IRuns`, `IMetricsLLM`, `IMetricsMath7M`, `ISuggestions`, `IGamification`.
* **`sheets_storage.py`** implements those using **GSheets** (one tab per entity).
* **`csv_storage.py`** implements the *same* interfaces using local CSVs.
* **`schemas.py`** maps dataclasses ↔ row dicts with column names **matching your tabs**.

  > **Result:** You can switch storage via `settings.STORAGE_BACKEND = "sheets" | "csv"` with **zero** UI/service changes.

### 7) `tests/`: confidence without bloat

* **Contract tests** ensure CSV and Sheets behave the same.
* Metric tests cover short text, punctuation-only, multilingual samples (Vietnamese/English).

---

## Minimal “how to build it” guidance (senior guardrails)

**1) Keep dependencies tiny.**
`streamlit`, `pydantic` (optional), `gspread/pygsheets` (pick one), `openai`, `python-dotenv`. That’s it.

**2) Type everything.**
Dataclasses + function return types (especially in services and metrics).

**3) Dependency injection, the simple way.**
Create a `get_storage()` in `settings.py` that returns **either** Sheets or CSV impl. Pass that into services **once** at app startup (cache in `app/state.py`). No DI framework needed.

**4) One entry point per use case.**
`run_service.run_turn(...)` should accept the 3 inputs + 2 selectors and return a single struct:

* solution text,
* `metrics_llm_est`,
* `metrics_math7m`,
* `run_id`.

**5) Unified metric keys.**
Always align fields as your README shows:

* Ground truth: `lexical_mattr_0_1`, `token_count`, `reading_ease_0_100`
* Estimates: `lexical_mattr_0_1_est`, `token_count_est`, `reading_ease_0_100_est`

**6) Logging.**
Each log line should include `{user_id, session_id, run_id}` to debug later.

**7) Secrets.**
Never commit credentials; read via env. Keep `GOOGLE_SERVICE_ACCOUNT_JSON` as a *path* or *JSON string* env.

---

## What to implement first (MVP path in 7 steps)

1. **Domain + persistence contracts** (`models.py`, `storage.py`, `csv_storage.py` with real CSV I/O).
2. **Metrics pipeline (Math7M)** (`mattr.py`, `lix.py`, `token_count.py`, `pipeline.py`) with tests.
3. **LLM Self-Eval** (`openai_client.py`, `prompts/self_eval.md`) returning `*_est` JSON.
4. **Services** (`run_service.py`, `auth_service.py`, `session_service.py`, `suggestion_service.py`, `gamification_service.py`).
5. **Streamlit pages** (`Login`, `Chat`, `Progress`) calling services; render metrics side-by-side.
6. **Sheets implementation** (`sheets_storage.py`) once CSV path is stable.
7. **Bootstrap** (`scripts/bootstrap_dev.py`) to seed taxonomy + a demo user.

Stay ruthless about scope: **no auto-send**, **no correctness checking**, **no heavy admin**. You already have the right metrics (MATTR, token count, LIX) and the right loop (Suggest → Apply → Replace & Resend).
