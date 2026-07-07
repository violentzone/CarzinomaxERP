/** Development Tracking endpoints: /api/v1/dev-tracking */
import { apiGet, apiPost } from '../lib/api'

export const devApi = {
  listInvestments: (params) => apiGet('/dev-tracking/investments', params),
  createInvestment: (payload) => apiPost('/dev-tracking/investments', payload),

  listWorkerPaychecks: (params) => apiGet('/dev-tracking/worker-paychecks', params),
  createWorkerPaycheck: (payload) => apiPost('/dev-tracking/worker-paychecks', payload),

  listDownloads: (params) => apiGet('/dev-tracking/downloads', params),
  createDownload: (payload) => apiPost('/dev-tracking/downloads', payload),
}
