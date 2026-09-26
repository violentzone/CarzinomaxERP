/** Auth endpoints: /api/v1/auth */
import { apiGet, apiPost, apiLogin } from '../lib/api'

export const authApi = {
  /** Resolves to the JWT string. */
  login: (email, password) => apiLogin(email, password),
  /** Revokes every token issued before now (204, no body). */
  logout: () => apiPost('/auth/logout'),
  /** The signed-in user record. */
  me: () => apiGet('/auth/me'),
}
