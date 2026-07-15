// Keeps track of whether we're logged in (the JWT "access pass"), and shares
// that across every page in the app without passing it around by hand.
import { createContext, useContext, useState, type ReactNode } from 'react'

type AuthContextValue = {
  token: string | null
  login: (token: string) => void
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  // Restore the token from the browser's storage on page load, so refreshing
  // the page doesn't log you out.
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('nexus_token'))

  const login = (newToken: string) => {
    localStorage.setItem('nexus_token', newToken)
    setToken(newToken)
  }

  const logout = () => {
    localStorage.removeItem('nexus_token')
    setToken(null)
  }

  return <AuthContext.Provider value={{ token, login, logout }}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used inside AuthProvider')
  return context
}
