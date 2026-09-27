/**
 * Development Tracking endpoints: /api/v1/dev_tracking
 *
 * Note: projects are keyed by `project_id` (not `id`); investments and
 * downloads use `id` and reference a project through `project_id`.
 */
import { apiGet, apiPost, apiPut, apiDelete } from '../lib/api'

export const INVESTMENT_CATEGORIES = ['cloud', 'software_licenses', 'hardware', 'consulting', 'other']
export const DOWNLOAD_PLATFORMS = ['github', 'dockerhub', 'npm', 'pypi', 'other']

export const devApi = {
  listProjects: () => apiGet('/dev_tracking/project_list'),
  getProject: (id) => apiGet(`/dev_tracking/project/${id}`),
  createProject: (payload) => apiPost('/dev_tracking/project', payload),
  updateProject: (id, payload) => apiPut(`/dev_tracking/project/${id}`, payload),
  deleteProject: (id) => apiDelete(`/dev_tracking/project/${id}`),

  listInvestments: () => apiGet('/dev_tracking/investment_list'),
  getInvestment: (id) => apiGet(`/dev_tracking/investment/${id}`),
  createInvestment: (payload) => apiPost('/dev_tracking/investment', payload),
  updateInvestment: (id, payload) => apiPut(`/dev_tracking/investment/${id}`, payload),
  deleteInvestment: (id) => apiDelete(`/dev_tracking/investment/${id}`),

  listDownloads: () => apiGet('/dev_tracking/download_list'),
  getDownload: (id) => apiGet(`/dev_tracking/download/${id}`),
  createDownload: (payload) => apiPost('/dev_tracking/download', payload),
  updateDownload: (id, payload) => apiPut(`/dev_tracking/download/${id}`, payload),
  deleteDownload: (id) => apiDelete(`/dev_tracking/download/${id}`),
}
