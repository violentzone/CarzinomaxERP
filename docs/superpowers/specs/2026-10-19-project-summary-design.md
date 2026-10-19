# Design note: Project summary (LLM-written overview of the whole system)

## Context

You want a feature that "creates a summary of the project", where the project is this codebase / the running Carzinomax Dev instance, not a single `DevProject` row. The working tree already holds the seed of it: `backend/app/ai_service/prompts/project_summary.md` (uncommitted, nothing loads it yet) says:

> Summary to give administrator insight of data status, generate about 300 words of summary containing contents below, give items of each topic. `## HR` How many user. `## Finance` …

So the deliverable is an LLM-written, roughly 300-word administrator overview of the data in every module, with a list of items per topic, driven by that prompt file. The numbers behind it must be computed by SQL, never by the model.

What exists today:
* `frontend/src/pages/Dashboard.jsx` is the landing page. It fetches every module's full list and computes KPIs in the browser. No backend endpoint aggregates anything; the only `func.sum` / `group_by` in the backend is `save_project_snapshots` in `app/core/github.py`.
* The LLM is used in two places only: the orchestrator (`app/ai_service/agents.py`) and the startup / `POST /chatbot/` ping (`llm.invoke('ping')`). No `with_structured_output` call exists yet.
* Finance, HR and SCM tables have no link to a dev project; `Finance` has only `expense_type`, `amount` and timestamps; `Product` has no stock or orders. The summary can therefore only describe what the tables hold (see the figures below).

Outcome after this work:
* `GET /api/v1/summary/figures` returns the deterministic numbers for the modules the caller may see (fast, no LLM).
* `POST /api/v1/summary/project` computes the same figures, hands them to the shared `llm` with the `project_summary.md` prompt and returns figures + a structured summary (headline, ~300-word overview, items per topic).
* The Dashboard gets a "Summary" card with a Generate button that calls the second endpoint and renders the result.
* `project_summary.md` is completed and becomes the only prompt of this feature.

No table changes, no new flag, no migration.

---

## Three answers I need from you (a reviewer who read this note as the implementer could not settle them)

1. **Which model is this built and verified against?** `backend/.env` currently sets `LLM_TYPE="remote"` with a DeepSeek model, while the local vLLM Qwen3.5-9B on the RTX 3060 is the other target you use. The note now defaults to `method='function_calling'` for the structured output because it works on both (DeepSeek supports tool calls; the local server already needs a tool parser for the orchestrator). `method='json_schema'` (guided decoding) is the better choice on vLLM only and is a one-word switch. The answer also decides whether the system check spends remote tokens or needs the GPU server up.
2. **Decision 4 below: may this feature call the shared `llm` directly with `with_structured_output`, outside the orchestrator?** `backend/AGENTS.md` reserves that for your approval. The alternative is a tool-less `create_agent(model=llm, system_prompt=SUMMARY_PROMPT, response_format=ProjectSummary)` next to the sub-agents in `agents.py` (langchain 1.4.2 wraps a Pydantic `response_format` in its tool strategy, so it is tool calling either way); it reads the result from `structured_response`, but `create_agent` only accepts a bare `BaseChatModel`, so `timeout` / `max_tokens` cannot be set for that call and the wall-clock bound has to be `asyncio.timeout(120)` around the invoke. I recommend the direct call for that reason.
3. **Decision 1 below: one section per module flag (recommended) or administrator-only (all four flags), as the word "administrator" in your stub suggests?** Admin-only removes the `None` sections and the caller argument from `collect_figures`, drops the "cover only the topics present" prompt rule, gates with all four flags (the frontend already has `isAdmin`), shows the card to administrators only, and changes the verification matrix. It also decides whether an HR-only user may trigger a model call at all.

## Decisions I made (please confirm or overrule)

