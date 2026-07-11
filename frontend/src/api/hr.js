/** Human Resources endpoints: /api/v1/hr */
import { apiGet, apiPost, apiPut, apiDelete } from '../lib/api'

export const hrApi = {
  listDepartments: () => apiGet('/hr/departments'),
  createDepartment: (payload) => apiPost('/hr/departments', payload),
  updateDepartment: (id, payload) => apiPut(`/hr/departments/${id}`, payload),
  deleteDepartment: (id) => apiDelete(`/hr/departments/${id}`),

  listEmployees: (params) => apiGet('/hr/employees', params),
  createEmployee: (payload) => apiPost('/hr/employees', payload),
  updateEmployee: (id, payload) => apiPut(`/hr/employees/${id}`, payload),
  deleteEmployee: (id) => apiDelete(`/hr/employees/${id}`),

  clockIn: (employeeId) => apiPost(`/hr/attendance/clock-in?employee_id=${employeeId}`),
  clockOut: (employeeId) => apiPost(`/hr/attendance/clock-out?employee_id=${employeeId}`),
  updateAttendance: (id, payload) => apiPut(`/hr/attendance/${id}`, payload),
  deleteAttendance: (id) => apiDelete(`/hr/attendance/${id}`),

  createLeave: (payload) => apiPost('/hr/leaves', payload),
  updateLeave: (id, payload) => apiPut(`/hr/leaves/${id}`, payload),
  deleteLeave: (id) => apiDelete(`/hr/leaves/${id}`),
  createPaycheck: (payload) => apiPost('/hr/paychecks', payload),
  updatePaycheck: (id, payload) => apiPut(`/hr/paychecks/${id}`, payload),
  deletePaycheck: (id) => apiDelete(`/hr/paychecks/${id}`),
}
