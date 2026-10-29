<div align="center">

# Carzinomax DEV

### The open-source ERP where AI does the data entry.

Snap a receipt or upload an invoice — the AI creates the bill, categorizes the
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

Carzinomax DEV flips it: the ERP does the paperwork **for** you. You hand it a
document; the AI does the busywork and asks you to confirm. The goal is an ERP
that a two-person company can actually run without hiring a bookkeeper.

## The flagship: "Receipt → Booked" 🚧

The wedge we're building first. Both halves work today: on the Finance page,
**Book from receipt** uploads a receipt or invoice, the AI reads it into a draft
(vendor, invoice number, total, dates, type, category, project, paid or not) and
the expense form opens prefilled for you to confirm. The same booking works in the
chat by attaching the document and saying "book it". Scheduling the payment works
too: give the bill a planned payment date (form or chat) and the Finance page's
Payments tab lists what is due today, missed or upcoming; the accountant pays
outside the system and marks the bill paid with one click.

```
You:  *uploads a $340 AWS invoice*

AI:   Booked it. Here's what I did:
      • Created expense       INV-AWS-0725  ·  $340.00
      • Categorized to        investment · Cloud (AWS)
      • Linked to project     carzinomax-dev
      • Due date              2026-08-14  → flagged

You:  Schedule the payment for the 12th.

AI:   Done. It is planned for 2026-08-12 and will show on the Payments tab that day.
```

One upload replaces five minutes of manual data entry — and it lands as a
proper record in your books, not a note in a spreadsheet. Today the AI proposes
while you confirm.

## ✅ What works today

The ERP is sized for a small unit and currently does four things: tracks the
software you're building and what it costs, pays the people building it,
classifies the unit's spending, and keeps a product catalog. The AI layer reads
receipts into expense drafts and runs the chat assistant.

