/** Human Resources endpoints: /api/v1/hr */
import { apiGet, apiPost } from '../lib/api'

export const hrApi = {
  listDepartments: () => apiGet('/hr/departments'),
  createDepartment: (payload) => apiPost('/hr/departments', payload),

  listEmployees: (params) => apiGet('/hr/employees', params),
  createEmployee: (payload) => apiPost('/hr/employees', payload),

  clockIn: (employeeId) => apiPost(`/hr/attendance/clock-in?employee_id=${employeeId}`),
  clockOut: (employeeId) => apiPost(`/hr/attendance/clock-out?employee_id=${employeeId}`),

  createLeave: (payload) => apiPost('/hr/leaves', payload),
  createPaycheck: (payload) => apiPost('/hr/paychecks', payload),
}
