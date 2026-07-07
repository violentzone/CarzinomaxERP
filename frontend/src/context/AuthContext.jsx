/* eslint-disable react-refresh/only-export-components -- provider + useAuth hook are intentionally colocated */
/**
 * Authentication context: holds the JWT + current user, exposes login/logout,
 * and a `hasRole` helper. The token persists in localStorage; on mount (or when
 * a token exists) we hydrate the user from `GET /auth/me`.
 */
import { createContext, useContext, useEffect, useState, useCallback } from 'react'
import { authApi } from '../api/auth'
import { getToken, setToken, ApiError } from '../lib/api'

const AuthContext = createContext(null)

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
      setUser(me)
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

  const login = useCallback(async (email, password) => {
    const { access_token } = await authApi.login(email, password)
    setToken(access_token)
    const me = await authApi.me()
    setUser(me)
    return me
  }, [])

  const logout = useCallback(() => {
    setToken(null)
    setUser(null)
  }, [])

  const hasRole = useCallback(
    (roles) => {
      if (!user) return false
      if (user.role === 'admin') return true
      if (!roles) return true
      return roles.includes(user.role)
    },
    [user],
  )

  const value = {
    user,
    loading,
    isAuthenticated: !!user,
    login,
    logout,
    hasRole,
    reload: loadUser,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within <AuthProvider>')
  return ctx
}
