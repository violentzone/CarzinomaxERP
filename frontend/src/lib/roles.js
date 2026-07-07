/**
 * Role → navigation config. Mirrors the backend RoleChecker gates:
 * finance→finance router, scm→scm, hr→hr, developer→dev-tracking. `admin`
 * bypasses every gate, so admin sees all modules.
 */
import {
  LayoutDashboard,
  Wallet,
  Boxes,
  Users,
  LineChart,
  ShieldCheck,
} from 'lucide-react'

/** Each item: which roles (besides admin) may access it. `null` = everyone. */
export const NAV_ITEMS = [
  { key: 'dashboard', label: 'Dashboard', path: '/', icon: LayoutDashboard, roles: null },
  { key: 'finance', label: 'Finance', path: '/finance', icon: Wallet, roles: ['finance'] },
  { key: 'scm', label: 'Supply Chain', path: '/scm', icon: Boxes, roles: ['scm'] },
  { key: 'hr', label: 'People', path: '/hr', icon: Users, roles: ['hr'] },
  { key: 'dev', label: 'Dev Tracking', path: '/dev-tracking', icon: LineChart, roles: ['developer'] },
  { key: 'users', label: 'Users', path: '/admin/users', icon: ShieldCheck, roles: [] }, // admin-only
]

/** Does `role` satisfy an item's `roles` requirement? admin always passes. */
export function canAccess(role, requiredRoles) {
  if (role === 'admin') return true
  if (requiredRoles === null) return true // open to all authenticated users
  return requiredRoles.includes(role)
}

export function navForRole(role) {
  return NAV_ITEMS.filter((item) => canAccess(role, item.roles))
}

export const ROLE_LABELS = {
  admin: 'Administrator',
  finance: 'Finance',
  scm: 'Supply Chain',
  hr: 'People Ops',
  developer: 'Developer',
  employee: 'Employee',
}
