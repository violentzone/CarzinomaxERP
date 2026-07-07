import { useEffect, useState } from 'react'
import { ApiError } from './api'

/**
 * Load a list from an async fetcher with loading / error / 403 handling.
 *
 * A 403 here means the current role lacks access to the module endpoint — we
 * surface it as `denied` so the page can render <AccessDenied> instead of the
 * table (and we do NOT log the user out). `reload()` bumps an internal tick to
 * re-run the effect; the effect re-reads the latest `fetcher`/`deps` closure.
 *
 * @param {Function} fetcher async () => rows
 * @param {Array} deps re-run when these change
 * @returns {{rows, loading, error, denied, reload, setRows}}
 */
export function useList(fetcher, deps = []) {
  const [rows, setRows] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [denied, setDenied] = useState(false)
  const [tick, setTick] = useState(0)

  const reload = () => setTick((t) => t + 1)

  useEffect(() => {
    let alive = true
    // Kicking off a fetch on mount / deps change is the intended use of an effect.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoading(true)
    fetcher()
      .then((data) => {
        if (!alive) return
        setRows(Array.isArray(data) ? data : [])
        setDenied(false)
        setError(null)
      })
      .catch((err) => {
        if (!alive) return
        if (err instanceof ApiError && err.status === 403) setDenied(true)
        else setError(err?.detail || err?.message || 'Failed to load')
        setRows([])
      })
      .finally(() => {
        if (alive) setLoading(false)
      })
    return () => {
      alive = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tick, ...deps])

  return { rows, loading, error, denied, reload, setRows }
}