1. **Gating: one section per module flag, 403 when the caller holds none.** A user with HR + Finance gets those two sections and a summary about them; an administrator (all four flags) gets everything. Alternative: administrator-only (all four flags required), matching the word "administrator" in your stub. I chose per-flag because the Dashboard and the orchestrator already work that way.
2. **Permission check reads the four flags from `current_user`** instead of calling `permission_check()` four times (it re-reads the user each time and logs a warning for every flag the caller lacks). This is a deviation from "permission check first"; the endpoint still begins with the gate, just without the helper. Say if you want the helper called per module anyway.
3. **New router file `app/api/v1/summary.py`, prefix `/summary`.** The feature spans all four modules, so no existing category file fits. No sidebar entry: it lives on the Dashboard. Registered in `api/v1/__init__.py`.
4. **The LLM is called directly through the shared `llm` (`llm.with_structured_output(ProjectSummary)`) in `app/ai_service/summary.py`, not through the orchestrator.** `backend/AGENTS.md` says feature code reaches the model only through the orchestrator and that a completion outside it needs your approval. The orchestrator cannot take a different system prompt per call, so this feature needs that approval. It stays inside LangChain (no `litellm` import, no second client) and uses structured output. Checked in the installed `langchain_litellm`: `ChatLiteLLM.with_structured_output` defaults to `method='json_schema'` (a `response_format` with `strict=True`), which vLLM turns into guided decoding; every field of the output model must therefore be required (no defaults, no `| None`).
5. **No chat tool in this iteration (REST-only, like GitHub repo list / rename / untrack).** The figure helpers are async (`AsyncSession`, same as `app/core/github.py`). Chat tools are sync and run in a worker thread; running an async helper on the global engine from there with `asyncio.run` is confirmed unsafe (asyncpg connections and the pool queue are bound to the loop that created them, and `AGENTS.md` forbids mixing the two sessions in one path). The sub-agents can already answer "how many users" through their `get_*` tools. If you want parity later, the path is to split each helper into a driver-agnostic statement builder (`select()` objects) plus a row-shaping step, so the router runs the statements with `await db.execute` and a tool runs the same statements with `SyncSessionLocal`; one helper, no copies. Not in this iteration.
6. **`GET /summary/figures` exists next to the POST.** It costs nothing, lets the system check verify the numbers without an LLM, and lets the Dashboard show the figures while the model writes. Drop it if you want the smallest surface.
7. **No persistence, no scheduler job.** A summary is generated on demand from a button; nothing is stored. A later version could keep the last summary or run it nightly, both need a table and are out of scope.
8. **Function length.** `hr_figures` runs about 12 queries and will exceed the 30-line guideline from your global CLAUDE.md. `backend/AGENTS.md` prefers one flat function per real step over micro-helpers, so I keep one function per module. Tell me if you would rather split HR into people / attendance / payroll helpers.
9. **Verification model.** The system check runs `POST /summary/project` against whatever `.env` configures (today the remote DeepSeek model, a few thousand tokens per call); `GET /summary/figures` and the 403 / 503 cases need no model. If you want it checked on the local Qwen server instead, the GPU server has to be up and `LLM_TYPE` / `LLM_API_BASE` / `LLM_MODEL` are overridden from the shell like the database variables, `.env` untouched.
10. **No new setting.** The structured-output method is a constant in `app/ai_service/summary.py`, not an environment variable; switching providers is an edit of one word there. Say if you want `LLM_STRUCTURED_OUTPUT` in `settings` and `.env.example` instead.

---

## Coding style: identical to the existing code (binding)

The implementation copies the nearest existing file and follows `backend/AGENTS.md` and the root `AGENT.md` word for word:

* **Reference files:** `app/api/v1/hr.py` (endpoint shape), `app/core/github.py` (core helper with Pydantic result models and `system_log`), `app/ai_service/agents.py` (`load_prompt`, use of the shared `llm`), `frontend/src/pages/Dashboard.jsx` and `frontend/src/pages/devTracking/DevTrackingPage.jsx` (in-file section components, `Card`, `StatCard`, `summary-row` tiles).
* **Routers:** `async def`, `current_user: User = Depends(get_current_user)`, `db = Depends(get_db)`, gate first, `log = user_log(current_user.id)`, `JSONResponse` envelope `{"status": "success", "data": ...}` / `{"status": "fail", "error": "..."}` with `media_type='application/json'`, result assigned to `response` then `return response`.
* **Core helpers:** `AsyncSession` + `select()` + `await db.execute(...)` / `await db.scalar(...)`; `system_log = system_log()` right after the imports if the module logs (the figure helpers do not log; the endpoint does).
* **Structured data is Pydantic** (`BaseModel`), never `@dataclass`. `str | None` typing, no `Optional` in new code, no `Any`, no `TYPE_CHECKING`, no string annotations.
* **Docstrings:** opening `"""` on its own line, summary on the next line, `Args:` directly under it, blank line, `Returns:` (and `Raises:` when the function raises on purpose). Identifiers in single backticks. Comments are one plain line that says why.
* **Quotes:** single quotes for strings, log and error messages; double quotes only for the JSON-like envelope dicts and text containing a single quote.
* **Flat functions:** one function per real step, no `_`-prefixed micro-helpers, no closures, no custom exception classes. `raise ValueError('message')` for bad input or a failed external call; the endpoint's `except Exception` logs `format_exc()` and returns the fail envelope.
* **Long lines are fine:** no wrapping of calls or f-strings to fit a column limit. f-strings only.
* **Config:** anything configurable goes through `app.core.config.settings` and `.env.example`. This feature adds no setting.
* **LLM:** the shared `llm` from `agents.py`, prompt text loaded from `prompts/project_summary.md` with `load_prompt`, system prompt held in its own variable, structured output via `with_structured_output(Pydantic model)`. Never import `litellm`.
* **Logging:** `user_log(current_user.id)` in the endpoint; `format_exc()` on caught exceptions; no `print`.
* **Frontend:** plain JSX, no TypeScript, no Tailwind, no new dependency. One API wrapper file per backend router in `src/api/` built on `src/lib/api.js`. Reuse the `ui/` kit (`Card`, `Button`, `Spinner`, `EmptyState`), tokens from `index.css`, classes from `ui.css` / `layout.css`, both themes, `prefers-reduced-motion` respected (existing `Card` animation only).
* **Line endings:** the working tree is CRLF; every touched file is normalised back to CRLF after editing (the Edit tool writes LF).
* **Docs honesty rule:** README marks the feature as working only once the system check passed; AGENT.md, backend/AGENTS.md and frontend/README.md are updated together.

