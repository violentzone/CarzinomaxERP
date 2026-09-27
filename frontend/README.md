# Carzinomax ERP — Frontend

A modern, animated single-page app for the Carzinomax ERP, built to match the
FastAPI backend under `backend/app/api/v1`. React 19 + Vite, with a violet /
electric design system, motion throughout (Framer Motion), and dashboard charts
(Recharts).

The ERP is sized for a small unit and does three things:

1. **Tracks programs in development** — projects, the money invested in each
   (cloud, licences, hardware, consulting) and their adoption (download / star
   snapshots per platform).
2. **Pays individual members** — every user is an employee; paychecks, leave
   and attendance are recorded per user.
3. **Handles the unit's finances** — a typed expense ledger plus an overview
   that rolls payroll, project investments and purchases into one view.

## Stack

- **React 19** + **Vite** (plain JSX)
- **react-router-dom** — routing & the authenticated app shell
- **framer-motion** — page transitions, staggered lists, spring modals, count-ups
- **recharts** — dashboard, finance and download charts
- **lucide-react** — icons
- Native `fetch` wrapper (`src/lib/api.js`) — no axios

## Getting started

```bash
# 1) Start the backend first (from ../backend) so /api is reachable on :8000
#    uv run uvicorn app.main:app --reload

# 2) Frontend
npm install
npm run dev        # http://localhost:5173
```

The Vite dev server proxies `/api` → `http://localhost:8000` (see
`vite.config.js`), so the SPA talks to the API same-origin. For a production
build, set `VITE_API_BASE_URL` (see `.env.example`) and `npm run build`.

Sign in with the admin seeded by the backend on first boot (the `ADMIN_EMAIL` /
`ADMIN_PASSWORD` from `backend/.env`).

## Structure

```
src/
  api/            One module per backend router (auth, hr, finance, scm, devTracking)
  components/
    ui/           Design-system kit: Button, Card, StatCard, Table, Modal, Tabs,
                  Badge, Field, ConfirmDialog, EmptyState, Toast, …
    layout/       AppLayout (shell), Sidebar (permission-gated nav), topbar
    ResourceSection.jsx   Generic list + create / edit / delete section
    SchemaForm.jsx        Schema-driven form + payload builder
    ProtectedRoute.jsx
  context/        AuthContext (JWT + user + module flags), ToastContext
  lib/            api client, formatters, motion variants, permissions→nav map,
                  useList / useUsers hooks, devStats (project traction maths)
  pages/          Login, Dashboard, devTracking/, hr/, finance/, scm/, admin/
  styles/         ui.css (kit), layout.css (shell/login/dashboard)
  index.css       Design tokens (light + dark, manual toggle via [data-theme])
```

## Backend contract

Every module endpoint answers with an envelope:

```json
{ "status": "success", "data": ... }      // 2xx  (data omitted on update/delete)
{ "status": "fail",    "error": "..." }   // 4xx  (403 = no module access)
```

`src/lib/api.js` unwraps the envelope, so API wrappers resolve straight to
`data`. Login is `POST /auth/login?user_email=…&password=…` and returns the
bare JWT; logout is `POST /auth/logout` and revokes every token issued before
now. Lists are `GET /<module>/<thing>_list`; single records are
`/<module>/<thing>/{id}` with POST (create), PUT (partial update) and DELETE.

## Access control

There are no roles. Each user carries four flags — `has_dev_access`,
`has_hr_access`, `has_finance_access`, `has_scm_access` — and each backend
router checks its own flag. The sidebar shows only the modules the signed-in
user holds a flag for; **Users & Access** lives under the HR flag because the
backend manages users through `/hr`. A user with all four flags is, for display
purposes, an administrator.

If an endpoint returns **403**, the page shows an in-page "Restricted area"
panel rather than signing you out. A **401** anywhere (expired or revoked
token) clears the session and returns you to the login screen.

## Module notes

- **Dev Tracking** — projects are keyed by `project_id`. "Downloads" for a
  project is the sum of the *latest* snapshot on each platform, not the sum of
  every row; "stars" is the highest count seen in those snapshots.
- **People & Payroll** — paychecks recompute `net_pay` (base + allowances −
  deductions) on save unless you type a value. Leave approve/reject records
  you as `approved_by_id`. The attendance punch bar clocks a member in with a
  new log at "now", or closes their latest open log and fills `total_hours`.
- **Finance** — the ledger only classifies expenses by type; the Overview tab
  pulls amounts from paychecks, investments and the product catalog, showing
  only what your flags allow.
- **Purchases** — the SCM router is a product catalog (SKU, cost, list price).

## Accessibility & motion

All non-essential animation is disabled under `prefers-reduced-motion`. Light
and dark themes are supported (auto by OS preference, with a manual toggle in
the top bar).
