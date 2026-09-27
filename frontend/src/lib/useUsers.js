import { useList } from './useList'
import { hrApi } from '../api/hr'
import { userName } from './format'

/**
 * Users double as the employee directory. This hook loads them once per
 * section and exposes lookup helpers for <select> options and table cells.
 */
export function useUsers() {
  const { rows, loading, denied, error, reload } = useList(() => hrApi.listUsers())
  const userMap = Object.fromEntries(rows.map((u) => [String(u.id), u]))
  const activeUsers = rows.filter((u) => u.is_active)
  const userOptions = [...rows]
    .sort((a, b) => Number(b.is_active) - Number(a.is_active) || userName(a).localeCompare(userName(b)))
    .map((u) => ({ value: String(u.id), label: u.is_active ? userName(u) : `${userName(u)} (inactive)` }))

  /** Display name for a user id; falls back to `#id`. */
  const nameOf = (id) => {
    if (id === null || id === undefined || id === '') return '—'
    const u = userMap[String(id)]
    return u ? userName(u) : `#${id}`
  }

  return { users: rows, activeUsers, userMap, userOptions, nameOf, loading, denied, error, reload }
}
