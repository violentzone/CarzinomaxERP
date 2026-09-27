/**
 * Low-level API client for the Carzinomax ERP backend.
 *
 * The backend speaks a small envelope protocol:
 *   - success  → `{ "status": "success", "data": ... }` (data omitted on update/delete)
 *   - failure  → `{ "status": "fail", "error": "message" }` with a 4xx status
 *   - auth     → FastAPI `HTTPException` bodies: `{ "detail": "message" }`
 *   - login    → the raw JWT string as the response body
 *
 * Every helper here unwraps the envelope (so callers receive `data` directly)
 * and throws an {@link ApiError} on non-2xx responses so callers can branch on
 * `status`. A 401 anywhere (other than login) means the session is gone; we
 * broadcast it so the auth context can sign the user out.
 */

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1'
const TOKEN_KEY = 'carzinomax.token'

/** Fired on `window` when the API rejects our token. */
export const UNAUTHORIZED_EVENT = 'carzinomax:unauthorized'

/** Error carrying the HTTP status and the backend's message. */
export class ApiError extends Error {
  constructor(status, detail) {
    super(typeof detail === 'string' ? detail : 'Request failed')
    this.name = 'ApiError'
    this.status = status
    this.detail = typeof detail === 'string' ? detail : 'Request failed'
  }
}

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token) {
  if (token) localStorage.setItem(TOKEN_KEY, token)
  else localStorage.removeItem(TOKEN_KEY)
}

/** Pull a human-readable message out of an error body (envelope or FastAPI). */
function extractDetail(body, fallback) {
  if (!body) return fallback
  if (typeof body === 'string') return body
  const d = body.error ?? body.detail ?? null
  if (typeof d === 'string') return d
  // Pydantic validation errors arrive as a list of {loc, msg, ...}
  if (Array.isArray(d)) {
    return d
      .map((e) => {
        const field = Array.isArray(e.loc) ? e.loc[e.loc.length - 1] : e.loc
        return field ? `${field}: ${e.msg}` : e.msg
      })
      .join(' · ')
  }
  return fallback
}

async function parse(res, { notifyUnauthorized = true } = {}) {
  const text = await res.text()
  let body = null
  if (text) {
    try {
      body = JSON.parse(text)
    } catch {
      body = text
    }
  }
  if (!res.ok) {
    if (res.status === 401 && notifyUnauthorized) {
      window.dispatchEvent(new CustomEvent(UNAUTHORIZED_EVENT))
    }
    throw new ApiError(res.status, extractDetail(body, `HTTP ${res.status}`))
  }
  // Unwrap the success envelope. Updates/deletes come back as `{status}` only,
  // in which case the caller gets the envelope itself (truthy, nothing useful).
  if (body && typeof body === 'object' && !Array.isArray(body) && body.status === 'success') {
    return 'data' in body ? body.data : body
  }
  return body
}

function authHeaders(extra = {}) {
  const token = getToken()
  return token ? { Authorization: `Bearer ${token}`, ...extra } : { ...extra }
}

/** Build a query string from a params object, skipping null/undefined/''. */
export function qs(params = {}) {
  const usp = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== '') usp.append(k, v)
  }
  const s = usp.toString()
  return s ? `?${s}` : ''
}

export function apiGet(path, params) {
  return fetch(`${BASE_URL}${path}${qs(params)}`, {
    headers: authHeaders(),
  }).then((r) => parse(r))
}

export function apiPost(path, body) {
  return fetch(`${BASE_URL}${path}`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: body === undefined ? undefined : JSON.stringify(body),
  }).then((r) => parse(r))
}

export function apiPut(path, body) {
  return fetch(`${BASE_URL}${path}`, {
    method: 'PUT',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(body),
  }).then((r) => parse(r))
}

export function apiDelete(path) {
  return fetch(`${BASE_URL}${path}`, {
    method: 'DELETE',
    headers: authHeaders(),
  }).then((r) => parse(r))
}

/**
 * Login — the backend takes `user_email` / `password` as query parameters and
 * answers with the bare JWT string. Resolves to the token.
 */
export async function apiLogin(email, password) {
  const res = await fetch(`${BASE_URL}/auth/login${qs({ user_email: email, password })}`, {
    method: 'POST',
  })
  const token = await parse(res, { notifyUnauthorized: false })
  if (typeof token !== 'string' || !token) {
    throw new ApiError(500, 'Login did not return a token')
  }
  // Defensive: strip quotes in case the server ever JSON-encodes the string.
  return token.replace(/^"|"$/g, '')
}
