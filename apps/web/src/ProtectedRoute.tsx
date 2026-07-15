// Blocks a page from showing unless we're logged in - sends you to the
// login screen instead if there's no access pass.
import type { ReactNode } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from './AuthContext'

export default function ProtectedRoute({ children }: { children: ReactNode }) {
  const { accessToken, initializing } = useAuth()

  // Still checking the cookie for a valid session - don't redirect yet,
  // or a logged-in user would flash to the login page on every reload.
  if (initializing) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-400">
        Loading...
      </div>
    )
  }

  if (!accessToken) return <Navigate to="/login" replace />
  return children
}

