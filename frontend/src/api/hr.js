/**
 * People & HR endpoints: /api/v1/hr
 *
 * Users double as the employee directory (there is no separate Employee
 * table), so user management also lives here and requires HR access.
 */
import { apiGet, apiPost, apiPut, apiDelete } from '../lib/api'

export const hrApi = {
  // Users / employees
  listUsers: () => apiGet('/hr/user_list'),
  getUser: (id) => apiGet(`/hr/user/${id}`),
  createUser: (payload) => apiPost('/hr/user', payload),
  updateUser: (id, payload) => apiPut(`/hr/user/${id}`, payload),
  deleteUser: (id) => apiDelete(`/hr/user/${id}`),

  // Departments
  listDepartments: () => apiGet('/hr/department_list'),
  createDepartment: (payload) => apiPost('/hr/department', payload),
  updateDepartment: (id, payload) => apiPut(`/hr/department/${id}`, payload),
  deleteDepartment: (id) => apiDelete(`/hr/department/${id}`),

  // Attendance logs
  listAttendance: () => apiGet('/hr/attendance_list'),
  createAttendance: (payload) => apiPost('/hr/attendance', payload),
  updateAttendance: (id, payload) => apiPut(`/hr/attendance/${id}`, payload),
  deleteAttendance: (id) => apiDelete(`/hr/attendance/${id}`),

  // Leave requests
  listLeaves: () => apiGet('/hr/leave_request_list'),
  createLeave: (payload) => apiPost('/hr/leave_request', payload),
  updateLeave: (id, payload) => apiPut(`/hr/leave_request/${id}`, payload),
  deleteLeave: (id) => apiDelete(`/hr/leave_request/${id}`),

  // Paychecks
  listPaychecks: () => apiGet('/hr/paycheck_list'),
  createPaycheck: (payload) => apiPost('/hr/paycheck', payload),
  updatePaycheck: (id, payload) => apiPut(`/hr/paycheck/${id}`, payload),
  deletePaycheck: (id) => apiDelete(`/hr/paycheck/${id}`),
}
