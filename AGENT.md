# CLAUDE.md & AGENT.md: Developer & Agent Reference Guide

Setup commands, run instructions, the real file layout, and the conventions an agent must follow when working on Carzinomax DEV. Keep this file in sync with the code; the public-facing overview lives in `README.md`.

---

## 🧭 What the project is

**Carzinomax DEV** — "the open-source ERP where AI does the data entry." An ERP sized for a small unit (solo founder to a handful of people). The flagship feature being built is the AI "receipt → booked" flow: a forwarded receipt or invoice becomes a categorized expense without manual entry. That flow does **not** exist yet; today the ERP is a set of CRUD modules plus an in-app chat assistant that can read, create, update and (with approval) delete records in every module.

Status is pre-alpha. The codebase was rebuilt from scratch ("Init v2"); an earlier version had a general ledger, invoicing, warehouses and role-based RBAC. **None of that exists anymore.** Do not add features that assume it does. Leftovers of the old version still sit in `app/schemas/` (see Known gaps); ignore them.

---

## 🛠️ Main Features (current state)

### 1. Auth & access control ([api/v1/auth.py](backend/app/api/v1/auth.py), [api/common/general.py](backend/app/api/common/general.py))
* Default admin seeded on startup from `ADMIN_EMAIL` / `ADMIN_PASSWORD` in `.env`, with all four module flags.
* `POST /auth/login?user_email=…&password=…` returns a bare JWT string (7-day expiry). `GET /auth/me` returns the current user. `POST /auth/logout` sets `tokens_valid_from` on the user so every token issued before now is rejected.
* **There are no roles.** `User` carries four booleans: `has_finance_access`, `has_scm_access`, `has_hr_access`, `has_dev_access`. Each router calls `permission_check('<finance|scm|hr|dev>', current_user.id, db)` at the top of every endpoint and returns a 403 envelope on failure.

### 2. People & Payroll / HR ([models/hr.py](backend/app/models/hr.py), [api/v1/hr.py](backend/app/api/v1/hr.py))
* Every `User` is an employee; the HR router owns user CRUD (`/hr/user…`; `/hr/employee_list` and `/hr/employee/{id}` are read-only aliases).
* `Department` (code, name, manager_id), `AttendanceLog` (clock in/out, `total_hours`), `LeaveRequest` (type, dates, pending/approved/rejected, `approved_by_id`), `Paycheck` (period, base, allowances, deductions, `net_pay`, draft/paid).
* Paycheck creation computes `net_pay = base + allowances − deductions` unless the client sends one.