| Area | Status | Notes |
|------|--------|-------|
| **Auth & access control** | ✅ Working | JWT login/logout (logout revokes every earlier token), seeded admin, per-module access flags |
| **People & Payroll (HR)** | ✅ Working | Every user is an employee. Departments, attendance clock-in/out with hours, leave requests with approve/reject, paychecks (base + allowances − deductions) |
| **Dev Tracking** | ✅ Working | Projects, money invested per project (the investment expenses booked in Finance against the project, listed read-only), download/star snapshots per platform (GitHub, Docker Hub, npm). GitHub repos linked to a project are synced when added, automatically and on demand (stars + release-asset downloads); the Dev Tracking page lists and adds them under its GitHub repos tab |
| **Finance** | ✅ Working | Expense ledger: type (paycheck / petty cash / investment / other), amount, vendor, invoice number, category, document date, due date, paid date, planned payment date, a derived payment status (paid / unpaid / overdue), optional dev project link and the receipt it was booked from. Unpaid and overdue bills are shown on the ledger and the overview; the Payments tab is the accountant's worklist (due today, missed, upcoming, unplanned) with one-click "Mark paid". An `investment` linked to a project is what Dev Tracking shows as that project's spend. The overview still rolls payroll, project investments and purchases into one view |
| **Purchases (SCM)** | 🚧 Minimal | Product catalog: SKU, cost, list price |
| **React frontend** | ✅ Working | Full SPA: dashboard, all modules, user & access admin, light/dark theme, permission-gated navigation |
| **LLM connection** | ✅ Working | Provider-agnostic via [litellm](https://github.com/BerriAI/litellm) (LangChain `ChatLiteLLM`): hosted APIs or a local server, one shared model client for the chat assistant and the summary mail. Connection is verified at startup |
| **Chat control** | 🚧 Minimal | In-app assistant: every module can be read, created and updated from chat through a LangChain orchestrator with per-module sub-agents; deletes pause for your approval. Approval state is in-memory (lost on restart). A receipt image or PDF attached to a message is read by the assistant (the configured model must accept image input, see "Pick an LLM") and booked as an expense when you ask |
| **AI back office** | 🚧 In progress | The "receipt → booked" flow above: upload → AI draft → confirm works on the Finance page and in the chat, and the bill can be scheduled (planned payment date, Payments tab, chat). The payment itself is still made by hand outside the system |
| **Background scheduler** | ✅ Working | APScheduler starts with the app; the `github_sync` job refreshes tracked GitHub repos on `GITHUB_SYNC_CRON` (default every 6 h); the `expense_status` job re-derives the payment status of open bills on `EXPENSE_STATUS_CRON` (default 00:05 daily) so they turn overdue; the `summary_mail` job asks the LLM for a Markdown status summary of every table and mails it over `SMTP_*` to every user with the "Receive project summary email" toggle on, daily / weekly / monthly at `SUMMARY_SEND_TIME` per `SUMMARY_SEND_FREQ` (no opt-in, no LLM call and no mail). The monthly payroll run is still planned |

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
- **Deploy:** Docker Compose — pgvector-enabled Postgres, the backend, and the built frontend behind nginx, from one file

## 🚀 Quickstart

**Prerequisites:** Docker with Compose v2.23 or newer. Nothing else — Python,
Node and PostgreSQL all live inside the containers.

### 1. Configure

```bash
git clone https://github.com/violentzone/carzinomax-dev.git
cd carzinomax-dev

# App settings and secrets — copy the example and fill in your values
cp backend/.env.example backend/.env
#   ADMIN_EMAIL, ADMIN_PASSWORD, SECRET_KEY
#   SMTP_HOSTNAME / SMTP_PORT / SMTP_USER / SMTP_PASSWORD / MAIL_FROM (outgoing mail, e.g. Gmail with an App Password)
#   SUMMARY_SEND_TIME (hour 0-23) / SUMMARY_SEND_FREQ (day|week|month), plus SUMMARY_SEND_WEEKDAY (0-6, Mon=0) for week or SUMMARY_SEND_MONTHDAY (1-31) for month
#   optional: PAYCHECK_CALCULATE_TIMESPOT, LLM_TYPE / LLM_MODEL / LLM_API_KEY / LLM_API_BASE
#   optional: UPLOAD_DIR, UPLOAD_MAX_BYTES (receipts and chat attachments; default backend/uploads and 10 MB per file)
#   optional: GITHUB_TOKEN (required only for private repos; lifts GitHub's API limit), GITHUB_SYNC_CRON (default every 6 h)
#   ADMIN_DB_CONNECTION can stay as-is — Compose points the backend at the bundled database

# Compose settings — optional: Postgres credentials and host ports
cp .env.example .env
```

> **Note:** never commit your real `.env`. `SECRET_KEY` has no default on purpose —
> the app refuses to start with a guessable key so tokens can't be forged.

### 2. Run

```bash
docker compose up --build
```

Then open **http://localhost:5173** for the app and **http://localhost:8000/docs**
for the interactive API docs. Sign in with the `ADMIN_EMAIL` / `ADMIN_PASSWORD`
from `backend/.env`. On first start the backend creates the schema, seeds the
admin user and pings the configured LLM. If the LLM check fails it is logged
and the rest of the ERP keeps working.

| Service | Image | What it does |
|---------|-------|--------------|
| `db` | `pgvector/pgvector:pg17` | PostgreSQL with the `vector` extension created on first start; data lives in the `pgdata` volume |
| `backend` | built from `backend/` | Runs `alembic upgrade head`, then uvicorn on port 8000 |
| `frontend` | built from `frontend/` | Vite production build served by nginx, which proxies `/api` to the backend so the app is same-origin |

- `backend/.env` is loaded into the backend container as-is, except
  `ADMIN_DB_CONNECTION`, which Compose points at the `db` service for you.
- The root `.env` holds only Compose-level settings: `POSTGRES_USER` /
  `POSTGRES_PASSWORD` / `POSTGRES_DB` and the host ports `DB_PORT`, `BACKEND_PORT`,
  `FRONTEND_PORT` (defaults 5432, 8000, 5173). Every value is optional.
- Postgres credentials are applied when the `pgdata` volume is first created.
  `docker compose down -v` removes the volume — and all data — so the next start
  begins fresh.
- Backend logs are written to `backend/logs/` and uploaded receipts and chat attachments to `backend/uploads/` on the host (layout in "Where uploads go" below).

### 3. Pick an LLM

`LLM_MODEL` uses litellm naming, `<provider>/<model>`:

```ini
# Hosted provider
LLM_TYPE="remote"
LLM_MODEL="anthropic/claude-sonnet-5"      # or openai/gpt-5, gemini/gemini-2.5-pro, ...
LLM_API_KEY="sk-..."

# Self-hosted (Ollama, vLLM, LM Studio, any OpenAI-compatible server)
LLM_TYPE="local"
LLM_MODEL="ollama/llama3.2-vision"         # or openai/<model> for OpenAI-compatible servers
LLM_API_BASE="http://host.docker.internal:11434"   # a server on the host machine; 127.0.0.1 would be the container itself
LLM_API_KEY=""                             # some local servers want a dummy value
```

**The model must accept image input (vision).** Receipts attached in the chat are
sent to it as images and there is no text-only fallback, so pick a vision model on
self-hosted servers too (`llama3.2-vision`, not a text-only `llama3`). PDFs are sent
as extracted text and work with any model.

`host.docker.internal` resolves to the host machine on Docker Desktop (Windows,
macOS). On Linux, add `extra_hosts: ["host.docker.internal:host-gateway"]` to the
`backend` service in `docker-compose.yml`.

### 4. Where uploads go

Receipts booked from the Finance page and files attached in the chat land in the
same place, `UPLOAD_DIR` (default `backend/uploads/`), laid out as:

```text
uploads/<user_id>/<attachment_uuid>.<ext>
```

- `<user_id>` is the user who uploaded the file. The folder proves ownership:
  only a file from your own folder can be linked when you create an expense.
- `<attachment_uuid>` is a random id made at upload time. It is **not** the
  expense id — the file exists before the expense does (upload → AI draft → you
  confirm → the expense row is created).
- `<ext>` is `jpg` for every image (PNG and WebP are re-encoded as JPEG, EXIF
  rotation applied, downscaled to about 1 MP) or `pdf`.

An expense points at its document through the `receipt_path` column, which
stores that relative path (`1/c25445de-….jpg`); `GET /finance/expense/{id}/receipt`
serves it back and the ledger shows it. Two gaps to know about: a receipt that
was read but never booked stays on disk with nothing pointing at it, and
deleting an expense does not delete its file. There is no cleanup job yet.

## 📁 Project structure

```text
docker-compose.yml         # Full stack: pgvector Postgres, backend, frontend (nginx) — see Quickstart
.env.example               # Compose-level settings: Postgres credentials, host ports

backend/
├── app/
│   ├── main.py            # App entrypoint: startup banner, admin seed, LLM check, scheduler
│   ├── api/
│   │   ├── common/        # get_current_user (JWT) and per-module permission_check
│   │   └── v1/            # Routers: auth, hr, finance, scm, dev_tracking, chatbot
│   ├── ai_service/        # ChatLiteLLM model, chat orchestrator + sub-agents, tool_store (one tool per CRUD op), prompts/
│   ├── core/              # config (pydantic-settings), database, security, scheduler, log_module, github (stars/downloads sync)
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
| `/finance` | expenses; `POST /receipt` uploads a receipt or invoice (PNG / JPEG / WebP / PDF, 10 MB) and answers with an AI-read expense draft plus the stored `receipt_path`, nothing is booked until `POST /expense`; `GET /expense/{id}/receipt` serves the stored file back |
| `/scm` | products |
| `/dev_tracking` | projects, investments, downloads, github_repo (tracked repos); `POST /github_sync[/{repo_id}]` refreshes stars + downloads now |
| `/chatbot` | `POST /chatbox` — streams the assistant's reply; answers `interrupt` events with `decision`. `POST /upload` — stores one attachment (PNG / JPEG / WebP / PDF, 10 MB) whose `id` goes into `chatbox` `attachments` |

Lists are `GET /<module>/<thing>_list`; single records are
`/<module>/<thing>/{id}` with `POST` (create), `PUT` (partial update) and
`DELETE`.

## 🗺️ Roadmap

- [x] Auth with per-module access flags and token revocation
- [x] People & Payroll — departments, attendance, leave, paychecks
- [x] Dev Tracking — projects, investments, adoption snapshots
- [x] GitHub stars / release-download sync on the scheduler, with a manual refresh endpoint
- [x] React frontend
- [x] Provider-agnostic LLM connection with startup health check
- [x] Chat control of every module (read / create / update, approval-gated delete)
- [x] Chat attachments: a receipt image or PDF attached in the chat is read by the assistant
- [x] Finance: amounts, vendors, invoice numbers, categories, document / due / paid dates, project link
- [x] **AI "receipt → booked" flow**: upload a receipt, confirm the AI draft, booked (Finance page and chat)
- [x] Scheduling the payment of a booked expense (planned payment date + Payments tab; paying stays manual)
- [ ] Monthly payroll job on the scheduler (`PAYCHECK_CALCULATE_TIMESPOT`)
- [x] Scheduled project summary email (`summary_mail` job on `SUMMARY_SEND_*`, LLM-written, sent to users who opted in)
- [ ] "Chase overdue invoices" — AI-drafted AR reminders
- [ ] Purchases: vendors and purchase orders on top of the product catalog

## 🤝 Contributing

This is an early, build-in-public project — issues, ideas, and PRs are all
welcome. If the vision resonates, the most helpful thing you can do right now is
**⭐ star the repo** and open an issue with what you'd want an AI-run ERP to do.

<details>
<summary><b>Local development without Docker</b> — hot reload, tests and a debugger</summary>

**Prerequisites:** Python 3.14+, [uv](https://github.com/astral-sh/uv), Node 20+,
and a PostgreSQL to point at. The compose database works fine for this:
`docker compose up db` exposes it on `localhost:5432`.

**Backend**

```bash
cd backend
cp .env.example .env
#   Same variables as the Docker setup, but ADMIN_DB_CONNECTION must now be reachable
#   from the host, e.g. postgresql://carzinomax:carzinomax@localhost:5432/carzinomax
#   for the compose database (match the POSTGRES_* values in your root .env).

uv sync                       # install dependencies
uv run alembic upgrade head   # create the schema
uv run uvicorn app.main:app --reload
```

API docs at **http://localhost:8000/docs**. First start seeds the admin user and
pings the LLM, exactly as in Docker.

**Frontend**

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173
```

The Vite dev server proxies `/api` to `http://localhost:8000`, so no CORS setup
is needed. For a production build outside Docker, set `VITE_API_BASE_URL` (see
`frontend/.env.example`) and run `npm run build`.

</details>

## 📄 License

Licensed under the **Apache License 2.0** — free to use, modify, and self-host,
including commercially. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
