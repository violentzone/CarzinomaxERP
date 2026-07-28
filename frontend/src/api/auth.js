/** Auth endpoints: /api/v1/auth */
import { apiGet, apiPost, apiPut, apiLogin } from '../lib/api'

export const authApi = {
  login: (email, password) => apiLogin(email, password),
  me: () => apiGet('/auth/me'),
  register: (payload) => apiPost('/auth/register', payload),
  listUsers: () => apiGet('/auth/users'),
  updateUser: (id, payload) => apiPut(`/auth/users/${id}`, payload),
}
