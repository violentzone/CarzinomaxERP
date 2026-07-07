<div align="center">

# CarzinomaxERP

### The open-source ERP where AI does the data entry.

Snap a receipt or forward an invoice — the AI creates the bill, categorizes the
expense, posts it to your ledger, and schedules the payment. Self-hostable, and
built for founders who'd rather build than bookkeep.

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python 3.14+](https://img.shields.io/badge/python-3.14+-3776AB.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![Status: pre-alpha](https://img.shields.io/badge/status-pre--alpha-orange.svg)](#-project-status)
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
      • Created vendor bill  INV-AWS-0725  ·  $340.00
      • Categorized to       6820 · Cloud Infrastructure
      • Posted journal entry (Dr Cloud Infra / Cr Accounts Payable) ✓ balanced
      • Due date            2026-08-14  → flagged
      Want me to schedule the payment for the 12th?
```

One forwarded email replaces five minutes of manual data entry — and it lands as
a proper double-entry transaction in your books, not a note in a spreadsheet.

## ✅ What works today

The accounting engine underneath the AI is real and running:

| Area | Status | Notes |
|------|--------|-------|
| **Auth & RBAC** | ✅ Working | JWT login, role-based route protection, seeded admin |
| **General Ledger** | ✅ Working | GL accounts + double-entry journal (debits must equal credits) |
| **Invoicing (AR/AP)** | ✅ Working | Customer/vendor invoices with line items + tax calculation |
| **Payments** | ✅ Working | Record payments; invoice status auto-updates (paid / partial) |
| **Fixed Assets** | ✅ Working | Asset registry (depreciation on the roadmap) |
| **SCM / HR / Dev-tracking** | 🚧 Scaffolded | Models + endpoints exist, being fleshed out |
| **AI back office** | 🔜 In progress | The "receipt → booked" flow above — the whole point |
| **React frontend** | 🔜 Planned | API-first today; UI is next |

## 🧱 Tech stack

- **Backend:** FastAPI (async), Python 3.14
- **Database:** PostgreSQL via SQLAlchemy 2.0 (async / asyncpg), migrations with Alembic
- **Auth:** JWT (PyJWT) + bcrypt, role-based access control
- **AI:** pluggable LLM layer — a hosted API for easy start, or self-host your own with vLLM
- **Frontend:** React *(planned)*
- **Tooling:** [uv](https://github.com/astral-sh/uv) for dependency management, loguru for logging

## 🚀 Quickstart

**Prerequisites:** Python 3.14+, PostgreSQL, and [uv](https://github.com/astral-sh/uv).

```bash
# 1. Clone
git clone https://github.com/violentzone/CarzinomaxERP.git
cd CarzinomaxERP/backend

# 2. Configure — copy the example and fill in your values
cp .env.example .env
#   set SECRET_KEY, ADMIN_EMAIL, ADMIN_PASSWORD, DATABASE_URL

# 3. Install dependencies
uv sync

# 4. Run
uv run uvicorn app.main:app --reload
```

Then open **http://localhost:8000/docs** for the interactive API docs. The app
creates its tables and seeds the admin user (from your `.env`) on first start.

> **Note:** never commit your real `.env`. `SECRET_KEY` has no default on purpose —
> the app refuses to start with a guessable key so tokens can't be forged.

## 📁 Project structure

```text
backend/app
├── main.py            # App entrypoint, startup/seed, health checks
├── api/v1             # Routers: auth, finance, scm, hr, dev_tracking
├── core               # config, database, security (JWT/hashing)
├── models             # SQLAlchemy ORM models
└── schemas            # Pydantic request/response schemas
```

## 🗺️ Roadmap

- [x] Accounting core — GL, invoicing, payments, double-entry journal
- [ ] **AI "receipt → booked" flow** (flagship demo)
- [ ] "Chase overdue invoices" — AI-drafted AR reminders
- [ ] React frontend
- [ ] Depreciation schedules for fixed assets
- [ ] Flesh out SCM (inventory, procurement) & HR (payroll, attendance)

## 🤝 Contributing

This is an early, build-in-public project — issues, ideas, and PRs are all
welcome. If the vision resonates, the most helpful thing you can do right now is
**⭐ star the repo** and open an issue with what you'd want an AI-run ERP to do.

## 📄 License

Licensed under the **Apache License 2.0** — free to use, modify, and self-host,
including commercially. See [LICENSE](LICENSE).
