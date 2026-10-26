# CLAUDE.md & AGENT.md: Developer & Agent Reference Guide

Setup commands, run instructions, the real file layout, and the conventions an agent must follow when working on Carzinomax DEV. Keep this file in sync with the code; the public-facing overview lives in `README.md`.

---

## 🧭 What the project is

**Carzinomax DEV** — "the open-source ERP where AI does the data entry." An ERP sized for a small unit (solo founder to a handful of people). The flagship feature being built is the AI "receipt → booked" flow: a forwarded receipt or invoice becomes a categorized expense without manual entry. The upload half of it exists (Finance page "Book from receipt" and the chat, see Finance below); email forwarding does not. Beyond that the ERP is a set of CRUD modules plus an in-app chat assistant that can read, create, update and (with approval) delete records in every module.

Status is pre-alpha. The codebase was rebuilt from scratch ("Init v2"); an earlier version had a general ledger, invoicing, warehouses and role-based RBAC. **None of that exists anymore.** Do not add features that assume it does. Leftovers of the old version still sit in `app/schemas/` (see Known gaps); ignore them.

---

## 🛠️ Main Features (current state)

### 1. Auth & access control ([api/v1/auth.py](backend/app/api/v1/auth.py), [api/common/general.py](backend/app/api/common/general.py))
* Default admin seeded on startup from `ADMIN_EMAIL` / `ADMIN_PASSWORD` in `.env`, with all four module flags and `send_summary` on.
* `POST /auth/login?user_email=…&password=…` returns a bare JWT string (7-day expiry). `GET /auth/me` returns the current user. `POST /auth/logout` sets `tokens_valid_from` on the user so every token issued before now is rejected.
* **There are no roles.** `User` carries four booleans: `has_finance_access`, `has_scm_access`, `has_hr_access`, `has_dev_access`. Each router calls `permission_check('<finance|scm|hr|dev>', current_user.id, db)` at the top of every endpoint and returns a 403 envelope on failure.
* `User` also carries `send_summary` (bool, default false): opt-in to the scheduled project summary mail (`summary_mail` job). It is **not** an access flag; it is settable through `POST`/`PUT /hr/user`, the `create_user` / `update_user` chat tools (and a `get_user_info` filter), and the "Receive project summary email" toggle in Users & Access.

### 2. People & Payroll / HR ([models/hr.py](backend/app/models/hr.py), [api/v1/hr.py](backend/app/api/v1/hr.py))
* Every `User` is an employee; the HR router owns user CRUD (`/hr/user…`; `/hr/employee_list` and `/hr/employee/{id}` are read-only aliases).
* `Department` (code, name, manager_id), `AttendanceLog` (clock in/out, `total_hours`), `LeaveRequest` (type, dates, pending/approved/rejected, `approved_by_id`), `Paycheck` (period, base, allowances, deductions, `net_pay`, draft/paid). `pay_period_end` is nullable: NULL means open-ended, the member is still working; period filters treat it as ongoing.
* Paycheck creation computes `net_pay = base + allowances − deductions` unless the client sends one.