---

## Backend

### 1. `app/core/summary.py` (new): figures, no LLM

One Pydantic model per module plus the container, and one async helper per module that fills it with `select(func.count(...))` / `func.coalesce(func.sum(...), 0)` / `group_by` statements, the way `save_project_snapshots` in `github.py` does. "Today" is `date.today()` (same source as `with_today` in `agents.py`); "this month" is the calendar month of today.

Facts checked against the installed SQLAlchemy / asyncpg that the implementation must respect:
* `Numeric` columns and their sums come back as `Decimal`: always `func.coalesce(func.sum(...), 0)` and cast with `float(...)` (also `Department.manager_id`, which is a bare `Numeric`, and the nullable `AttendanceLog.total_hours`).
* `Finance.expense_type` is a non-native `Enum`: a grouped `select(Finance.expense_type, func.sum(Finance.amount))` returns the `ExpenseType` member, so the dict key is `row.expense_type.value`.
* `created_at` / `clock_in` are `DateTime(timezone=True)`: build every bound as an aware UTC datetime (`datetime(year, month, 1, tzinfo=timezone.utc)`, `datetime.now(timezone.utc)`); asyncpg silently reads a naive datetime as host-local time and shifts the month boundary.
* Attendance periods filter on `AttendanceLog.date` (a `Date`), not on `clock_in`.
* The HR router accepts any status string, so leave and paycheck counts group by `status` and read the known keys (`pending` / `approved` / `rejected`, `draft` / `paid`); unknown values are simply not counted.
* `module_access` and `admin_count` count active users only (`User.is_active.is_(True)`), because `get_current_user` rejects inactive users; the docstring says so. `user_count` / `active_user_count` give the raw split.

```python
class HrFigures(BaseModel):
    user_count: int                      # count(users)
    active_user_count: int               # is_active
    admin_count: int                     # all four flags true
    module_access: dict[str, int]        # {'finance': n, 'scm': n, 'hr': n, 'dev': n}
    department_count: int
    departments_without_manager: int     # manager_id IS NULL
    clocked_in_today: int                # attendance_logs.date == today
    open_attendance: int                 # clock_out IS NULL
    hours_this_month: float              # sum(total_hours) where date >= first of month
    pending_leave: int                   # status == 'pending'
    oldest_pending_leave_days: int | None  # today - min(created_at) of pending rows
    on_leave_today: int                  # status == 'approved' and start_date <= today <= end_date
    draft_paychecks: int                 # status == 'draft'
    paid_paychecks: int                  # status == 'paid'
    net_pay_this_month: float            # sum(net_pay) where status == 'paid' and payment_date in month
    next_payment_date: date | None       # min(payment_date) where status == 'draft' and payment_date >= today

class FinanceFigures(BaseModel):
    expense_count: int
    total_amount: float
    by_type: dict[str, float]            # all four ExpenseType values, 0.0 when none
    this_month_total: float              # created_at >= first of this month (UTC)
    last_month_total: float
    largest_amount: float | None
    newest_at: datetime | None           # max(created_at)

class ScmFigures(BaseModel):
    product_count: int
    average_unit_price: float | None
    average_cost: float | None
    average_margin: float | None         # avg(unit_price - cost)
    below_cost_count: int                # unit_price < cost
    without_description_count: int

class DevFigures(BaseModel):
    project_count: int
    projects_without_repo: int           # no dev_github_repos row
    investment_total: float
    investment_this_month: float         # dev_investments.date >= first of month
    investment_by_category: dict[str, float]
    tracked_repo_count: int
    repos_with_error: int                # last_error IS NOT NULL
    last_synced_at: datetime | None      # max(last_synced_at)
    total_stars: int                     # coalesce(sum(star_count), 0) over dev_github_repos
    total_downloads: int                 # coalesce(sum(download_count), 0) over dev_github_repos
    snapshot_count: int                  # dev_project_downloads rows
    newest_snapshot_date: date | None

class ProjectFigures(BaseModel):
    today: date
    generated_at: datetime
    hr: HrFigures | None = None          # None = caller has no access to the module
    finance: FinanceFigures | None = None
    scm: ScmFigures | None = None
    dev: DevFigures | None = None
```

