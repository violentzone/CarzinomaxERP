import { useState } from 'react'
import { Building2, CalendarDays, Clock, Users, Wallet } from 'lucide-react'
import PageHeader from '../../components/ui/PageHeader'
import Tabs from '../../components/ui/Tabs'
import ResourceSection from '../../components/ResourceSection'
import { hrApi } from '../../api/hr'
import EmployeesSection from './EmployeesSection'
import AttendanceSection from './AttendanceSection'
import LeavesSection from './LeavesSection'
import PaychecksSection from './PaychecksSection'

const TABS = [
  { key: 'departments', label: 'Departments', icon: Building2 },
  { key: 'employees', label: 'Employees', icon: Users },
  { key: 'attendance', label: 'Attendance', icon: Clock },
  { key: 'leaves', label: 'Leaves', icon: CalendarDays },
  { key: 'paychecks', label: 'Paychecks', icon: Wallet },
]

/** People & HR module: departments, employees, attendance, leave and payroll. */
export default function HrPage() {
  const [tab, setTab] = useState('departments')

  return (
    <div className="module-page">
      <PageHeader
        title="People & HR"
        subtitle="Teams, employees, attendance, leave and payroll."
        icon={Users}
      />
      <Tabs tabs={TABS} active={tab} onChange={setTab} idBase="hr" />

      <div className="tab-panel">
        {tab === 'departments' && (
          <ResourceSection
            title="Departments"
            subtitle="Organise employees into teams and cost centres."
            moduleName="People & HR"
            fetcher={() => hrApi.listDepartments()}
            create={hrApi.createDepartment}
            createLabel="New department"
            createTitle="New department"
            update={(row, payload) => hrApi.updateDepartment(row.id, payload)}
            updateTitle="Edit department"
            remove={(row) => hrApi.deleteDepartment(row.id)}
            removeLabel="department"
            removeHint="Employees in this department will be unassigned, not deleted."
            emptyHint="Create your first department to group employees."
            columns={[
              { key: 'code', header: 'Code', render: (r) => <span className="mono cell-strong">{r.code}</span> },
              { key: 'name', header: 'Name', render: (r) => <span className="cell-strong">{r.name}</span> },
              { key: 'manager_id', header: 'Manager', render: (r) => (r.manager_id ?? '—') },
            ]}
            fields={[
              { key: 'code', label: 'Department code', required: true, placeholder: 'ENG' },
              { key: 'name', label: 'Name', required: true, placeholder: 'Engineering' },
              { key: 'manager_id', label: 'Manager ID', type: 'number', min: 0, nullable: true, hint: 'Employee ID of the department manager.' },
            ]}
          />
        )}

        {tab === 'employees' && <EmployeesSection />}
        {tab === 'attendance' && <AttendanceSection />}
        {tab === 'leaves' && <LeavesSection />}
        {tab === 'paychecks' && <PaychecksSection />}
      </div>
    </div>
  )
}