### 3. Dev Tracking ([models/dev_tracking.py](backend/app/models/dev_tracking.py), [api/v1/dev_tracking.py](backend/app/api/v1/dev_tracking.py))
* `DevProject` (keyed by `project_id`), `DevInvestment` (date, amount, vendor, category: cloud / software_licenses / hardware / consulting / other, listed in `DEV_INVESTMENT_CATEGORIES`), `ProjectDownload` (per-platform download/star snapshots: github, dockerhub, npm). Deleting a project cascades to its investments, snapshots and tracked repos.
* `GithubRepo` (table `dev_github_repos`: `project_id`, unique `full_name` as `owner/name`, latest `star_count` / `download_count`, `last_synced_at`, `last_error`). `app/core/github.py` fetches `stargazers_count` and the sum of release-asset `download_count` over all releases (httpx; `GITHUB_TOKEN` is optional for public repos and required for private ones) and upserts **one `ProjectDownload` row per project per UTC day** (platform `github`, totals over the project's repos, updated in place; hand edits to that row are overwritten). It runs from the scheduler and from `POST /dev_tracking/github_sync[/{repo_id}]`, which answers `{synced: [...], failed: [...]}`; a repo whose fetch fails keeps its old numbers and stores `last_error`. REST CRUD lives at `/dev_tracking/github_repo…`: `POST /github_repo` commits the row and then runs `sync_github_repos(db, repo.id)` so the numbers and today's snapshot are there right away (a failed pull leaves the repo tracked with `last_error`), and renaming a repo clears its cached numbers. Chat has `create_github_repo` only (tracks a repo and pulls its numbers right away, via `fetch_repo_stats_once`, no snapshot); list / rename / untrack stay REST-only (owner decision).

### 4. Finance ([models/finance.py](backend/app/models/finance.py), [api/v1/finance.py](backend/app/api/v1/finance.py), [core/finance.py](backend/app/core/finance.py), [core/receipts.py](backend/app/core/receipts.py))
* `Finance` (table `finance`): UUID id, `expense_type` enum (`paycheck`, `petty_cash`, `investment`, `other`), required `amount` (Numeric 15,2), `vendor`, `reference` (invoice / receipt number), `description`, `category` (String; allowed values are the `ExpenseCategory` Literal in `models/finance.py`: cloud, software_licenses, hardware, consulting, travel, office, meals, other), `expense_date` (Date, not null, Python default today), `due_date`, `paid_date` (NULL = unpaid; unpaid with `due_date` < today = overdue), `project_id` (FK `dev_projects`, ON DELETE SET NULL), `receipt_path` (`"<user_id>/<uuid>.<ext>"` under `UPLOAD_DIR`, the document the expense was booked from, served back by `GET /finance/expense/{id}/receipt`). Every column is in `0001_init`.
* REST: `CreateExpense` / `UpdateExpense` carry all fields (`receipt_path` on create only; it must be a file `POST /finance/receipt` stored for the caller, else 400). Create validates `project_id` (404) and calls `investment_from_expense` (`core/finance.py`): an `investment` with a `project_id` also inserts a `DevInvestment` row in the same commit (owner decision, double entry; a category outside `DEV_INVESTMENT_CATEGORIES` is mirrored as `other`). Update and delete do **not** touch the mirror. A user with finance access but no dev flag still writes that mirror row. Unlike the other routers, update treats an explicit `null` for `vendor`, `reference`, `description`, `category`, `due_date`, `paid_date` or `project_id` (`CLEARABLE_EXPENSE_FIELDS`, checked via `model_fields_set`) as "clear it", because the ledger form sends null for an emptied field and re-opening a bill needs `paid_date` cleared; an omitted field is still left alone. The chat `update_expense` keeps the project-wide None = no change rule.
* `POST /finance/receipt` (multipart `file`, finance permission, tag `[RECEIPT]`): `save_attachment` (same sniffing, 10 MB cap and JPEG downscale as the chat upload) → `extract_receipt` → `{"receipt_path", "draft", "note"}`. `draft` is `ReceiptDraft` (`core/receipts.py`: vendor, reference, amount, currency (display only, never stored), expense_date / due_date as ISO strings, `paid` (true for a till or card receipt, false for an invoice, null when unclear), expense_type, category, description, project_name resolved to `project_id` by the router, confidence high / medium / low, notes) with lenient validators (a mis-formatted date, unknown type or category becomes None instead of failing the draft). When the model cannot read it (scanned PDF without text layer, unusable answer, provider down) the endpoint still answers 200 with `draft: null` and `note`, because the file is stored and the user can book by hand. Nothing is booked by this endpoint.
* `GET /finance/expense/{id}/receipt` (finance permission, tag `[RECEIPT]`) answers with the stored file itself (`FileResponse`, media type from the stored extension, `Content-Disposition: inline`), not the JSON envelope; 404 envelope when the expense does not exist, has no `receipt_path`, or the file is missing, has an unknown extension or is not under `UPLOAD_ROOT`. Any user with finance access may view any expense's receipt (the ledger is shared); the DB row is the authority, the path is resolved under `UPLOAD_ROOT` only.
* `extract_receipt` builds the same block shapes as the chat (`image` block or PDF text in `<attachment>`), prepends `prompts/receipt_extract_prompt.md` plus a `<context>` block (today, allowed types and categories, project names) and calls `llm.with_structured_output(ReceiptDraft, method='json_schema', strict=False)`; JSON-schema mode because local vision models rarely support tool calling, not strict because strict schemas refuse optional fields. It lives in its own module because `core/finance.py` is imported by `tool_store.py`, and importing `app.ai_service` from there would be circular.
* Frontend: the ledger has a "Book from receipt" button (file picker → `POST /finance/receipt` → the create modal opens prefilled with the draft and a note; Save posts the normal create with `receipt_path`), a payment-status filter, unpaid / overdue tiles, and the overview shows the ledger total and unpaid bills. Dates in the draft fill the form as they are; `paid_date` is set to the document date when `paid` is true. A row with a `receipt_path` is clickable (vendor name, plus a paperclip row action): `ReceiptModal` fetches the file with the bearer token (`apiGetBlob`) and shows it through an object URL, an image inline or a PDF in a frame, with an "Open in new tab" link.

### 5. Purchases / SCM ([models/scm.py](backend/app/models/scm.py), [api/v1/scm.py](backend/app/api/v1/scm.py))
* Minimal. `Product` (sku, name, description, unit_price, cost). No vendors, warehouses or purchase orders.

### 6. LLM model ([ai_service/agents.py](backend/app/ai_service/agents.py))
* The live model object is `llm`, a module-level `ChatLiteLLM` in `agents.py` (re-exported from `app.ai_service`). It is built from `LLM_MODEL` / `LLM_API_KEY`, and `LLM_API_BASE` only when `LLM_TYPE == 'local'`.
* Startup runs `llm.invoke('ping', max_tokens=1)` once; failure is logged and does not block startup. `POST /chatbot/` repeats the same ping on demand (bearer token, any signed-in user; answers `{live, message}` directly, not the envelope).
* `llm` is the only model client. New AI code goes through it or the orchestrator; never import litellm directly or build a second client.
* Config: `LLM_TYPE` (`remote` | `local`), `LLM_MODEL` (litellm `<provider>/<model>` naming), `LLM_API_KEY`, `LLM_API_BASE`. The model must accept image input: chat attachments are sent as image blocks with no text-only fallback (README, "Pick an LLM").

### 6b. Chat control ([ai_service/agents.py](backend/app/ai_service/agents.py), [ai_service/tool_store.py](backend/app/ai_service/tool_store.py), [api/v1/chatbot.py](backend/app/api/v1/chatbot.py))
* `POST /chatbot/chatbox` takes `ChatboxRequest` (`message`, `history`, `thread_id`, `decision`, `attachments`; schema in `app/schemas/chatbot.py`) and streams NDJSON events `token` / `interrupt` / `done` / `error` from a LangChain `create_agent` orchestrator built per request by `init_orchestrator(user_id)`.
* Orchestrator prompt = `prompts/orchestrator_prompt.md` + a `<context>` block (today, caller id, name, four flags). Sub-agent queries are prefixed with today's date (`with_today`) so relative periods resolve.
* `tool_store.py` holds one `@tool` per operation, get / create / update / delete for every table (41 tools), all sync via `SyncSessionLocal`. Style: a `XxxDetail` row model + `GetXxxOutput` with `total`, filters applied only when not `None`, `None` when nothing matches, `raise ValueError` on bad input. **No logging and no `user_id` parameter in tools**; access is decided by which tools the orchestrator receives. Leave has `review_leave_request` (approve/reject) instead of a generic update. The finance tools carry every `Finance` column: `get_expenses` filters on `expense_date` (not `created_at`), `vendor` (case-insensitive contains), `project_id` and `unpaid_only`; `create_expense` defaults `expense_date` to today, mirrors an investment with a project through `investment_from_expense` like REST, and takes an optional `attachment_id` (the `id` on the `<attachment>` block) that it resolves through `attachment_path(None, id)` (`core/uploads.py`: `user_id=None` globs every user's directory after the id format check, because tools do not know the caller; the uuid4 is known only to its uploader) into `receipt_path`, so an expense booked in chat keeps its receipt.
* Sub-agents (`hr_helper`, `expanse_helper`, `scm_helper`, `dev_helper`, prompts in `ai_service/prompts/`) own read + create + update and are attached only when the caller has the module flag. `create_leave_request` is attached for every user. Delete tools sit on the orchestrator itself (`*_DELETE_TOOLS` lists) and go through `HumanInTheLoopMiddleware` (approve / reject).
* Approval state lives in a single in-process `MemorySaver` checkpointer (lost on restart). The client keeps a `thread_id`; the server namespaces it as `<user_id>:<thread_id>` so nobody can resume another user's paused run. A request with `decision` resumes the paused run; a new `message` while an approval is pending is rejected with 400. The client's `history` (last 10 messages) is only used when the checkpoint for the thread is empty.
* The stream forwards only the orchestrator's own model tokens (`langgraph_node == 'model'`, no nested namespace); sub-agent output and tool results are not streamed.
* Booking a receipt in chat: the orchestrator sees the image in the turn it arrives only (`CurrentImageOnly`), so `orchestrator_prompt.md` rule 11 makes the first-turn summary list every bookable field and rule 12 describes the booking (type and category choice, `project_id` via `dev_helper` when the user has dev access, otherwise no project link, `paid_date` = document date for a paid receipt, currency warning). `expanse_helper` cannot look projects up; the orchestrator passes the id, and passes the document's `attachment_id` so the booked expense gets its `receipt_path`.
* Attachments: `POST /chatbot/upload` (multipart field `file`, auth only, one file per request) sniffs the type from the bytes (PNG / JPEG / WebP / PDF), caps the size at `UPLOAD_MAX_BYTES` (10 MB), re-encodes images as JPEG (at most 1,003,520 pixels, EXIF-rotated) and stores the file as `<UPLOAD_DIR>/<user_id>/<uuid>.<ext>` (`app/core/uploads.py`; no table, kept forever, `uploads/` is gitignored). The returned `id` goes into `ChatboxRequest.attachments` (at most `MAX_ATTACHMENTS` = 5, of which one image). `attachment_blocks` in `agents.py` turns them into content blocks on the user turn: an image block (`{'type': 'image', 'base64', 'mime_type'}`) or the pypdf text inside an `<attachment>` text block. The `CurrentImageOnly` middleware keeps the image block of the newest user turn only, so every model request carries at most one image (small-GPU vision models); older turns show `[image no longer attached]` to the model while the checkpoint stays intact. Attachments reach the orchestrator only (sub-agent queries stay text), are not replayed from `history` after a restart (the client marks such turns with `[attached: name]`), and an unknown or foreign id is a 400 before the stream starts.
* Adding a tool: write it in `tool_store.py` in the existing style, add it to the right sub-agent list (or the module's `*_DELETE_TOOLS`) in `agents.py`, and describe it in that agent's prompt file.
* `agents.py` has a `__main__` CLI loop for manual testing: `uv run python -m app.ai_service.agents` from `backend/` (uses user id 1).

### 7. Scheduler ([core/scheduler.py](backend/app/core/scheduler.py))
* An `AsyncIOScheduler` starts and stops with the app. Two jobs are registered: `summary_mail` (below) and `github_sync` (`CronTrigger.from_crontab(GITHUB_SYNC_CRON)`, default `0 */6 * * *`, `misfire_grace_time=3600`) opens its own `SessionLocal` session and calls `sync_github_repos`. Jobs catch every exception and log through `system_log()` with a `Scheduler:` prefix, because APScheduler reports job errors via std `logging`, which is not forwarded to loguru. An invalid cron string is logged at startup and the job is skipped. There is one scheduler per process, so run the backend single-worker.
* `PAYCHECK_CALCULATE_TIMESPOT` (cron string, default `0 0 1 * *`) is still read into settings but unused; the monthly payroll job is planned, not implemented.
* `send_email(send_to, subject, body) -> list[str]` (sync, stdlib `smtplib`, 30 s timeout) sends plain-text mail through `SMTP_HOSTNAME` / `SMTP_PORT` (465 = implicit SSL, anything else STARTTLS) / `SMTP_USER` / `SMTP_PASSWORD` / `MAIL_FROM`, all required from `.env`; it returns the accepted addresses, logs `[EMAIL]`, and raises on connection failure. Call it from async code via `asyncio.to_thread`.
* `generate_summary()` asks the shared `llm` (`ChatLiteLLM`, via `ainvoke` with a system + human message) for a Markdown status summary of every table. SCM goes in as raw `to_dict()` rows; HR, Finance and Dev Tracking go in pre-aggregated in SQL as plain dicts. `query_finance_summary(session)` covers expense count and total, this month vs last month by `expense_date`, total per type, largest expense, newest `created_at`, unpaid count / total (no `paid_date`), overdue count / total and the next due date. `query_hr_summary(session)` covers users (total, active / inactive, administrators with all four flags, per-module counts; raw user rows, which include `hashed_password`, are no longer sent), departments without a manager, today's attendance and open clock-ins, hours this month, pending leave with the oldest request's `created_at`, users on approved leave today, draft / paid paychecks, net pay paid this month, next and overdue draft payment dates. `query_dev_tracking_summary(session)` covers project count and projects without a repo via a left join on `GithubRepo`, investment totals overall / this month / per category, repo count with stars, downloads, last sync and error count, snapshot count and newest date) so the payload stays small as snapshots accumulate. `send_summary()` is the job itself: it selects the emails of users with `send_summary`, returns early with no LLM call and no mail when nobody opted in (an empty To header is refused by SMTP), otherwise calls `generate_summary()` and `send_email` via `asyncio.to_thread` with the subject `Carzinomax Dev summary`, and returns the accepted addresses. It never raises: every failure is logged as `[SUMMARY_MAIL] failed` with the traceback and it returns an empty list. It is registered in `start_scheduler()` as job id `summary_mail` with `misfire_grace_time=3600` on a `CronTrigger` built from the settings, which `config.py` validates at startup — `SUMMARY_SEND_TIME` (hour 0-23, server local, minute 0), `SUMMARY_SEND_FREQ` (`day` | `week` | `month`), `SUMMARY_SEND_WEEKDAY` (0-6, Monday = 0, required when `week`), `SUMMARY_SEND_MONTHDAY` (1-31, required when `month`). The filter is `send_summary` only; `is_active` is not checked.

### 8. Frontend ([frontend/](frontend/))
* React 19 + Vite SPA, complete for every backend module: Dashboard, People & Payroll, Finance, Purchases, Dev Tracking, Users & Access. Framer Motion, Recharts, lucide-react, react-router. Native `fetch` wrapper in `src/lib/api.js` (no axios).
* Dev Tracking has a fourth tab, **GitHub repos**: lists `dev_github_repos` (stars, downloads, last sync, error) and adds a repo; remove / rename / `github_sync` have no UI yet.
* Finance's ledger tab has **Book from receipt** (hidden file input → `financeApi.readReceipt` → `ResourceSection`'s `openCreate(values, note)` opens the create modal prefilled; `preparePayload` adds `receipt_path` on create), a payment-status filter and unpaid / overdue tiles; shared helpers in `lib/expenses.js` (`isOverdue`) and `lib/uploads.js` (upload limits, also used by the chat composer). Rows booked from a document open `ReceiptModal` (in `pages/finance/FinancePage.jsx`) via `financeApi.fetchReceipt` → `apiGetBlob`.
* Chat assistant: `components/chat/ChatPanel.jsx` (slide-over drawer mounted in `AppLayout`), `lib/useChat.js` (transcript, `send`, `decide`, `reset`, client-generated `thread_id`), `api/chatbot.js` (NDJSON reader over `apiPostStream`, `upload` over `apiPostForm`). The composer's paperclip or a pasted image attaches PNG / JPEG / WebP / PDF files (5 per message, 10 MB each); they upload before the turn streams and show as chips / thumbnails in the user bubble.
* Vite dev server proxies `/api` → `http://localhost:8000`. Sidebar is gated by the user's module flags. 403 shows an in-page "Restricted" panel; 401 clears the session.
* Details in [frontend/README.md](frontend/README.md).

### ⚠️ Known gaps (do not build on these)
* `app/schemas/finance.py`, `scm.py`, `hr.py`, `dev_tracking.py` describe tables from the old version (GL accounts, journal entries, invoices, fixed assets, payments, product categories, dev worker paychecks). They are re-exported by `schemas/__init__.py` but **used by nothing**. Routers define their own request models inline.
* `app/middleware/` is an empty package; `langgraph-supervisor` is in `pyproject.toml` but never imported.
* `backend/README.md` is empty.
* `GithubRepo` has REST endpoints but no chat tool (owner decision; add one in `tool_store.py` on request).
* An existing database does not get the new finance columns from Alembic (single baseline edited in place): recreate it, or add the columns by hand.

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
│       │   ├── tool_store.py            # 41 @tool CRUD tools (sync sessions)
│       │   └── prompts/                 # orchestrator_prompt.md + hr/expanse/scm/dev_helper_prompt.md, receipt_extract_prompt.md, project_summary.md
│       ├── api/
│       │   ├── common/general.py        # get_current_user (JWT bearer), permission_check
│       │   └── v1/                      # Routers, all mounted under /api/v1
│       │       ├── __init__.py          # api_router aggregates the six routers
│       │       ├── auth.py              # /auth: login, logout, me
│       │       ├── hr.py                # /hr: users, departments, attendance, leave_requests, paychecks
│       │       ├── finance.py           # /finance: expenses, receipt (AI draft from an upload), expense/{id}/receipt (serves the stored file)
│       │       ├── scm.py               # /scm: products
│       │       ├── dev_tracking.py      # /dev_tracking: projects, investments, downloads, github_repo, github_sync
│       │       └── chatbot.py           # /chatbot: LLM ping (auth), attachment upload, NDJSON chatbox stream
│       ├── core/
│       │   ├── config.py                # pydantic-settings; derives ASYNC_DATABASE_URL (asyncpg)
│       │   ├── database.py              # async engine + SessionLocal/get_db; sync engine (psycopg) + SyncSessionLocal/get_sync_db
│       │   ├── finance.py               # investment_from_expense: mirror of an investment expense into dev_investments (REST + chat tool)
│       │   ├── github.py                # GitHub stars/downloads fetch + sync_github_repos (scheduler job and manual endpoint)
│       │   ├── log_module.py            # system_log() / user_log(user_id) on loguru
│       │   ├── receipts.py              # ReceiptDraft + extract_receipt: the LLM reads a receipt into an expense draft (structured output)
│       │   ├── scheduler.py             # APScheduler start/stop + the github_sync job
│       │   ├── security.py              # JWT create/decode, bcrypt hashing
│       │   └── uploads.py               # Chat attachments: sniff type, store, downscale images, load (by owner or by id alone), PDF text
│       ├── middleware/                  # Empty package (unused)
│       ├── models/                      # SQLAlchemy 2.0 models
│       │   ├── base.py                  # Base (with to_dict()) + TimestampMixin
│       │   ├── auth.py                  # User
│       │   ├── hr.py                    # Department, AttendanceLog, LeaveRequest, Paycheck
│       │   ├── finance.py               # ExpenseType, ExpenseCategory, Finance
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
        ├── lib/                         # api.js, format.js, motion.js, roles.js, devStats.js, expenses.js, uploads.js, useChat/useList/useTheme/useUsers hooks
        ├── pages/                       # Login, Dashboard, hr/, finance/, scm/, devTracking/, admin/, NotFound
        └── styles/                      # ui.css, layout.css (tokens live in index.css)
```

---

## 🚀 Setup & Execution Commands

### Backend
Requires Python 3.14+, PostgreSQL, and [uv](https://github.com/astral-sh/uv). Run everything from `backend/` (the repo-root `pyproject.toml` is an empty placeholder).

```bash
cd backend
cp .env.example .env        # fill in ADMIN_DB_CONNECTION, ADMIN_EMAIL, ADMIN_PASSWORD, SECRET_KEY, LLM_*, SMTP_* / MAIL_FROM, SUMMARY_SEND_TIME / SUMMARY_SEND_FREQ (+ WEEKDAY or MONTHDAY); optional GITHUB_TOKEN / GITHUB_SYNC_CRON / UPLOAD_DIR / UPLOAD_MAX_BYTES
uv sync
uv run alembic upgrade head # tables are created ONLY by Alembic; startup does not create_all
uv run uvicorn app.main:app --reload
```

* API docs: http://localhost:8000/docs. Health: `/health`.
* Schema changes go into `migration/versions/0001_init.py` (the single baseline revision); do not add new revisions. A database that already exists is therefore not migrated: recreate it (`docker compose down -v`) or add the columns by hand (see Known gaps).
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
* **Endpoint shape.** Lists are `GET /<module>/<thing>_list`; single records are `/<module>/<thing>/{id}` with `POST` (create), `PUT` (partial update, all fields optional, `None` = leave unchanged; Finance additionally clears `CLEARABLE_EXPENSE_FIELDS` on an explicit `null`, see Finance above) and `DELETE`. Follow the existing pattern in `hr.py` when adding a resource.
* **Permission check first.** Every endpoint takes `current_user: User = Depends(get_current_user)` and begins with `if not await permission_check('<module>', current_user.id, db): return 403 envelope`. Do not add role checkers or new access flags without discussion.
* **Request models.** Routers define their request models inline as Pydantic v2 `BaseModel` subclasses next to the endpoints (e.g. `CreateExpense`, `CreatePaycheck`). The only shared schemas in use are `app/schemas/auth.py` and `app/schemas/chatbot.py`. Do not import the legacy finance/scm/hr/dev_tracking schemas. Responses are built from `model.to_dict()`, not from response schemas.
* **Logging.** One logger per file, never passed as an argument: `app/core/` modules bind `system_log = system_log()` right after the imports; endpoints start with `log = user_log(current_user.id)`. `system_log` is for startup/shutdown/auth attempts and background work, `user_log` for what a user triggered. Never `print` (the `__main__` block in `agents.py` is the one exception). Log `format_exc()` on caught exceptions. Chat tools do not log. Every message starts with an upper-snake-case tag in brackets naming the resource or job, e.g. `[USER]`, `[PAYCHECK]`, `[GITHUB_SYNC]`, `[SUMMARY_MAIL]`: CRUD routers tag per resource, jobs and infrastructure per file or job.
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
* Plain JSX, no TypeScript. One API wrapper file per backend router in `src/api/`, using `src/lib/api.js`, which unwraps the envelope so wrappers resolve to `data`. Streaming endpoints use `apiPostStream`; binary files (a stored receipt) use `apiGetBlob` and an object URL, because an `<img src>` cannot carry the bearer token.
* Reuse the `ui/` kit and `ResourceSection` + `SchemaForm` for new CRUD screens instead of hand-rolling tables and forms.
* Navigation and page access are driven by the four module flags via `src/lib/roles.js`; a new module needs a flag mapping there and a route in `App.jsx`.
* Chat UI state belongs in `lib/useChat.js`; `ChatPanel` stays mounted so the transcript survives route changes.
* Respect `prefers-reduced-motion` and both themes (tokens in `index.css`).

### Docs
* `README.md` follows an honesty rule for building in public: mark features as working, minimal, or planned. Do not claim the AI flow works until the demo exists.
* When a module's real capability changes, update `README.md`, this file, and `frontend/README.md` together.

### Workflow: one designer, one reviewer
* Every feature or multi-step change is built by two separate agents: the **designer** (who also implements) and an independent **reviewer** that did not write the design or the code. The reviewer is a fresh general-purpose agent, never a fork of the designer, briefed with this file, the design file and the files the change touches.
* Order of work: the designer writes the design to a file → the reviewer evaluates it and answers in four lists (blocking / should-fix / nits / confirmed-fine) → the designer fixes the design → implementation goes step by step, and after every step the designer sends the **same** reviewer the step's scope and diff and applies its fixes before starting the next step → the recap to the owner reports the reviewer's findings and what was done about them.
* The reviewer reads the actual code, not the designer's summary of it; its job is to catch assumptions the designer anchored on (a helper that does not exist, a convention breach, a wrong library call). A step is not done while a blocking or should-fix finding is open.
