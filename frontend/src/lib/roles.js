/**
 * Module permissions → navigation config.
 *
 * The backend has no role column: each user carries four boolean flags
 * (`has_finance_access`, `has_scm_access`, `has_hr_access`, `has_dev_access`)
 * and every module router checks the matching flag. A user with all four is,
 * for display purposes, an administrator. User management itself lives in the
 * HR router, so the Users page is gated on HR access.
 */
import { LayoutDashboard, Wallet, Boxes, Users, LineChart, ShieldCheck } from 'lucide-react'

/** Module key → user flag. */
export const MODULE_FLAGS = {
  finance: 'has_finance_access',
  scm: 'has_scm_access',
  hr: 'has_hr_access',
  dev: 'has_dev_access',
}

export const MODULE_LABELS = {
  finance: 'Finance',
  scm: 'Purchases',
  hr: 'People & Payroll',
  dev: 'Dev Tracking',
}

/** Each item: which module flag unlocks it. `null` = every signed-in user. */
export const NAV_ITEMS = [
  { key: 'dashboard', label: 'Dashboard', path: '/', icon: LayoutDashboard, module: null },
  { key: 'dev', label: 'Dev Tracking', path: '/dev-tracking', icon: LineChart, module: 'dev' },
  { key: 'hr', label: 'People & Payroll', path: '/hr', icon: Users, module: 'hr' },
  { key: 'finance', label: 'Finance', path: '/finance', icon: Wallet, module: 'finance' },
  { key: 'scm', label: 'Purchases', path: '/scm', icon: Boxes, module: 'scm' },
  { key: 'users', label: 'Users & Access', path: '/admin/users', icon: ShieldCheck, module: 'hr' },
]

/** Does `user` hold the flag for `module`? `null` module is open to everyone. */
export function canAccess(user, module) {
  if (!user) return false
  if (module === null || module === undefined) return true
  const flag = MODULE_FLAGS[module]
  return flag ? !!user[flag] : false
}

export function navForUser(user) {
  return NAV_ITEMS.filter((item) => canAccess(user, item.module))
}

/** Modules the user can open, in a stable order. */
export function modulesFor(user) {
  return Object.keys(MODULE_FLAGS).filter((m) => canAccess(user, m))
}

export function isAdmin(user) {
  return !!user && Object.values(MODULE_FLAGS).every((flag) => !!user[flag])
}

/** Short human label for the sidebar chip: "Administrator", "Finance · HR", "Member". */
export function accessLabel(user) {
  if (!user) return ''
  if (isAdmin(user)) return 'Administrator'
  const mods = modulesFor(user).map((m) => MODULE_LABELS[m])
  if (!mods.length) return 'Member'
  if (mods.length > 2) return `${mods.length} modules`
  return mods.join(' · ')
}
