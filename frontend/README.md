# Carzinomax ERP — Frontend

A modern, animated single-page app for the Carzinomax ERP, built to match the
FastAPI backend under `backend/app/api/v1`. React 19 + Vite, with a violet /
electric design system, motion throughout (Framer Motion), and dashboard charts
(Recharts).

## Stack

- **React 19** + **Vite** (plain JSX)
- **react-router-dom** — routing & the authenticated app shell
- **framer-motion** — page transitions, staggered lists, spring modals, count-ups
- **recharts** — dashboard & downloads charts
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
  api/            One module per backend router (auth, finance, scm, hr, devTracking)
  components/
    ui/           Design-system kit: Button, Card, StatCard, Table, Modal, Tabs,
                  Badge, Field, LineItemsEditor, SessionList, Toast, …
    layout/       AppLayout (shell), Sidebar (role-gated nav), topbar
    ResourceSection.jsx / SchemaForm.jsx   Generic list+create + schema forms
    ProtectedRoute.jsx
  context/        AuthContext (JWT + user + role), ToastContext
  lib/            api client, formatters, motion variants, role→nav map, hooks
  pages/          Login, Dashboard, finance/, scm/, hr/, devTracking/, admin/
  styles/         ui.css (kit), layout.css (shell/login/dashboard)
  index.css       Design tokens (light + dark, manual toggle via [data-theme])
```

## Role-based access

The backend gates each router by role (`admin` sees everything; `finance`,
`scm`, `hr`, `developer` each see their module). The sidebar shows only the
modules the signed-in user may use. If an endpoint returns **403** for the
current role, the page shows an in-page "Restricted area" panel rather than
logging the user out — only a bad/expired token (a 403 from `/auth/me`) signs
you out.

## Notes on POST-only resources

Several backend resources are create-only (no list endpoint): payments, journal
entries, leaves, paychecks, shipments, purchase orders. Their screens show a
create form plus a **"created this session"** list built from the API response —
this list is not persisted and clears on refresh.

## Accessibility & motion

All non-essential animation is disabled under `prefers-reduced-motion`. Light
and dark themes are supported (auto by OS preference, with a manual toggle in
the top bar).
