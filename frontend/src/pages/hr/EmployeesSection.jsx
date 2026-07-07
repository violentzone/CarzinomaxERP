import { hrApi } from '../../api/hr'
import { useList } from '../../lib/useList'
import { currency, today } from '../../lib/format'
import Badge from '../../components/ui/Badge'
import ResourceSection from '../../components/ResourceSection'

const STATUS_OPTIONS = [
  { value: 'active', label: 'Active' },
  { value: 'on_leave', label: 'On leave' },
  { value: 'terminated', label: 'Terminated' },
]

/**
 * Employees list + create. Wraps <ResourceSection> so the department_id <select>
 * and the "Department" column can resolve against the live departments list.
 */
export default function EmployeesSection() {
  const { rows: departments } = useList(() => hrApi.listDepartments())

  const deptOptions = (departments || []).map((d) => ({ value: String(d.id), label: d.name }))
  const deptMap = Object.fromEntries((departments || []).map((d) => [String(d.id), d.name]))

  const fields = [
    { key: 'first_name', label: 'First name', required: true, placeholder: 'Ada' },
    { key: 'last_name', label: 'Last name', required: true, placeholder: 'Lovelace' },
    { key: 'email', label: 'Email', type: 'email', required: true, placeholder: 'ada@company.com' },
    { key: 'phone', label: 'Phone', placeholder: '+1 555 0100' },
    { key: 'hire_date', label: 'Hire date', type: 'date', required: true, default: today() },
    { key: 'job_title', label: 'Job title', required: true, placeholder: 'Software Engineer' },
    { key: 'salary', label: 'Salary', type: 'number', step: '0.01', min: 0 },
    {
      key: 'department_id',
      label: 'Department',
      type: 'select',
      options: deptOptions,
      placeholder: deptOptions.length ? 'Select department…' : 'Create a department first',
    },
    { key: 'status', label: 'Status', type: 'select', default: 'active', options: STATUS_OPTIONS },
  ]

  return (
    <ResourceSection
      title="Employees"
      subtitle="Everyone on the team and their employment details."
      moduleName="People & HR"
      fetcher={() => hrApi.listEmployees()}
      create={hrApi.createEmployee}
      createLabel="New employee"
      createTitle="New employee"
      emptyHint="Add your first team member to get started."
      columns={[
        {
          key: 'name',
          header: 'Name',
          render: (r) => <span className="cell-strong">{`${r.first_name} ${r.last_name}`}</span>,
        },
        { key: 'email', header: 'Email', render: (r) => <span className="muted">{r.email}</span> },
        { key: 'job_title', header: 'Job title' },
        { key: 'department', header: 'Department', render: (r) => (deptMap[String(r.department_id)] || '—') },
        { key: 'salary', header: 'Salary', align: 'right', render: (r) => <span className="cell-num">{currency(r.salary)}</span> },
        { key: 'status', header: 'Status', render: (r) => <Badge status={r.status} /> },
      ]}
      fields={fields}
    />
  )
}
