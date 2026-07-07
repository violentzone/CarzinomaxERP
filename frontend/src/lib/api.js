/**
 * Low-level API client for the Carzinomax ERP backend.
 *
 * Wraps `fetch` with base-URL resolution, JWT bearer injection, JSON handling,
 * the form-encoded login flow, and normalized errors. Every helper throws an
 * {@link ApiError} on non-2xx responses so callers can branch on `status`.
 */

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1'
const TOKEN_KEY = 'carzinomax.token'

/** Error carrying the HTTP status and the FastAPI `detail` message. */
export class ApiError extends Error {
  constructor(status, detail) {
    super(typeof detail === 'string' ? detail : 'Request failed')
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token) {
  if (token) localStorage.setItem(TOKEN_KEY, token)
  else localStorage.removeItem(TOKEN_KEY)
}

/** Pull a human-readable message out of a FastAPI error body. */
function extractDetail(body, fallback) {
  if (!body) return fallback
  const d = body.detail ?? body
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

async function parse(res) {
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
    throw new ApiError(res.status, extractDetail(body, `HTTP ${res.status}`))
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
  }).then(parse)
}

export function apiPost(path, body) {
  return fetch(`${BASE_URL}${path}`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(body),
  }).then(parse)
}

/** OAuth2 password login — the backend expects url-encoded form data. */
export function apiLogin(email, password) {
  const form = new URLSearchParams()
  form.append('username', email)
  form.append('password', password)
  return fetch(`${BASE_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: form.toString(),
  }).then(parse)
}