Helpers (all `async`, all take `db: AsyncSession`):

* `hr_figures(db, today) -> HrFigures`
* `finance_figures(db, today) -> FinanceFigures`
* `scm_figures(db) -> ScmFigures`
* `dev_figures(db, today) -> DevFigures`
* `collect_figures(db, caller: User) -> ProjectFigures`: reads `caller.has_*_access`, calls the helpers for the flags held, fills the rest with `None`.

Status strings used: leave `pending` / `approved` / `rejected`, paycheck `draft` / `paid` (same literals as `tool_store.py`).

### 2. `app/ai_service/summary.py` (new): the one LLM call

```python
class TopicSummary(BaseModel):
    topic: Literal['HR', 'Finance', 'Purchases', 'Dev Tracking']
    items: list[str]                     # 3 to 6 short facts, numbers taken from the figures

class ProjectSummary(BaseModel):
    headline: str                        # one sentence
    overview: str                        # about 300 words, plain text
    topics: list[TopicSummary]           # one entry per module present in the figures

SUMMARY_PROMPT = load_prompt('project_summary.md')   # system prompt in its own variable

async def write_project_summary(figures: ProjectFigures) -> ProjectSummary:
    """
    Ask the shared model for the administrator summary of `figures`
    Args:
        figures: Numbers of the modules the caller may see, absent modules are None and are left out of the request

    Returns:
        `ProjectSummary` as the model wrote it

    Raises:
        ValueError: the model could not be reached or returned no usable summary
    """
```

Body: `structured_llm = llm.with_structured_output(ProjectSummary, method='function_calling')` is built once at module level next to `SUMMARY_PROMPT` (no network call at import, startup without an LLM is unaffected); the user turn is `<context>today: …</context>` followed by `figures.model_dump_json(exclude_none=True, indent=2)`; the call is `await structured_llm.ainvoke([SystemMessage(SUMMARY_PROMPT), HumanMessage(user_turn)], timeout=120, max_tokens=4000)`; `OutputParserException` (malformed or non-conforming JSON) and any other exception are re-raised as `ValueError` carrying the original message, which the endpoint logs with `format_exc()`.

Checked in the installed packages (langchain 1.4.2, langchain-litellm 0.9.0, litellm 1.91.2):
* `ChatLiteLLM.with_structured_output` overrides the base class; its default is `method='json_schema'` (a `response_format` with `strict=True`), which litellm passes to the server untouched. vLLM turns that into guided decoding, the most reliable path on the local Qwen server; DeepSeek documents only `json_object`, not `json_schema` with `strict`, so on the remote provider the default could fail on every call. `method='function_calling'` (a tool call with `tool_choice='required'`) works on both, hence the default here; one comment line next to it says when to switch to `json_schema`.
* Every `ProjectSummary` / `TopicSummary` field stays required (no defaults, no `| None`) so the `json_schema` switch keeps working (`strict=True` rejects optional fields on OpenAI-style servers).
* `timeout` and `max_tokens` reach `litellm.acompletion` only with `include_raw=False` (the chain is a `RunnableSequence` whose first step is the bound model); with `include_raw=True` the kwargs are dropped and litellm's 600 s default applies. So `include_raw` stays `False` and parse failures surface as exceptions. The shared `llm` has `max_retries=1` (one attempt) and no `max_tokens`. A thinking model counts its reasoning inside `max_tokens`, hence the 4,000 cap rather than a tight one; the JSON itself is about 500 tokens.
* A thinking model served with a reasoning parser puts its thinking in `reasoning_content` (kept in `additional_kwargs`) and the tool call / JSON in the structured part; both parse.
* The compose nginx has `proxy_read_timeout 300s`, so a 120 s call survives the proxy in the Docker stack.

