/**
 * Development Tracking endpoints: /api/v1/dev_tracking
 *
 * Note: projects are keyed by `project_id` (not `id`); downloads use `id` and
 * reference a project through `project_id`. Investments are the finance
 * expenses (UUID `id`, `expense_date`) of type `investment` with a `project_id`;
 * they are booked and edited on the Finance page, Dev Tracking only lists them.
 */
import { apiGet, apiPost, apiPut, apiDelete } from '../lib/api'

export const DOWNLOAD_PLATFORMS = ['github', 'dockerhub', 'npm', 'pypi', 'other']

export const devApi = {
  listProjects: () => apiGet('/dev_tracking/project_list'),
  getProject: (id) => apiGet(`/dev_tracking/project/${id}`),
  createProject: (payload) => apiPost('/dev_tracking/project', payload),
  updateProject: (id, payload) => apiPut(`/dev_tracking/project/${id}`, payload),
  deleteProject: (id) => apiDelete(`/dev_tracking/project/${id}`),

  listInvestments: () => apiGet('/dev_tracking/investment_list'),

  listDownloads: () => apiGet('/dev_tracking/download_list'),
  getDownload: (id) => apiGet(`/dev_tracking/download/${id}`),
  createDownload: (payload) => apiPost('/dev_tracking/download', payload),
  updateDownload: (id, payload) => apiPut(`/dev_tracking/download/${id}`, payload),
  deleteDownload: (id) => apiDelete(`/dev_tracking/download/${id}`),

  // Tracked GitHub repos; stars / downloads are filled by the backend (on create and by the scheduled sync), never sent by the client
  listGithubRepos: () => apiGet('/dev_tracking/github_repo_list'),
  createGithubRepo: (payload) => apiPost('/dev_tracking/github_repo', payload),
}
