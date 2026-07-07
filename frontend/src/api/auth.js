/** Auth endpoints: /api/v1/auth */
import { apiGet, apiPost, apiLogin } from '../lib/api'

export const authApi = {
  login: (email, password) => apiLogin(email, password),
  me: () => apiGet('/auth/me'),
  register: (payload) => apiPost('/auth/register', payload),
}
