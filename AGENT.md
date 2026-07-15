# CLAUDE.md & AGENT.md: Developer & Agent Reference Guide

This document provides system setup commands, build/run instructions, detailed project file structures, and a comprehensive overview of features in CarzinomaxERP.

---

## 🛠️ Main Features in CarzinomaxERP

### 1. Security & RBAC
* Seeded Administrator account creation on startup.
* Route-based role validation (`"admin"`, `"finance"`, `"hr"`, `"scm"`).
* JWT session issuance.

### 2. Finance Module ([models/finance.py](file:///D:/python/server1/carzinomaxERP/backend/app/models/finance.py))
* **General Ledger**: Accounts hierarchy with classification (Asset, Liability, Equity, Revenue, Expense).
* **Double-Entry Transactions**: Balance checks ensuring that every [JournalEntry](file:///D:/python/server1/carzinomaxERP/backend/app/models/finance.py#L20) has equal debits and credits.
* **Invoicing**: Detailed sales/purchase invoices with automated tax rates and payments status hooks.
* **Fixed Assets**: Ledger database representing asset values and purchase codes.
* **Auto-Scheduler**: A monthly background job ([core/scheduler.py](file:///D:/python/server1/carzinomaxERP/backend/app/core/scheduler.py)) configured using `apscheduler` that runs on the **1st day of every month at midnight** to compute salaries for active employees and record them as payments.

### 3. HR Module ([models/hr.py](file:///D:/python/server1/carzinomaxERP/backend/app/models/hr.py))
* **Personnel Directory**: Employee contract tracking (job titles, salaries, active/leave statuses).
* **Attendance System**: Time clock event loggers with worked hours tracking.
* **Time-off Workflow**: Leave requests handling.
* **Payroll**: Automated paycheck computations factoring in base pay, deductions, and allowances.

### 4. Supply Chain Management (SCM) ([models/scm.py](file:///D:/python/server1/carzinomaxERP/backend/app/models/scm.py))
* **Inventory Control**: Multi-warehouse stock tracking, stock movement tracking (ins, outs, transfers), and SKU codes.
* **Procurement**: Vendor directories, purchase orders status management (ordered, received, cancelled), and shipments check-ins.

### 5. Developer Activity tracking ([models/dev_tracking.py](file:///D:/python/server1/carzinomaxERP/backend/app/models/dev_tracking.py))
* Metric collection tracking cloud costs (AWS/GCP), external paychecks for workers, and download metrics across platform package managers (Docker Hub, GitHub, npm).

---

## 📂 File Structure

Below is the directory map of the codebase.

```text
carzinomaxERP/
├── backend/                             # FastAPI Python Backend
│   ├── app/
│   │   ├── api/v1/                      # Route controllers
│   │   │   ├── auth.py                  # User authentication router
│   │   │   ├── dev_tracking.py          # Developer metrics tracking router
│   │   │   ├── finance.py               # General ledger, invoices, payments router
│   │   │   ├── hr.py                    # Personnel, leaves, paychecks router
│   │   │   └── scm.py                   # SCM catalog, POs, warehouses router
│   │   ├── core/                        # Core system services
│   │   │   ├── config.py                # Pydantic system settings
│   │   │   ├── database.py              # Engine setup & get_db dependency
│   │   │   ├── log_module.py            # Loguru log routing helper
│   │   │   ├── scheduler.py             # Monthly salary background scheduler
│   │   │   └── security.py              # JWT token and hashing utilities
│   │   ├── models/                      # SQLAlchemy models
│   │   │   ├── auth.py                  # User/Role model
│   │   │   ├── dev_tracking.py          # Dev metrics models
│   │   │   ├── finance.py               # Accounting models
│   │   │   ├── hr.py                    # Payroll/Personnel models
│   │   │   └── scm.py                   # Inventory/Procurement models
│   │   └── schemas/                     # Pydantic validation schemas
│   ├── migration/                       # Alembic migrations folder
│   ├── pyproject.toml                   # Project UV dependencies configuration
│   └── requirements.txt                 # Synced dependency lockfile
│
├── frontend/                            # React (Vite + Tailwind CSS / Vanilla CSS)
│   ├── src/
│   │   ├── api/                         # Frontend API Axios calls wrappers
│   │   │   ├── auth.js
│   │   │   ├── devTracking.js
│   │   │   ├── finance.js
│   │   │   ├── hr.js
│   │   │   └── scm.js
│   │   ├── components/                  # UI components
│   │   ├── pages/                       # Screen views
│   │   │   ├── finance/                 # Ledger/Invoice/Payments dashboard
│   │   │   ├── hr/                      # Department/Personnel management
│   │   │   ├── scm/                     # Inventory tracking/Purchase Orders
│   │   │   ├── devTracking/             # Server investment charts
│   │   │   ├── Dashboard.jsx            # Main dashboard overview
│   │   │   ├── Login.jsx                # User login screen
│   │   │   └── NotFound.jsx
│   │   ├── App.jsx                      # Client router setup
│   │   └── main.jsx                     # Vite mount point
```

---

## 🚀 Setup & Execution Commands

### Backend (FastAPI)
The backend is powered by FastAPI, Python 3.14+, and PostgreSQL. Dependency management is handled via `uv`.

* **Configuration**: Copy [backend/.env.example](file:///D:/python/server1/carzinomaxERP/backend/.env.example) to `.env` and fill in database credentials and secret keys.
* **Install Dependencies**:
  ```bash
  cd backend
  uv sync
  ```
* **Run Server**:
  ```bash
  uv run uvicorn app.main:app --reload
  ```
* **Database Migrations** (Alembic):
  * Create a new migration revision:
    ```bash
    uv run alembic revision --autogenerate -m "description_of_change"
    ```
  * Apply migrations:
    ```bash
    uv run alembic upgrade head
    ```

### Frontend (React + Vite)
The frontend is built with React, Vite, and CSS.

* **Install Dependencies**:
  ```bash
  cd frontend
  npm install
  ```
* **Run Developer Server**:
  ```bash
  npm run dev
  ```
* **Build Application**:
  ```bash
  npm run build
  ```

---

## 📝 Coding Standards & Conventions

### Python / FastAPI
* Use async database sessions (`AsyncSession`) with SQLAlchemy 2.0 type mapping conventions ([Base](file:///D:/python/server1/carzinomaxERP/backend/app/core/database.py#L23) class).
* Validate payloads using **Pydantic v2** schemas in [backend/app/schemas/](file:///D:/python/server1/carzinomaxERP/backend/app/schemas/).
* Use `system_log()` and `user_log()` from [log_module.py](file:///D:/python/server1/carzinomaxERP/backend/app/core/log_module.py) for all logging. Avoid using standard python `print`.
* Protect route groups using the role checker dependency: `APIRouter(dependencies=[Depends(RoleChecker(["role_name"]))])`.
