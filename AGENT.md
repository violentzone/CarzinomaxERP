# CLAUDE.md & AGENT.md: Developer & Agent Reference Guide

Setup commands, run instructions, the real file layout, and the conventions an agent must follow when working on CarzinomaxERP. Keep this file in sync with the code; the public-facing overview lives in `README.md`.

---

## 🧭 What the project is

**CarzinomaxERP** — "the open-source ERP where AI does the data entry." An ERP sized for a small unit (solo founder to a handful of people). The flagship feature being built is the AI "receipt → booked" flow: a forwarded receipt or invoice becomes a categorized expense without manual entry. That flow does **not** exist yet; today the ERP is a set of CRUD modules plus a ready-to-use LLM router.

Status is pre-alpha. The codebase was rebuilt from scratch ("Init v2"); an earlier version had a general ledger, invoicing, warehouses and role-based RBAC. **None of that exists anymore.** Do not add features that assume it does.

---

## 🛠️ Main Features (current state)

### 1. Auth & access control ([api/v1/auth.py](backend/app/api/v1/auth.py), [api/common/general.py](backend/app/api/common/general.py))
* Default admin seeded on startup from `ADMIN_EMAIL` / `ADMIN_PASSWORD` in `.env`, with all four module flags.
* `POST /auth/login?user_email=…&password=…` returns a bare JWT string. `GET /auth/me` returns the current user. `POST /auth/logout` sets `tokens_valid_from` on the user so every token issued before now is rejected.
* **There are no roles.** `User` carries four booleans: `has_finance_access`, `has_scm_access`, `has_hr_access`, `has_dev_access`. Each router calls `permission_check('<module>', current_user.id, db)` at the top of every endpoint and returns a 403 envelope on failure.

### 2. People & Payroll / HR ([models/hr.py](backend/app/models/hr.py), [api/v1/hr.py](backend/app/api/v1/hr.py))
* Every `User` is an employee; the HR router owns user CRUD (`/hr/user…`, with `/hr/employee…` aliases).
* `Department` (code, name, manager_id), `AttendanceLog` (clock in/out, `total_hours`), `LeaveRequest` (type, dates, pending/approved/rejected, `approved_by_id`), `Paycheck` (period, base, allowances, deductions, `net_pay`, draft/paid).
* Paycheck creation computes `net_pay = base + allowances − deductions` unless the client sends one.

### 3. Dev Tracking ([models/dev_tracking.py](backend/app/models/dev_tracking.py), [api/v1/dev_tracking.py](backend/app/api/v1/dev_tracking.py))
* `DevProject` (keyed by `project_id`), `DevInvestment` (date, amount, vendor, category: cloud / software_licenses / hardware / consulting), `ProjectDownload` (per-platform download/star snapshots: github, dockerhub, npm).

### 4. Finance ([models/finance.py](backend/app/models/finance.py), [api/v1/finance.py](backend/app/api/v1/finance.py))
* Minimal. `Finance` has a UUID id and an `expense_type` enum (`paycheck`, `petty_cash`, `investment`, `other`) and nothing else. No amounts, vendors or dates yet. The frontend Finance overview derives totals from paychecks, investments and products.

### 5. Purchases / SCM ([models/scm.py](backend/app/models/scm.py), [api/v1/scm.py](backend/app/api/v1/scm.py))
* Minimal. `Product` (sku, name, description, unit_price, cost). No vendors, warehouses or purchase orders.

### 6. LLM router ([ai_service/llm_router.py](backend/app/ai_service/llm_router.py))
* `LlmRouter(user_id, function_called)` wraps litellm. Methods: `chat()`, `stream_chat()` (async generator), `parsed_chat(..., response_format=PydanticModel)` which validates the response against the model. All calls are logged to the user's log. Errors are re-raised as `LlmException`.
* `LlmRouter.model_check()` runs once at startup (a one-token ping). Failure is logged and does not block startup.
* Config: `LLM_TYPE` (`remote` | `local`), `LLM_MODEL` (litellm `<provider>/<model>` naming), `LLM_KEY`, `LLM_API_BASE` (used only when `local`).
* Nothing calls the router yet apart from the startup check. New AI features should instantiate it per request with the caller's user id.

