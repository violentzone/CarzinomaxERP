<div align="center">

# CarzinomaxERP

### The open-source ERP where AI does the data entry.

Snap a receipt or forward an invoice — the AI creates the bill, categorizes the
expense, posts it to your ledger, and schedules the payment. Self-hostable, and
built for founders who'd rather build than bookkeep.

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python 3.14+](https://img.shields.io/badge/python-3.14+-3776AB.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![React 19](https://img.shields.io/badge/React-19-61DAFB.svg)](https://react.dev/)
[![Status: pre-alpha](https://img.shields.io/badge/status-pre--alpha-orange.svg)](#-what-works-today)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](#-contributing)

**⭐ Star the repo to follow along — we're building in public.**

</div>

---

## Why another ERP?

Existing ERPs (Odoo, ERPNext, SAP) are powerful but assume you have a **team of
people to feed them data** — someone to type in invoices, reconcile payments,
and categorize every expense. Solo founders and tiny teams don't have that.

CarzinomaxERP flips it: the ERP does the paperwork **for** you. You hand it a
document; the AI does the busywork and asks you to confirm. The goal is an ERP
that a two-person company can actually run without hiring a bookkeeper.

## The flagship: "Receipt → Booked" 🔜

The wedge we're building first:

```
You:  *forwards a $340 AWS invoice*

AI:   Booked it. Here's what I did:
      • Created expense       INV-AWS-0725  ·  $340.00
      • Categorized to        investment · Cloud (AWS)
      • Linked to project     carzinomax-erp
      • Due date              2026-08-14  → flagged
      Want me to schedule the payment for the 12th?
```

One forwarded email replaces five minutes of manual data entry — and it lands
as a proper record in your books, not a note in a spreadsheet.

## ✅ What works today

The ERP is sized for a small unit and currently does four things: tracks the
software you're building and what it costs, pays the people building it,
classifies the unit's spending, and keeps a product catalog. The AI layer is
wired in but not yet driving any feature.

| Area | Status | Notes |
|------|--------|-------|
| **Auth & access control** | ✅ Working | JWT login/logout (logout revokes every earlier token), seeded admin, per-module access flags |
| **People & Payroll (HR)** | ✅ Working | Every user is an employee. Departments, attendance clock-in/out with hours, leave requests with approve/reject, paychecks (base + allowances − deductions) |
| **Dev Tracking** | ✅ Working | Projects, money invested per project (cloud, licences, hardware, consulting), download/star snapshots per platform (GitHub, Docker Hub, npm) |
| **Finance** | 🚧 Minimal | Typed expense ledger (paycheck / petty cash / investment / other). The Finance overview rolls payroll, project investments and purchases into one view |
| **Purchases (SCM)** | 🚧 Minimal | Product catalog: SKU, cost, list price |
| **React frontend** | ✅ Working | Full SPA: dashboard, all modules, user & access admin, light/dark theme, permission-gated navigation |
| **LLM router** | ✅ Working | Provider-agnostic via [litellm](https://github.com/BerriAI/litellm): hosted APIs or a local server. Connection is verified at startup; chat, streaming and schema-validated (parsed) calls are ready |
| **AI back office** | 🔜 In progress | The "receipt → booked" flow above — the whole point. No AI-driven endpoints yet |
| **Background scheduler** | 🚧 Scaffolded | APScheduler starts with the app; no jobs registered yet (monthly payroll run is planned) |

Every module endpoint answers with the same envelope, so the frontend and any
future AI agent share one contract:

```json
{ "status": "success", "data": ... }      // 2xx
{ "status": "fail",    "error": "..." }   // 4xx  (403 = no module access)
```

## 🔐 Access model

There are no roles. Each user carries four flags — `has_dev_access`,
`has_hr_access`, `has_finance_access`, `has_scm_access` — and each backend
router checks its own flag on every request. The sidebar shows only the modules
the signed-in user holds a flag for. A user with all four flags is, for display
purposes, an administrator. The admin seeded from `.env` on first boot has all
four.

## 🧱 Tech stack

- **Backend:** FastAPI (async), Python 3.14, [uv](https://github.com/astral-sh/uv) for dependencies
- **Database:** PostgreSQL via SQLAlchemy 2.0 (async / asyncpg), migrations with Alembic
- **Auth:** JWT (PyJWT) + bcrypt, per-module access flags, logout-based token revocation
- **AI:** [litellm](https://github.com/BerriAI/litellm) router — point it at Anthropic, OpenAI, Gemini, or a self-hosted Ollama / OpenAI-compatible server
- **Scheduling:** APScheduler (async)
- **Logging:** loguru, with a system log plus one log file per user
- **Frontend:** React 19 + Vite, react-router, Framer Motion, Recharts, lucide-react (no axios — a small `fetch` wrapper)

## 🚀 Quickstart

**Prerequisites:** Python 3.14+, PostgreSQL, [uv](https://github.com/astral-sh/uv), and Node 20+ for the frontend.

### 1. Backend

```bash
git clone https://github.com/violentzone/CarzinomaxERP.git
cd CarzinomaxERP/backend

# Configure — copy the example and fill in your values
cp .env.example .env
#   ADMIN_DB_CONNECTION, ADMIN_EMAIL, ADMIN_PASSWORD, SECRET_KEY
#   optional: PAYCHECK_CALCULATE_TIMESPOT, LLM_TYPE / LLM_MODEL / LLM_KEY / LLM_API_BASE

# Install dependencies
uv sync

# Create the database schema
uv run alembic upgrade head

# Run
uv run uvicorn app.main:app --reload
```

Then open **http://localhost:8000/docs** for the interactive API docs. On first
start the app seeds the admin user from your `.env` and pings the configured
LLM. If the LLM check fails it is logged and the rest of the ERP keeps working.

> **Note:** never commit your real `.env`. `SECRET_KEY` has no default on purpose —
> the app refuses to start with a guessable key so tokens can't be forged.

### 2. Frontend

```bash
cd ../frontend
npm install
npm run dev        # http://localhost:5173
```

The Vite dev server proxies `/api` to `http://localhost:8000`, so no CORS setup
is needed in development. Sign in with the `ADMIN_EMAIL` / `ADMIN_PASSWORD` from
`backend/.env`. For a production build, set `VITE_API_BASE_URL` (see
`frontend/.env.example`) and run `npm run build`.

### 3. Pick an LLM

`LLM_MODEL` uses litellm naming, `<provider>/<model>`:

```ini
# Hosted provider
LLM_TYPE="remote"
LLM_MODEL="anthropic/claude-sonnet-5"      # or openai/gpt-5, gemini/gemini-2.5-pro, ...
LLM_KEY="sk-..."

# Self-hosted (Ollama, vLLM, LM Studio, any OpenAI-compatible server)
LLM_TYPE="local"
LLM_MODEL="ollama/llama3"                  # or openai/<model> for OpenAI-compatible servers
LLM_API_BASE="http://127.0.0.1:11434"
LLM_KEY=""                                 # some local servers want a dummy value
```

## 📁 Project structure

```text
backend/
├── app/
│   ├── main.py            # App entrypoint: startup banner, admin seed, LLM check, scheduler
│   ├── api/
│   │   ├── common/        # get_current_user (JWT) and per-module permission_check
│   │   └── v1/            # Routers: auth, hr, finance, scm, dev_tracking
│   ├── ai_service/        # LlmRouter — litellm wrapper: model_check, chat, stream_chat, parsed_chat
│   ├── core/              # config (pydantic-settings), database, security, scheduler, log_module
│   ├── models/            # SQLAlchemy 2.0 ORM models
│   └── schemas/           # Pydantic request/response schemas
├── migration/             # Alembic environment + versions
└── pyproject.toml

frontend/
└── src/
    ├── api/               # One module per backend router
    ├── components/        # UI kit (ui/), app shell (layout/), generic ResourceSection + SchemaForm
    ├── context/           # AuthContext (JWT + module flags), ToastContext
    ├── lib/               # fetch wrapper, formatters, motion, permissions → nav map, hooks
    └── pages/             # Login, Dashboard, hr/, finance/, scm/, devTracking/, admin/
```

## 🔌 API at a glance

All routes live under `/api/v1` and, except for login, expect an
`Authorization: Bearer <token>` header.

| Router | Endpoints |
|--------|-----------|
| `/auth` | `POST /login`, `POST /logout`, `GET /me` |
| `/hr` | users (employees), departments, attendance, leave requests, paychecks |
| `/finance` | expenses |
| `/scm` | products |
| `/dev_tracking` | projects, investments, downloads |

Lists are `GET /<module>/<thing>_list`; single records are
`/<module>/<thing>/{id}` with `POST` (create), `PUT` (partial update) and
`DELETE`.

## 🗺️ Roadmap

- [x] Auth with per-module access flags and token revocation
- [x] People & Payroll — departments, attendance, leave, paychecks
- [x] Dev Tracking — projects, investments, adoption snapshots
- [x] React frontend
- [x] LLM router with startup health check
- [ ] **AI "receipt → booked" flow** (flagship demo)
- [ ] Finance: amounts, vendors, dates and due-date tracking on expenses
- [ ] Monthly payroll job on the scheduler (`PAYCHECK_CALCULATE_TIMESPOT`)
- [ ] "Chase overdue invoices" — AI-drafted AR reminders
- [ ] Purchases: vendors and purchase orders on top of the product catalog

## 🤝 Contributing

This is an early, build-in-public project — issues, ideas, and PRs are all
welcome. If the vision resonates, the most helpful thing you can do right now is
**⭐ star the repo** and open an issue with what you'd want an AI-run ERP to do.

## 📄 License

Licensed under the **Apache License 2.0** — free to use, modify, and self-host,
including commercially. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
