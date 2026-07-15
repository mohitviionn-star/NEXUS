// Keeps track of login state. The access token lives only in memory (never
// saved to disk) - the refresh token lives in an httpOnly cookie we never
// touch directly; `authFetch` uses it automatically to recover from an
// expired access token instead of just failing.
import {
  createContext,
  useContext,
  useCallback,
  useEffect,
  useState,
  type ReactNode,
} from "react";

const API_BASE = "http://localhost:8000";


type AuthContextValue = {
  accessToken: string | null
  initializing: boolean
  login: (accessToken: string) => void
  logout: () => void
  authFetch: (path: string, options?: RequestInit) => Promise<Response>
}

const AuthContext = createContext<AuthContextValue | null>(null);

async function requestNewAccessToken(): Promise<string | null> {
  const response = await fetch(`${API_BASE}/api/v1/auth/refresh`, {
    method: 'POST',
    credentials: 'include', // send the httpOnly cookie even though it's a different port
  })
  if (!response.ok) return null
  const data = await response.json()
  return data.access_token
}


export function AuthProvider({ children }: { children: ReactNode }) {
  const [accessToken, setAccessToken] = useState<string | null>(null)
  const [initializing, setInitializing] = useState(true)

  // On first load, silently ask the backend "do I still have a valid
  // cookie?" instead of assuming we're logged out just because there's
  // nothing in memory yet.
  useEffect(() => {
    requestNewAccessToken()
      .then(setAccessToken)
      .finally(() => setInitializing(false))
  }, [])

  const login = (newAccessToken: string) => {
    setAccessToken(newAccessToken)
  }

  const logout = useCallback(() => {
    setAccessToken(null)
    fetch(`${API_BASE}/api/v1/auth/logout`, {
      method: 'POST',
      credentials: 'include',
    }).catch(() => {})
  }, [])

  // Makes an authenticated request. If the access token has expired (401),
  // silently trades the cookie for a new one and retries once.
  const authFetch = useCallback(
    async (path: string, options: RequestInit = {}) => {
      const attempt = (token: string | null) =>
        fetch(`${API_BASE}${path}`, {
          ...options,
          credentials: 'include',
          headers: { ...options.headers, Authorization: `Bearer ${token}` },
        })

      let response = await attempt(accessToken)

      if (response.status === 401) {
        const newAccessToken = await requestNewAccessToken()
        if (!newAccessToken) {
          setAccessToken(null)
          throw new Error('Session expired')
        }
        setAccessToken(newAccessToken)
        response = await attempt(newAccessToken)
      }

      return response
    },
    [accessToken],
  )

  return (
    <AuthContext.Provider value={{ accessToken, initializing, login, logout, authFetch }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}
