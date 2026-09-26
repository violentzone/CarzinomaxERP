import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Building2, CalendarDays, Clock, Users, Wallet, ShieldCheck } from 'lucide-react'
import PageHeader from '../../components/ui/PageHeader'
import Tabs from '../../components/ui/Tabs'
import Button from '../../components/ui/Button'
import ResourceSection from '../../components/ResourceSection'
import { hrApi } from '../../api/hr'
import { useUsers } from '../../lib/useUsers'
import PaychecksSection from './PaychecksSection'
import LeavesSection from './LeavesSection'
import AttendanceSection from './AttendanceSection'

const TABS = [
  { key: 'paychecks', label: 'Paychecks', icon: Wallet },
  { key: 'leaves', label: 'Leave', icon: CalendarDays },
  { key: 'attendance', label: 'Attendance', icon: Clock },
  { key: 'departments', label: 'Departments', icon: Building2 },
]

/** People & Payroll: pay every member, track leave and attendance, group into departments. */
export default function HrPage() {
  const [tab, setTab] = useState('paychecks')

  return (
    <div className="module-page">
      <PageHeader
        title="People & Payroll"
        subtitle="Pay each member, approve leave, log attendance and organise departments."
        icon={Users}
        actions={
          <Link to="/admin/users">
            <Button variant="outline" icon={ShieldCheck}>
              Manage users
            </Button>
          </Link>
        }
      />
      <Tabs tabs={TABS} active={tab} onChange={setTab} idBase="hr" />

      <div className="tab-panel">
        {tab === 'paychecks' && <PaychecksSection />}
        {tab === 'leaves' && <LeavesSection />}
        {tab === 'attendance' && <AttendanceSection />}
        {tab === 'departments' && <DepartmentsSection />}
      </div>
    </div>
  )
}

function DepartmentsSection() {
  const { userOptions, nameOf } = useUsers()

  return (
    <ResourceSection
      title="Departments"
      subtitle="Teams and cost centres, each with an optional manager."
      moduleName="People & Payroll"
      fetcher={() => hrApi.listDepartments()}
      create={hrApi.createDepartment}
      createLabel="New department"
      createTitle="New department"
      update={(row, payload) => hrApi.updateDepartment(row.id, payload)}
      updateTitle="Edit department"
      remove={(row) => hrApi.deleteDepartment(row.id)}
      removeLabel="department"
      emptyHint="Create your first department to group the team."
      emptyIcon={Building2}
      columns={[
        { key: 'code', header: 'Code', render: (r) => <span className="mono cell-strong">{r.code}</span> },
        { key: 'name', header: 'Name', render: (r) => <span className="cell-strong">{r.name}</span> },
        { key: 'manager_id', header: 'Manager', render: (r) => nameOf(r.manager_id) },
      ]}
      fields={[
        { key: 'code', label: 'Department code', required: true, placeholder: 'ENG' },
        { key: 'name', label: 'Name', required: true, placeholder: 'Engineering' },
        {
          key: 'manager_id',
          label: 'Manager',
          type: 'select',
          numeric: true,
          nullable: true,
          full: true,
          options: userOptions,
          placeholder: userOptions.length ? 'Select a manager…' : 'No users yet',
        },
      ]}
    />
  )
}