`load_prompt` and `llm` are imported by explicit name from `app.ai_service.agents` (the way `chatbot.py` does it); `app/core/summary.py` never imports `app.ai_service`, so the import graph stays acyclic. Importing `agents` builds the four sub-agents at import time; the router already pays that cost, nothing new.

### 3. `app/ai_service/prompts/project_summary.md` (complete the stub)

Keep the stub's purpose line and the per-topic headings, extend to the four modules and the same sections the other prompts use (`# Role`, `# Context`, `# Rules`, `# Topics`, `# Output`, `# Example`). Key rules:

* Write only from the figures in the request. Never invent a number, a name or a date; when a figure is `null`, say the data is missing.
* Cover only the topics present in the request (absent modules are not mentioned, not even as "no access").
* `overview`: about 300 words, plain prose for an administrator, lead with what needs attention (pending leave, open attendance, repos with sync errors, products below cost, draft paychecks due).
* `topics[].items`: 3 to 6 one-line facts per topic, each carrying its number, e.g. "12 users, 11 active, 2 administrators".
* English, no markdown, no currency symbol, two decimals for amounts.
* The `# Example` block uses placeholders, not data.

### 4. `app/api/v1/summary.py` (new) and registration

```python
summary_router = APIRouter(prefix="/summary", tags=["Summary"])

@summary_router.get("/figures")
async def get_project_figures(current_user: User = Depends(get_current_user), db = Depends(get_db)):
    # gate: any of the four flags, else 403 fail envelope
    # figures = await collect_figures(db, current_user)
    # 200 {"status": "success", "data": figures.model_dump(mode='json')}

@summary_router.post("/project")
async def create_project_summary(current_user: User = Depends(get_current_user), db = Depends(get_db)):
    # same gate, same figures
    # try: summary = await write_project_summary(figures)
    # except Exception: log.error(format_exc()); 503 {"status": "fail", "error": "The assistant model is not available"}
    # 200 {"status": "success", "data": {"figures": ..., "summary": summary.model_dump()}}
```

`api/v1/__init__.py`: import `summary_router`, `api_router.include_router(summary_router)` after `dev_tracking_router`. (That file also imports `chatbot_router` twice, lines 3 and 8; harmless, left alone unless you say otherwise.)

The gate reads the four flags off the already-loaded `current_user` and returns the 403 fail envelope when none is set; `collect_figures` then fills only the sections the caller holds, so an HR-only user never receives finance totals. Nothing in `main.py` or `app/middleware/` (empty) interferes with a router gated this way, and there is no server-side admin concept, only the four flags.

Response examples:

```json
GET /summary/figures  →  {"status": "success", "data": {"today": "2026-10-19", "generated_at": "2026-10-19T08:00:00+00:00",
  "hr": {"user_count": 12, "active_user_count": 11, ...}, "finance": {...}, "scm": null, "dev": {...}}}

POST /summary/project  →  {"status": "success", "data": {"figures": {...same as above...},
  "summary": {"headline": "...", "overview": "...~300 words...",
              "topics": [{"topic": "HR", "items": ["12 users, 11 active, 2 administrators", "3 leave requests pending, oldest 9 days", ...]}, ...]}}}

no flag          →  403 {"status": "fail", "error": "Permission denied"}
model unreachable →  503 {"status": "fail", "error": "The assistant model is not available"}
```

Timing: a local 9B model writes ~450 output tokens from a ~1,200-token request, expect 15 to 40 s on the RTX 3060, and it shares the GPU with the chat. The call carries `timeout=120`; nothing else is serialised.

---

## Frontend