### 3. Dev Tracking ([models/dev_tracking.py](backend/app/models/dev_tracking.py), [api/v1/dev_tracking.py](backend/app/api/v1/dev_tracking.py))
* `DevProject` (keyed by `project_id`), `DevInvestment` (date, amount, vendor, category: cloud / software_licenses / hardware / consulting), `ProjectDownload` (per-platform download/star snapshots: github, dockerhub, npm). Deleting a project cascades to its investments, snapshots and tracked repos.
* `GithubRepo` (table `dev_github_repos`: `project_id`, unique `full_name` as `owner/name`, latest `star_count` / `download_count`, `last_synced_at`, `last_error`). `app/core/github.py` fetches `stargazers_count` and the sum of release-asset `download_count` over all releases (httpx; `GITHUB_TOKEN` is optional for public repos and required for private ones) and upserts **one `ProjectDownload` row per project per UTC day** (platform `github`, totals over the project's repos, updated in place; hand edits to that row are overwritten). It runs from the scheduler and from `POST /dev_tracking/github_sync[/{repo_id}]`, which answers `{synced: [...], failed: [...]}`; a repo whose fetch fails keeps its old numbers and stores `last_error`. REST CRUD lives at `/dev_tracking/github_repo…` (renaming a repo clears its cached numbers). Chat has `create_github_repo` only (tracks a repo and pulls its numbers right away); list / rename / untrack stay REST-only (owner decision).

### 4. Finance ([models/finance.py](backend/app/models/finance.py), [api/v1/finance.py](backend/app/api/v1/finance.py))
* Minimal. `Finance` has a UUID id, an `expense_type` enum (`paycheck`, `petty_cash`, `investment`, `other`) and a required `amount` (Numeric 15,2; present in `0001_init`). No vendors or dates yet.
* The REST request models `CreateExpense` / `UpdateExpense`, the frontend ledger form and the chat tools (`create_expense`, `update_expense`) all send `amount`. The frontend Finance overview still derives totals from paychecks, investments and products.

### 5. Purchases / SCM ([models/scm.py](backend/app/models/scm.py), [api/v1/scm.py](backend/app/api/v1/scm.py))
* Minimal. `Product` (sku, name, description, unit_price, cost). No vendors, warehouses or purchase orders.

### 6. LLM model ([ai_service/agents.py](backend/app/ai_service/agents.py), [ai_service/llm_router.py](backend/app/ai_service/llm_router.py))
* The live model object is `llm`, a module-level `ChatLiteLLM` in `agents.py` (re-exported from `app.ai_service`). It is built from `LLM_MODEL` / `LLM_API_KEY`, and `LLM_API_BASE` only when `LLM_TYPE == 'local'`.
* Startup runs `llm.invoke('ping', max_tokens=1)` once; failure is logged and does not block startup. `POST /chatbot/` repeats the same ping on demand (no auth, takes `user_id` as a query param).
* `LlmRouter` in `llm_router.py` (litellm wrapper with `chat()`, `stream_chat()`, `parsed_chat(response_format=…)`, `model_check()`) is **not referenced anywhere**. Treat it as legacy; new AI code goes through `llm` or the orchestrator.
* Config: `LLM_TYPE` (`remote` | `local`), `LLM_MODEL` (litellm `<provider>/<model>` naming), `LLM_API_KEY`, `LLM_API_BASE`. The model must accept image input: chat attachments are sent as image blocks with no text-only fallback (README, "Pick an LLM").

### 6b. Chat control ([ai_service/agents.py](backend/app/ai_service/agents.py), [ai_service/tool_store.py](backend/app/ai_service/tool_store.py), [api/v1/chatbot.py](backend/app/api/v1/chatbot.py))
* `POST /chatbot/chatbox` takes `ChatboxRequest` (`message`, `history`, `thread_id`, `decision`, `attachments`; schema in `app/schemas/chatbot.py`) and streams NDJSON events `token` / `interrupt` / `done` / `error` from a LangChain `create_agent` orchestrator built per request by `init_orchestrator(user_id)`.
* Orchestrator prompt = `prompts/orchestrator_prompt.md` + a `<context>` block (today, caller id, name, four flags). Sub-agent queries are prefixed with today's date (`with_today`) so relative periods resolve.
* `tool_store.py` holds one `@tool` per operation, get / create / update / delete for every table (40 tools), all sync via `SyncSessionLocal`. Style: a `XxxDetail` row model + `GetXxxOutput` with `total`, filters applied only when not `None`, `None` when nothing matches, `raise ValueError` on bad input. **No logging and no `user_id` parameter in tools**; access is decided by which tools the orchestrator receives. Leave has `review_leave_request` (approve/reject) instead of a generic update.
* Sub-agents (`hr_helper`, `expanse_helper`, `scm_helper`, `dev_helper`, prompts in `ai_service/prompts/`) own read + create + update and are attached only when the caller has the module flag. `create_leave_request` is attached for every user. Delete tools sit on the orchestrator itself (`*_DELETE_TOOLS` lists) and go through `HumanInTheLoopMiddleware` (approve / reject).
* Approval state lives in a single in-process `MemorySaver` checkpointer (lost on restart). The client keeps a `thread_id`; the server namespaces it as `<user_id>:<thread_id>` so nobody can resume another user's paused run. A request with `decision` resumes the paused run; a new `message` while an approval is pending is rejected with 400. The client's `history` (last 10 messages) is only used when the checkpoint for the thread is empty.
* The stream forwards only the orchestrator's own model tokens (`langgraph_node == 'model'`, no nested namespace); sub-agent output and tool results are not streamed.
* Attachments: `POST /chatbot/upload` (multipart field `file`, auth only, one file per request) sniffs the type from the bytes (PNG / JPEG / WebP / PDF), caps the size at `UPLOAD_MAX_BYTES` (10 MB), re-encodes images as JPEG (at most 1,003,520 pixels, EXIF-rotated) and stores the file as `<UPLOAD_DIR>/<user_id>/<uuid>.<ext>` (`app/core/uploads.py`; no table, kept forever, `uploads/` is gitignored). The returned `id` goes into `ChatboxRequest.attachments` (at most `MAX_ATTACHMENTS` = 5, of which one image). `attachment_blocks` in `agents.py` turns them into content blocks on the user turn: an image block (`{'type': 'image', 'base64', 'mime_type'}`) or the pypdf text inside an `<attachment>` text block. The `CurrentImageOnly` middleware keeps the image block of the newest user turn only, so every model request carries at most one image (small-GPU vision models); older turns show `[image no longer attached]` to the model while the checkpoint stays intact. Attachments reach the orchestrator only (sub-agent queries stay text), are not replayed from `history` after a restart (the client marks such turns with `[attached: name]`), and an unknown or foreign id is a 400 before the stream starts.
* Adding a tool: write it in `tool_store.py` in the existing style, add it to the right sub-agent list (or the module's `*_DELETE_TOOLS`) in `agents.py`, and describe it in that agent's prompt file.
* `agents.py` has a `__main__` CLI loop for manual testing: `uv run python -m app.ai_service.agents` from `backend/` (uses user id 1).

### 7. Scheduler ([core/scheduler.py](backend/app/core/scheduler.py))
* An `AsyncIOScheduler` starts and stops with the app. One job is registered: `github_sync` (`CronTrigger.from_crontab(GITHUB_SYNC_CRON)`, default `0 */6 * * *`, `misfire_grace_time=3600`) opens its own `SessionLocal` session and calls `sync_github_repos`. Jobs catch every exception and log through `system_log()` with a `Scheduler:` prefix, because APScheduler reports job errors via std `logging`, which is not forwarded to loguru. An invalid cron string is logged at startup and the job is skipped. There is one scheduler per process, so run the backend single-worker.
* `PAYCHECK_CALCULATE_TIMESPOT` (cron string, default `0 0 1 * *`) is still read into settings but unused; the monthly payroll job is planned, not implemented.

### 8. Frontend ([frontend/](frontend/))
* React 19 + Vite SPA, complete for every backend module: Dashboard, People & Payroll, Finance, Purchases, Dev Tracking, Users & Access. Framer Motion, Recharts, lucide-react, react-router. Native `fetch` wrapper in `src/lib/api.js` (no axios).
* Dev Tracking has a fourth tab, **GitHub repos**: lists `dev_github_repos` (stars, downloads, last sync, error) and adds a repo; remove / rename / `github_sync` have no UI yet.
* Chat assistant: `components/chat/ChatPanel.jsx` (slide-over drawer mounted in `AppLayout`), `lib/useChat.js` (transcript, `send`, `decide`, `reset`, client-generated `thread_id`), `api/chatbot.js` (NDJSON reader over `apiPostStream`, `upload` over `apiPostForm`). The composer's paperclip or a pasted image attaches PNG / JPEG / WebP / PDF files (5 per message, 10 MB each); they upload before the turn streams and show as chips / thumbnails in the user bubble.
* Vite dev server proxies `/api` → `http://localhost:8000`. Sidebar is gated by the user's module flags. 403 shows an in-page "Restricted" panel; 401 clears the session.
* Details in [frontend/README.md](frontend/README.md) (does not mention the chat drawer yet).

### ⚠️ Known gaps (do not build on these)
* `app/schemas/finance.py`, `scm.py`, `hr.py`, `dev_tracking.py` describe tables from the old version (GL accounts, journal entries, invoices, fixed assets, payments, product categories, dev worker paychecks). They are re-exported by `schemas/__init__.py` but **used by nothing**. Routers define their own request models inline.
* `LlmRouter` (`ai_service/llm_router.py`) has no callers.
* `app/middleware/` is an empty package; `langgraph-supervisor` is in `pyproject.toml` but never imported.
* `POST /chatbot/` is unauthenticated.
* `backend/README.md` is empty.
* `GithubRepo` has REST endpoints but no chat tool (owner decision; add one in `tool_store.py` on request).

---

## 📂 File Structure

```text
carzinomax-dev/                      # repo folder on disk is still CarzinomaxERP
├── README.md                            # Public overview (keep honest: works / minimal / planned)
├── AGENT.md                             # This file (tracked). CLAUDE.md / AGENTS.md are gitignored copies if you make them
├── LICENSE, NOTICE                      # Apache 2.0
├── pyproject.toml                       # Empty uv root (no deps); the real project is backend/pyproject.toml
├── skills-lock.json                     # Pins the LangChain skills vendored below
├── .agents/skills/, .claude/skills/     # Vendored langchain-ai/langchain-skills (langchain/langgraph/deep-agents guides); not app code
├── MasterBrain/                         # Private strategy notes — gitignored, never publish (may be absent)
│
├── backend/                             # FastAPI backend (Python 3.14, uv)
│   ├── .env.example                     # Copy to .env; SECRET_KEY has no default on purpose
│   ├── alembic.ini
│   ├── migration/                       # Alembic env + versions (0001_init is the baseline and the only revision)
│   ├── pyproject.toml / uv.lock         # Source of truth for deps; requirements.txt is a pip export
│   ├── logs/                            # Runtime logs (gitignored): system/system.log, users/<id>/user.log
│   ├── uploads/                         # Chat attachments (gitignored): <user_id>/<uuid>.<ext>
│   └── app/
│       ├── main.py                      # Lifespan: banner, admin seed, LLM ping, scheduler; CORS; /health
│       ├── ai_service/
│       │   ├── __init__.py              # exports `llm`, `init_orchestrator`
│       │   ├── agents.py                # ChatLiteLLM `llm`, sub-agents, orchestrator factory, HITL delete tools
│       │   ├── tool_store.py            # 40 @tool CRUD tools (sync sessions)
│       │   ├── llm_router.py            # LlmRouter (litellm) — legacy, unreferenced
│       │   └── prompts/                 # orchestrator_prompt.md + hr/expanse/scm/dev_helper_prompt.md
│       ├── api/
│       │   ├── common/general.py        # get_current_user (JWT bearer), permission_check
│       │   └── v1/                      # Routers, all mounted under /api/v1
│       │       ├── __init__.py          # api_router aggregates the six routers
│       │       ├── auth.py              # /auth: login, logout, me
│       │       ├── hr.py                # /hr: users, departments, attendance, leave_requests, paychecks
│       │       ├── finance.py           # /finance: expenses
│       │       ├── scm.py               # /scm: products
│       │       ├── dev_tracking.py      # /dev_tracking: projects, investments, downloads, github_repo, github_sync
│       │       └── chatbot.py           # /chatbot: LLM ping, attachment upload, NDJSON chatbox stream
│       ├── core/
│       │   ├── config.py                # pydantic-settings; derives ASYNC_DATABASE_URL (asyncpg)
│       │   ├── database.py              # async engine + SessionLocal/get_db; sync engine (psycopg) + SyncSessionLocal/get_sync_db
│       │   ├── github.py                # GitHub stars/downloads fetch + sync_github_repos (scheduler job and manual endpoint)
│       │   ├── log_module.py            # system_log() / user_log(user_id) on loguru
│       │   ├── scheduler.py             # APScheduler start/stop + the github_sync job
│       │   ├── security.py              # JWT create/decode, bcrypt hashing
│       │   └── uploads.py               # Chat attachments: sniff type, store, downscale images, load, PDF text
│       ├── middleware/                  # Empty package (unused)
│       ├── models/                      # SQLAlchemy 2.0 models
│       │   ├── base.py                  # Base (with to_dict()) + TimestampMixin
│       │   ├── auth.py                  # User
│       │   ├── hr.py                    # Department, AttendanceLog, LeaveRequest, Paycheck
│       │   ├── finance.py               # ExpenseType, Finance
│       │   ├── scm.py                   # Product
│       │   └── dev_tracking.py          # DevProject, DevInvestment, ProjectDownload, GithubRepo
│       └── schemas/
│           ├── auth.py                  # Token, TokenPayload, User* (used by auth + security)
│           ├── chatbot.py               # ChatMessage, ChatboxRequest (used by chatbot router)
│           └── finance.py, scm.py, hr.py, dev_tracking.py   # Legacy v1 schemas, unused
│
└── frontend/                            # React 19 + Vite SPA
    ├── .env.example                     # VITE_API_BASE_URL (default /api/v1)
    ├── vite.config.js                   # /api proxy to :8000
    └── src/
        ├── api/                         # One module per backend router (auth, hr, finance, scm, devTracking, chatbot)
        ├── components/ui/               # Design-system kit
        ├── components/layout/           # AppLayout (mounts ChatPanel), Sidebar
        ├── components/chat/ChatPanel.jsx
        ├── components/ResourceSection.jsx, SchemaForm.jsx, ProtectedRoute.jsx
        ├── context/                     # AuthContext, ToastContext
        ├── lib/                         # api.js, format.js, motion.js, roles.js, devStats.js, useChat/useList/useTheme/useUsers hooks
        ├── pages/                       # Login, Dashboard, hr/, finance/, scm/, devTracking/, admin/, NotFound
        └── styles/                      # ui.css, layout.css (tokens live in index.css)
```

---

## 🚀 Setup & Execution Commands

### Backend
Requires Python 3.14+, PostgreSQL, and [uv](https://github.com/astral-sh/uv). Run everything from `backend/` (the repo-root `pyproject.toml` is an empty placeholder).

```bash
cd backend
cp .env.example .env        # fill in ADMIN_DB_CONNECTION, ADMIN_EMAIL, ADMIN_PASSWORD, SECRET_KEY, LLM_*; optional GITHUB_TOKEN / GITHUB_SYNC_CRON / UPLOAD_DIR / UPLOAD_MAX_BYTES
uv sync
uv run alembic upgrade head # tables are created ONLY by Alembic; startup does not create_all
uv run uvicorn app.main:app --reload
```

* API docs: http://localhost:8000/docs. Health: `/health`.
* Schema changes go into `migration/versions/0001_init.py` (the single baseline revision); do not add new revisions.
* Databases created by the pre-Alembic `create_all` flow are auto-stamped at `0001` by `migration/env.py`.
* Chat agent without the API: `uv run python -m app.ai_service.agents` (interactive loop, approves deletes from the terminal).

### Frontend
```bash
cd frontend
npm install
npm run dev      # http://localhost:5173, proxies /api to the backend
npm run build    # set VITE_API_BASE_URL for production first
npm run lint
```

### Tests
There is no test suite (`backend/.pytest_cache` exists but holds nothing). If you add one, put it under `backend/tests/` and run with `uv run pytest`.

---

## 📝 Coding Standards & Conventions

### Backend (Python / FastAPI)
* **Async everywhere in routers.** Use `AsyncSession` from `Depends(get_db)`; queries via `select()` + `await db.scalars(...)` / `await db.get(Model, id)`. SQLAlchemy 2.0 `Mapped[...]` / `mapped_column(...)` style; new models inherit `Base` and usually `TimestampMixin`, and must be exported from `app/models/__init__.py`.
* **Sync only inside chat tools.** `tool_store.py` and `init_orchestrator` use `SyncSessionLocal` (psycopg) because LangChain tools run synchronously. Do not mix the two session types in one code path.
* **Response envelope.** Every module endpoint returns `JSONResponse` with `{"status": "success", "data": ...}` on 2xx or `{"status": "fail", "error": "..."}` on 4xx. Serialize ORM objects with `model.to_dict()` (from `Base`), never hand-built dicts. Update and delete omit `data`.
* **Endpoint shape.** Lists are `GET /<module>/<thing>_list`; single records are `/<module>/<thing>/{id}` with `POST` (create), `PUT` (partial update, all fields optional) and `DELETE`. Follow the existing pattern in `hr.py` when adding a resource.
* **Permission check first.** Every endpoint takes `current_user: User = Depends(get_current_user)` and begins with `if not await permission_check('<module>', current_user.id, db): return 403 envelope`. Do not add role checkers or new access flags without discussion.
* **Request models.** Routers define their request models inline as Pydantic v2 `BaseModel` subclasses next to the endpoints (e.g. `CreateExpense`, `CreatePaycheck`). The only shared schemas in use are `app/schemas/auth.py` and `app/schemas/chatbot.py`. Do not import the legacy finance/scm/hr/dev_tracking schemas. Responses are built from `model.to_dict()`, not from response schemas.
* **Logging.** One logger per file, never passed as an argument: `app/core/` modules bind `system_log = system_log()` right after the imports; endpoints start with `log = user_log(current_user.id)`. `system_log` is for startup/shutdown/auth attempts and background work, `user_log` for what a user triggered. Never `print` (the `__main__` block in `agents.py` is the one exception). Log `format_exc()` on caught exceptions. Chat tools do not log.
* **Config.** All settings come from `app.core.config.settings` (pydantic-settings, `.env`). Add new variables there and to `.env.example`. Never commit `.env`.
* **LLM calls.** Use the shared `llm` (`ChatLiteLLM`) from `app.ai_service` or go through the orchestrator; never import litellm or build a second model client in a router. For anything the code will act on, use structured output (a Pydantic model via `with_structured_output` or a tool) rather than parsing free text.
* **Chat tools.** One `@tool` per operation in `tool_store.py`; keep the `XxxDetail` / `GetXxxOutput` / `DeleteOutput` return models, filter only on non-`None` args, raise `ValueError` for bad input, no `user_id` argument. Register the tool in `agents.py` and document it in the matching prompt file; deletes go on the orchestrator and into the module's `*_DELETE_TOOLS`.
* **Startup must not hard-depend on the LLM.** The ping is best-effort; keep it that way so the ERP runs without an AI provider.
* **Scheduler jobs.** Register them in `start_scheduler()` before `scheduler.start()`. A job opens its own `SessionLocal` session, catches every exception and logs via the file's `system_log` with a `Scheduler:` prefix. Logic shared with an endpoint lives in `app/core/` (e.g. `github.py`) so the router calls the same function. Config errors (bad cron) are logged and the job skipped; startup keeps working.
* **Style.** PEP 8, type hints everywhere, f-strings only, short flat functions. Assign a call's result to a variable and return the variable (`response = JSONResponse(...)` then `return response`, not `return JSONResponse(...)`); existing `return func(...)` lines stay unless I ask. Copy the nearest existing endpoint or tool (`hr.py`, `tool_store.py`, `agents.py` and `core/github.py` are the reference files); if no pattern fits, ask me before inventing one. In detail:
  * **Docstrings.** Opening `"""` on its own line, the summary on the next line, `Args:` directly under it with no blank line, then a blank line and `Returns:` (and `Raises:` when the function raises on purpose). Identifiers in single backticks, never RST ``double`` backticks. A comment is one plain line that says why.
  * **Quotes.** Single quotes for strings, log messages and raised messages; double quotes only for JSON-like dict literals (the response envelope) and when the text contains a single quote.
  * **Flat functions.** One function does one real step top to bottom. No private micro-helpers (`_headers`, `_api_error`, `_load_repos`): a helper exists only when it is a step on its own that more than one caller or a test needs (`fetch_repo_stats`, `save_project_snapshots`). No `_` prefix on module-level names, no closures to share a logger.
  * **Structured data is Pydantic.** `BaseModel` for every record that is passed around (`XxxDetail`, `GetXxxOutput`, `GithubSyncResult`), never `@dataclass`.
  * **Errors.** `raise ValueError('message')` for bad input or a failed external call; the caller's `except Exception` logs `format_exc()` and turns it into the fail envelope. No custom exception classes, no status-code attributes.
  * **Long lines are fine.** Do not wrap a call or an f-string to fit 100 or 120 columns; a long statement on one line beats paren-aligned hanging indents.
  * **Typing.** `str | None` in new code (`Optional[...]` only where the surrounding model already uses it), no `TYPE_CHECKING` imports, no string annotations, no `Any` return types.

### Frontend (React)
* Plain JSX, no TypeScript. One API wrapper file per backend router in `src/api/`, using `src/lib/api.js`, which unwraps the envelope so wrappers resolve to `data`. Streaming endpoints use `apiPostStream`.
* Reuse the `ui/` kit and `ResourceSection` + `SchemaForm` for new CRUD screens instead of hand-rolling tables and forms.
* Navigation and page access are driven by the four module flags via `src/lib/roles.js`; a new module needs a flag mapping there and a route in `App.jsx`.
* Chat UI state belongs in `lib/useChat.js`; `ChatPanel` stays mounted so the transcript survives route changes.
* Respect `prefers-reduced-motion` and both themes (tokens in `index.css`).

### Docs
* `README.md` follows an honesty rule for building in public: mark features as working, minimal, or planned. Do not claim the AI flow works until the demo exists.
* When a module's real capability changes, update `README.md`, this file, and `frontend/README.md` together.
