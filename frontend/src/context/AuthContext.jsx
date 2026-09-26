/* eslint-disable react-refresh/only-export-components -- provider + useAuth hook are intentionally colocated */
/**
 * Authentication context: holds the JWT + current user, exposes login/logout
 * and a `can(module)` helper. The token persists in localStorage; on mount (or
 * when a token exists) we hydrate the user from `GET /auth/me`. Any 401 from
 * the API (expired or revoked token) signs the user out.
 */
import { createContext, useContext, useEffect, useState, useCallback } from 'react'
import { authApi } from '../api/auth'
import { getToken, setToken, ApiError, UNAUTHORIZED_EVENT } from '../lib/api'
import { canAccess, isAdmin } from '../lib/roles'

const AuthContext = createContext(null)

/** Never keep the password hash around on the client, even if the API sends it. */
function sanitize(user) {
  if (!user) return null
  // eslint-disable-next-line no-unused-vars
  const { hashed_password, ...rest } = user
  return rest
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  const loadUser = useCallback(async () => {
    if (!getToken()) {
      setUser(null)
      setLoading(false)
      return
    }
    try {
      const me = await authApi.me()
      setUser(sanitize(me))
    } catch (err) {
      // A bad/expired token surfaces here — drop it so the app shows login.
      if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
        setToken(null)
      }
      setUser(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    // Bootstrap the session on mount — legitimately sets state as it loads.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadUser()
  }, [loadUser])

  // Token rejected mid-session (expired, or revoked by a logout elsewhere).
  useEffect(() => {
    const onUnauthorized = () => {
      setToken(null)
      setUser(null)
    }
    window.addEventListener(UNAUTHORIZED_EVENT, onUnauthorized)
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, onUnauthorized)
  }, [])

  const login = useCallback(async (email, password) => {
    const token = await authApi.login(email, password)
    setToken(token)
    try {
      const me = sanitize(await authApi.me())
      setUser(me)
      return me
    } catch (err) {
      setToken(null)
      throw err
    }
  }, [])

  const logout = useCallback(async () => {
    try {
      // Revokes every token issued before now, on every device.
      if (getToken()) await authApi.logout()
    } catch {
      // Already signed out server-side (or offline) — clear locally regardless.
    } finally {
      setToken(null)
      setUser(null)
    }
  }, [])

  const can = useCallback((module) => canAccess(user, module), [user])

  const value = {
    user,
    loading,
    isAuthenticated: !!user,
    isAdmin: isAdmin(user),
    login,
    logout,
    can,
    reload: loadUser,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within <AuthProvider>')
  return ctx
}