### 6b. Chat control ([ai_service/agents.py](backend/app/ai_service/agents.py), [ai_service/tool_store.py](backend/app/ai_service/tool_store.py), [api/v1/chatbot.py](backend/app/api/v1/chatbot.py))
* `POST /chatbot/chatbox` streams NDJSON (`token` / `interrupt` / `done` / `error`) from a LangChain `create_agent` orchestrator built per request by `init_orchestrator(user_id)`. The model is `ChatLiteLLM` on the same `LLM_*` settings.
* `tool_store.py` holds one `@tool` per operation, get / create / update / delete for every table (40 tools), all sync via `SyncSessionLocal`. Style: a `XxxDetail` row model + `GetXxxOutput` with `total`, filters applied only when not `None`, `None` when nothing matches, `raise ValueError` on bad input. **No logging and no `user_id` parameter in tools**; access is decided by which tools the orchestrator receives.
* Sub-agents (`hr_helper`, `expanse_helper`, `scm_helper`, `dev_helper`, prompts in `ai_service/prompts/`) own read + create + update and are attached only when the caller has the module flag. `create_leave_request` is attached for every user. Delete tools sit on the orchestrator itself and go through `HumanInTheLoopMiddleware` (approve / reject) with an in-process `MemorySaver` checkpointer; the client keeps a `thread_id` and answers an `interrupt` event with `decision`.
* Adding a tool: write it in `tool_store.py` in the existing style, add it to the right sub-agent list (or the module's `*_DELETE_TOOLS`) in `agents.py`, and describe it in that agent's prompt file.

### 7. Scheduler ([core/scheduler.py](backend/app/core/scheduler.py))
* An `AsyncIOScheduler` starts and stops with the app. **No jobs are registered.** `PAYCHECK_CALCULATE_TIMESPOT` (cron string, default `0 0 1 * *`) is read into settings but unused; the monthly payroll job is planned, not implemented.

### 8. Frontend ([frontend/](frontend/))
* React 19 + Vite SPA, complete for every backend module: Dashboard, People & Payroll, Finance, Purchases, Dev Tracking, Users & Access. Framer Motion, Recharts, lucide-react, react-router. Native `fetch` wrapper in `src/lib/api.js` (no axios).
* Vite dev server proxies `/api` → `http://localhost:8000`. Sidebar is gated by the user's module flags. 403 shows an in-page "Restricted" panel; 401 clears the session.
* Details in [frontend/README.md](frontend/README.md).

---

## 📂 File Structure

```text
carzinomaxERP/
├── README.md                            # Public overview (keep honest: works / minimal / planned)
├── CLAUDE.md, AGENT.md                  # This file (identical copies; CLAUDE.md is gitignored)
├── LICENSE, NOTICE                      # Apache 2.0
├── MasterBrain/                         # Private strategy notes — gitignored, never publish
│
├── backend/                             # FastAPI backend (Python 3.14, uv)
│   ├── .env.example                     # Copy to .env; SECRET_KEY has no default on purpose
│   ├── alembic.ini
│   ├── migration/                       # Alembic env + versions (0001_init is the baseline)
│   ├── pyproject.toml / uv.lock
│   ├── logs/                            # Runtime logs (gitignored): system/system.log, users/<id>/user.log
│   └── app/
│       ├── main.py                      # Lifespan: banner, admin seed, LLM check, scheduler; CORS; /health
│       ├── ai_service/
│       │   └── llm_router.py            # LlmRouter (litellm)
│       ├── api/
│       │   ├── common/general.py        # get_current_user (JWT bearer), permission_check
│       │   └── v1/                      # Routers, all mounted under /api/v1
│       │       ├── __init__.py          # api_router aggregates the five routers
│       │       ├── auth.py              # /auth: login, logout, me
│       │       ├── hr.py                # /hr: users, departments, attendance, leave_requests, paychecks
│       │       ├── finance.py           # /finance: expenses
│       │       ├── scm.py               # /scm: products
│       │       └── dev_tracking.py      # /dev_tracking: projects, investments, downloads
│       ├── core/
│       │   ├── config.py                # pydantic-settings; derives ASYNC_DATABASE_URL (asyncpg)
│       │   ├── database.py              # async engine, SessionLocal, get_db dependency
│       │   ├── log_module.py            # system_log() / user_log(user_id) on loguru
│       │   ├── scheduler.py             # APScheduler start/stop (no jobs yet)
│       │   └── security.py              # JWT create/decode, bcrypt hashing
│       ├── models/                      # SQLAlchemy 2.0 models
│       │   ├── base.py                  # Base (with to_dict()) + TimestampMixin
│       │   ├── auth.py                  # User
│       │   ├── hr.py                    # Department, AttendanceLog, LeaveRequest, Paycheck
│       │   ├── finance.py               # ExpenseType, Finance
│       │   ├── scm.py                   # Product
│       │   └── dev_tracking.py          # DevProject, DevInvestment, ProjectDownload
│       └── schemas/auth.py              # Token, TokenPayload, User* schemas (the only shared schemas)
│
└── frontend/                            # React 19 + Vite SPA
    ├── .env.example                     # VITE_API_BASE_URL (default /api/v1)
    ├── vite.config.js                   # /api proxy to :8000
    └── src/
        ├── api/                         # One module per backend router
        ├── components/ui/               # Design-system kit
        ├── components/layout/           # AppLayout, Sidebar
        ├── components/ResourceSection.jsx, SchemaForm.jsx, ProtectedRoute.jsx
        ├── context/                     # AuthContext, ToastContext
        ├── lib/                         # api.js, format.js, motion.js, roles.js, hooks
        └── pages/                       # Login, Dashboard, hr/, finance/, scm/, devTracking/, admin/
```

---

## 🚀 Setup & Execution Commands

### Backend
Requires Python 3.14+, PostgreSQL, and [uv](https://github.com/astral-sh/uv).

```bash
cd backend
cp .env.example .env        # fill in ADMIN_DB_CONNECTION, ADMIN_EMAIL, ADMIN_PASSWORD, SECRET_KEY, LLM_*
uv sync
uv run alembic upgrade head # tables are created ONLY by Alembic; startup does not create_all
uv run uvicorn app.main:app --reload
```

* API docs: http://localhost:8000/docs. Health: `/health`.
* New migration after a model change: `uv run alembic revision --autogenerate -m "describe_change"`, then `uv run alembic upgrade head`. Alembic reads the same `.env` via `app.core.config.settings`.
* Databases created by the pre-Alembic `create_all` flow are auto-stamped at `0001` by `migration/env.py`.

### Frontend
```bash
cd frontend
npm install
npm run dev      # http://localhost:5173, proxies /api to the backend
npm run build    # set VITE_API_BASE_URL for production first
npm run lint
```

### Tests
There is no test suite yet (`.pytest_cache` is empty). If you add one, put it under `backend/tests/` and run with `uv run pytest`.

---

## 📝 Coding Standards & Conventions

### Backend (Python / FastAPI)
* **Async everywhere.** Use `AsyncSession` from `Depends(get_db)`; queries via `select()` + `await db.scalars(...)` / `await db.get(Model, id)`. SQLAlchemy 2.0 `Mapped[...]` / `mapped_column(...)` style; new models inherit `Base` and usually `TimestampMixin`, and must be exported from `app/models/__init__.py`.
* **Response envelope.** Every module endpoint returns `JSONResponse` with `{"status": "success", "data": ...}` on 2xx or `{"status": "fail", "error": "..."}` on 4xx. Serialize ORM objects with `model.to_dict()` (from `Base`), never hand-built dicts. Update and delete omit `data`.
* **Endpoint shape.** Lists are `GET /<module>/<thing>_list`; single records are `/<module>/<thing>/{id}` with `POST` (create), `PUT` (partial update, all fields optional) and `DELETE`. Follow the existing pattern in `hr.py` when adding a resource.
* **Permission check first.** Every endpoint takes `current_user: User = Depends(get_current_user)` and begins with `if not await permission_check('<module>', current_user.id, db): return 403 envelope`. Do not add role checkers or new access flags without discussion.
* **Request models.** Routers define their request models inline as Pydantic v2 `BaseModel` subclasses next to the endpoints (e.g. `CreateExpense`, `CreatePaycheck`). The only shared schemas are the auth ones in `app/schemas/auth.py` (`Token`, `TokenPayload`, `UserCreate`, `UserUpdate`, `UserResponse`). Responses are built from `model.to_dict()`, not from response schemas. Keep new request models inline unless two routers genuinely share one.
* **Logging.** Use `system_log()` for startup/shutdown/auth-attempt events and `user_log(user_id)` inside endpoints. Never `print`. Log `format_exc()` on caught exceptions.
* **Config.** All settings come from `app.core.config.settings` (pydantic-settings, `.env`). Add new variables there and to `.env.example`. Never commit `.env`.
* **LLM calls.** Go through `LlmRouter`; never import litellm directly in a router. Use `parsed_chat` with a Pydantic `response_format` for anything the code will act on.
* **Startup must not hard-depend on the LLM.** The model check is best-effort; keep it that way so the ERP runs without an AI provider.

### Frontend (React)
* Plain JSX, no TypeScript. One API wrapper file per backend router in `src/api/`, using `src/lib/api.js`, which unwraps the envelope so wrappers resolve to `data`.
* Reuse the `ui/` kit and `ResourceSection` + `SchemaForm` for new CRUD screens instead of hand-rolling tables and forms.
* Navigation and page access are driven by the four module flags via `src/lib/roles.js`; a new module needs a flag mapping there and a route in `App.jsx`.
* Respect `prefers-reduced-motion` and both themes (tokens in `index.css`).

### Docs
* `README.md` follows an honesty rule for building in public: mark features as working, minimal, or planned. Do not claim the AI flow works until the demo exists.
* When a module's real capability changes, update `README.md`, this file, and `frontend/README.md` together.
