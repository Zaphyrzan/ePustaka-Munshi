import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { api, unwrap } from '../api/client'
import type { AuthSession } from '../types'

interface AuthContextValue {
  session: AuthSession | null
  loading: boolean
  login: (username: string, password: string) => Promise<AuthSession>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<AuthSession | null>(null)
  const [loading, setLoading] = useState(true)

  // Restore session from the Flask-Login cookie on first load
  useEffect(() => {
    unwrap<AuthSession>(api.get('/api/auth/me'))
      .then(setSession)
      .catch(() => setSession(null))
      .finally(() => setLoading(false))
  }, [])

  async function login(username: string, password: string) {
    const data = await unwrap<AuthSession>(
      api.post('/api/auth/login', { username, password, remember_me: true }),
    )
    setSession(data)
    return data
  }

  async function logout() {
    try {
      await api.post('/api/auth/logout')
    } finally {
      setSession(null)
    }
  }

  return (
    <AuthContext.Provider value={{ session, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