* `frontend/src/api/summary.js`: `export const summaryApi = { figures: () => apiGet('/summary/figures'), project: () => apiPost('/summary/project') }`.
* `frontend/src/pages/Dashboard.jsx`: a `SummarySection` function in the same file (the in-file section pattern of `DevTrackingPage.jsx`), rendered directly under the hero when `modules.length > 0`:
  * idle: `Card` with title "Summary", one line "An AI-written overview of the modules you can see", `Button` "Generate" (lucide `Sparkles`).
  * loading: `Spinner` + "Writing summary…" (same `table-loading` markup as the page's own loader), button disabled.
  * done: headline as the card title, overview as paragraphs, `topics` as a `grid cols-2` of lists with the topic name as label; "Regenerate" button.
  * error: `toast.error(err.detail)` and a muted inline line; the rest of the dashboard is untouched.
  * Not generated on page load (slow, shares the GPU with the chat); the figures endpoint is not called by the Dashboard in this iteration (it keeps its client-side KPIs), so no existing behaviour changes.
* No `roles.js` change, no route, no nav entry.

---

## Docs

* `README.md`: "API at a glance" row `/summary`: `GET /figures`, `POST /project` (LLM-written overview); "What works today" frontend row mentions the summary card; roadmap tick if one matches.
* `AGENT.md`: feature section "9. Project summary" (figures helper, prompt, endpoints, gating), file tree entries for the three new backend files and `api/summary.js`, Known gaps unchanged.
* `backend/AGENTS.md`: tree entries, one line under "Chat orchestrator in six lines" or a new "Project summary in two lines" (figures in `core/summary.py`, model call in `ai_service/summary.py`, REST-only), LLM bullet gets "the project summary calls the shared `llm` directly with structured output (approved)".
* `frontend/README.md`: Module notes bullet "Dashboard: Summary card calls `POST /summary/project` …".

---

## Verification (done = system check passes)

Up front: the check starts a throwaway Postgres container `carzinomax-pg` on port 55432 and removes it afterwards; `.env` is not touched (env vars override it). Port 5432 belongs to another project.

1. `docker run -d --name carzinomax-pg -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=carzinomax -p 55432:5432 postgres:latest`; export `ADMIN_DB_CONNECTION` and `DATABASE_URL` to `postgresql://postgres:postgres@localhost:55432/carzinomax`; `uv run alembic upgrade head`; `uv run uvicorn app.main:app --port 8765` in the background.
2. httpx script (`PYTHONPATH=backend uv run python <script>`): log in as admin (`POST /auth/login?user_email=&password=`, body is the bare JWT), seed a few rows through the existing endpoints (2 users with different flags, a department, an attendance log without clock-out, a pending leave, a draft and a paid paycheck, 3 expenses of 2 types, 2 products one below cost, a project with an investment), then:
   * `GET /summary/figures` as admin: four sections, every number checked against the seeded rows.
   * as the HR-only user: `hr` filled, the other three `null`.
   * as a user with no flags: 403 fail envelope.
   * `POST /summary/project` as admin with the LLM configured: 200, `summary.topics` has one entry per present module, overview non-empty; with `LLM_MODEL` pointed at nothing: 503 fail envelope, figures endpoint still 200.
3. Pressure test: `httpx.AsyncClient` + `asyncio.gather`, 50 concurrent `GET /summary/figures` as admin; threshold p95 < 500 ms on the local container. `POST /summary/project` is excluded (LLM).
4. Frontend: `npm run lint` and `npm run build` in `frontend/`; the Dashboard section rendered through the Vite `ssrLoadModule` harness with a fixture summary (idle, loading, done, error states). Chrome against localhost is not usable on this machine.
5. Remove the container.

---

## Touch points

```text
app/core/summary.py (new)  →  app/ai_service/summary.py (new)  →  app/ai_service/prompts/project_summary.md (complete)
→ app/api/v1/summary.py (new)  →  app/api/v1/__init__.py (register)
→ frontend/src/api/summary.js (new)  →  frontend/src/pages/Dashboard.jsx (SummarySection)
→ README.md, AGENT.md, backend/AGENTS.md, frontend/README.md
```

## Out of scope

Chat tool parity (decision 5), storing or scheduling summaries, per-`DevProject` summaries, Finance / SCM data that the tables do not hold (dates per expense, stock, orders), tests (none exist in the repo; say if you want a `tests/` suite started with this feature).

## Provider check (2026-10-19, DeepSeek thinking mode from .env)

* `function_calling` is rejected: 400 "Thinking mode does not support this tool_choice". `json_schema` is rejected: 400 "This response_format type is unavailable now".
* `json_mode` works, but a 4,000-token cap cut the JSON off because thinking tokens count inside it. Use `method='json_mode'`, spell the JSON object out in the prompt's Output section, cap at about 16,000 tokens or none, allow about three minutes. On the local vLLM server json_mode and json_schema both work, so json_mode is the portable choice.
